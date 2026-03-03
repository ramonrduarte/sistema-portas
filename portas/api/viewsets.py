from rest_framework.viewsets import ModelViewSet
from portas.models import Acabamento, EspessuraVidro, VidroBase, Puxador, Divisor, Perfil, PerfilPuxador, Cliente
from .serializers import (
    AcabamentoSerializer,
    EspessuraVidroSerializer,
    VidroBaseSerializer,
    PuxadorSerializer,
    DivisorSerializer,
    PerfilSerializer,
    PerfilPuxadorSerializer,
    ClienteSerializer
)

class AcabamentoViewSet(ModelViewSet):
    queryset = Acabamento.objects.all().order_by("nome")
    serializer_class = AcabamentoSerializer

class EspessuraVidroViewSet(ModelViewSet):
    queryset = EspessuraVidro.objects.all().order_by("valor_mm")
    serializer_class = EspessuraVidroSerializer

class VidroBaseViewSet(ModelViewSet):
    queryset = VidroBase.objects.select_related("espessura").all()
    serializer_class = VidroBaseSerializer
    lookup_field = "codigo"

class PuxadorViewSet(ModelViewSet):
    queryset = Puxador.objects.all().order_by("descricao")
    serializer_class = PuxadorSerializer
    lookup_field = "codigo"

class DivisorViewSet(ModelViewSet):
    queryset = Divisor.objects.all().order_by("descricao")
    serializer_class = DivisorSerializer
    lookup_field = "codigo"

class PerfilViewSet(ModelViewSet):
    queryset = (
        Perfil.objects
        .select_related("acabamento")
        .prefetch_related(
            "puxadores_compativeis",
            "puxadores_simples_compativeis",
            "divisores_compativeis",
            "vidros_compativeis",
            "espessuras_vidro_compativeis",
        )
        .all()
        .order_by("descricao")
    )
    serializer_class = PerfilSerializer
    lookup_field = "codigo"

class PerfilPuxadorViewSet(ModelViewSet):
    queryset = (
        PerfilPuxador.objects
        .select_related("acabamento")
        .all()
        .order_by("descricao")
    )
    serializer_class = PerfilPuxadorSerializer
    lookup_field = "codigo"

class ClienteViewSet(ModelViewSet):
    queryset = Cliente.objects.all().order_by("nome")
    serializer_class = ClienteSerializer
    lookup_field = "codigo"   