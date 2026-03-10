from datetime import date as Date, datetime
from urllib.parse import urlencode
from decimal import Decimal

from django.contrib.auth.decorators import login_required
from django.core.paginator import Paginator
from django.db import transaction
from django.db.models import Count
from django.http import HttpResponse, HttpResponseForbidden
from django.shortcuts import get_object_or_404, redirect, render
from django.template.loader import render_to_string
from django.urls import reverse
from django.utils.html import format_html

from ..forms import PedidoForm, PedidoItemForm, PedidoNovoOrcamentoForm
from ..models import (
    Cliente,
    ConfiguracaoEmpresa,
    Divisor,
    Pedido,
    PedidoItem,
    Perfil,
    PerfilPuxador,
    Puxador,
    VidroBase,
)
from ..services.orcamento import calc_total
from ..services import producao as svc_producao
from ..views_base import _get_perms, _sem_permissao


# ── helpers ───────────────────────────────────────────────────────────────────

def _adicional_pairs(form):
    """Retorna lista de (val_field, obs_field) para os 4 slots de adicional."""
    return [
        (form["adicional_valor"],  form["adicional_obs"]),
        (form["adicional2_valor"], form["adicional2_obs"]),
        (form["adicional3_valor"], form["adicional3_obs"]),
        (form["adicional4_valor"], form["adicional4_obs"]),
    ]


def _ctx_item_form(form, pedido=None):
    ctx = {"form": form, "adicional_pairs": _adicional_pairs(form)}
    if pedido:
        ctx["pedido"] = pedido
    return ctx


def _itens_e_total(pedido):
    itens = list(pedido.itens.select_related(
        "perfil", "acabamento", "perfil_puxador", "puxador", "divisor", "vidro"
    ).all())
    total = sum(item.valor_total for item in itens)
    return itens, total


def _resp_atualiza_tabela(request, pedido):
    """Resposta HTMX: atualiza tabela de itens + resumo lateral + fecha modal."""
    itens, total = _itens_e_total(pedido)
    tabela_html = render_to_string(
        "portas/pedido/_itens_tabela.html",
        {"pedido": pedido, "itens": itens},
        request=request,
    )
    oob_tabela = f'<div hx-swap-oob="innerHTML:#tabelaItens">{tabela_html}</div>'
    oob_resumo = (
        '<div hx-swap-oob="innerHTML:#resumoPedido">'
        '<div class="d-flex justify-content-between fw-semibold fs-5">'
        f'<span>Total</span><span>R$\xa0{total:,.2f}</span>'
        '</div></div>'
    )
    resp = HttpResponse(oob_tabela + oob_resumo)
    resp["HX-Trigger"] = "fecharModalCadastro"
    return resp


# ── Lista ──────────────────────────────────────────────────────────────────────

_PER_PAGE_OPCOES = [10, 20, 50, 100]


@login_required
def pedidos_lista(request):
    if not _get_perms(request.user)["pedidos"]["ver"]:
        return _sem_permissao("Você não tem permissão para visualizar pedidos.")

    q        = (request.GET.get("q") or "").strip()
    data_de  = (request.GET.get("data_de") or "").strip()
    data_ate = (request.GET.get("data_ate") or "").strip()
    try:
        per_page = int(request.GET.get("per_page", 20))
        if per_page not in _PER_PAGE_OPCOES:
            per_page = 20
    except (ValueError, TypeError):
        per_page = 20

    qs = Pedido.objects.select_related("cliente", "usuario").order_by("-id")

    if q:
        if q.isdigit():
            qs = qs.filter(id=int(q))
        else:
            qs = (qs.filter(cliente__nome__icontains=q) |
                  qs.filter(cliente__codigo__icontains=q))

    if data_de:
        try:
            qs = qs.filter(data__gte=datetime.strptime(data_de, "%Y-%m-%d").date())
        except ValueError:
            data_de = ""

    if data_ate:
        try:
            qs = qs.filter(data__lte=datetime.strptime(data_ate, "%Y-%m-%d").date())
        except ValueError:
            data_ate = ""

    paginator = Paginator(qs, per_page)
    try:
        page_num = int(request.GET.get("page", 1))
    except (ValueError, TypeError):
        page_num = 1
    page_obj = paginator.get_page(page_num)

    ctx = {
        "pedidos": page_obj,
        "page_obj": page_obj,
        "q": q,
        "data_de": data_de,
        "data_ate": data_ate,
        "per_page": per_page,
        "per_page_opcoes": _PER_PAGE_OPCOES,
    }

    if request.headers.get("HX-Request") == "true":
        return render(request, "portas/pedido/_pedido_tabela.html", ctx)
    return render(request, "portas/pedido/pedido_lista.html", ctx)


# ── Rascunho de pedido (sessão) ────────────────────────────────────────────────

_SESSION_KEY = "pedido_rascunho_itens"


def _total_rascunho(itens):
    return sum(Decimal(i["valor_total"]) for i in itens)


