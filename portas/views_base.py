# portas/views_base.py
from django.http import HttpResponseForbidden
from django.urls import reverse_lazy
from django.views.generic import ListView, CreateView, UpdateView


def _get_perms(user):
    """Retorna o dict de permissões do usuário (mesmo formato do context processor)."""
    if user.is_staff:
        return {
            "pedidos":  {"ver": True, "criar": True, "editar": True, "excluir": True},
            "producao": {"ver": True, "alterar_status": True},
            "clientes": {"ver": True, "editar": True, "excluir": True},
            "cadastros":{"ver": True, "editar": True, "excluir": True},
            "admin":    True,
        }
    try:
        p = user.perfil
        return {
            "pedidos":  {"ver": p.perm_pedidos_ver, "criar": p.perm_pedidos_criar,
                         "editar": p.perm_pedidos_editar, "excluir": p.perm_pedidos_excluir},
            "producao": {"ver": p.perm_producao_ver, "alterar_status": p.perm_producao_alterar_status},
            "clientes": {"ver": p.perm_clientes_ver, "editar": p.perm_clientes_editar,
                         "excluir": p.perm_clientes_excluir},
            "cadastros":{"ver": p.perm_cadastros_ver, "editar": p.perm_cadastros_editar,
                         "excluir": p.perm_cadastros_excluir},
            "admin":    False,
        }
    except Exception:
        return {
            "pedidos":  {"ver": True, "criar": True, "editar": True, "excluir": False},
            "producao": {"ver": True, "alterar_status": False},
            "clientes": {"ver": True, "editar": True, "excluir": False},
            "cadastros":{"ver": False, "editar": False, "excluir": False},
            "admin":    False,
        }


def _sem_permissao(msg="Você não tem permissão para realizar esta ação."):
    return HttpResponseForbidden(
        f'<div class="alert alert-danger m-3"><i class="bi bi-shield-exclamation me-2"></i>{msg}</div>'
    )


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
