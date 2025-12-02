from django.contrib import admin
from .models import (
    Acabamento,
    Perfil,
    PerfilPuxador,
    Puxador,
    Divisor,
    VidroBase,
    ExtraServico,
    Orcamento,
    ItemOrcamento,
)

admin.site.register(Acabamento)
admin.site.register(Perfil)
admin.site.register(PerfilPuxador)
admin.site.register(Puxador)
admin.site.register(Divisor)
admin.site.register(VidroBase)
admin.site.register(ExtraServico)
admin.site.register(Orcamento)
admin.site.register(ItemOrcamento)
