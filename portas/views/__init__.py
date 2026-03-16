from .produtos import (
    lista_perfis_puxador,
    cadastrar_perfil_puxador,
    excluir_perfil_puxador,
    lista_acabamentos,
    cadastrar_acabamento,
    excluir_acabamento,
    lista_perfis,
    cadastrar_perfil,
    excluir_perfil,
    lista_puxadores,
    cadastrar_puxador,
    excluir_puxador,
    lista_espessuras,
    cadastrar_espessura,
    excluir_espessura,
    lista_vidros,
    cadastrar_vidro,
    excluir_vidro,
    lista_divisores,
    cadastrar_divisor,
    excluir_divisor,
    perfil_vidros_por_espessuras,
    perfil_compativeis_por_acabamento,
)
from .clientes import (
    ClienteListView,
    ClienteCreateView,
    ClienteUpdateView,
    ClienteDeleteView,
    cliente_detalhe,
)
from .usuarios import (
    UsuarioListView,
    UsuarioCreateView,
    UsuarioUpdateView,
    UsuarioDeleteView,
)
from .pedidos import (
    pedidos_lista,
    pedido_novo,
    pedido_detalhe,
    pedido_excluir,
    pedido_cancelar,
    pedido_reabrir,
    pedido_imprimir,
    pedido_item_novo,
    pedido_item_temp_add,
    pedido_item_temp_remove,
    pedido_controle,
    pedido_insumos,
    pedido_plano_corte,
    pedido_relatorio,
    htmx_remove_item,
    htmx_calcular_item,
    htmx_cliente_selecionar,
    htmx_perfis_por_acabamento,
    htmx_opcoes_por_perfil,
    htmx_clientes_sugestoes,
    pedido_observacoes,
    pedido_previsao,
    pedido_enviar_corte,
    pedido_enviar_montagem,
    pedido_enviar_wise,
    pedido_duplicar,
)

__all__ = [
    # produtos
    "lista_perfis_puxador", "cadastrar_perfil_puxador", "excluir_perfil_puxador",
    "lista_acabamentos", "cadastrar_acabamento", "excluir_acabamento",
    "lista_perfis", "cadastrar_perfil", "excluir_perfil",
    "lista_puxadores", "cadastrar_puxador", "excluir_puxador",
    "lista_espessuras", "cadastrar_espessura", "excluir_espessura",
    "lista_vidros", "cadastrar_vidro", "excluir_vidro",
    "lista_divisores", "cadastrar_divisor", "excluir_divisor",
    "perfil_vidros_por_espessuras", "perfil_compativeis_por_acabamento",
    # clientes
    "ClienteListView", "ClienteCreateView", "ClienteUpdateView", "ClienteDeleteView", "cliente_detalhe",
    # usuários
    "UsuarioListView", "UsuarioCreateView", "UsuarioUpdateView", "UsuarioDeleteView",
    # pedidos
    "pedidos_lista", "pedido_novo", "pedido_detalhe", "pedido_excluir", "pedido_cancelar", "pedido_reabrir", "pedido_imprimir",
    "pedido_item_novo", "pedido_item_temp_add", "pedido_item_temp_remove",
    "pedido_controle", "pedido_insumos", "pedido_plano_corte", "pedido_relatorio",
    "htmx_remove_item", "htmx_calcular_item",
    "htmx_cliente_selecionar", "htmx_perfis_por_acabamento",
    "htmx_opcoes_por_perfil", "htmx_clientes_sugestoes", "pedido_observacoes", "pedido_previsao",
    "pedido_enviar_corte", "pedido_enviar_montagem", "pedido_enviar_wise",
    # integrações
    "bimer_config", "bimer_testar_conexao", "bimer_sincronizar", "bimer_sincronizar_clientes",
    # configurações
    "configuracoes_empresa",
]

from .integracoes import bimer_config, bimer_testar_conexao, bimer_sincronizar, bimer_sincronizar_clientes
from .configuracoes import configuracoes_empresa
