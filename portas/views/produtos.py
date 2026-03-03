from django.contrib.auth.decorators import login_required
from django.shortcuts import render, get_object_or_404, redirect
from django.http import HttpResponse
from django.db.models import ProtectedError
from django.template.loader import render_to_string

from ..models import Perfil, PerfilPuxador, Puxador, EspessuraVidro, VidroBase, Divisor, Acabamento
from ..forms import (
    PerfilForm, PerfilPuxadorForm, PuxadorForm,
    EspessuraVidroForm, VidroBaseForm, DivisorForm, AcabamentoForm,
)


# ── PERFIL PUXADOR ────────────────────────────────────────────────────────────

@login_required
def lista_perfis_puxador(request):
    perfis_puxador = PerfilPuxador.objects.select_related("acabamento").all().order_by("descricao")
    return render(request, "portas/perfil_puxador/perfil_puxador_lista.html", {"perfis_puxador": perfis_puxador})


@login_required
def cadastrar_perfil_puxador(request, pk=None):
    perfil = get_object_or_404(PerfilPuxador, pk=pk) if pk else None

    if request.method == "POST":
        form = PerfilPuxadorForm(request.POST, instance=perfil)
        if form.is_valid():
            form.save()
            perfis_puxador = PerfilPuxador.objects.select_related("acabamento").all().order_by("descricao")
            if request.headers.get("HX-Request") == "true":
                return render(request, "portas/perfil_puxador/perfil_puxador_tabela.html", {"perfis_puxador": perfis_puxador})
            return redirect("lista_perfis_puxador")
        return render(request, "portas/perfil_puxador/perfil_puxador_form.html", {"form": form, "perfil": perfil})

    form = PerfilPuxadorForm(instance=perfil)
    return render(request, "portas/perfil_puxador/perfil_puxador_form.html", {"form": form, "perfil": perfil})


@login_required
def excluir_perfil_puxador(request, pk):
    perfil = get_object_or_404(PerfilPuxador, pk=pk)

    if request.method == "POST":
        try:
            perfil.delete()
        except ProtectedError:
            return render(request, "portas/_mensagem_erro.html", {
                "mensagem": "Este perfil puxador está em uso e não pode ser excluído."
            })
        perfis_puxador = PerfilPuxador.objects.select_related("acabamento").all().order_by("descricao")
        if request.headers.get("HX-Request") == "true":
            return render(request, "portas/perfil_puxador/perfil_puxador_tabela.html", {"perfis_puxador": perfis_puxador})
        return redirect("lista_perfis_puxador")

    return render(request, "modais/excluir_produto.html", {
        "titulo": "Confirmar exclusão",
        "texto": f'Tem certeza que deseja excluir o perfil puxador <strong>({perfil.codigo}) {perfil.descricao}</strong>?',
        "post_url": "excluir_perfil_puxador",
        "obj_id": perfil.pk,
        "target_id": "#conteudoTabela",
    })


# ── ACABAMENTO ────────────────────────────────────────────────────────────────

@login_required
def lista_acabamentos(request):
    acabamentos = Acabamento.objects.all().order_by("nome")
    return render(request, "portas/acabamento/acabamento_lista.html", {"acabamentos": acabamentos})


@login_required
def cadastrar_acabamento(request, pk=None):
    acabamento = get_object_or_404(Acabamento, pk=pk) if pk else None

    if request.method == "POST":
        form = AcabamentoForm(request.POST, instance=acabamento)
        if form.is_valid():
            form.save()
            acabamentos = Acabamento.objects.all().order_by("nome")
            if request.headers.get("HX-Request") == "true":
                return render(request, "portas/acabamento/acabamento_tabela.html", {"acabamentos": acabamentos})
            return redirect("lista_acabamentos")
    else:
        form = AcabamentoForm(instance=acabamento)

    return render(request, "portas/acabamento/acabamento_form.html", {"form": form, "acabamento": acabamento})


