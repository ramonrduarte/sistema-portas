from datetime import date, timedelta
from collections import defaultdict

from django.conf import settings
from django.db.models import Count, Exists, OuterRef
from django.http import Http404, HttpResponseBadRequest
from django.shortcuts import render

from ..models import AssistenteIAConfig, ConfiguracaoEmpresa, Pedido, PedidoItem, PedidoItemVidro
from ..services import gemini_assistente as svc_gemini


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


# ── Chat público de orçamento via IA (Gemini) ────────────────────────────────

def _sessao_chat_key(token):
    return f"assistente_chat_{token}"


def _verificar_token_assistente(token):
    config = AssistenteIAConfig.get()
    if str(config.token_chat) != str(token):
        raise Http404
    if not (config.ativo and config.chave_configurada()):
        raise Http404
    return config


def _historico_para_exibicao(contents):
    mensagens = []
    for item in contents:
        role = item.get("role")
        if role not in ("user", "model"):
            continue
        texto = "".join(part.get("text", "") for part in item.get("parts", []))
        if texto.strip():
            mensagens.append({"role": role, "texto": texto.strip()})
    return mensagens


def assistente_chat(request, token):
    config = _verificar_token_assistente(token)
    contents = request.session.get(_sessao_chat_key(token), [])
    return render(request, "portas/publico/assistente_chat.html", {
        "config": config,
        "token": token,
        "mensagens": _historico_para_exibicao(contents),
    })


def assistente_chat_mensagem(request, token):
    """HTMX POST — envia uma pergunta ao assistente e retorna as novas mensagens."""
    config = _verificar_token_assistente(token)
    if request.method != "POST":
        return HttpResponseBadRequest()

    pergunta = (request.POST.get("pergunta") or "").strip()
    if not pergunta:
        return HttpResponseBadRequest()

    sessao_key = _sessao_chat_key(token)
    contents = request.session.get(sessao_key, [])

    base_url_api = request.build_absolute_uri("/api/assistente")
    erro = None
    try:
        _, novo_contents = svc_gemini.enviar_mensagem(
            config, pergunta, contents,
            base_url_api=base_url_api, token_api=settings.GPT_API_TOKEN,
        )
    except svc_gemini.GeminiError as e:
        novo_contents = contents + [
            {"role": "user", "parts": [{"text": pergunta}]},
            {"role": "model", "parts": [{"text": f"⚠️ {e}"}]},
        ]
        erro = str(e)
    else:
        config.registrar_chamada()

    request.session[sessao_key] = novo_contents
    request.session.modified = True

    # Apenas a resposta do assistente — a mensagem do usuário já foi exibida
    # de forma otimista pelo JS no momento do envio.
    novas_mensagens = _historico_para_exibicao(novo_contents)[-1:]
    return render(request, "portas/publico/_assistente_chat_mensagens.html", {
        "mensagens": novas_mensagens,
        "erro": erro,
    })
