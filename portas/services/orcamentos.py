import logging
from datetime import date, timedelta

logger = logging.getLogger(__name__)


def limpar_orcamentos_expirados():
    """Exclui orçamentos cujo campo `data` seja anterior ao limite configurado."""
    from portas.models import ConfiguracaoEmpresa, Pedido

    config = ConfiguracaoEmpresa.get()
    dias = config.dias_expiracao_orcamento

    if not dias:
        logger.info("Limpeza de orçamentos desativada (0 dias).")
        return

    limite = date.today() - timedelta(days=dias)
    resultado = Pedido.objects.filter(status="orcamento", data__lt=limite).delete()
    qtd = resultado[0] if resultado else 0
    logger.info("Limpeza de orçamentos: %d excluído(s) (limite: %s).", qtd, limite)
