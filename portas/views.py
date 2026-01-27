from django.views.generic import ListView, CreateView, UpdateView
from django.contrib.auth.decorators import login_required, permission_required
from django.views import View
from .views_base import AtivoQuerysetMixin, BaseCRUDMixin
from django.shortcuts import render, get_object_or_404, redirect
from .models import Orcamento, Perfil, Acabamento, PerfilPuxador, Puxador, EspessuraVidro, VidroBase, Divisor, Cliente, UsuarioPerfil
from .forms import Porta1PuxadorForm, PerfilForm, AcabamentoForm, PerfilPuxadorForm, PuxadorForm, EspessuraVidroForm, VidroBaseForm, DivisorForm, ClienteForm, UsuarioPerfilForm
from .services.calculo import calcular_porta_1x_puxador
from django.http import JsonResponse, HttpResponse
from django.db.models import ProtectedError
from django.template.loader import render_to_string


def calcular_porta_1p_view(request):
    orcamento = None
    resultado = None

    if request.method == "POST":
        form = Porta1PuxadorForm(request.POST, perfil_id=request.POST.get("perfil_estrutura"))
        if form.is_valid():
            orcamento = Orcamento.objects.create(
                tipo_porta="1P_PUXADOR",
                cliente_nome=form.cleaned_data.get("cliente_nome", ""),
            )

            resultado = calcular_porta_1x_puxador(
                orcamento=orcamento,
                largura_porta_m=form.cleaned_data["largura_porta_m"],
                altura_porta_m=form.cleaned_data["altura_porta_m"],
                quantidade=form.cleaned_data["quantidade"],
                perfil_estrutura=form.cleaned_data["perfil_estrutura"],
                perfil_puxador=form.cleaned_data["perfil_puxador"],
                vidro_base=form.cleaned_data["vidro_base"],
            )
    else:
        form = Porta1PuxadorForm()

    return render(request, "portas/calcular_porta_1p.html", {
        "form": form,
        "orcamento": orcamento,
        "resultado": resultado,
    })

def cadastrar_perfil_modal(request):
    if request.method == "POST":
        form = PerfilForm(request.POST)
        if form.is_valid():
            perfil = form.save()
            # Se você faz regras extras (espessura/vidros) aqui, mantenha:
            esp = form.cleaned_data.get("espessura_vidro")
            if esp:
                perfil.espessuras_vidro_compativeis.set([esp])
            else:
                perfil.espessuras_vidro_compativeis.clear()

            vidros_sel = form.cleaned_data.get("vidros_compativeis")
            if vidros_sel:
                perfil.vidros_compativeis.set(vidros_sel)
            else:
                perfil.vidros_compativeis.clear()

            perfis = Perfil.objects.select_related("acabamento").all().order_by("descricao")
            return render(request, "portas/perfil/perfil_tabela.html", {"perfis": perfis})

        return render(request, "portas/perfil/perfil_form.html", {"form": form, "perfil": None})

    form = PerfilForm()
    return render(request, "portas/perfil/perfil_form.html", {"form": form, "perfil": None})

def editar_perfil_modal(request, pk):
    perfil = get_object_or_404(Perfil, pk=pk)

    if request.method == "POST":
        form = PerfilForm(request.POST, instance=perfil)
        if form.is_valid():
            perfil = form.save()

            esp = form.cleaned_data.get("espessura_vidro")
            if esp:
                perfil.espessuras_vidro_compativeis.set([esp])
            else:
                perfil.espessuras_vidro_compativeis.clear()

            vidros_sel = form.cleaned_data.get("vidros_compativeis")
            if vidros_sel:
                perfil.vidros_compativeis.set(vidros_sel)
            else:
                perfil.vidros_compativeis.clear()

            perfis = Perfil.objects.select_related("acabamento").all().order_by("descricao")
            return render(request, "portas/perfil/perfil_tabela.html", {"perfis": perfis})

        return render(request, "portas/perfil/perfil_form.html", {"form": form, "perfil": perfil})

    form = PerfilForm(instance=perfil)
    return render(request, "portas/perfil/perfil_form.html", {"form": form, "perfil": perfil})



