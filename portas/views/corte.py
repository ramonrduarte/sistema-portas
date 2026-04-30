from collections import defaultdict

from django.contrib.auth.decorators import login_required
from django.db.models import Exists, OuterRef
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_POST

from ..models import Pedido, PedidoItem, PedidoItemVidro, PedidoItemVidroServico
from ..services import producao as svc_producao
from ..services.producao import _calcular_dimensoes_vidro, _calcular_largura_perfil
from ..views_base import _get_perms, _sem_permissao


def _tem_corte_especial():
    """Subquery: True se o PedidoItemVidro tem ao menos um serviço com corte_especial=True."""
    return Exists(
        PedidoItemVidroServico.objects.filter(
            item=OuterRef("pk"),
            servico__corte_especial=True,
        )
    )


def _consolidar_vidros(itens_porta, itens_avulso):
    """Agrupa peças de vidro por tipo+dimensão para exibição na lista de corte."""
    mapa = {}
    for item in itens_porta:
        for gw, gh in _calcular_dimensoes_vidro(item):
            key = (item.vidro_id, gw, gh)
            if key not in mapa:
                mapa[key] = {"vidro": item.vidro, "largura_mm": gw, "altura_mm": gh, "quantidade": 0}
            mapa[key]["quantidade"] += item.quantidade
    for item in itens_avulso:
        key = (item.vidro_id, item.largura_mm, item.altura_mm)
        if key not in mapa:
            mapa[key] = {"vidro": item.vidro, "largura_mm": item.largura_mm, "altura_mm": item.altura_mm, "quantidade": 0}
        mapa[key]["quantidade"] += item.quantidade
    return sorted(mapa.values(), key=lambda x: (str(x["vidro"]), x["largura_mm"], x["altura_mm"]))


def _contadores_filas():
    tem_especial = _tem_corte_especial()
    perfis = PedidoItem.objects.filter(pedido__status="producao", perfil_cortado=False).count()
    vidros_ret = (
        PedidoItem.objects.filter(
            pedido__status="producao", vidro_cortado=False, vidro__isnull=False,
        ).count()
        + PedidoItemVidro.objects.filter(
            pedido__status="producao", vidro_cortado=False,
        ).exclude(tem_especial).count()
    )
    vidros_org = PedidoItemVidro.objects.filter(
        pedido__status="producao", vidro_cortado=False,
    ).filter(tem_especial).count()
    # Itens prontos para montar: cortes concluídos e montagem pendente
    montagem = PedidoItem.objects.filter(
        pedido__status="producao",
        pedido__tipo="porta",
        perfil_cortado=True,
        montagem_feita=False,
    ).exclude(vidro__isnull=False, vidro_cortado=False).count()
    return {"perfis": perfis, "vidros_ret": vidros_ret, "vidros_org": vidros_org, "montagem": montagem}


# ── Fila: corte de perfis ─────────────────────────────────────────────────────

@login_required
def fila_corte_perfis(request):
    if not _get_perms(request.user)["producao"]["ver"]:
        return _sem_permissao("Você não tem permissão para acessar as filas de corte.")

    itens_qs = (
        PedidoItem.objects
        .filter(pedido__status="producao", perfil_cortado=False)
        .select_related("pedido__cliente", "perfil__acabamento", "perfil_puxador", "puxador", "divisor", "vidro")
        .order_by("pedido_id", "id")
    )

    pedidos_map = defaultdict(lambda: {"pedido": None, "itens": []})
    all_item_ids = []
    for item in itens_qs:
        item.perfil_largura_corte = _calcular_largura_perfil(item)
        pedidos_map[item.pedido_id]["pedido"] = item.pedido
        pedidos_map[item.pedido_id]["itens"].append(item)
        all_item_ids.append(item.id)

    pedidos_grupos = list(pedidos_map.values())
    pedido_ids = list(pedidos_map.keys())

    # Gerar plano apenas para os itens selecionados via GET params
    plan_item_ids = [int(x) for x in request.GET.getlist("plan_items") if x.isdigit()]
    plano = None
    if plan_item_ids and pedido_ids:
        plano = svc_producao.calcular_plano_corte(
            pedido_ids, item_ids=plan_item_ids, item_vidro_ids=[]
        )

    return render(request, "portas/corte/fila_perfis.html", {
        "pedidos_grupos": pedidos_grupos,
        "all_item_ids": all_item_ids,
        "plan_item_ids": plan_item_ids,
        "plano": plano,
        "contadores": _contadores_filas(),
        "fila_ativa": "perfis",
    })


# ── Fila: corte de vidros retangulares ───────────────────────────────────────

