from datetime import date, timedelta
from collections import defaultdict

from django.db.models import Count, Exists, OuterRef
from django.http import Http404
from django.shortcuts import render

from ..models import ConfiguracaoEmpresa, Pedido, PedidoItem, PedidoItemVidro


def _verificar_token(token):
    config = ConfiguracaoEmpresa.get()
    if str(config.token_monitor) != str(token):
        raise Http404
    return config


def monitor_producao(request, token):
    _verificar_token(token)
    config = ConfiguracaoEmpresa.get()
    pedidos = (
        Pedido.objects
        .filter(status="producao")
        .select_related("cliente", "usuario")
        .annotate(
            tem_perfil_pendente=Exists(
                PedidoItem.objects.filter(pedido=OuterRef("pk"), perfil_cortado=False)
            ),
            tem_itens_com_vidro=Exists(
                PedidoItem.objects.filter(pedido=OuterRef("pk"), vidro__isnull=False)
            ),
            tem_vidro_pendente=Exists(
                PedidoItem.objects.filter(pedido=OuterRef("pk"), vidro_cortado=False, vidro__isnull=False)
            ),
            tem_vidro_avulso_pendente=Exists(
                PedidoItemVidro.objects.filter(pedido=OuterRef("pk"), vidro_cortado=False)
            ),
            tem_montagem_pendente=Exists(
                PedidoItem.objects.filter(pedido=OuterRef("pk"), montagem_feita=False)
            ),
        )
        .order_by("data", "id")
    )
    return render(request, "portas/publico/monitor_producao.html", {
        "pedidos": pedidos,
        "config": config,
        "token": token,
    })


def agenda_entregas(request, token):
    _verificar_token(token)
    config = ConfiguracaoEmpresa.get()
    hoje = date.today()
    limite = hoje + timedelta(weeks=5)

    pedidos_qs = (
        Pedido.objects
        .filter(data_previsao__gte=hoje, data_previsao__lte=limite)
        .exclude(status__in=["cancelado", "concluido"])
        .select_related("cliente")
        .order_by("data_previsao", "id")
    )

    por_dia = defaultdict(list)
    for p in pedidos_qs:
        por_dia[p.data_previsao].append(p)

    # Semanas completas (seg–dom) cobrindo hoje até limite
    inicio = hoje - timedelta(days=hoje.weekday())  # segunda da semana atual
    semanas = []
    for w in range(5):
        semana = []
        for d in range(7):
            dia = inicio + timedelta(weeks=w, days=d)
            semana.append({
                "data": dia,
                "pedidos": por_dia.get(dia, []),
                "hoje": dia == hoje,
                "passado": dia < hoje,
            })
        semanas.append(semana)

    DIAS_PT = ["Seg", "Ter", "Qua", "Qui", "Sex", "Sáb", "Dom"]
    return render(request, "portas/publico/agenda_entregas.html", {
        "semanas": semanas,
        "dias_semana": DIAS_PT,
        "config": config,
        "token": token,
        "hoje": hoje,
    })