# ==== PERFIL PUXADOR ==== #
def lista_perfis_puxador(request):
    perfis_puxador = (
        PerfilPuxador.objects
        .select_related("acabamento")
        .all()
        .order_by("descricao")
    )
    return render(
        request,
        "portas/perfil_puxador/perfil_puxador_lista.html",
        {"perfis_puxador": perfis_puxador},
    )

def cadastrar_perfil_puxador(request, pk=None):
    perfil = get_object_or_404(PerfilPuxador, pk=pk) if pk else None

    if request.method == "POST":
        form = PerfilPuxadorForm(request.POST, instance=perfil)
        if form.is_valid():
            form.save()

            perfis_puxador = (
                PerfilPuxador.objects
                .select_related("acabamento")
                .all()
                .order_by("descricao")
            )

            if request.headers.get("HX-Request") == "true":
                return render(
                    request,
                    "portas/perfil_puxador/perfil_puxador_tabela.html",
                    {"perfis_puxador": perfis_puxador},
                )

            return redirect("lista_perfis_puxador")

        return render(
            request,
            "portas/perfil_puxador/perfil_puxador_form.html",
            {"form": form, "perfil": perfil},
        )

    form = PerfilPuxadorForm(instance=perfil)
    return render(
        request,
        "portas/perfil_puxador/perfil_puxador_form.html",
        {"form": form, "perfil": perfil},
    )

def excluir_perfil_puxador(request, pk):
    perfil = get_object_or_404(PerfilPuxador, pk=pk)

    if request.method == "POST":
        try:
            perfil.delete()
        except ProtectedError:
            return render(request, "portas/_mensagem_erro.html", {
                "mensagem": "Este perfil puxador está em uso e não pode ser excluído."
            })

        perfis_puxador = (
            PerfilPuxador.objects
            .select_related("acabamento")
            .all()
            .order_by("descricao")
        )

        if request.headers.get("HX-Request") == "true":
            return render(request, "portas/perfil_puxador/perfil_puxador_tabela.html", {
                "perfis_puxador": perfis_puxador
            })

        return redirect("lista_perfis_puxador")

    # GET (abre modal)
    return render(request, "modais/excluir_produto.html", {
        "titulo": "Confirmar exclusão",
        "texto": f'Tem certeza que deseja excluir o perfil puxador <strong>({perfil.codigo}) {perfil.descricao}</strong>?',
        "post_url": "excluir_perfil_puxador",
        "obj_id": perfil.pk,
        "target_id": "#conteudoTabela",   # ✅ padrão
    })


# ==== ACABAMENTO ==== # ok
def lista_acabamentos(request):
    acabamentos = Acabamento.objects.all().order_by("nome")
    return render(request, "portas/acabamento/acabamento_lista.html", {"acabamentos": acabamentos})

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

    if request.headers.get("HX-Request") == "true":
        return render(request, "portas/acabamento/acabamento_form.html", {"form": form, "acabamento": acabamento})

    return render(request, "portas/acabamento/acabamento_form.html", {"form": form, "acabamento": acabamento})

def excluir_acabamento(request, pk):
    acabamento = get_object_or_404(Acabamento, pk=pk)

    if request.method == "POST":
        try:
            acabamento.delete()
        except ProtectedError:
            # se estiver em uso
            return render(request, "portas/_mensagem_erro.html", {
                "mensagem": "Este acabamento está em uso e não pode ser excluído."
            })

        acabamentos = Acabamento.objects.all().order_by("nome")
        if request.headers.get("HX-Request") == "true":
            return render(request, "portas/acabamento/acabamento_tabela.html", {"acabamentos": acabamentos})
        return redirect("lista_acabamentos")

    return render(request, "modais/excluir_produto.html", {
        "titulo": "Excluir acabamento",
        "texto": f"Tem certeza que deseja excluir o acabamento <strong>“{acabamento}”</strong>?",
        "post_url": "excluir_acabamento",
        "obj_id": acabamento.pk,
    })


