_ADMIN_PERMS = {
    "pedidos":  {"ver": True, "criar": True, "editar": True, "excluir": True},
    "producao": {"ver": True, "alterar_status": True},
    "clientes": {"ver": True, "editar": True, "excluir": True},
    "cadastros":{"ver": True, "editar": True, "excluir": True},
    "admin":    True,
}

_DEFAULT_PERMS = {
    "pedidos":  {"ver": True, "criar": True, "editar": True, "excluir": False},
    "producao": {"ver": True, "alterar_status": False},
    "clientes": {"ver": True, "editar": True, "excluir": False},
    "cadastros":{"ver": False, "editar": False, "excluir": False},
    "admin":    False,
}


def config_empresa(request):
    from .models import ConfiguracaoEmpresa
    ctx = {"config_empresa": ConfiguracaoEmpresa.get()}

    if request.user.is_authenticated:
        if request.user.is_staff:
            ctx["perms_usuario"] = _ADMIN_PERMS
        else:
            try:
                p = request.user.perfil
                ctx["perms_usuario"] = {
                    "pedidos": {
                        "ver":     p.perm_pedidos_ver,
                        "criar":   p.perm_pedidos_criar,
                        "editar":  p.perm_pedidos_editar,
                        "excluir": p.perm_pedidos_excluir,
                    },
                    "producao": {
                        "ver":            p.perm_producao_ver,
                        "alterar_status": p.perm_producao_alterar_status,
                    },
                    "clientes": {
                        "ver":     p.perm_clientes_ver,
                        "editar":  p.perm_clientes_editar,
                        "excluir": p.perm_clientes_excluir,
                    },
                    "cadastros": {
                        "ver":     p.perm_cadastros_ver,
                        "editar":  p.perm_cadastros_editar,
                        "excluir": p.perm_cadastros_excluir,
                    },
                    "admin": False,
                }
            except Exception:
                ctx["perms_usuario"] = _DEFAULT_PERMS

    return ctx