@login_required
def excluir_acabamento(request, pk):
    acabamento = get_object_or_404(Acabamento, pk=pk)

    if request.method == "POST":
        try:
            acabamento.delete()
        except ProtectedError:
            return render(request, "portas/_mensagem_erro.html", {
                "mensagem": "Este acabamento está em uso e não pode ser excluído."
            })
        acabamentos = Acabamento.objects.all().order_by("nome")
        if request.headers.get("HX-Request") == "true":
            return render(request, "portas/acabamento/acabamento_tabela.html", {"acabamentos": acabamentos})
        return redirect("lista_acabamentos")

    return render(request, "modais/excluir_produto.html", {
        "titulo": "Excluir acabamento",
        "texto": f'Tem certeza que deseja excluir o acabamento <strong>"{acabamento}"</strong>?',
        "post_url": "excluir_acabamento",
        "obj_id": acabamento.pk,
    })


# ── PERFIL ────────────────────────────────────────────────────────────────────

def _perfil_qs():
    return (
        Perfil.objects
        .select_related("acabamento")
        .prefetch_related(
            "puxadores_compativeis", "puxadores_simples_compativeis",
            "divisores_compativeis", "vidros_compativeis", "espessuras_vidro_compativeis",
        )
        .all()
        .order_by("descricao")
    )


@login_required
def lista_perfis(request):
    return render(request, "portas/perfil/perfil_lista.html", {"perfis": _perfil_qs()})


@login_required
def cadastrar_perfil(request, pk=None):
    perfil = get_object_or_404(Perfil, pk=pk) if pk else None

    if request.method == "POST":
        form = PerfilForm(request.POST, instance=perfil)
        if form.is_valid():
            perfil = form.save()
            perfil.espessuras_vidro_compativeis.set(form.cleaned_data.get("espessuras_vidro"))
            vidros_sel = form.cleaned_data.get("vidros_compativeis")
            if vidros_sel:
                perfil.vidros_compativeis.set(vidros_sel)
            else:
                perfil.vidros_compativeis.clear()

            if request.headers.get("HX-Request") == "true":
                resp = render(request, "portas/perfil/perfil_tabela.html", {"perfis": _perfil_qs()})
                resp["HX-Trigger"] = "fecharModalCadastro"
                return resp
            return redirect("lista_perfis")

        return render(request, "portas/perfil/perfil_form.html", {"form": form, "perfil": perfil})

    form = PerfilForm(instance=perfil)
    return render(request, "portas/perfil/perfil_form.html", {"form": form, "perfil": perfil})


@login_required
def excluir_perfil(request, pk):
    perfil = get_object_or_404(Perfil, pk=pk)

    if request.method == "POST":
        try:
            perfil.delete()
        except ProtectedError:
            return render(request, "portas/_mensagem_erro.html", {
                "mensagem": "Este perfil está em uso e não pode ser excluído."
            })
        if request.headers.get("HX-Request") == "true":
            return render(request, "portas/perfil/perfil_tabela.html", {"perfis": _perfil_qs()})
        return redirect("lista_perfis")

    return render(request, "modais/excluir_produto.html", {
        "titulo": "Excluir perfil",
        "texto": f'Tem certeza que deseja excluir o perfil <strong>"{perfil.codigo} - {perfil.descricao}"</strong>?',
        "post_url": "excluir_perfil",
        "obj_id": perfil.pk,
        "target_id": "#conteudoTabela",
    })


# ── PUXADOR ───────────────────────────────────────────────────────────────────

@login_required
def lista_puxadores(request):
    puxadores = Puxador.objects.select_related("acabamento").all().order_by("descricao")
    return render(request, "portas/puxador/puxador_lista.html", {"puxadores": puxadores})


@login_required
def cadastrar_puxador(request, pk=None):
    puxador = get_object_or_404(Puxador, pk=pk) if pk else None

    if request.method == "POST":
        form = PuxadorForm(request.POST, instance=puxador)
        if form.is_valid():
            form.save()
            puxadores = Puxador.objects.select_related("acabamento").all().order_by("descricao")
            if request.headers.get("HX-Request") == "true":
                return render(request, "portas/puxador/puxador_tabela.html", {"puxadores": puxadores})
            return redirect("lista_puxadores")
    else:
        form = PuxadorForm(instance=puxador)

    return render(request, "portas/puxador/puxador_form.html", {"form": form, "puxador": puxador})