def _resp_atualiza_rascunho(request, itens):
    """Retorna tabela de rascunho atualizada + OOB de total + fecha modal."""
    total = _total_rascunho(itens)
    tabela_html = render_to_string(
        "portas/pedido/_itens_rascunho.html",
        {"itens": itens},
        request=request,
    )
    oob_tabela = f'<div hx-swap-oob="innerHTML:#tabelaRascunho">{tabela_html}</div>'
    oob_resumo = (
        '<div hx-swap-oob="innerHTML:#resumoRascunho">'
        '<div class="d-flex justify-content-between fw-semibold fs-5">'
        f"<span>Total</span><span>R$\xa0{total:,.2f}</span>"
        "</div></div>"
    )
    resp = HttpResponse(oob_tabela + oob_resumo)
    resp["HX-Trigger"] = "fecharModalCadastro"
    return resp


# ── Novo pedido ────────────────────────────────────────────────────────────────

@login_required
def pedido_novo(request):
    if not _get_perms(request.user)["pedidos"]["criar"]:
        return _sem_permissao("Você não tem permissão para criar pedidos.")
    if request.method == "POST":
        cliente_id = request.POST.get("cliente", "").strip()
        itens = request.session.get(_SESSION_KEY, [])
        total = _total_rascunho(itens)

        # Validação simples
        cliente_display = ""
        erro_cliente = not cliente_id
        erro_itens = not itens

        if cliente_id:
            try:
                c = Cliente.objects.get(pk=cliente_id)
                cliente_display = f"{c.codigo} – {c.nome}"
            except Cliente.DoesNotExist:
                erro_cliente = True
                cliente_id = ""

        if erro_cliente or erro_itens:
            return render(request, "portas/pedido/pedido_novo.html", {
                "itens": itens,
                "total": total,
                "cliente_id": cliente_id,
                "cliente_display": cliente_display,
                "erro_cliente": erro_cliente,
                "erro_itens": erro_itens,
            })

        obs = request.POST.get("observacoes", "").strip() or None
        with transaction.atomic():
            pedido = Pedido.objects.create(cliente=c, usuario=request.user, observacoes=obs)
            for item_data in itens:
                PedidoItem.objects.create(
                    pedido=pedido,
                    largura_mm=item_data["largura_mm"],
                    altura_mm=item_data["altura_mm"],
                    quantidade=item_data["quantidade"],
                    acabamento_id=item_data["acabamento_id"],
                    perfil_id=item_data["perfil_id"],
                    perfil_puxador_id=item_data.get("perfil_puxador_id"),
                    qtd_perfil_puxador=item_data.get("qtd_perfil_puxador"),
                    puxador_id=item_data.get("puxador_id"),
                    qtd_puxador=item_data.get("qtd_puxador"),
                    puxador_tamanho_mm=item_data.get("puxador_tamanho_mm"),
                    divisor_id=item_data.get("divisor_id"),
                    qtd_divisor=item_data.get("qtd_divisor"),
                    divisor_altura_1=item_data.get("divisor_altura_1"),
                    divisor_altura_2=item_data.get("divisor_altura_2"),
                    puxador_sobreposto=item_data.get("puxador_sobreposto", True),
                    vidro_id=item_data.get("vidro_id"),
                    adicional_valor=item_data.get("adicional_valor") or None,
                    adicional_obs=item_data.get("adicional_obs") or "",
                    adicional2_valor=item_data.get("adicional2_valor") or None,
                    adicional2_obs=item_data.get("adicional2_obs") or "",
                    adicional3_valor=item_data.get("adicional3_valor") or None,
                    adicional3_obs=item_data.get("adicional3_obs") or "",
                    adicional4_valor=item_data.get("adicional4_valor") or None,
                    adicional4_obs=item_data.get("adicional4_obs") or "",
                    valor_unitario=Decimal(item_data["valor_unitario"]),
                    valor_total=Decimal(item_data["valor_total"]),
                )

        request.session.pop(_SESSION_KEY, None)
        return redirect("pedido_detalhe", pk=pedido.pk)

    # GET: limpa rascunho e exibe a página de novo pedido
    request.session[_SESSION_KEY] = []
    return render(request, "portas/pedido/pedido_novo.html", {
        "itens": [],
        "total": Decimal("0"),
    })


