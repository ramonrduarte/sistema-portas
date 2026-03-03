from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.http import HttpResponseForbidden
from django.shortcuts import redirect, render

from ..forms import BimerConfigForm
from ..models import BimerConfig
from ..services import bimer as svc_bimer


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
