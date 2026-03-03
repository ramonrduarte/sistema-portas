from django.contrib.auth.mixins import LoginRequiredMixin
from django.views.generic import ListView, CreateView, UpdateView
from django.views import View
from django.shortcuts import render, get_object_or_404, redirect

from ..views_base import AtivoQuerysetMixin, BaseCRUDMixin, _get_perms, _sem_permissao
from ..models import Cliente
from ..forms import ClienteForm


class ClienteListView(LoginRequiredMixin, AtivoQuerysetMixin, ListView):
    model = Cliente
    template_name = "clientes/lista.html"
    context_object_name = "clientes"
    only_active = False

    def dispatch(self, request, *args, **kwargs):
        if request.user.is_authenticated and not _get_perms(request.user)["clientes"]["ver"]:
            return _sem_permissao("Você não tem permissão para visualizar clientes.")
        return super().dispatch(request, *args, **kwargs)

    def get_queryset(self):
        return super().get_queryset().order_by("nome")


class ClienteCreateView(LoginRequiredMixin, BaseCRUDMixin, CreateView):
    model = Cliente
    form_class = ClienteForm
    template_name = "clientes/form.html"
    success_url_name = "clientes_lista"

    def dispatch(self, request, *args, **kwargs):
        if request.user.is_authenticated and not _get_perms(request.user)["clientes"]["editar"]:
            return _sem_permissao("Você não tem permissão para cadastrar clientes.")
        return super().dispatch(request, *args, **kwargs)

    def get(self, request, *args, **kwargs):
        self.object = None
        form = self.get_form()
        return render(request, self.template_name, {"form": form, "object": None})

    def form_valid(self, form):
        self.object = form.save()
        if self.request.headers.get("HX-Request") == "true":
            clientes = Cliente.objects.all().order_by("nome")
            resp = render(self.request, "clientes/_tabela.html", {"clientes": clientes})
            resp["HX-Trigger"] = "fecharModalCadastro"
            return resp
        return redirect(self.success_url_name)

    def form_invalid(self, form):
        return render(self.request, self.template_name, {"form": form, "object": None})


class ClienteUpdateView(LoginRequiredMixin, BaseCRUDMixin, UpdateView):
    model = Cliente
    form_class = ClienteForm
    template_name = "clientes/form.html"
    success_url_name = "clientes_lista"

    def dispatch(self, request, *args, **kwargs):
        if request.user.is_authenticated and not _get_perms(request.user)["clientes"]["editar"]:
            return _sem_permissao("Você não tem permissão para editar clientes.")
        return super().dispatch(request, *args, **kwargs)

    def form_valid(self, form):
        self.object = form.save()
        if self.request.headers.get("HX-Request") == "true":
            clientes = Cliente.objects.all().order_by("nome")
            resp = render(self.request, "clientes/_tabela.html", {"clientes": clientes})
            resp["HX-Trigger"] = "fecharModalCadastro"
            return resp
        return redirect(self.success_url_name)

    def form_invalid(self, form):
        return render(self.request, self.template_name, {"form": form, "object": self.object})


class ClienteDeleteView(LoginRequiredMixin, View):
    def dispatch(self, request, *args, **kwargs):
        if request.user.is_authenticated and not _get_perms(request.user)["clientes"]["excluir"]:
            return _sem_permissao("Você não tem permissão para excluir clientes.")
        return super().dispatch(request, *args, **kwargs)

    def get(self, request, pk):
        cliente = get_object_or_404(Cliente, pk=pk)
        return render(request, "modais/excluir_produto.html", {
            "titulo": "Excluir cliente",
            "texto": f"Tem certeza que deseja excluir o cliente <strong>{cliente.nome}</strong>?",
            "post_url": "clientes_excluir",
            "obj_id": cliente.pk,
            "target_id": "#conteudoTabela",
        })

    def post(self, request, pk):
        cliente = get_object_or_404(Cliente, pk=pk)
        cliente.delete()
        if request.headers.get("HX-Request") == "true":
            clientes = Cliente.objects.all().order_by("nome")
            return render(request, "clientes/_tabela.html", {"clientes": clientes})
        return redirect("clientes_lista")
