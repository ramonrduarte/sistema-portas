from django.urls import path
from . import views

urlpatterns = [
    # Porta 1p
    path("porta-1p/", views.calcular_porta_1p_view, name="porta_1p"),
    path(
        "porta-1p/opcoes-compativeis/",
        views.carregar_opcoes_compativeis,
        name="porta_1p_opcoes_compativeis",
    ),

    # Perfis (estrutura)
    path("perfis/", views.lista_perfis, name="lista_perfis"),
    path("perfis/novo/", views.cadastrar_perfil, name="cadastrar_perfil"),
    path("perfis/<int:pk>/editar/", views.cadastrar_perfil, name="editar_perfil"),

    # Acabamentos
    path("acabamentos/", views.lista_acabamentos, name="lista_acabamentos"),
    path("acabamentos/novo/", views.cadastrar_acabamento, name="cadastrar_acabamento"),
    path(
        "acabamentos/<int:pk>/editar/",
        views.cadastrar_acabamento,
        name="editar_acabamento",
    ),

    # Perfil Puxador
    path("perfis-puxador/", views.lista_perfis_puxador, name="lista_perfis_puxador"),
    path(
        "perfis-puxador/novo/",
        views.cadastrar_perfil_puxador,
        name="cadastrar_perfil_puxador",
    ),
    path(
        "perfis-puxador/<int:pk>/editar/",
        views.cadastrar_perfil_puxador,
        name="editar_perfil_puxador",
    ),

    # Puxadores simples
    path("puxadores/", views.lista_puxadores, name="lista_puxadores"),
    path("puxadores/novo/", views.cadastrar_puxador, name="cadastrar_puxador"),
    path(
        "puxadores/<int:pk>/editar/",
        views.cadastrar_puxador,
        name="editar_puxador",
    ),

    # HTMX - combinações completas (puxadores + espessura + vidros)
    path(
        "perfis/opcoes-combinacoes/",
        views.carregar_combinacoes_perfil,
        name="perfil_opcoes_combinacoes",
    ),

    # HTMX - apenas lista de vidros ao trocar espessura
    path(
        "perfis/vidros-por-espessura/",
        views.carregar_vidros_por_espessura,
        name="perfil_vidros_por_espessura",
    ),

    # Espessuras de vidro
    path("espessuras/", views.lista_espessuras, name="lista_espessuras"),
    path("espessuras/novo/", views.cadastrar_espessura, name="cadastrar_espessura"),
    path("espessuras/<int:pk>/editar/", views.cadastrar_espessura, name="editar_espessura"),

    # Vidros
    path("vidros/", views.lista_vidros, name="lista_vidros"),
    path("vidros/novo/", views.cadastrar_vidro, name="cadastrar_vidro"),
    path("vidros/<int:pk>/editar/", views.cadastrar_vidro, name="editar_vidro"),

    # Divisores
    path("divisores/", views.lista_divisores, name="lista_divisores"),
    path("divisores/novo/", views.cadastrar_divisor, name="cadastrar_divisor"),
    path("divisores/<int:pk>/editar/", views.cadastrar_divisor, name="editar_divisor"),

    # Clientes
    path("clientes/", views.lista_clientes, name="lista_clientes"),
    path("clientes/novo/", views.cadastrar_cliente, name="cadastrar_cliente"),
    path("clientes/<int:pk>/editar/", views.cadastrar_cliente, name="editar_cliente"),
]
