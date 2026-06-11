from django.conf import settings
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.http import HttpResponseForbidden
from django.shortcuts import redirect, render
from django.urls import reverse

from ..forms import AssistenteIAConfigForm, BimerConfigForm
from ..models import AssistenteIAConfig, BimerConfig
from ..services import bimer as svc_bimer
from ..services import gemini_assistente as svc_gemini


def _apenas_staff(request):
    return request.user.is_authenticated and request.user.is_staff


@login_required
def bimer_config(request):
    if not _apenas_staff(request):
        return redirect("pedidos_lista")

    config = BimerConfig.get()

    if request.method == "POST":
        form = BimerConfigForm(request.POST, instance=config)
        if form.is_valid():
            form.save()
            messages.success(request, "Configuração salva com sucesso.")
            return redirect("bimer_config")
    else:
        form = BimerConfigForm(instance=config)

    return render(request, "portas/integracoes/bimer.html", {
        "form":   form,
        "config": config,
    })


@login_required
def bimer_testar_conexao(request):
    """HTMX POST — testa credenciais e retorna badge de status inline."""
    if not _apenas_staff(request):
        return HttpResponseForbidden()

    config = BimerConfig.get()
    ok, msg = svc_bimer.testar_conexao(config)
    return render(request, "portas/integracoes/_status_conexao.html", {
        "ok":  ok,
        "msg": msg,
    })


@login_required
def bimer_sincronizar(request):
    """HTMX POST — dispara sync de preços e retorna resultado inline."""
    if not _apenas_staff(request):
        return HttpResponseForbidden()

    resultado = svc_bimer.sincronizar_precos()
    config    = BimerConfig.get()
    return render(request, "portas/integracoes/_resultado_sync.html", {
        "resultado": resultado,
        "config":    config,
    })


@login_required
def bimer_sincronizar_clientes(request):
    """HTMX POST — dispara sync de clientes do Bimer e retorna resultado inline."""
    if not _apenas_staff(request):
        return HttpResponseForbidden()

    resultado = svc_bimer.sincronizar_clientes()
    config    = BimerConfig.get()
    return render(request, "portas/integracoes/_resultado_sync_clientes.html", {
        "resultado": resultado,
        "config":    config,
    })


@login_required
def assistente_ia_config(request):
    if not _apenas_staff(request):
        return redirect("pedidos_lista")

    config = AssistenteIAConfig.get()

    if request.method == "POST":
        form = AssistenteIAConfigForm(request.POST, instance=config)
        if form.is_valid():
            form.save()
            messages.success(request, "Configuração salva com sucesso.")
            return redirect("assistente_ia_config")
    else:
        form = AssistenteIAConfigForm(instance=config)

    chat_url = request.build_absolute_uri(
        reverse("assistente_chat", args=[config.token_chat])
    )
    schema_url = request.build_absolute_uri(reverse("assistente_schema"))

    return render(request, "portas/integracoes/assistente_ia.html", {
        "form":                  form,
        "config":                config,
        "chat_url":              chat_url,
        "schema_url":            schema_url,
        "gpt_token_configurado": bool(settings.GPT_API_TOKEN),
    })


@login_required
def assistente_ia_token(request):
    """HTMX GET — retorna o valor do GPT_API_TOKEN para exibição pontual (staff only)."""
    if not _apenas_staff(request):
        return HttpResponseForbidden()
    return render(request, "portas/integracoes/_gpt_token.html", {
        "token": settings.GPT_API_TOKEN,
    })


@login_required
def assistente_ia_gerar_novo_link(request):
    """POST — gera um novo token para o chat público, revogando o link anterior."""
    if not _apenas_staff(request):
        return redirect("pedidos_lista")
    if request.method != "POST":
        return redirect("assistente_ia_config")

    import uuid
    config = AssistenteIAConfig.get()
    config.token_chat = uuid.uuid4()
    config.save(update_fields=["token_chat"])
    messages.success(request, "Novo link gerado. O link anterior deixou de funcionar.")
    return redirect("assistente_ia_config")


@login_required
def assistente_ia_testar_conexao(request):
    """HTMX POST — testa a chave do Gemini e retorna badge de status inline."""
    if not _apenas_staff(request):
        return HttpResponseForbidden()

    config = AssistenteIAConfig.get()
    ok, msg = svc_gemini.testar_api_key(config.api_key, config.modelo)
    return render(request, "portas/integracoes/_status_conexao.html", {
        "ok":  ok,
        "msg": msg,
    })