@login_required
def fila_corte_vidros_retangulares(request):
    if not _get_perms(request.user)["producao"]["ver"]:
        return _sem_permissao("Você não tem permissão para acessar as filas de corte.")

    tem_especial = _tem_corte_especial()

    # Itens de porta com vidro: sempre retangulares
    itens_porta = list(
        PedidoItem.objects
        .filter(pedido__status="producao", vidro_cortado=False, vidro__isnull=False)
        .select_related("pedido__cliente", "perfil", "perfil_puxador", "puxador", "divisor", "vidro__espessura")
        .order_by("pedido_id", "id")
    )
    for _item in itens_porta:
        pecas = _calcular_dimensoes_vidro(_item)
        _item.vidro_largura_corte = pecas[0][0]
        _item.vidro_altura_corte = pecas[0][1]
    # Itens avulsos SEM serviço de corte especial
    itens_avulso = list(
        PedidoItemVidro.objects
        .filter(pedido__status="producao", vidro_cortado=False)
        .exclude(tem_especial)
        .select_related("pedido__cliente", "vidro__espessura")
        .order_by("pedido_id", "id")
    )

    pedidos_map = defaultdict(lambda: {"pedido": None, "itens_porta": [], "itens_avulso": []})

    for item in itens_porta:
        pedidos_map[item.pedido_id]["pedido"] = item.pedido
        pedidos_map[item.pedido_id]["itens_porta"].append(item)
    for item in itens_avulso:
        pedidos_map[item.pedido_id]["pedido"] = item.pedido
        pedidos_map[item.pedido_id]["itens_avulso"].append(item)

    pedidos_grupos = list(pedidos_map.values())

    plan_porta_ids = set(int(x) for x in request.GET.getlist("plan_items") if x.isdigit())
    plan_avulso_ids = set(int(x) for x in request.GET.getlist("plan_avulsos") if x.isdigit())

    if plan_porta_ids or plan_avulso_ids:
        lista_vidros = _consolidar_vidros(
            [i for i in itens_porta if i.id in plan_porta_ids],
            [i for i in itens_avulso if i.id in plan_avulso_ids],
        )
    else:
        lista_vidros = None

    return render(request, "portas/corte/fila_vidros.html", {
        "pedidos_grupos": pedidos_grupos,
        "lista_vidros": lista_vidros,
        "plan_porta_ids": list(plan_porta_ids),
        "plan_avulso_ids": list(plan_avulso_ids),
        "contadores": _contadores_filas(),
        "fila_ativa": "retangular",
        "titulo_fila": "Vidros Retangulares",
    })


# ── Fila: corte de vidros orgânicos ──────────────────────────────────────────

@login_required
def fila_corte_vidros_organicos(request):
    if not _get_perms(request.user)["producao"]["ver"]:
        return _sem_permissao("Você não tem permissão para acessar as filas de corte.")

    tem_especial = _tem_corte_especial()

    # Apenas itens avulsos COM serviço de corte especial (molde, redondo, etc.)
    itens_avulso = list(
        PedidoItemVidro.objects
        .filter(pedido__status="producao", vidro_cortado=False)
        .filter(tem_especial)
        .select_related("pedido__cliente", "vidro__espessura")
        .prefetch_related("servicos__servico")
        .order_by("pedido_id", "id")
    )

    pedidos_map = defaultdict(lambda: {"pedido": None, "itens_porta": [], "itens_avulso": []})

    for item in itens_avulso:
        pedidos_map[item.pedido_id]["pedido"] = item.pedido
        pedidos_map[item.pedido_id]["itens_avulso"].append(item)

    pedidos_grupos = list(pedidos_map.values())

    plan_avulso_ids = set(int(x) for x in request.GET.getlist("plan_avulsos") if x.isdigit())

    if plan_avulso_ids:
        lista_vidros = _consolidar_vidros([], [i for i in itens_avulso if i.id in plan_avulso_ids])
    else:
        lista_vidros = None

    return render(request, "portas/corte/fila_vidros.html", {
        "pedidos_grupos": pedidos_grupos,
        "lista_vidros": lista_vidros,
        "plan_porta_ids": [],
        "plan_avulso_ids": list(plan_avulso_ids),
        "contadores": _contadores_filas(),
        "fila_ativa": "organico",
        "titulo_fila": "Vidros Orgânicos",
    })


# ── Ações: marcar como cortado ───────────────────────────────────────────────

@login_required
@require_POST
def marcar_perfil_cortado(request, item_pk):
    if not _get_perms(request.user)["producao"]["alterar_status"]:
        return _sem_permissao("Você não tem permissão para alterar etapas de corte.")
    item = get_object_or_404(PedidoItem, pk=item_pk)
    item.perfil_cortado = True
    item.save(update_fields=["perfil_cortado"])
    return redirect("fila_corte_perfis")