@login_required
def pedido_item_temp_add(request):
    if not _get_perms(request.user)["pedidos"]["criar"]:
        return _sem_permissao()
    if request.method == "POST":
        form = PedidoItemForm(request.POST)
        if form.is_valid():
            cd = form.cleaned_data
            perfil = cd["perfil"]
            pp = cd.get("perfil_puxador")
            pux = cd.get("puxador")
            divisor = cd.get("divisor")
            vidro = cd.get("vidro")
            qtd_pp = int(cd.get("qtd_perfil_puxador") or 0)
            qtd_pux = int(cd.get("qtd_puxador") or 0)
            pux_tam = cd.get("puxador_tamanho_mm") or 0
            pux_sobreposto = cd.get("puxador_sobreposto", True)
            qtd_div = int(cd.get("qtd_divisor") or 0)
            div_alt_1 = cd.get("divisor_altura_1") or None
            div_alt_2 = cd.get("divisor_altura_2") or None
            qtd = cd["quantidade"]
            adicional = sum(
                cd.get(k) or Decimal("0")
                for k in ("adicional_valor", "adicional2_valor", "adicional3_valor", "adicional4_valor")
            )
            config = ConfiguracaoEmpresa.get()

            valor_unit = calc_total(
                preco_perfil_m=perfil.preco,
                largura_mm=cd["largura_mm"],
                altura_mm=cd["altura_mm"],
                preco_pp_m=(pp.preco if pp else None),
                qtd_pp=(qtd_pp or None),
                preco_puxador_m=(pux.preco if pux else None),
                qtd_puxador=(qtd_pux or None),
                puxador_tamanho_mm=(pux_tam or None),
                preco_divisor_m=(divisor.preco if divisor else None),
                qtd_divisor=(qtd_div or None),
                preco_vidro_m2=(vidro.preco if vidro else None),
                custo_mao_obra=(config.custo_mao_obra if config.custo_mao_obra else None),
            ) + adicional

            # Monta a descrição: Porta modelo1/modelo2 Acabamento LxA Vidro
            modelos = [m for m in [
                perfil.modelo,
                pp.modelo if pp else None,
                pux.modelo if pux else None,
                divisor.modelo if divisor else None,
            ] if m]
            descricao = "Porta " + "/".join(modelos)
            descricao += " " + cd["acabamento"].nome
            descricao += " " + f"{cd['largura_mm']}×{cd['altura_mm']}"
            if vidro:
                descricao += " " + vidro.descricao

            item_data = {
                "descricao": descricao,
                "largura_mm": cd["largura_mm"],
                "altura_mm": cd["altura_mm"],
                "quantidade": qtd,
                "acabamento_id": cd["acabamento"].pk,
                "perfil_id": perfil.pk,
                "perfil_puxador_id": pp.pk if pp else None,
                "qtd_perfil_puxador": qtd_pp or None,
                "puxador_id": pux.pk if pux else None,
                "qtd_puxador": qtd_pux or None,
                "puxador_tamanho_mm": pux_tam or None,
                "puxador_sobreposto": pux_sobreposto,
                "divisor_id": divisor.pk if divisor else None,
                "qtd_divisor": qtd_div or None,
                "divisor_altura_1": div_alt_1,
                "divisor_altura_2": div_alt_2,
                "vidro_id": vidro.pk if vidro else None,
                "adicional_valor":  f"{cd.get('adicional_valor') or 0:.2f}" if cd.get("adicional_valor") else None,
                "adicional_obs":    cd.get("adicional_obs") or "",
                "adicional2_valor": f"{cd.get('adicional2_valor') or 0:.2f}" if cd.get("adicional2_valor") else None,
                "adicional2_obs":   cd.get("adicional2_obs") or "",
                "adicional3_valor": f"{cd.get('adicional3_valor') or 0:.2f}" if cd.get("adicional3_valor") else None,
                "adicional3_obs":   cd.get("adicional3_obs") or "",
                "adicional4_valor": f"{cd.get('adicional4_valor') or 0:.2f}" if cd.get("adicional4_valor") else None,
                "adicional4_obs":   cd.get("adicional4_obs") or "",
                "valor_unitario": f"{valor_unit:.2f}",
                "valor_total": f"{valor_unit * Decimal(qtd):.2f}",
            }
            # Monta adicionais_list p/ compatibilidade com o template (igual à property do modelo)
            item_data["adicionais_list"] = [
                (v, o) for v, o in [
                    (item_data["adicional_valor"],  item_data["adicional_obs"]),
                    (item_data["adicional2_valor"], item_data["adicional2_obs"]),
                    (item_data["adicional3_valor"], item_data["adicional3_obs"]),
                    (item_data["adicional4_valor"], item_data["adicional4_obs"]),
                ] if v
            ]

            itens = request.session.get(_SESSION_KEY, [])
            itens.append(item_data)
            request.session[_SESSION_KEY] = itens
            request.session.modified = True

            return _resp_atualiza_rascunho(request, itens)

        return render(request, "portas/pedido/item_form.html", _ctx_item_form(form))

    form = PedidoItemForm()
    return render(request, "portas/pedido/item_form.html", _ctx_item_form(form))


@login_required
def pedido_item_temp_remove(request, idx):
    if not _get_perms(request.user)["pedidos"]["criar"]:
        return _sem_permissao()
    itens = request.session.get(_SESSION_KEY, [])
    if 0 <= idx < len(itens):
        itens.pop(idx)
        request.session[_SESSION_KEY] = itens
        request.session.modified = True
    return _resp_atualiza_rascunho(request, itens)


# ── Detalhe do pedido ─────────────────────────────────────────────────────────

