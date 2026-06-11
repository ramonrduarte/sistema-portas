import uuid

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.shortcuts import redirect, render

from ..forms import ConfiguracaoEmpresaForm
from ..models import ConfiguracaoEmpresa


@login_required
def configuracoes_empresa(request):
    if not request.user.is_staff:
        return redirect("pedidos_lista")

    config = ConfiguracaoEmpresa.get()

    if request.method == "POST":
        form = ConfiguracaoEmpresaForm(request.POST, request.FILES, instance=config)
        if form.is_valid():
            form.save()
            messages.success(request, "Configurações salvas com sucesso.")
            return redirect("configuracoes_empresa")
    else:
        form = ConfiguracaoEmpresaForm(instance=config)

    return render(request, "configuracoes/empresa.html", {
        "form":   form,
        "config": config,
    })


@login_required
def configuracoes_regenerar_token_monitor(request):
    """POST — gera novo token_monitor, invalidando os links públicos anteriores."""
    if not request.user.is_staff:
        return redirect("pedidos_lista")
    if request.method != "POST":
        return redirect("configuracoes_empresa")

    config = ConfiguracaoEmpresa.get()
    config.token_monitor = uuid.uuid4()
    config.save(update_fields=["token_monitor"])
    messages.success(request, "Token das páginas públicas regenerado. Os links anteriores deixaram de funcionar.")
    return redirect("configuracoes_empresa")
