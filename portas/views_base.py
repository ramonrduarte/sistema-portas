# portas/views_base.py
from django.urls import reverse_lazy
from django.views.generic import ListView, CreateView, UpdateView


class AtivoQuerysetMixin:
    """Filtra por ativo=True por padrão, mas você pode desativar se quiser."""
    only_active = True

    def get_queryset(self):
        qs = super().get_queryset()
        if getattr(self, "only_active", True) and hasattr(self.model, "ativo"):
            qs = qs.filter(ativo=True)
        return qs


class BaseCRUDMixin:
    """
    Mixin base pra Create/UpdateView:
    - define template padrão de formulário (pode ser modal)
    - define como calcular success_url com nome de URL.
    """
    template_name = "shared/modal_form.html"
    success_url_name = None  # ex: "clientes_lista"

    def get_success_url(self):
        if not self.success_url_name:
            raise ValueError("Defina success_url_name na view.")
        return reverse_lazy(self.success_url_name)