@login_required
def pedido_detalhe(request, pk):
    if not _get_perms(request.user)["pedidos"]["ver"]:
        return _sem_permissao("Você não tem permissão para visualizar pedidos.")
    pedido = get_object_or_404(Pedido.objects.select_related("cliente"), pk=pk)
    itens, total = _itens_e_total(pedido)
    return render(request, "portas/pedido/pedido_detalhe.html", {
        "pedido": pedido,
        "itens": itens,
        "total_pedido": total,
        "obs_salva": request.GET.get("obs_salva") == "1",
    })


# ── Duplicar pedido ──────────────────────────────────────────────────────────

@login_required
def pedido_duplicar(request, pk):
    if not _get_perms(request.user)["pedidos"]["editar"]:
        return _sem_permissao("Você não tem permissão para criar pedidos.")
    original = get_object_or_404(
        Pedido.objects.select_related("cliente").prefetch_related("itens"),
        pk=pk,
    )
    novo = Pedido.objects.create(
        cliente=original.cliente,
        usuario=request.user,
        observacoes=original.observacoes,
        status="aberto",
    )
    for item in original.itens.all():
        PedidoItem.objects.create(
            pedido=novo,
            largura_mm=item.largura_mm,
            altura_mm=item.altura_mm,
            quantidade=item.quantidade,
            acabamento=item.acabamento,
            perfil=item.perfil,
            perfil_puxador=item.perfil_puxador,
            qtd_perfil_puxador=item.qtd_perfil_puxador,
            puxador=item.puxador,
            qtd_puxador=item.qtd_puxador,
            puxador_tamanho_mm=item.puxador_tamanho_mm,
            puxador_sobreposto=item.puxador_sobreposto,
            vidro=item.vidro,
            divisor=item.divisor,
            qtd_divisor=item.qtd_divisor,
            divisor_altura_1=item.divisor_altura_1,
            divisor_altura_2=item.divisor_altura_2,
            adicional_valor=item.adicional_valor,
            adicional_obs=item.adicional_obs,
            adicional2_valor=item.adicional2_valor,
            adicional2_obs=item.adicional2_obs,
            adicional3_valor=item.adicional3_valor,
            adicional3_obs=item.adicional3_obs,
            adicional4_valor=item.adicional4_valor,
            adicional4_obs=item.adicional4_obs,
            valor_unitario=item.valor_unitario,
            valor_total=item.valor_total,
        )
    return redirect("pedido_detalhe", pk=novo.pk)


# ── Observações do pedido ────────────────────────────────────────────────────

@login_required
def pedido_observacoes(request, pk):
    if not _get_perms(request.user)["pedidos"]["editar"]:
        return _sem_permissao()
    pedido = get_object_or_404(Pedido, pk=pk)
    if request.method == "POST":
        pedido.observacoes = request.POST.get("observacoes", "").strip() or None
        pedido.save(update_fields=["observacoes"])
    return redirect(reverse("pedido_detalhe", args=[pk]) + "?obs_salva=1")


# ── Enviar pedido para Wise (integração Bimer) ────────────────────────────────

@login_required
def pedido_enviar_wise(request, pk):
    if not _get_perms(request.user)["producao"]["alterar_status"]:
        return _sem_permissao("Você não tem permissão para alterar o status de pedidos.")
    pedido = get_object_or_404(Pedido.objects.select_related("cliente"), pk=pk)

    if request.method == "POST":
        if pedido.status == "wise":
            return HttpResponse(
                '<div class="alert alert-warning m-3">Pedido já está com status Wise.</div>',
                status=400,
            )

        from ..models import BimerConfig
        from ..services import bimer as svc_bimer

        config = BimerConfig.get()
        ok, msg = svc_bimer.enviar_pedido_bimer(config, pedido)

        if not ok:
            return render(request, "portas/pedido/_confirm_wise.html", {
                "pedido": pedido,
                "erro": msg,
            })

        pedido.status = "wise"
        pedido.save(update_fields=["status"])

        qs = Pedido.objects.select_related("cliente", "usuario").order_by("-id")
        resp = HttpResponse(
            render_to_string("portas/pedido/_pedido_tabela.html", {"pedidos": qs}, request=request)
        )
        resp["HX-Trigger"] = "fecharModalCadastro"
        return resp

    return render(request, "portas/pedido/_confirm_wise.html", {"pedido": pedido})


# ── Reabrir pedido ───────────────────────────────────────────────────────────

@login_required
def pedido_reabrir(request, pk):
    if not _get_perms(request.user)["producao"]["alterar_status"]:
        return _sem_permissao("Você não tem permissão para alterar o status de pedidos.")
    pedido = get_object_or_404(Pedido.objects.select_related("cliente"), pk=pk)

    if request.method == "POST":
        if pedido.status in ("wise", "concluido"):
            return HttpResponse(
                '<div class="alert alert-danger m-3">Pedidos Wise ou Concluídos não podem ser reabertos.</div>',
                status=403,
            )
        if pedido.status == "aberto":
            return HttpResponse(
                '<div class="alert alert-warning m-3">Pedido já está aberto.</div>',
                status=400,
            )
        pedido.status = "aberto"
        pedido.save(update_fields=["status"])
        qs = Pedido.objects.select_related("cliente", "usuario").order_by("-id")
        resp = HttpResponse(
            render_to_string("portas/pedido/_pedido_tabela.html", {"pedidos": qs}, request=request)
        )
        resp["HX-Trigger"] = "fecharModalCadastro"
        return resp

    return render(request, "portas/pedido/_confirm_reabrir.html", {"pedido": pedido})


