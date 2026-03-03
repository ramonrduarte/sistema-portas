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