@login_required
def excluir_puxador(request, pk):
    puxador = get_object_or_404(Puxador, pk=pk)

    if request.method == "POST":
        try:
            puxador.delete()
        except ProtectedError:
            return render(request, "portas/_mensagem_erro.html", {
                "mensagem": "Este puxador está em uso e não pode ser excluído."
            })
        puxadores = Puxador.objects.select_related("acabamento").all().order_by("descricao")
        if request.headers.get("HX-Request") == "true":
            return render(request, "portas/puxador/puxador_tabela.html", {"puxadores": puxadores})
        return redirect("lista_puxadores")

    return render(request, "modais/excluir_produto.html", {
        "titulo": "Excluir puxador",
        "texto": f'Tem certeza que deseja excluir o puxador <strong>"({puxador.codigo}) {puxador.descricao}"</strong>?',
        "post_url": "excluir_puxador",
        "obj_id": puxador.pk,
    })


# ── ESPESSURA ─────────────────────────────────────────────────────────────────

@login_required
def lista_espessuras(request):
    espessuras = EspessuraVidro.objects.all().order_by('valor_mm')
    return render(request, 'portas/espessura/espessura_lista.html', {'espessuras': espessuras})


@login_required
def cadastrar_espessura(request, pk=None):
    espessura = get_object_or_404(EspessuraVidro, pk=pk) if pk else None
    origem = request.GET.get("origem") or request.POST.get("origem")

    if request.method == "POST":
        form = EspessuraVidroForm(request.POST, instance=espessura)
        if form.is_valid():
            nova = form.save()

            if origem == "vidro" and request.headers.get("HX-Request") == "true":
                vidro_form = VidroBaseForm(initial={"espessura": nova.pk})
                html = render_to_string(
                    "portas/vidro/espessura_select_oob.html",
                    {"vidro_form": vidro_form},
                    request=request,
                )
                response = HttpResponse(html)
                response["HX-Trigger"] = "espessura-salva"
                return response

            espessuras = EspessuraVidro.objects.all().order_by("valor_mm")
            if request.headers.get("HX-Request") == "true":
                return render(request, "portas/espessura/espessura_tabela.html", {"espessuras": espessuras})
            return redirect("lista_espessuras")
    else:
        form = EspessuraVidroForm(instance=espessura)

    return render(request, "portas/espessura/espessura_form.html", {
        "form": form, "espessura": espessura, "origem": origem,
    })


@login_required
def excluir_espessura(request, pk):
    espessura = get_object_or_404(EspessuraVidro, pk=pk)

    if request.method == "POST":
        try:
            espessura.delete()
        except ProtectedError:
            return render(request, "portas/_mensagem_erro.html", {
                "mensagem": "Esta espessura está em uso e não pode ser excluída."
            })
        espessuras = EspessuraVidro.objects.all().order_by('valor_mm')
        if request.headers.get("HX-Request") == "true":
            return render(request, 'portas/espessura/espessura_tabela.html', {'espessuras': espessuras})
        return redirect("lista_espessuras")

    return render(request, "modais/excluir_produto.html", {
        "titulo": "Excluir espessura",
        "texto": f'Tem certeza que deseja excluir a espessura <strong>"{espessura.valor_mm}mm"</strong>?',
        "post_url": "excluir_espessura",
        "obj_id": espessura.pk,
    })


# ── VIDROS ────────────────────────────────────────────────────────────────────

@login_required
def lista_vidros(request):
    vidros = VidroBase.objects.select_related("espessura").all().order_by("espessura")
    return render(request, "portas/vidro/vidro_lista.html", {"vidros": vidros})