# ==== PERFIL ==== #
def lista_perfis(request):
    perfis = (
        Perfil.objects
        .select_related("acabamento")
        .prefetch_related("puxadores_compativeis", "puxadores_simples_compativeis", "divisores_compativeis", "vidros_compativeis", "espessuras_vidro_compativeis")
        .all()
        .order_by("descricao")
    )
    return render(request, "portas/perfil/perfil_lista.html", {"perfis": perfis})

def cadastrar_perfil(request, pk=None):
    perfil = get_object_or_404(Perfil, pk=pk) if pk else None

    if request.method == "POST":
        form = PerfilForm(request.POST, instance=perfil)
        if form.is_valid():
            perfil = form.save()

            # (sua regra) salva 1 espessura via campo "espessura_vidro"
            esp = form.cleaned_data.get("espessura_vidro")
            if esp:
                perfil.espessuras_vidro_compativeis.set([esp])
            else:
                perfil.espessuras_vidro_compativeis.clear()

            # (sua regra) salva vidros compatíveis do campo extra "vidros_compativeis"
            vidros_sel = form.cleaned_data.get("vidros_compativeis")
            if vidros_sel:
                perfil.vidros_compativeis.set(vidros_sel)
            else:
                perfil.vidros_compativeis.clear()

            perfis = (
                Perfil.objects
                .select_related("acabamento")
                .prefetch_related("puxadores_compativeis", "puxadores_simples_compativeis", "divisores_compativeis", "vidros_compativeis", "espessuras_vidro_compativeis")
                .all()
                .order_by("descricao")
            )

            # HTMX -> devolve só a tabela
            if request.headers.get("HX-Request") == "true":
                return render(request, "portas/perfil/perfil_tabela.html", {"perfis": perfis})

            return redirect("lista_perfis")

        # POST com erro -> devolve o modal com erros
        return render(request, "portas/perfil/perfil_form.html", {"form": form, "perfil": perfil})

    # GET -> devolve o formulário pro modal
    form = PerfilForm(instance=perfil)
    return render(request, "portas/perfil/perfil_form.html", {"form": form, "perfil": perfil})

def excluir_perfil(request, pk):
    perfil = get_object_or_404(Perfil, pk=pk)

    if request.method == "POST":
        try:
            perfil.delete()
        except ProtectedError:
            return render(request, "portas/_mensagem_erro.html", {
                "mensagem": "Este perfil está em uso e não pode ser excluído."
            })

        perfis = Perfil.objects.select_related("acabamento").all().order_by("descricao")
        return render(request, "portas/perfil/perfil_tabela.html", {"perfis": perfis})

    # GET: modal de confirmação
    return render(request, "portas/_confirmar_exclusao_modal.html", {
        "titulo": "Excluir perfil",
        "texto": f"Tem certeza que deseja excluir o perfil <strong>({perfil.codigo}) {perfil.descricao}</strong>?",
        "post_url": "excluir_perfil",
        "obj_id": perfil.pk,
        "target_id": "#tabelaPerfis",
    })


# ==== PUXADOR ==== # ok
def lista_puxadores(request):
    puxadores = Puxador.objects.select_related("acabamento").all().order_by("descricao")
    return render(request, "portas/puxador/puxador_lista.html", {"puxadores": puxadores})

def cadastrar_puxador(request, pk=None):
    puxador = get_object_or_404(Puxador, pk=pk) if pk else None

    if request.method == "POST":
        form = PuxadorForm(request.POST, instance=puxador)
        if form.is_valid():
            form.save()

            puxadores = Puxador.objects.select_related("acabamento").all().order_by("descricao")

            # Se veio do HTMX, devolve só a tabela atualizada
            if request.headers.get("HX-Request") == "true":
                return render(request, "portas/puxador/puxador_tabela.html", {"puxadores": puxadores})

            return redirect("lista_puxadores")
    else:
        form = PuxadorForm(instance=puxador)

    # GET via HTMX -> devolve só o formulário (para o modal)
    if request.headers.get("HX-Request") == "true":
        return render(request, "portas/puxador/puxador_form.html", {"form": form, "puxador": puxador})

    # GET normal -> página inteira
    return render(request, "portas/puxador/puxador_form.html", {"form": form, "puxador": puxador})

