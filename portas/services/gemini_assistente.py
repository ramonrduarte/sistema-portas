"""
Integração com a API Gemini (Google AI) para o chat público de orçamento.

O assistente usa "function calling": o modelo pode chamar `listar_opcoes` e
`calcular_porta`, que são executadas fazendo requisições HTTP à própria API
do assistente (portas/api_assistente/) — o mesmo backend já usado pelo
Custom GPT, autenticado com o GPT_API_TOKEN. Isso garante que o cálculo
seja sempre feito pela mesma lógica validada, sem duplicação.
"""
import time

import requests

GEMINI_API_BASE = "https://generativelanguage.googleapis.com/v1beta"

MAX_RODADAS_FUNCAO = 5

# O modelo às vezes responde 503 ("overloaded"/"high demand") por instabilidade
# transitória do free tier do Google — vale a pena tentar de novo automaticamente
# antes de mostrar o erro para o usuário.
RETRIES_503 = 2
ESPERA_RETRY_SEGUNDOS = 3

INSTRUCAO_SISTEMA = (
    "Você é um assistente de orçamentos do Sistema de Portas. Ajude o usuário "
    "a montar e calcular o valor de uma porta, usando exclusivamente as funções "
    "disponíveis (listar_opcoes e calcular_porta) para obter dados reais do "
    "catálogo e do cálculo — nunca invente IDs, preços ou valores. "
    "Sempre que precisar de IDs de perfil, vidro, puxador, divisor ou serviço, "
    "use listar_opcoes primeiro. Responda de forma objetiva e amigável, em português."
)

FUNCOES = [
    {
        "name": "listar_opcoes",
        "description": (
            "Lista o catálogo disponível para orçamento: perfis, perfis-puxador, "
            "puxadores simples, divisores, vidros, acabamentos e serviços de porta, "
            "com seus respectivos IDs e compatibilidades. Use para descobrir os IDs "
            "necessários antes de chamar calcular_porta."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "busca": {
                    "type": "string",
                    "description": "Filtra os itens cuja descrição contenha este texto (opcional)",
                },
                "acabamento": {
                    "type": "string",
                    "description": "Filtra pelo nome do acabamento (opcional)",
                },
            },
        },
    },
    {
        "name": "calcular_porta",
        "description": (
            "Calcula o valor de uma porta a partir das opções escolhidas. "
            "Os IDs de perfil, vidro, puxador, divisor e serviços devem ser "
            "obtidos antes via listar_opcoes."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "largura_mm": {"type": "integer", "description": "Largura da porta em milímetros"},
                "altura_mm": {"type": "integer", "description": "Altura da porta em milímetros"},
                "quantidade": {"type": "integer", "description": "Quantidade de portas iguais (padrão 1)"},
                "perfil_id": {"type": "integer", "description": "ID do perfil (obrigatório)"},
                "perfil_puxador_id": {"type": "integer", "description": "ID do perfil-puxador (opcional)"},
                "qtd_perfil_puxador": {"type": "integer", "description": "1 ou 2 — obrigatório se perfil_puxador_id for informado"},
                "puxador_id": {"type": "integer", "description": "ID do puxador simples (opcional, exclusivo com perfil_puxador)"},
                "qtd_puxador": {"type": "integer", "description": "1 ou 2 — obrigatório se puxador_id for informado"},
                "puxador_tamanho_mm": {"type": "integer", "description": "Tamanho do puxador simples em mm — obrigatório se puxador_id for informado"},
                "vidro_id": {"type": "integer", "description": "ID do vidro (opcional)"},
                "divisor_id": {"type": "integer", "description": "ID do divisor (opcional)"},
                "qtd_divisor": {"type": "integer", "description": "Quantidade de divisores — obrigatório se divisor_id for informado"},
                "puxador_sobreposto": {"type": "boolean", "description": "Se o puxador é sobreposto (padrão true) — afeta o cálculo de serviços"},
                "servicos_porta_ids": {
                    "type": "array",
                    "items": {"type": "integer"},
                    "description": "IDs dos serviços de porta selecionados (opcional, obtidos em listar_opcoes)",
                },
                "desconto": {"type": "number", "description": "Percentual de desconto (0-100) sobre o valor base + serviços (opcional)"},
                "adicionais": {
                    "type": "array",
                    "items": {
                        "type": "object",
                        "properties": {
                            "valor": {"type": "number"},
                            "descricao": {"type": "string"},
                        },
                    },
                    "description": "Lista de até 4 valores adicionais, cada um com valor e descrição (opcional)",
                },
            },
            "required": ["largura_mm", "altura_mm", "perfil_id"],
        },
    },
]


class GeminiError(Exception):
    pass


def _post_com_retry(url, api_key, body):
    """POST ao Gemini com novas tentativas em caso de 503 (sobrecarga transitória)."""
    tentativa = 0
    while True:
        resp = requests.post(url, params={"key": api_key}, json=body, timeout=60)
        if resp.status_code != 503 or tentativa >= RETRIES_503:
            return resp
        tentativa += 1
        time.sleep(ESPERA_RETRY_SEGUNDOS)


