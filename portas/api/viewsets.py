from rest_framework.viewsets import ModelViewSet
from rest_framework.permissions import IsAuthenticated, IsAdminUser

from portas.models import Acabamento, EspessuraVidro, VidroBase, Puxador, Divisor, Perfil, PerfilPuxador, Cliente
from .serializers import (
    AcabamentoSerializer,
    EspessuraVidroSerializer,
    VidroBaseSerializer,
    PuxadorSerializer,
    DivisorSerializer,
    PerfilSerializer,
    PerfilPuxadorSerializer,
    ClienteSerializer,
)


class ReadOrAdminMixin:
    """Leitura: qualquer usuário autenticado. Escrita (POST/PUT/PATCH/DELETE): apenas staff."""
    def get_permissions(self):
        if self.action in ("list", "retrieve"):
            return [IsAuthenticated()]
        return [IsAdminUser()]


class AcabamentoViewSet(ReadOrAdminMixin, ModelViewSet):
    queryset = Acabamento.objects.all().order_by("nome")
    serializer_class = AcabamentoSerializer


class EspessuraVidroViewSet(ReadOrAdminMixin, ModelViewSet):
    queryset = EspessuraVidro.objects.all().order_by("valor_mm")
    serializer_class = EspessuraVidroSerializer


class VidroBaseViewSet(ReadOrAdminMixin, ModelViewSet):
    queryset = VidroBase.objects.select_related("espessura").all()
    serializer_class = VidroBaseSerializer
    lookup_field = "codigo"


class PuxadorViewSet(ReadOrAdminMixin, ModelViewSet):
    queryset = Puxador.objects.all().order_by("descricao")
    serializer_class = PuxadorSerializer
    lookup_field = "codigo"


class DivisorViewSet(ReadOrAdminMixin, ModelViewSet):
    queryset = Divisor.objects.all().order_by("descricao")
    serializer_class = DivisorSerializer
    lookup_field = "codigo"


class PerfilViewSet(ReadOrAdminMixin, ModelViewSet):
    queryset = Perfil.objects.select_related("acabamento").all()
    serializer_class = PerfilSerializer
    lookup_field = "codigo"


class PerfilPuxadorViewSet(ReadOrAdminMixin, ModelViewSet):
    queryset = PerfilPuxador.objects.select_related("acabamento").all()
    serializer_class = PerfilPuxadorSerializer
    lookup_field = "codigo"


class ClienteViewSet(ReadOrAdminMixin, ModelViewSet):
    queryset = Cliente.objects.all().order_by("nome")
    serializer_class = ClienteSerializer
