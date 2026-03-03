from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .viewsets import AcabamentoViewSet, EspessuraVidroViewSet, VidroBaseViewSet, PuxadorViewSet, DivisorViewSet, PerfilViewSet, PerfilPuxadorViewSet, ClienteViewSet

router = DefaultRouter()
router.register(r"acabamentos", AcabamentoViewSet)
router.register(r"espessuras", EspessuraVidroViewSet)
router.register(r"vidros", VidroBaseViewSet)
router.register(r"puxadores", PuxadorViewSet)
router.register(r"divisores", DivisorViewSet)
router.register(r"perfis", PerfilViewSet)
router.register(r"perfil-puxadores", PerfilPuxadorViewSet)
router.register(r"clientes", ClienteViewSet)

urlpatterns = [
    path("", include(router.urls)),
]