@login_required
def cadastrar_vidro(request, pk=None):
    vidrobase = get_object_or_404(VidroBase, pk=pk) if pk else None

    if request.method == "POST":
        form = VidroBaseForm(request.POST, instance=vidrobase)
        if form.is_valid():
            form.save()
            vidros = VidroBase.objects.select_related("espessura").all().order_by("descricao")
            if request.headers.get("HX-Request") == "true":
                return render(request, "portas/vidro/vidro_tabela.html", {"vidros": vidros})
            return redirect("lista_vidros")
    else:
        form = VidroBaseForm(instance=vidrobase)

    return render(request, "portas/vidro/vidro_form.html", {"form": form, "vidro": vidrobase})


@login_required
def excluir_vidro(request, pk):
    vidro = get_object_or_404(VidroBase, pk=pk)

    if request.method == "POST":
        try:
            vidro.delete()
        except ProtectedError:
            return render(request, "portas/_mensagem_erro.html", {
                "mensagem": "Este vidro está em uso e não pode ser excluído."
            })
        vidros = VidroBase.objects.select_related("espessura").all().order_by("descricao")
        if request.headers.get("HX-Request") == "true":
            return render(request, 'portas/vidro/vidro_tabela.html', {'vidros': vidros})
        return redirect("lista_vidros")

    return render(request, "modais/excluir_produto.html", {
        "titulo": "Excluir vidro",
        "texto": f'Tem certeza que deseja excluir o vidro <strong>({vidro.codigo}) {vidro.descricao} - {vidro.espessura}</strong>?',
        "post_url": "excluir_vidro",
        "obj_id": vidro.pk,
    })


# ── DIVISOR ───────────────────────────────────────────────────────────────────

@login_required
def lista_divisores(request):
    divisores = Divisor.objects.select_related("acabamento").all().order_by("descricao")
    return render(request, "portas/divisor/divisor_lista.html", {"divisores": divisores})


@login_required
def cadastrar_divisor(request, pk=None):
    divisor = get_object_or_404(Divisor, pk=pk) if pk else None

    if request.method == "POST":
        form = DivisorForm(request.POST, instance=divisor)
        if form.is_valid():
            form.save()
            divisores = Divisor.objects.select_related("acabamento").all().order_by("descricao")
            if request.headers.get("HX-Request") == "true":
                return render(request, "portas/divisor/divisor_tabela.html", {"divisores": divisores})
            return redirect("lista_divisores")
    else:
        form = DivisorForm(instance=divisor)

    return render(request, "portas/divisor/divisor_form.html", {"form": form, "divisor": divisor})


@login_required
def excluir_divisor(request, pk):
    divisor = get_object_or_404(Divisor, pk=pk)

    if request.method == "POST":
        try:
            divisor.delete()
        except ProtectedError:
            return render(request, "portas/_mensagem_erro.html", {
                "mensagem": "Este divisor está em uso e não pode ser excluído."
            })
        divisores = Divisor.objects.select_related("acabamento").all().order_by("descricao")
        if request.headers.get("HX-Request") == "true":
            return render(request, 'portas/divisor/divisor_tabela.html', {'divisores': divisores})
        return redirect("lista_divisores")

    return render(request, "modais/excluir_produto.html", {
        "titulo": "Excluir divisor",
        "texto": f'Tem certeza que deseja excluir o divisor <strong>({divisor.codigo}) {divisor.descricao}</strong>?',
        "post_url": "excluir_divisor",
        "obj_id": divisor.pk,
    })


# ── HTMX auxiliares de Perfil ─────────────────────────────────────────────────

@login_required
def perfil_vidros_por_espessuras(request):
    perfil_id = request.GET.get("perfil_id")
    instance = Perfil.objects.filter(pk=perfil_id).first() if perfil_id else None
    form = PerfilForm(data=request.GET, instance=instance)
    return render(request, "portas/perfil/_campo_vidros.html", {"form": form})


@login_required
def perfil_compativeis_por_acabamento(request):
    perfil_id = request.GET.get("perfil_id")
    instance = Perfil.objects.filter(pk=perfil_id).first() if perfil_id else None
    form = PerfilForm(data=request.GET, instance=instance)
    return render(request, "portas/perfil/_compativeis_por_acabamento_cols.html", {"form": form})
