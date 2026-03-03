from django.contrib.auth.mixins import LoginRequiredMixin
from django.views.generic import ListView, CreateView, UpdateView
from django.views import View
from django.shortcuts import render, get_object_or_404, redirect

from ..views_base import BaseCRUDMixin
from ..models import UsuarioPerfil
from ..forms import UsuarioPerfilForm


class UsuarioListView(LoginRequiredMixin, ListView):
    model = UsuarioPerfil
    template_name = "usuarios/lista.html"
    context_object_name = "usuarios"

    def get_queryset(self):
        return UsuarioPerfil.objects.select_related("user").all().order_by("user__username")


class UsuarioCreateView(LoginRequiredMixin, BaseCRUDMixin, CreateView):
    model = UsuarioPerfil
    form_class = UsuarioPerfilForm
    template_name = "usuarios/form.html"
    success_url_name = "usuarios_lista"

    def get(self, request, *args, **kwargs):
        self.object = None
        form = self.get_form()
        return render(request, self.template_name, {"form": form, "object": None})

    def form_valid(self, form):
        self.object = form.save()
        if self.request.headers.get("HX-Request") == "true":
            usuarios = UsuarioPerfil.objects.select_related("user").all().order_by("codigo")
            resp = render(self.request, "usuarios/_tabela.html", {"usuarios": usuarios})
            resp["HX-Trigger"] = "fecharModalCadastro"
            return resp
        return redirect(self.success_url_name)

    def form_invalid(self, form):
        return render(self.request, self.template_name, {"form": form, "object": None})


class UsuarioUpdateView(LoginRequiredMixin, BaseCRUDMixin, UpdateView):
    model = UsuarioPerfil
    form_class = UsuarioPerfilForm
    template_name = "usuarios/form.html"
    success_url_name = "usuarios_lista"

    def form_valid(self, form):
        self.object = form.save()
        if self.request.headers.get("HX-Request") == "true":
            usuarios = UsuarioPerfil.objects.select_related("user").all().order_by("codigo")
            resp = render(self.request, "usuarios/_tabela.html", {"usuarios": usuarios})
            resp["HX-Trigger"] = "fecharModalCadastro"
            return resp
        return redirect(self.success_url_name)

    def form_invalid(self, form):
        return render(self.request, self.template_name, {"form": form, "object": self.object})


class UsuarioDeleteView(LoginRequiredMixin, View):
    def get(self, request, pk):
        perfil = get_object_or_404(UsuarioPerfil.objects.select_related("user"), pk=pk)
        return render(request, "modais/excluir_produto.html", {
            "titulo": "Excluir usuário",
            "texto": f"Tem certeza que deseja excluir o usuário <strong>{perfil.user.username}</strong>?",
            "post_url": "usuarios_excluir",
            "obj_id": perfil.pk,
            "target_id": "#conteudoTabela",
        })

    def post(self, request, pk):
        perfil = get_object_or_404(UsuarioPerfil.objects.select_related("user"), pk=pk)
        perfil.user.delete()  # cascade remove o perfil
        if request.headers.get("HX-Request") == "true":
            usuarios = UsuarioPerfil.objects.select_related("user").all().order_by("codigo")
            return render(request, "usuarios/_tabela.html", {"usuarios": usuarios})
        return redirect("usuarios_lista")