@login_required
@require_POST
def marcar_perfil_cortado_pedido(request, pedido_pk):
    if not _get_perms(request.user)["producao"]["alterar_status"]:
        return _sem_permissao("Você não tem permissão para alterar etapas de corte.")
    pedido = get_object_or_404(Pedido, pk=pedido_pk, status="producao")
    pedido.itens.update(perfil_cortado=True)
    return redirect("fila_corte_perfis")


@login_required
@require_POST
def marcar_vidro_cortado_item_porta(request, item_pk):
    if not _get_perms(request.user)["producao"]["alterar_status"]:
        return _sem_permissao("Você não tem permissão para alterar etapas de corte.")
    item = get_object_or_404(PedidoItem, pk=item_pk)
    item.vidro_cortado = True
    item.save(update_fields=["vidro_cortado"])
    return redirect("fila_corte_vidros_retangulares")


@login_required
@require_POST
def marcar_vidro_cortado_item_avulso(request, item_pk):
    if not _get_perms(request.user)["producao"]["alterar_status"]:
        return _sem_permissao("Você não tem permissão para alterar etapas de corte.")
    item = get_object_or_404(PedidoItemVidro, pk=item_pk)
    item.vidro_cortado = True
    item.save(update_fields=["vidro_cortado"])
    tem_especial = _tem_corte_especial()
    # Redireciona para a fila de onde o item veio
    veio_organico = PedidoItemVidro.objects.filter(pk=item_pk).filter(tem_especial).exists()
    return redirect("fila_corte_vidros_organicos" if veio_organico else "fila_corte_vidros_retangulares")


@login_required
@require_POST
def marcar_vidro_cortado_pedido(request, pedido_pk):
    """Marca todos os itens de vidro de um pedido como cortados."""
    if not _get_perms(request.user)["producao"]["alterar_status"]:
        return _sem_permissao("Você não tem permissão para alterar etapas de corte.")
    get_object_or_404(Pedido, pk=pedido_pk, status="producao")
    PedidoItem.objects.filter(pedido_id=pedido_pk, vidro__isnull=False).update(vidro_cortado=True)
    PedidoItemVidro.objects.filter(pedido_id=pedido_pk).update(vidro_cortado=True)
    fila = request.POST.get("fila", "retangular")
    return redirect("fila_corte_vidros_organicos" if fila == "organico" else "fila_corte_vidros_retangulares")


# ── Fila: montagem ────────────────────────────────────────────────────────────

@login_required
def fila_montagem(request):
    if not _get_perms(request.user)["producao"]["ver"]:
        return _sem_permissao("Você não tem permissão para acessar a fila de montagem.")

    # Itens prontos: perfil cortado, vidro cortado (se tiver), montagem pendente
    itens_qs = (
        PedidoItem.objects
        .filter(
            pedido__status="producao",
            pedido__tipo="porta",
            perfil_cortado=True,
            montagem_feita=False,
        )
        .exclude(vidro__isnull=False, vidro_cortado=False)
        .select_related("pedido__cliente", "perfil__acabamento", "vidro__espessura", "puxador", "divisor", "perfil_puxador", "acabamento")
        .order_by("pedido_id", "id")
    )

    pedidos_map = defaultdict(lambda: {"pedido": None, "itens": []})
    for item in itens_qs:
        pedidos_map[item.pedido_id]["pedido"] = item.pedido
        pedidos_map[item.pedido_id]["itens"].append(item)

    pedidos_grupos = list(pedidos_map.values())

    return render(request, "portas/corte/fila_montagem.html", {
        "pedidos_grupos": pedidos_grupos,
        "contadores": _contadores_filas(),
        "fila_ativa": "montagem",
    })


@login_required
@require_POST
def marcar_montagem_feita(request, item_pk):
    if not _get_perms(request.user)["producao"]["alterar_status"]:
        return _sem_permissao("Você não tem permissão para alterar etapas de montagem.")
    item = get_object_or_404(PedidoItem, pk=item_pk)
    item.montagem_feita = True
    item.save(update_fields=["montagem_feita"])
    return redirect("fila_montagem")


@login_required
@require_POST
def marcar_montagem_feita_pedido(request, pedido_pk):
    if not _get_perms(request.user)["producao"]["alterar_status"]:
        return _sem_permissao("Você não tem permissão para alterar etapas de montagem.")
    get_object_or_404(Pedido, pk=pedido_pk)
    PedidoItem.objects.filter(
        pedido_id=pedido_pk,
        perfil_cortado=True,
        montagem_feita=False,
    ).exclude(vidro__isnull=False, vidro_cortado=False).update(montagem_feita=True)
    return redirect("fila_montagem")