# ── Excluir pedido ───────────────────────────────────────────────────────────

@login_required
def pedido_excluir(request, pk):
    if not _get_perms(request.user)["pedidos"]["excluir"]:
        return _sem_permissao("Você não tem permissão para excluir pedidos.")
    pedido = get_object_or_404(Pedido.objects.select_related("cliente"), pk=pk)

    if request.method == "POST":
        if pedido.status != "aberto":
            return HttpResponse(
                '<div class="alert alert-danger m-3">Só é permitido excluir pedidos com status <strong>Aberto</strong>.</div>',
                status=400,
            )
        pedido.delete()
        qs = Pedido.objects.select_related("cliente", "usuario").order_by("-id")
        resp = HttpResponse(
            render_to_string("portas/pedido/_pedido_tabela.html", {"pedidos": qs}, request=request)
        )
        resp["HX-Trigger"] = "fecharModalCadastro"
        return resp

    # GET → carrega modal de confirmação
    return render(request, "portas/pedido/_confirm_excluir.html", {"pedido": pedido})


# ── Cancelar pedido ──────────────────────────────────────────────────────────

@login_required
def pedido_cancelar(request, pk):
    if not _get_perms(request.user)["pedidos"]["excluir"]:
        return _sem_permissao("Você não tem permissão para cancelar pedidos.")
    pedido = get_object_or_404(Pedido.objects.select_related("cliente"), pk=pk)

    if request.method == "POST":
        if pedido.status in ("wise", "concluido"):
            return HttpResponse(
                '<div class="alert alert-danger m-3">Pedidos Wise ou Concluídos não podem ser cancelados.</div>',
                status=403,
            )
        if pedido.status == "cancelado":
            return HttpResponse(
                '<div class="alert alert-warning m-3">Pedido já está cancelado.</div>',
                status=400,
            )
        pedido.status = "cancelado"
        pedido.save(update_fields=["status"])
        qs = Pedido.objects.select_related("cliente", "usuario").order_by("-id")
        resp = HttpResponse(
            render_to_string("portas/pedido/_pedido_tabela.html", {"pedidos": qs}, request=request)
        )
        resp["HX-Trigger"] = "fecharModalCadastro"
        return resp

    # GET → carrega modal de confirmação
    return render(request, "portas/pedido/_confirm_cancelar.html", {"pedido": pedido})


# ── Imprimir pedido ───────────────────────────────────────────────────────────

_ITENS_PG1 = 6   # itens na 1ª página (tem cabeçalho + cliente + rodapé)
_ITENS_PGN = 9   # itens nas páginas seguintes


def _paginar(itens):
    """Divide a lista de itens em sub-listas para cada página A5."""
    lista = list(itens)
    if not lista:
        return [[]]
    paginas = [lista[:_ITENS_PG1]]
    lista = lista[_ITENS_PG1:]
    while lista:
        paginas.append(lista[:_ITENS_PGN])
        lista = lista[_ITENS_PGN:]
    return paginas


@login_required
def pedido_imprimir(request, pk):
    if not _get_perms(request.user)["pedidos"]["ver"]:
        return _sem_permissao("Você não tem permissão para visualizar pedidos.")
    pedido = get_object_or_404(Pedido.objects.select_related("cliente"), pk=pk)
    itens, total = _itens_e_total(pedido)
    return render(request, "portas/pedido/pedido_imprimir.html", {
        "pedido": pedido,
        "paginas": _paginar(itens),
        "total_pedido": total,
    })


# ── Adicionar item ────────────────────────────────────────────────────────────

