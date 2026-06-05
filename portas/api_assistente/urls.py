from django.urls import path
from .views import CalcularPortaView, OpcoesView, SchemaView

urlpatterns = [
    path("opcoes/", OpcoesView.as_view(), name="assistente_opcoes"),
    path("calcular-porta/", CalcularPortaView.as_view(), name="assistente_calcular_porta"),
    path("schema.json", SchemaView.as_view(), name="assistente_schema"),
]