def excluir_puxador(request, pk):
    puxador = get_object_or_404(Puxador, pk=pk)

    if request.method == "POST":
        puxador.delete()
        puxadores = Puxador.objects.select_related("acabamento").all().order_by("descricao")
        if request.headers.get("HX-Request") == "true":
            return render(request, "portas/puxador/puxador_tabela.html", {"puxadores": puxadores})
        return redirect("lista_puxadores")

    return render(request, "modais/excluir_produto.html", {
        "titulo": "Excluir puxador",
        "texto": f"Tem certeza que deseja excluir o puxador <STRONG>“({puxador.codigo}) {puxador.descricao}”</STRONG>?",
        "post_url": "excluir_puxador",
        "obj_id": puxador.pk,
    })


# ==== ESPESSURA ==== # ok
def lista_espessuras(request):
    espessuras = EspessuraVidro.objects.all().order_by('valor_mm')
    return render(request, 'portas/espessura/espessura_lista.html', {'espessuras': espessuras})

def cadastrar_espessura(request, pk=None):
    espessura = get_object_or_404(EspessuraVidro, pk=pk) if pk else None
    origem = request.GET.get("origem") or request.POST.get("origem")

    if request.method == "POST":
        form = EspessuraVidroForm(request.POST, instance=espessura)
        if form.is_valid():
            nova = form.save()

            if origem == "vidro" and request.headers.get("HX-Request") == "true":
                nova = form.save()

                vidro_form = VidroBaseForm(initial={"espessura": nova.pk})
                html = render_to_string(
                    "portas/vidro/espessura_select_oob.html",
                    {"vidro_form": vidro_form},
                    request=request
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

    # HTMX: devolve só o form (pro modal)
    if request.headers.get("HX-Request") == "true":
        return render(request, "portas/espessura/espessura_form.html", {
            "form": form,
            "espessura": espessura,
            "origem": origem,  # manda pro template
        })

    return render(request, "portas/espessura/espessura_form.html", {"form": form, "espessura": espessura})

def excluir_espessura(request, pk):
    espessura = get_object_or_404(EspessuraVidro, pk=pk)

    if request.method == "POST":
        espessura.delete()
        espessuras = EspessuraVidro.objects.all().order_by('valor_mm')
        if request.headers.get("HX-Request") == "true":
            return render(request, 'portas/espessura/espessura_tabela.html', {'espessuras': espessuras})
        return redirect("lista_espessuras")
        
    return render(request, "modais/excluir_produto.html", {
        "titulo": "Excluir espessura",
        "texto": f"Tem certeza que deseja excluir a espessura <STRONG>“{espessura.valor_mm}mm”</STRONG>?",
        "post_url": "excluir_espessura",
        "obj_id": espessura.pk,
    })


# ==== VIDROS ==== # ok
def lista_vidros(request):
    vidros = VidroBase.objects.select_related("espessura").all().order_by("descricao")
    return render(request, "portas/vidro/vidro_lista.html", {"vidros": vidros})

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

    if request.headers.get("HX-Request") == "true":
        return render(request, "portas/vidro/vidro_form.html", {"form": form, "vidro": vidrobase})

    # GET normal -> página inteira
    return render(request, "portas/vidro/vidro_form.html", {"form": form, "vidro": vidrobase})

def excluir_vidro(request, pk):
    vidro = get_object_or_404(VidroBase, pk=pk)

    if request.method == "POST":
        vidro.delete()
        vidros = VidroBase.objects.all()
        if request.headers.get("HX-Request") == "true":
            return render(request, 'portas/vidro/vidro_tabela.html', {'vidros': vidros})
        return redirect("lista_vidros")
        
    return render(request, "modais/excluir_produto.html", {
        "titulo": "Excluir vidro",
        "texto": f"Tem certeza que deseja excluir o vidro <STRONG>({vidro.codigo}) {vidro.descricao} - {vidro.espessura}</STRONG>?",
        "post_url": "excluir_vidro",
        "obj_id": vidro.pk,
    })


# ==== FUNCOES ==== #
def carregar_vidros_por_espessura(request):
    perfil_id = request.GET.get("perfil_id")
    instance = Perfil.objects.filter(pk=perfil_id).first() if perfil_id else None

    form = PerfilForm(data=request.GET, instance=instance)
    return render(request, "portas/_perfil_vidros_por_espessura.html", {"form": form})

def carregar_compativeis_por_acabamento(request):
    perfil_id = request.GET.get("perfil_id")
    instance = Perfil.objects.filter(pk=perfil_id).first() if perfil_id else None

    form = PerfilForm(data=request.GET, instance=instance)
    return render(request, "portas/_perfil_compativeis_por_acabamento.html", {"form": form})

def carregar_combinacoes_perfil(request):
    perfil_id = request.GET.get("perfil_id")
    instance = Perfil.objects.filter(pk=perfil_id).first() if perfil_id else None
    form = PerfilForm(data=request.GET, instance=instance)
    return render(request, "portas/_perfil_combinacoes.html", {"form": form})

def carregar_opcoes_compativeis(request):
    """
    Usada pelo HTMX: recebe o id do perfil_estrutura via GET
    e devolve só o pedaço do formulário com os selects filtrados.
    """
    perfil_id = request.GET.get("perfil_estrutura")
    form = Porta1PuxadorForm(perfil_id=perfil_id)
    return render(request, "portas/_opcoes_compativeis.html", {"form": form})


# ==== DIVISOR ==== ok
def lista_divisores(request):
    divisores = Divisor.objects.select_related("acabamento").all().order_by("descricao")
    return render(request, "portas/divisor/divisor_lista.html", {"divisores": divisores})

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

    # GET (ou POST inválido) via HTMX -> devolve form pro modal
    if request.headers.get("HX-Request") == "true":
        return render(request, "portas/divisor/divisor_form.html", {"form": form, "divisor": divisor})

    # Se abrir sem HTMX (não é o padrão), pode redirecionar pra lista
    return render(request, "portas/divisor/divisor_form.html", {"form": form, "divisor": divisor})

def excluir_divisor(request, pk):
    divisor = get_object_or_404(Divisor, pk=pk)

    if request.method == "POST":
        divisor.delete()
        divisores = Divisor.objects.all()
        if request.headers.get("HX-Request") == "true":
            return render(request, 'portas/divisor/divisor_tabela.html', {'divisores': divisores})
        return redirect("lista_vidros")
        
    return render(request, "modais/excluir_produto.html", {
        "titulo": "Excluir divisor",
        "texto": f"Tem certeza que deseja excluir o divisor <STRONG>({divisor.codigo}) {divisor.descricao}</STRONG>?",
        "post_url": "excluir_divisor",
        "obj_id": divisor.pk,
    })


# ==== CLIENTES ==== #
def lista_clientes(request):
    clientes = Cliente.objects.all().order_by("nome")
    return render(request, "portas/lista_clientes.html", {"clientes": clientes})

def cadastrar_cliente(request, pk=None):
    if pk:
        cliente = get_object_or_404(Cliente, pk=pk)
    else:
        cliente = None

    if request.method == "POST":
        form = ClienteForm(request.POST, instance=cliente)
        if form.is_valid():
            form.save()
            clientes = Cliente.objects.all().order_by("nome")

            # Se veio do HTMX, devolve só a tabela atualizada
            if request.headers.get("HX-Request") == "true":
                return render(
                    request,
                    "portas/_clientes_tabela.html",
                    {"clientes": clientes},
                )

            # Acesso “normal” (sem HTMX) – redireciona
            return redirect("lista_clientes")
    else:
        form = ClienteForm(instance=cliente)

    # GET via HTMX -> devolve só o formulário (para o modal)
    if request.headers.get("HX-Request") == "true":
        return render(
            request,
            "portas/_cliente_form.html",
            {"form": form, "cliente": cliente},
        )

    # GET normal -> página de formulário inteira (se quiser acessar direto)
    return render(
        request,
        "portas/cliente_form.html",
        {"form": form, "cliente": cliente},
    )

class ClienteListView(AtivoQuerysetMixin, ListView):
    model = Cliente
    template_name = "clientes/lista.html"
    context_object_name = "clientes"
    only_active = False

class ClienteCreateView(BaseCRUDMixin, CreateView):
    model = Cliente
    form_class = ClienteForm
    template_name = "clientes/form.html"
    success_url_name = "clientes_lista"

    def form_invalid(self, form):
        # Se veio via fetch (AJAX), devolve só o HTML do form com erros
        if self.request.headers.get("X-Requested-With") == "XMLHttpRequest":
            return render(self.request, "clientes/form.html", {"form": form})
        return super().form_invalid(form)

    def form_valid(self, form):
        response = super().form_valid(form)
        # Se veio via fetch (AJAX), devolve um JSON dizendo que deu certo
        if self.request.headers.get("X-Requested-With") == "XMLHttpRequest":
            return JsonResponse({"ok": True})
        return response

class ClienteUpdateView(BaseCRUDMixin, UpdateView):
    model = Cliente
    form_class = ClienteForm
    template_name = "clientes/form.html"
    success_url_name = "clientes_lista"

    def form_invalid(self, form):
        if self.request.headers.get("X-Requested-With") == "XMLHttpRequest":
            return render(self.request, "clientes/form.html", {"form": form})
        return super().form_invalid(form)

    def form_valid(self, form):
        response = super().form_valid(form)
        if self.request.headers.get("X-Requested-With") == "XMLHttpRequest":
            return JsonResponse({"ok": True})
        return response

class ClienteDeleteView(View):
    """Exclui cliente via POST e volta para a lista."""
    def post(self, request, pk):
        cliente = get_object_or_404(Cliente, pk=pk)
        cliente.delete()
        return redirect("clientes_lista")    


# ==== USUÁRIOS ==== #
class UsuarioListView(AtivoQuerysetMixin, ListView):
    model = UsuarioPerfil
    template_name = "usuarios/lista.html"
    context_object_name = "usuarios"
    only_active = False

    def get_queryset(self):
        qs = super().get_queryset().select_related("user")
        return qs.order_by("codigo")

class UsuarioCreateView(BaseCRUDMixin, CreateView):
    model = UsuarioPerfil
    form_class = UsuarioPerfilForm
    template_name = "usuarios/form.html"
    success_url_name = "usuarios_lista"

    def form_invalid(self, form):
        # Se veio via fetch (AJAX), devolve só o HTML do form com erros
        if self.request.headers.get("X-Requested-With") == "XMLHttpRequest":
            return render(self.request, "usuarios/form.html", {"form": form})
        return super().form_invalid(form)

    def form_valid(self, form):
        response = super().form_valid(form)
        # Se veio via fetch (AJAX), devolve um JSON dizendo que deu certo
        if self.request.headers.get("X-Requested-With") == "XMLHttpRequest":
            return JsonResponse({"ok": True})
        return response

class UsuarioUpdateView(BaseCRUDMixin, UpdateView):
    model = UsuarioPerfil
    form_class = UsuarioPerfilForm
    template_name = "usuarios/form.html"
    success_url_name = "usuarios_lista"

    def form_invalid(self, form):
        if self.request.headers.get("X-Requested-With") == "XMLHttpRequest":
            return render(self.request, "usuarios/form.html", {"form": form})
        return super().form_invalid(form)

    def form_valid(self, form):
        response = super().form_valid(form)
        if self.request.headers.get("X-Requested-With") == "XMLHttpRequest":
            return JsonResponse({"ok": True})
        return response

class UsuarioDeleteView(View):
    def post(self, request, pk):
        perfil = get_object_or_404(UsuarioPerfil, pk=pk)
        user = perfil.user
        user.delete()
        return redirect("usuarios_lista")