@login_required
def pedido_item_novo(request, pedido_pk):
    if not _get_perms(request.user)["pedidos"]["editar"]:
        return _sem_permissao("Você não tem permissão para editar pedidos.")
    pedido = get_object_or_404(Pedido, pk=pedido_pk)
    if pedido.status != "aberto":
        return HttpResponseForbidden("Itens só podem ser adicionados a pedidos em aberto.")

    if request.method == "POST":
        form = PedidoItemForm(request.POST)
        if form.is_valid():
            cd = form.cleaned_data
            perfil = cd["perfil"]
            pp = cd.get("perfil_puxador")
            pux = cd.get("puxador")
            divisor = cd.get("divisor")
            vidro = cd.get("vidro")
            qtd_pp = int(cd.get("qtd_perfil_puxador") or 0)
            qtd_pux = int(cd.get("qtd_puxador") or 0)
            pux_tam = cd.get("puxador_tamanho_mm") or 0
            pux_sobreposto = cd.get("puxador_sobreposto", True)
            qtd_div = int(cd.get("qtd_divisor") or 0)
            div_alt_1 = cd.get("divisor_altura_1") or None
            div_alt_2 = cd.get("divisor_altura_2") or None
            qtd = cd["quantidade"]
            adicional = sum(
                cd.get(k) or Decimal("0")
                for k in ("adicional_valor", "adicional2_valor", "adicional3_valor", "adicional4_valor")
            )
            config = ConfiguracaoEmpresa.get()

            valor_unit = calc_total(
                preco_perfil_m=perfil.preco,
                largura_mm=cd["largura_mm"],
                altura_mm=cd["altura_mm"],
                preco_pp_m=(pp.preco if pp else None),
                qtd_pp=(qtd_pp or None),
                preco_puxador_m=(pux.preco if pux else None),
                qtd_puxador=(qtd_pux or None),
                puxador_tamanho_mm=(pux_tam or None),
                preco_divisor_m=(divisor.preco if divisor else None),
                qtd_divisor=(qtd_div or None),
                preco_vidro_m2=(vidro.preco if vidro else None),
                custo_mao_obra=(config.custo_mao_obra if config.custo_mao_obra else None),
            ) + adicional

            PedidoItem.objects.create(
                pedido=pedido,
                largura_mm=cd["largura_mm"],
                altura_mm=cd["altura_mm"],
                quantidade=qtd,
                acabamento=cd["acabamento"],
                perfil=perfil,
                perfil_puxador=pp,
                qtd_perfil_puxador=(qtd_pp or None),
                puxador=pux,
                qtd_puxador=(qtd_pux or None),
                puxador_tamanho_mm=(pux_tam or None),
                puxador_sobreposto=pux_sobreposto,
                divisor=divisor,
                qtd_divisor=(qtd_div or None),
                divisor_altura_1=div_alt_1,
                divisor_altura_2=div_alt_2,
                vidro=vidro,
                adicional_valor=(cd.get("adicional_valor") or None),
                adicional_obs=cd.get("adicional_obs") or "",
                adicional2_valor=(cd.get("adicional2_valor") or None),
                adicional2_obs=cd.get("adicional2_obs") or "",
                adicional3_valor=(cd.get("adicional3_valor") or None),
                adicional3_obs=cd.get("adicional3_obs") or "",
                adicional4_valor=(cd.get("adicional4_valor") or None),
                adicional4_obs=cd.get("adicional4_obs") or "",
                valor_unitario=valor_unit,
                valor_total=(valor_unit * Decimal(qtd)),
            )

            return _resp_atualiza_tabela(request, pedido)

        return render(request, "portas/pedido/item_form.html", _ctx_item_form(form, pedido))

    form = PedidoItemForm()
    return render(request, "portas/pedido/item_form.html", _ctx_item_form(form, pedido))


# ── Remover item ──────────────────────────────────────────────────────────────

@login_required
def htmx_remove_item(request, pedido_pk, item_pk):
    if not _get_perms(request.user)["pedidos"]["editar"]:
        return _sem_permissao("Você não tem permissão para editar pedidos.")
    pedido = get_object_or_404(Pedido, pk=pedido_pk)
    if pedido.status != "aberto":
        return HttpResponseForbidden("Itens só podem ser removidos de pedidos em aberto.")
    PedidoItem.objects.filter(pk=item_pk, pedido=pedido).delete()
    return _resp_atualiza_tabela(request, pedido)


# ── Cálculo em tempo real ─────────────────────────────────────────────────────

@login_required
def htmx_calcular_item(request):
    _tmpl = "portas/pedido/_resumo_calculo.html"
    try:
        largura = int(request.GET.get("largura_mm") or 0)
        altura = int(request.GET.get("altura_mm") or 0)
        qtd = int(request.GET.get("quantidade") or 1)
        perfil_id = request.GET.get("perfil")

        if not perfil_id or not largura or not altura:
            return render(request, _tmpl, {"erro": "Preencha largura, altura e selecione o perfil."})

        perfil = Perfil.objects.filter(pk=perfil_id).first()
        if not perfil:
            return render(request, _tmpl, {"erro": "Perfil não encontrado."})

        pp_id = request.GET.get("perfil_puxador")
        qtd_pp = int(request.GET.get("qtd_perfil_puxador") or 0)
        pux_id = request.GET.get("puxador")
        qtd_pux = int(request.GET.get("qtd_puxador") or 0)
        pux_tam = int(request.GET.get("puxador_tamanho_mm") or 0)
        div_id = request.GET.get("divisor")
        qtd_div = int(request.GET.get("qtd_divisor") or 0)
        vidro_id = request.GET.get("vidro")
        adicional = sum(
            Decimal(request.GET.get(k) or 0)
            for k in ("adicional_valor", "adicional2_valor", "adicional3_valor", "adicional4_valor")
        )
        config = ConfiguracaoEmpresa.get()

        pp = PerfilPuxador.objects.filter(pk=pp_id).first() if pp_id else None
        pux = Puxador.objects.filter(pk=pux_id).first() if pux_id else None
        divisor = Divisor.objects.filter(pk=div_id).first() if div_id else None
        vidro = VidroBase.objects.filter(pk=vidro_id).first() if vidro_id else None

        valor_unit = calc_total(
            preco_perfil_m=perfil.preco,
            largura_mm=largura,
            altura_mm=altura,
            preco_pp_m=(pp.preco if pp else None),
            qtd_pp=(qtd_pp or None),
            preco_puxador_m=(pux.preco if pux else None),
            qtd_puxador=(qtd_pux or None),
            puxador_tamanho_mm=(pux_tam or None),
            preco_divisor_m=(divisor.preco if divisor else None),
            qtd_divisor=(qtd_div or None),
            preco_vidro_m2=(vidro.preco if vidro else None),
            custo_mao_obra=(config.custo_mao_obra if config.custo_mao_obra else None),
        ) + adicional

        return render(request, _tmpl, {
            "valor_unitario": valor_unit,
            "valor_total": valor_unit * Decimal(qtd),
            "adicional": adicional if adicional else None,
        })

    except (ValueError, TypeError):
        return render(request, _tmpl, {"erro": "Dados inválidos para cálculo."})


