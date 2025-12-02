from django.shortcuts import render, get_object_or_404, redirect
from .models import Orcamento, Perfil, Acabamento, PerfilPuxador, Puxador, EspessuraVidro, VidroBase, Divisor, Cliente
from .forms import Porta1PuxadorForm, PerfilForm, AcabamentoForm, PerfilPuxadorForm, PuxadorForm, EspessuraVidroForm, VidroBaseForm, DivisorForm, ClienteForm
from .services.calculo import calcular_porta_1x_puxador


# === JÁ EXISTIA: tela de orçamento ===
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


# === NOVO: lista de perfis ===
def lista_perfis(request):
    perfis = Perfil.objects.all().order_by("descricao")
    return render(request, "portas/lista_perfis.html", {"perfis": perfis})


def cadastrar_perfil(request, pk=None):
    if pk:
        perfil = get_object_or_404(Perfil, pk=pk)
    else:
        perfil = None

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
            return redirect("lista_perfis")
    else:
        form = PerfilForm(instance=perfil)

    return render(request, "portas/perfil_form.html", {"form": form, "perfil": perfil})



def carregar_opcoes_compativeis(request):
    """
    Usada pelo HTMX: recebe o id do perfil_estrutura via GET
    e devolve só o pedaço do formulário com os selects filtrados.
    """
    perfil_id = request.GET.get("perfil_estrutura")
    form = Porta1PuxadorForm(perfil_id=perfil_id)
    return render(request, "portas/_opcoes_compativeis.html", {"form": form})


def lista_acabamentos(request):
    acabamentos = Acabamento.objects.all().order_by("nome")
    return render(request, "portas/lista_acabamentos.html", {"acabamentos": acabamentos})


def cadastrar_acabamento(request, pk=None):
    if pk:
        acabamento = get_object_or_404(Acabamento, pk=pk)
    else:
        acabamento = None

    if request.method == "POST":
        form = AcabamentoForm(request.POST, instance=acabamento)
        if form.is_valid():
            form.save()
            return redirect("lista_acabamentos")
    else:
        form = AcabamentoForm(instance=acabamento)

    return render(request, "portas/acabamento_form.html", {"form": form, "acabamento": acabamento})


# ==== PERFIL PUxADOR ====

def lista_perfis_puxador(request):
    perfis_puxador = PerfilPuxador.objects.select_related("acabamento").all().order_by(
        "descricao"
    )
    return render(
        request,
        "portas/lista_perfis_puxador.html",
        {"perfis_puxador": perfis_puxador},
    )


def cadastrar_perfil_puxador(request, pk=None):
    if pk:
        perfil_puxador = get_object_or_404(PerfilPuxador, pk=pk)
    else:
        perfil_puxador = None

    if request.method == "POST":
        form = PerfilPuxadorForm(request.POST, instance=perfil_puxador)
        if form.is_valid():
            form.save()
            return redirect("lista_perfis_puxador")
    else:
        form = PerfilPuxadorForm(instance=perfil_puxador)

    return render(
        request,
        "portas/perfil_puxador_form.html",
        {"form": form, "perfil_puxador": perfil_puxador},
    )


# ==== PUXADOR SIMPLES ====

def lista_puxadores(request):
    puxadores = Puxador.objects.select_related("acabamento").all().order_by("descricao")
    return render(request, "portas/lista_puxadores.html", {"puxadores": puxadores})


def cadastrar_puxador(request, pk=None):
    if pk:
        puxador = get_object_or_404(Puxador, pk=pk)
    else:
        puxador = None

    if request.method == "POST":
        form = PuxadorForm(request.POST, instance=puxador)
        if form.is_valid():
            form.save()
            return redirect("lista_puxadores")
    else:
        form = PuxadorForm(instance=puxador)

    return render(
        request,
        "portas/puxador_form.html",
        {"form": form, "puxador": puxador},
    )

def carregar_combinacoes_perfil(request):
    """
    HTMX no cadastro de Perfil:
    recebe acabamento (e possivelmente outros campos) e
    devolve o HTML das combinações completas.
    """
    perfil_id = request.GET.get("perfil_id")
    instance = None
    if perfil_id:
        instance = Perfil.objects.filter(pk=perfil_id).first()

    form = PerfilForm(data=request.GET, instance=instance)
    return render(request, "portas/_perfil_combinacoes.html", {"form": form})




def lista_espessuras(request):
    espessuras = EspessuraVidro.objects.all().order_by("valor_mm")
    return render(
        request,
        "portas/lista_espessuras.html",
        {"espessuras": espessuras},
    )


def cadastrar_espessura(request, pk=None):
    if pk:
        espessura = get_object_or_404(EspessuraVidro, pk=pk)
    else:
        espessura = None

    if request.method == "POST":
        form = EspessuraVidroForm(request.POST, instance=espessura)
        if form.is_valid():
            form.save()
            return redirect("lista_espessuras")
    else:
        form = EspessuraVidroForm(instance=espessura)

    return render(
        request,
        "portas/espessura_form.html",
        {"form": form, "espessura": espessura},
    )


def lista_vidros(request):
    vidros = VidroBase.objects.select_related("espessura").all().order_by(
        "descricao"
    )
    return render(
        request,
        "portas/lista_vidros.html",
        {"vidros": vidros},
    )


def cadastrar_vidro(request, pk=None):
    if pk:
        vidro = get_object_or_404(VidroBase, pk=pk)
    else:
        vidro = None

    if request.method == "POST":
        form = VidroBaseForm(request.POST, instance=vidro)
        if form.is_valid():
            form.save()
            return redirect("lista_vidros")
    else:
        form = VidroBaseForm(instance=vidro)

    return render(
        request,
        "portas/vidro_form.html",
        {"form": form, "vidro": vidro},
    )

def carregar_vidros_por_espessura(request):
    """
    HTMX: ao mudar a espessura, atualiza só os vidros compatíveis.
    """
    perfil_id = request.GET.get("perfil_id")
    instance = None
    if perfil_id:
        instance = Perfil.objects.filter(pk=perfil_id).first()

    form = PerfilForm(data=request.GET, instance=instance)
    return render(request, "portas/_perfil_vidros.html", {"form": form})

# ==== DIVISOR ====


def lista_divisores(request):
    divisores = Divisor.objects.select_related("acabamento").all().order_by("descricao")
    return render(
        request,
        "portas/lista_divisores.html",
        {"divisores": divisores},
    )


def cadastrar_divisor(request, pk=None):
    if pk:
        divisor = get_object_or_404(Divisor, pk=pk)
    else:
        divisor = None

    if request.method == "POST":
        form = DivisorForm(request.POST, instance=divisor)
        if form.is_valid():
            form.save()
            return redirect("lista_divisores")
    else:
        form = DivisorForm(instance=divisor)

    return render(
        request,
        "portas/divisor_form.html",
        {"form": form, "divisor": divisor},
    )


# ==== CLIENTES ====

# ==== CLIENTES ====

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










