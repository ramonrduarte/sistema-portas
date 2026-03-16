from django.urls import path
from . import views
from .views import ClienteListView, ClienteCreateView, ClienteUpdateView, ClienteDeleteView, UsuarioListView, UsuarioCreateView, UsuarioUpdateView, UsuarioDeleteView


urlpatterns = [

    # Perfis (estrutura)
    path("perfis/", views.lista_perfis, name="lista_perfis"),
    path("perfis/novo/", views.cadastrar_perfil, name="cadastrar_perfil"),
    path("perfis/<int:pk>/editar/", views.cadastrar_perfil, name="editar_perfil"),
    path("perfis/<int:pk>/excluir/", views.excluir_perfil, name="excluir_perfil"),

    # Acabamentos
    path("acabamentos/", views.lista_acabamentos, name="lista_acabamentos"),
    path("acabamentos/novo/", views.cadastrar_acabamento, name="cadastrar_acabamento"),
    path("acabamentos/<int:pk>/editar/", views.cadastrar_acabamento, name="editar_acabamento"),
    path("acabamentos/<int:pk>/excluir/", views.excluir_acabamento, name="excluir_acabamento"),

    # Perfil Puxador
    path("perfis-puxador/", views.lista_perfis_puxador, name="lista_perfis_puxador"),
    path("perfis-puxador/novo/", views.cadastrar_perfil_puxador, name="cadastrar_perfil_puxador"),
    path("perfis-puxador/<int:pk>/editar/", views.cadastrar_perfil_puxador, name="editar_perfil_puxador"),
    path("perfis-puxador/<int:pk>/excluir/", views.excluir_perfil_puxador, name="excluir_perfil_puxador"),

    # Puxadores simples
    path("puxadores/", views.lista_puxadores, name="lista_puxadores"),
    path("puxadores/novo/", views.cadastrar_puxador, name="cadastrar_puxador"),
    path("puxadores/<int:pk>/editar/",views.cadastrar_puxador, name="editar_puxador"),
    path("puxadores/<int:pk>/excluir/", views.excluir_puxador, name="excluir_puxador"),

    # HTMX - combinações completas (puxadores + espessura + vidros)
    path("perfis/compativeis-por-acabamento/", views.perfil_compativeis_por_acabamento, name="perfil_compativeis_por_acabamento"),

    path("perfis/vidros-por-espessuras/", views.perfil_vidros_por_espessuras, name="perfil_vidros_por_espessuras"),

    # Espessuras de vidro
    path('espessuras/', views.lista_espessuras, name='lista_espessuras'),
    path('espessuras/nova/', views.cadastrar_espessura, name='cadastrar_espessura'),
    path('espessuras/<int:pk>/editar/', views.cadastrar_espessura, name='editar_espessura'),
    path('espessuras/<int:pk>/excluir/', views.excluir_espessura, name='excluir_espessura'),

    # Vidros
    path("vidros/", views.lista_vidros, name="lista_vidros"),
    path("vidros/novo/", views.cadastrar_vidro, name="cadastrar_vidro"),
    path("vidros/<int:pk>/editar/", views.cadastrar_vidro, name="editar_vidro"),
    path("vidros/<int:pk>/excluir/", views.excluir_vidro, name="excluir_vidro"),

    # Divisores
    path("divisores/", views.lista_divisores, name="lista_divisores"),
    path("divisores/novo/", views.cadastrar_divisor, name="cadastrar_divisor"),
    path("divisores/<int:pk>/editar/", views.cadastrar_divisor, name="editar_divisor"),
    path("divisores/<int:pk>/excluir/", views.excluir_divisor, name="excluir_divisor"),

    # Clientes
    path("clientes/", ClienteListView.as_view(), name="clientes_lista"),
    path("clientes/novo/", ClienteCreateView.as_view(), name="clientes_novo"),
    path("clientes/<int:pk>/", views.cliente_detalhe, name="cliente_detalhe"),
    path("clientes/<int:pk>/editar/", ClienteUpdateView.as_view(), name="clientes_editar"),
    path("clientes/<int:pk>/excluir/", ClienteDeleteView.as_view(), name="clientes_excluir"),

    # Usuarios
    path("usuarios/", UsuarioListView.as_view(), name="usuarios_lista"),
    path("usuarios/novo/", UsuarioCreateView.as_view(), name="usuarios_novo"),
    path("usuarios/<int:pk>/editar/", UsuarioUpdateView.as_view(), name="usuarios_editar"),
    path("usuarios/<int:pk>/excluir/", UsuarioDeleteView.as_view(), name="usuarios_excluir"),

    # ==== PEDIDOS ====
    path("pedidos/", views.pedidos_lista, name="pedidos_lista"),
    path("pedidos/novo/", views.pedido_novo, name="pedido_novo"),
    path("pedidos/controle/", views.pedido_controle, name="pedido_controle"),
    path("pedidos/insumos/", views.pedido_insumos, name="pedido_insumos"),
    path("pedidos/plano-corte/", views.pedido_plano_corte, name="pedido_plano_corte"),
    path("pedidos/relatorio/", views.pedido_relatorio, name="pedido_relatorio"),

    # HTMX - cliente inline
    path("pedidos/htmx/clientes-sugestoes/", views.htmx_clientes_sugestoes, name="htmx_clientes_sugestoes"),
    path("pedidos/htmx/cliente-selecionar/<int:pk>/", views.htmx_cliente_selecionar, name="htmx_cliente_selecionar"),

    # HTMX - dependências acabamento/perfil/opções
    path("pedidos/htmx/perfis-por-acabamento/", views.htmx_perfis_por_acabamento, name="htmx_perfis_por_acabamento"),
    path("pedidos/htmx/opcoes-por-perfil/", views.htmx_opcoes_por_perfil, name="htmx_opcoes_por_perfil"),
    path("pedidos/htmx/calcular-item/", views.htmx_calcular_item, name="htmx_calcular_item"),
    path("pedidos/htmx/item-temp/add/", views.pedido_item_temp_add, name="pedido_item_temp_add"),
    path("pedidos/htmx/item-temp/<int:idx>/remover/", views.pedido_item_temp_remove, name="pedido_item_temp_remove"),

    # Detalhe e itens (com <int:pk> devem vir DEPOIS das rotas htmx/)
    path("pedidos/<int:pk>/", views.pedido_detalhe, name="pedido_detalhe"),
    path("pedidos/<int:pk>/excluir/", views.pedido_excluir, name="pedido_excluir"),
    path("pedidos/<int:pk>/cancelar/", views.pedido_cancelar, name="pedido_cancelar"),
    path("pedidos/<int:pk>/reabrir/", views.pedido_reabrir, name="pedido_reabrir"),
    path("pedidos/<int:pk>/imprimir/", views.pedido_imprimir, name="pedido_imprimir"),
    path("pedidos/<int:pedido_pk>/itens/novo/", views.pedido_item_novo, name="pedido_item_novo"),
    path("pedidos/<int:pedido_pk>/itens/<int:item_pk>/remover/", views.htmx_remove_item, name="htmx_remove_item"),
    path("pedidos/<int:pk>/observacoes/", views.pedido_observacoes, name="pedido_observacoes"),
    path("pedidos/<int:pk>/previsao/", views.pedido_previsao, name="pedido_previsao"),
    path("pedidos/<int:pk>/corte/", views.pedido_enviar_corte, name="pedido_enviar_corte"),
    path("pedidos/<int:pk>/montagem/", views.pedido_enviar_montagem, name="pedido_enviar_montagem"),
    path("pedidos/<int:pk>/wise/", views.pedido_enviar_wise, name="pedido_enviar_wise"),
    path("pedidos/<int:pk>/duplicar/", views.pedido_duplicar, name="pedido_duplicar"),

    # Integrações
    path("integracoes/bimer/",                      views.bimer_config,                name="bimer_config"),
    path("integracoes/bimer/testar/",               views.bimer_testar_conexao,        name="bimer_testar_conexao"),
    path("integracoes/bimer/sincronizar/",          views.bimer_sincronizar,           name="bimer_sincronizar"),
    path("integracoes/bimer/sincronizar-clientes/", views.bimer_sincronizar_clientes,  name="bimer_sincronizar_clientes"),

    # Configurações
    path("configuracoes/", views.configuracoes_empresa, name="configuracoes_empresa"),

]