# ── HTMX — cascata acabamento / perfil ────────────────────────────────────────

@login_required
def htmx_perfis_por_acabamento(request):
    form = PedidoNovoOrcamentoForm(request.GET or None)
    return render(request, "portas/pedido/_col_perfil.html", {"form": form})


@login_required
def htmx_opcoes_por_perfil(request):
    form = PedidoNovoOrcamentoForm(request.GET or None)
    return render(request, "portas/pedido/_col_opcoes.html", {"form": form})


# ── HTMX — busca de clientes ──────────────────────────────────────────────────

@login_required
def htmx_clientes_sugestoes(request):
    termo = (request.GET.get("q") or "").strip()
    min_len = 2
    limite = 10

    if len(termo) < min_len:
        return render(request, "portas/pedido/_cliente_sugestoes.html", {
            "clientes": [], "min_len": min_len, "termo": termo,
        })

    qs = Cliente.objects.filter(ativo=True)
    if termo.isdigit():
        qs = qs.filter(codigo__startswith=termo)
    else:
        qs = qs.filter(nome__icontains=termo)

    return render(request, "portas/pedido/_cliente_sugestoes.html", {
        "clientes": qs.order_by("nome")[:limite],
        "min_len": min_len,
        "termo": termo,
    })


# ── Controle de produção ──────────────────────────────────────────────────────

@login_required
def pedido_controle(request):
    if not _get_perms(request.user)["producao"]["ver"]:
        return _sem_permissao("Você não tem permissão para acessar o controle de produção.")
    valid_statuses = [s[0] for s in Pedido.STATUS_CHOICES]
    status_filtro = request.GET.get("status", "aberto")
    if status_filtro not in valid_statuses:
        status_filtro = "aberto"

    if request.method == "POST":
        action = request.POST.get("action", "")
        ids = request.POST.getlist("pedido_ids")

        if ids and action == "ver_insumos":
            ids_str = ",".join(ids)
            return redirect(f"{reverse('pedido_insumos')}?ids={ids_str}")

        if ids and action in valid_statuses:
            if not _get_perms(request.user)["producao"]["alterar_status"]:
                return _sem_permissao("Você não tem permissão para alterar o status de produção.")

            if action == "wise":
                from ..models import BimerConfig
                from ..services import bimer as svc_bimer

                config = BimerConfig.get()
                erros_bimer = []
                enviados = []
                for pedido in Pedido.objects.filter(pk__in=ids).select_related("cliente"):
                    ok, msg = svc_bimer.enviar_pedido_bimer(config, pedido)
                    if ok:
                        pedido.status = "wise"
                        pedido.save(update_fields=["status"])
                        enviados.append(pedido.numero)
                    else:
                        erros_bimer.append(f"#{pedido.numero}: {msg}")

                if erros_bimer:
                    msgs_erro = " | ".join(erros_bimer)
                    qs = urlencode({"status": "producao", "bimer_erro": msgs_erro[:400]})
                    return redirect(f"{reverse('pedido_controle')}?{qs}")
                return redirect(f"{reverse('pedido_controle')}?status=wise")

            qs_bulk = Pedido.objects.filter(pk__in=ids)
            # Reabrir e cancelar não se aplicam a pedidos wise/concluido
            if action in ("aberto", "cancelado"):
                qs_bulk = qs_bulk.exclude(status__in=("wise", "concluido"))
            qs_bulk.update(status=action)
            # Redireciona para a aba do status que foi aplicado
            return redirect(f"{reverse('pedido_controle')}?status={action}")

        return redirect(f"{reverse('pedido_controle')}?status={status_filtro}")

    qs = (
        Pedido.objects
        .filter(status=status_filtro)
        .select_related("cliente", "usuario")
        .annotate(nr_itens=Count("itens"))
        .order_by("-id")
    )
    return render(request, "portas/pedido/pedido_controle.html", {
        "pedidos": qs,
        "status_filtro": status_filtro,
        "status_choices": Pedido.STATUS_CHOICES,
    })