def _executar_funcao(nome, args, *, base_url_api, token_api):
    """Executa a função chamada pelo Gemini delegando para a API do assistente."""
    headers = {"Authorization": f"Bearer {token_api}"}

    if nome == "listar_opcoes":
        params = {}
        if args.get("busca"):
            params["busca"] = args["busca"]
        if args.get("acabamento"):
            params["acabamento"] = args["acabamento"]
        resp = requests.get(f"{base_url_api}/opcoes/", params=params, headers=headers, timeout=30)
    elif nome == "calcular_porta":
        resp = requests.post(f"{base_url_api}/calcular-porta/", json=args, headers=headers, timeout=30)
    else:
        return {"erro": f"Função desconhecida: {nome}"}

    try:
        return resp.json()
    except ValueError:
        return {"erro": f"Resposta inválida da API ({resp.status_code})"}


def _extrair_texto_e_chamadas(candidate):
    texto = ""
    chamadas = []
    for part in candidate.get("content", {}).get("parts", []):
        if "text" in part:
            texto += part["text"]
        if "functionCall" in part:
            chamadas.append(part["functionCall"])
    return texto, chamadas


def testar_api_key(api_key, modelo="gemini-2.0-flash"):
    """Faz uma chamada mínima para validar a chave de API. Retorna (ok, msg)."""
    if not api_key:
        return False, "Informe uma chave de API."

    url = f"{GEMINI_API_BASE}/models/{modelo}:generateContent"
    body = {"contents": [{"role": "user", "parts": [{"text": "Responda apenas: ok"}]}]}

    try:
        resp = requests.post(url, params={"key": api_key}, json=body, timeout=20)
    except requests.RequestException as e:
        return False, f"Falha de conexão: {e}"

    if resp.status_code == 200:
        return True, "Conexão estabelecida com sucesso."

    try:
        detalhe = resp.json().get("error", {}).get("message", resp.text)
    except ValueError:
        detalhe = resp.text
    return False, f"Erro {resp.status_code}: {detalhe}"


def enviar_mensagem(config, pergunta, historico, *, base_url_api, token_api):
    """
    Envia uma mensagem ao Gemini, executando as funções solicitadas (function
    calling) até obter uma resposta final em texto.

    `historico` é uma lista de mensagens no formato da API Gemini
    (role "user"/"model", parts). Retorna (texto_resposta, novo_historico).
    """
    api_key = config.api_key
    if not api_key:
        raise GeminiError("Assistente IA não configurado: chave de API ausente.")

    url = f"{GEMINI_API_BASE}/models/{config.modelo}:generateContent"
    contents = list(historico) + [{"role": "user", "parts": [{"text": pergunta}]}]

    for _ in range(MAX_RODADAS_FUNCAO):
        body = {
            "system_instruction": {"parts": [{"text": INSTRUCAO_SISTEMA}]},
            "contents": contents,
            "tools": [{"functionDeclarations": FUNCOES}],
        }
        resp = _post_com_retry(url, api_key, body)
        if resp.status_code != 200:
            try:
                detalhe = resp.json().get("error", {}).get("message", resp.text)
            except ValueError:
                detalhe = resp.text
            if resp.status_code == 503:
                raise GeminiError(
                    "O Gemini está temporariamente sobrecarregado (alta demanda no "
                    "modelo gratuito). Aguarde alguns segundos e tente enviar a "
                    "mensagem novamente."
                )
            if resp.status_code == 429:
                raise GeminiError(
                    "O limite diário gratuito do Gemini para este modelo foi atingido "
                    "(a conta gratuita permite poucas mensagens por dia). Não adianta "
                    "tentar de novo agora — espere a cota renovar (geralmente no dia "
                    "seguinte) ou ative o faturamento no Google AI Studio para aumentar "
                    "o limite."
                )
            raise GeminiError(f"Erro {resp.status_code} ao consultar o Gemini: {detalhe}")

        dados = resp.json()
        candidatos = dados.get("candidates") or []
        if not candidatos:
            raise GeminiError("O Gemini não retornou nenhuma resposta.")

        candidate = candidatos[0]
        texto, chamadas = _extrair_texto_e_chamadas(candidate)
        contents.append(candidate.get("content", {"role": "model", "parts": []}))

        if not chamadas:
            return texto.strip(), contents

        partes_resposta = []
        for chamada in chamadas:
            nome = chamada.get("name")
            args = chamada.get("args") or {}
            resultado = _executar_funcao(nome, args, base_url_api=base_url_api, token_api=token_api)
            partes_resposta.append({
                "functionResponse": {"name": nome, "response": {"resultado": resultado}},
            })
        contents.append({"role": "function", "parts": partes_resposta})

    raise GeminiError("O assistente não conseguiu concluir a resposta após várias tentativas.")