# ── Insumos ───────────────────────────────────────────────────────────────────

@login_required
def pedido_insumos(request):
    if not _get_perms(request.user)["producao"]["ver"]:
        return _sem_permissao("Você não tem permissão para visualizar insumos.")
    ids_param = request.GET.get("ids", "")
    try:
        pedido_ids = [int(i) for i in ids_param.split(",") if i.strip().isdigit()]
    except ValueError:
        pedido_ids = []

    insumos = svc_producao.calcular_insumos(pedido_ids) if pedido_ids else {}
    pedidos = Pedido.objects.filter(pk__in=pedido_ids).select_related("cliente").order_by("id")

    return render(request, "portas/pedido/pedido_insumos.html", {
        "pedidos": pedidos,
        "insumos": insumos,
        "ids_param": ids_param,
    })


# ── Plano de corte ────────────────────────────────────────────────────────────

@login_required
def pedido_plano_corte(request):
    if not _get_perms(request.user)["producao"]["ver"]:
        return _sem_permissao("Você não tem permissão para visualizar o plano de corte.")
    ids_param = request.GET.get("ids", "")
    try:
        pedido_ids = [int(i) for i in ids_param.split(",") if i.strip().isdigit()]
    except ValueError:
        pedido_ids = []

    plano = svc_producao.calcular_plano_corte(pedido_ids) if pedido_ids else {"perfis": [], "vidros": []}
    pedidos = Pedido.objects.filter(pk__in=pedido_ids).select_related("cliente").order_by("id")

    return render(request, "portas/pedido/pedido_plano_corte.html", {
        "pedidos": pedidos,
        "plano": plano,
        "ids_param": ids_param,
    })


# ── Relatório de pedidos concluídos ──────────────────────────────────────────

@login_required
def pedido_relatorio(request):
    if not _get_perms(request.user)["producao"]["ver"]:
        return _sem_permissao("Você não tem permissão para visualizar relatórios.")
    data_inicio_str = request.GET.get("data_inicio", "")
    data_fim_str    = request.GET.get("data_fim", "")
    cliente_id      = request.GET.get("cliente_id", "")
    status_filtro   = request.GET.get("status", "concluido")

    STATUS_CHOICES = [
        ("aberto",    "Aberto"),
        ("producao",  "Em produção"),
        ("wise",      "Wise"),
        ("concluido", "Concluído"),
        ("cancelado", "Cancelado"),
    ]

    qs = (
        Pedido.objects
        .filter(status=status_filtro)
        .select_related("cliente", "usuario")
        .annotate(nr_itens=Count("itens"))
    )

    data_inicio = None
    data_fim    = None
    try:
        if data_inicio_str:
            data_inicio = Date.fromisoformat(data_inicio_str)
            qs = qs.filter(data__gte=data_inicio)
    except ValueError:
        pass
    try:
        if data_fim_str:
            data_fim = Date.fromisoformat(data_fim_str)
            qs = qs.filter(data__lte=data_fim)
    except ValueError:
        pass
    if cliente_id:
        qs = qs.filter(cliente_id=cliente_id)

    qs = qs.order_by("-id")
    pedido_ids = list(qs.values_list("id", flat=True))
    insumos = svc_producao.calcular_insumos(pedido_ids) if pedido_ids else {}
    clientes = Cliente.objects.filter(ativo=True).order_by("nome")

    return render(request, "portas/pedido/pedido_relatorio.html", {
        "pedidos": qs,
        "insumos": insumos,
        "clientes": clientes,
        "data_inicio": data_inicio_str,
        "data_fim": data_fim_str,
        "cliente_id": cliente_id,
        "status_filtro": status_filtro,
        "status_choices": STATUS_CHOICES,
    })


# ── HTMX — busca de clientes ──────────────────────────────────────────────────

@login_required
def htmx_cliente_selecionar(request, pk):
    c = get_object_or_404(Cliente, pk=pk)
    return HttpResponse(format_html("""
<input hx-swap-oob="outerHTML"
       type="hidden"
       name="cliente"
       id="id_cliente"
       value="{}">

<div hx-swap-oob="outerHTML"
     id="clienteResultados"
     class="small text-success mt-1">
  Selecionado: <strong>{}</strong> - {}
</div>

<input hx-swap-oob="outerHTML"
       id="clienteBusca"
       type="text"
       name="q"
       class="form-control"
       placeholder="Digite o código ou parte do nome..."
       value="{} - {}"
       hx-get="{}"
       hx-trigger="keyup changed delay:400ms"
       hx-target="#clienteSugestoes"
       hx-swap="innerHTML">

<div hx-swap-oob="innerHTML" id="clienteSugestoes"></div>
""",
        c.id,
        c.codigo, c.nome,
        c.codigo, c.nome,
        request.build_absolute_uri(reverse("htmx_clientes_sugestoes")),
    ))
