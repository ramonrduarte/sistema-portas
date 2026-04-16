"""
Serviço de integração com a API do Bimer (Alterdata).

Autenticação documentada em:
  https://bimer-api-docs.alterdata.com.br

Endpoints confirmados:
  POST /auth/token           — obtém access_token + refresh_token
  POST /auth/refresh-token   — renova tokens
  GET  /auth/validate        — valida token atual
  GET  /api/produtos?codigo={codigo}
       — busca produto por código → retorna identificador interno
  GET  /api/empresas/{id_empresa}/produtos/{bimer_id}/precos/{id_tabela}
       — retorna preço do produto para a empresa e tabela especificadas
"""
import logging
import requests
from datetime import datetime, timedelta, timezone as dt_tz

from django.utils import timezone

logger = logging.getLogger(__name__)


def _parse_expires(expires_raw):
    """
    Converte o campo expiresIn do Bimer para um datetime aware.

    O Bimer retorna expiresIn como Unix timestamp absoluto (segundos desde 1970),
    não como duração. Ex.: 1767139200 → 2026-xx-xx HH:MM.
    Se o valor for 0 ou inválido, assume 1 hora a partir de agora.
    """
    try:
        val = int(expires_raw)
        if val > 0:
            return datetime.fromtimestamp(val, tz=dt_tz.utc)
    except (TypeError, ValueError, OSError):
        pass
    return timezone.now() + timedelta(hours=1)

_TIMEOUT = 30        # segundos para chamadas de auth
_TIMEOUT_PRECO = 15  # segundos para chamadas de preço
_TIMEOUT_ENVIO = 60  # segundos para envio de pedidos (POST pode demorar mais)


# ── Autenticação ──────────────────────────────────────────────────────────────

def obter_token(config):
    """
    Autentica no Bimer com username + password.
    POST /auth/token  (multipart/form-data)
    Salva access_token, refresh_token e token_expires_at no config.
    """
    url = f"{config.base_url.rstrip('/')}/auth/token"
    resp = requests.post(
        url,
        data={"username": config.username, "password": config.password},
        timeout=_TIMEOUT,
    )
    resp.raise_for_status()
    data = resp.json()

    config.access_token     = data["accessToken"]
    config.refresh_token    = data.get("refreshToken", "")
    config.token_expires_at = _parse_expires(data.get("expiresIn"))
    config.save(update_fields=["access_token", "refresh_token", "token_expires_at"])
    return config.access_token


def renovar_token(config):
    """
    Renova tokens via POST /auth/refresh-token.
    Salva os novos tokens no config.
    """
    url = f"{config.base_url.rstrip('/')}/auth/refresh-token"
    resp = requests.post(
        url,
        data={
            "username":     config.username,
            "token":        config.access_token,
            "refreshToken": config.refresh_token,
        },
        timeout=_TIMEOUT,
    )
    resp.raise_for_status()
    data = resp.json()

    config.access_token     = data["accessToken"]
    config.refresh_token    = data.get("refreshToken", config.refresh_token)
    config.token_expires_at = _parse_expires(data.get("expiresIn"))
    config.save(update_fields=["access_token", "refresh_token", "token_expires_at"])
    return config.access_token


def get_valid_token(config):
    """
    Retorna um token válido.
    Tenta renovar via refresh_token; se falhar, re-autentica com username/password.
    """
    if config.token_valido():
        return config.access_token
    if config.refresh_token:
        try:
            return renovar_token(config)
        except Exception:
            logger.warning("Falha ao renovar token Bimer; re-autenticando.", exc_info=True)
    return obter_token(config)


def _bimer_request(config, method, path, **kwargs):
    """
    Faz uma requisição autenticada à API Bimer com retry automático de token.

    Fluxo:
      1. Obtém token válido (renova/reautentica se necessário)
      2. Faz a requisição com Authorization: Bearer
      3. Se retornar 401 → força re-autenticação e tenta mais uma vez
      4. Qualquer outro erro HTTP propaga normalmente

    Uso:
      resp = _bimer_request(config, "get", "/api/produtos", params={"codigo": "XYZ"})
      resp = _bimer_request(config, "post", "/api/venda/pedidos", json=payload)
    """
    base = config.base_url.rstrip("/")
    url  = f"{base}{path}"

    token = get_valid_token(config)
    headers = kwargs.pop("headers", {})
    headers["Authorization"] = f"Bearer {token}"

    resp = getattr(requests, method)(url, headers=headers, **kwargs)

    if resp.status_code == 401:
        # Token rejeitado pelo servidor — força nova autenticação e tenta uma vez mais
        token = obter_token(config)
        headers["Authorization"] = f"Bearer {token}"
        resp = getattr(requests, method)(url, headers=headers, **kwargs)

    resp.raise_for_status()
    return resp


def testar_conexao(config):
    """
    Testa as credenciais e a conectividade com a API.
    Retorna (True, mensagem) em caso de sucesso ou (False, mensagem) em caso de erro.
    """
    if not config.base_url or not config.username or not config.senha_configurada():
        return False, "Preencha URL base, usuário e senha antes de testar."
    try:
        token = obter_token(config)
        url   = f"{config.base_url.rstrip('/')}/auth/validate"
        resp  = requests.get(
            url,
            headers={"Authorization": f"Bearer {token}"},
            timeout=_TIMEOUT,
        )
        resp.raise_for_status()
        return True, "Conexão bem-sucedida. Token válido."
    except requests.HTTPError as e:
        corpo = e.response.text[:300] if e.response is not None else ""
        return False, f"Erro HTTP {e.response.status_code}: {corpo}"
    except requests.ConnectionError:
        return False, "Não foi possível conectar ao servidor. Verifique a URL base."
    except Exception as e:
        return False, str(e)


# ── Sincronização de preços ───────────────────────────────────────────────────

def _obter_bimer_id(config, obj):
    """
    Etapa 1: busca o identificador interno do produto no Bimer pelo código local.

    GET /api/produtos?codigo={codigo}
    Resposta esperada: { "identificador": "XXXXXXXXXX", ... }
    (ou lista com um item contendo "identificador")

    Salva o identificador em obj.bimer_id para evitar buscas futuras.
    Retorna o identificador ou None se não encontrado.
    """
    resp = _bimer_request(config, "get", "/api/produtos",
                          params={"codigo": obj.codigo}, timeout=_TIMEOUT_PRECO)
    data = resp.json()

    # Resposta no formato { "Erros": [...], "ListaObjetos": [...] }
    if isinstance(data, dict) and "ListaObjetos" in data:
        lista = data["ListaObjetos"]
        data  = lista[0] if lista else {}

    bimer_id = data.get("Identificador", "")
    if bimer_id:
        obj.bimer_id = bimer_id
        obj.save(update_fields=["bimer_id"])
        return bimer_id

    # Produto não encontrado ou ListaObjetos vazia
    raise ValueError(f"Produto {obj.codigo} não encontrado no Bimer.")


def _buscar_preco_bimer(config, obj):
    """
    Fluxo de 2 etapas para obter o preço atualizado de um produto:

    Etapa 1 — Obter o identificador interno do produto (bimer_id):
      - Se obj.bimer_id já estiver preenchido, usa o valor cacheado (pula a busca).
      - Caso contrário: GET /api/produtos?codigo={codigo} → salva identificador em obj.bimer_id.

    Etapa 2 — Buscar o preço:
      GET /api/empresas/{id_empresa}/produtos/{bimer_id}/precos/{id_tabela}
      Resposta esperada: { "valorPreco": 123.45, ... }

    Retorna o valor do preço (Decimal/float) ou None se não disponível.
    """
    # Etapa 1: garantir que temos o bimer_id
    bimer_id = obj.bimer_id or _obter_bimer_id(config, obj)
    if not bimer_id:
        raise ValueError(f"Produto {obj.codigo} não encontrado no Bimer.")

    # Etapa 2: buscar preço
    path = f"/api/empresas/{config.identificador_empresa}/produtos/{bimer_id}/precos/{config.identificador_tabela_precos}"
    resp = _bimer_request(config, "get", path, timeout=_TIMEOUT_PRECO)
    data = resp.json()

    # Resposta no formato { "Erros": [...], "ListaObjetos": [...] }
    raw = data  # guarda para diagnóstico
    if isinstance(data, dict) and "ListaObjetos" in data:
        lista = data["ListaObjetos"]
        data  = lista[0] if lista else {}

    valor = data.get("Valor")
    if valor is None:
        erros = raw.get("Erros", []) if isinstance(raw, dict) else []
        raise ValueError(
            f"ListaObjetos vazia ou sem campo 'Valor'. "
            f"Erros API: {erros}. "
            f"Path: {path}"
        )
    return valor


def sincronizar_precos():
    """
    Busca preços de todos os produtos ativos no Bimer e atualiza o banco local.

    Fluxo por produto:
      1. Se bimer_id estiver vazio → GET /api/produto/{codigo} para obter e salvar o ID
      2. GET /api/precoProduto?identificadorEmpresa=...&identificadorProduto=...&identificadorTabelaPrecos=...
      3. Atualiza obj.preco se o valor retornado for válido

    Salva resumo e erros em config.log_sync.
    Retorna dict com: status, atualizados, erros.
    """
    from ..models import BimerConfig, Perfil, PerfilPuxador, Puxador, Divisor, VidroBase

    config = BimerConfig.get()
    if not config.ativo:
        return {"status": "inativo", "msg": "Integração desativada."}

    if not config.identificador_empresa:
        msg = "Configure o Identificador da empresa antes de sincronizar."
        config.log_sync = msg
        config.ultima_sincronizacao = timezone.now()
        config.save(update_fields=["log_sync", "ultima_sincronizacao"])
        return {"status": "erro_config", "msg": msg}

    erros       = []
    atualizados = 0

    for model_cls in [Perfil, PerfilPuxador, Puxador, Divisor, VidroBase]:
        for obj in model_cls.objects.filter(ativo=True):
            try:
                novo_preco = _buscar_preco_bimer(config, obj)
                if novo_preco is not None:
                    obj.preco = novo_preco
                    obj.save(update_fields=["preco"])
                    atualizados += 1
                else:
                    erros.append(f"{model_cls.__name__} {obj.codigo}: preço não retornado pela API.")
            except Exception as e:
                erros.append(f"{model_cls.__name__} {obj.codigo}: {e}")

    config.ultima_sincronizacao = timezone.now()
    config.log_sync = (
        f"{atualizados} produto(s) atualizados. "
        f"{len(erros)} erro(s).\n" + "\n".join(erros)
    )
    config.save(update_fields=["ultima_sincronizacao", "log_sync"])

    return {"status": "ok", "atualizados": atualizados, "erros": erros}


# ── Envio de pedido para o Bimer ─────────────────────────────────────────────

_BIMER_ID_PORTA = "00A0000AU5"  # Identificador fixo do produto "Porta" no Bimer


def enviar_pedido_bimer(config, pedido):
    """
    Envia um Pedido de Venda para o Bimer ao mover para status 'wise'.

    Endpoint: POST /api/venda/pedidos
    Cada PedidoItem vira uma linha com produto fixo '00A0000AU5' (Porta),
    descrição do sistema, quantidade e valor unitário.

    Retorna (True, msg) em caso de sucesso ou (False, msg) em caso de erro.
    """
    if not config.ativo:
        return False, "Integração Bimer desativada."

    if not config.identificador_empresa:
        return False, "Configure o Identificador da empresa no Bimer."

    if not pedido.cliente.bimer_id:
        return False, (
            f"Cliente '{pedido.cliente.nome}' não possui identificador Bimer. "
            "Sincronize os clientes primeiro."
        )

    data_str         = pedido.data.strftime("%Y-%m-%d")
    data_emissao_str = data_str

    # ── Monta itens: uma linha por porta ─────────────────────────────────────
    itens_bimer = []
    for item in pedido.itens.all():
        valor_total = float(item.valor_unitario) * item.quantidade
        itens_bimer.append({
            "IdentificadorProduto":   _BIMER_ID_PORTA,
            "IdentificadorSetorSaida": "00A0000005",
            "QuantidadePedida":       item.quantidade,
            "Repasses": [{"identificadorCategoria": "000000000R", "IdentificadorPessoa": "00A00001RR"}],
            "Valor":                  round(valor_total, 2),
            "ValorUnitario":          float(item.valor_unitario),
            "descricaoComplementar":  item.descricao,
            "PIS":    {"CodigoSituacaoTributaria": "01"},
            "COFINS": {"CodigoSituacaoTributaria": "01"},
        })

    # ── Payload baseado no JSON de exemplo confirmado ─────────────────────────
    payload = {
        "CodigoEmpresa":               1,
        "CodigoPedidoDeCompraCliente": str(pedido.numero),
        "DataCadastro":                data_str,
        "DataEmissao":                 data_emissao_str,
        "faturamentoParcial":          True,
        "IdentificadorCliente":        pedido.cliente.bimer_id,
        "IdentificadorOperacao":       "00A0000047",
        "IdentificadorSetor":          "00A0000005",
        "Itens":                       itens_bimer,
        "Prazo": {
            "Identificador":                      "00A000001H",
            "IdentificadorFormaPagamentoEntrada": "00A0000037",
        },
        "Status":                         "A",
        "TipoFrete":                      "E",
        "IndicadorAtendimentoPresencial": "2",
        "Transportadora": {
            "Quantidade": 1,
            "Especie":    "Volume(s)",
        },
        "ObservacaoDocumento": pedido.observacoes or "",
    }

    try:
        resp = _bimer_request(config, "post", "/api/venda/pedidos",
                              json=payload, timeout=_TIMEOUT_ENVIO)
        data = resp.json()

        # Resposta pode ser objeto único ou lista
        obj = data[0] if isinstance(data, list) and data else (data if isinstance(data, dict) else {})
        bimer_id = obj.get("Identificador") or obj.get("identificador", "")
        codigo   = obj.get("Codigo") or obj.get("codigo", "")
        return True, f"Pedido de venda criado no Bimer. Código: {codigo} / ID: {bimer_id}", bimer_id

    except requests.HTTPError as e:
        url_usada = f"{config.base_url.rstrip('/')}/api/venda/pedidos"
        corpo = e.response.text[:400] if e.response is not None else ""
        return False, f"Erro HTTP {e.response.status_code} — URL: {url_usada} — {corpo}", ""
    except requests.ConnectionError:
        return False, "Não foi possível conectar ao Bimer. Verifique a URL base.", ""
    except Exception as e:
        return False, str(e), ""


_BUSCA_NAO_ENCONTRADO = None          # pedido não existe no Bimer
_BUSCA_ERRO_API       = object()      # não foi possível verificar (erro de comunicação)


def buscar_pedido_bimer(config, pedido_numero):
    """
    Verifica se um pedido já existe no Bimer pelo CodigoPedidoDeCompraCliente.

    Usado antes de reenviar, para evitar duplicatas quando o envio anterior
    teve timeout (POST chegou ao servidor mas a resposta nunca voltou).

    Endpoint: GET /api/venda/pedidos?codigoPedidoDeCompraCliente={pedido_numero}
    Resposta esperada: { "ListaObjetos": [{ "Identificador": "...", "Codigo": "..." }] }

    Retorna:
      dict {"bimer_id": ..., "codigo": ...}  — pedido encontrado
      None  (_BUSCA_NAO_ENCONTRADO)           — chamada OK mas pedido não existe
      _BUSCA_ERRO_API                         — não foi possível verificar (não reenviar!)
    """
    try:
        resp = _bimer_request(
            config, "get", "/api/venda/pedidos",
            params={"codigoPedidoDeCompraCliente": str(pedido_numero)},
            timeout=_TIMEOUT,
        )
        data = resp.json()

        lista = []
        if isinstance(data, list):
            lista = data
        elif isinstance(data, dict):
            lista = data.get("ListaObjetos") or []

        if not lista:
            return _BUSCA_NAO_ENCONTRADO

        obj = lista[0]
        bimer_id = obj.get("Identificador") or obj.get("identificador", "")
        codigo   = obj.get("Codigo") or obj.get("codigo", "")
        return {"bimer_id": bimer_id, "codigo": codigo}

    except Exception:
        logger.warning(
            "Não foi possível verificar pedido #%s no Bimer.",
            pedido_numero,
            exc_info=True,
        )
        return _BUSCA_ERRO_API


# ── Sincronização de clientes ─────────────────────────────────────────────────

def sincronizar_clientes():
    """
    Importa clientes do Bimer filtrando pela característica configurada.

    Endpoint: GET /api/pessoas/porCaracteristica
      Parâmetros: identificadorCaracteristica, limite, pagina
      Resposta: { "Paginacao": { "TotalPagina": N, ... }, "ListaObjetos": [...] }

    Lógica:
      - Percorre todas as páginas (paginação automática)
      - Se o cliente já existir pelo bimer_id → ignora
      - Se não existir → cria um novo Cliente com os dados do Bimer
    """
    from ..models import BimerConfig, Cliente

    config = BimerConfig.get()
    if not config.ativo:
        return {"status": "inativo", "msg": "Integração desativada."}

    if not config.identificador_caracteristica_clientes:
        msg = "Configure o Identificador da característica de clientes antes de sincronizar."
        config.log_sync_clientes = msg
        config.ultima_sincronizacao_clientes = timezone.now()
        config.save(update_fields=["log_sync_clientes", "ultima_sincronizacao_clientes"])
        return {"status": "erro_config", "msg": msg}

    erros     = []
    importados = 0
    ignorados  = 0

    pagina = 1
    while True:
        try:
            resp = _bimer_request(
                config, "get", "/api/pessoas/porCaracteristica",
                params={
                    "identificadorCaracteristica": config.identificador_caracteristica_clientes,
                    "limite": 30,
                    "pagina": pagina,
                },
                timeout=_TIMEOUT,
            )
        except requests.HTTPError as e:
            corpo = e.response.text[:300] if e.response is not None else ""
            msg = f"Erro HTTP {e.response.status_code} ao buscar página {pagina}: {corpo}"
            config.log_sync_clientes = msg
            config.ultima_sincronizacao_clientes = timezone.now()
            config.save(update_fields=["log_sync_clientes", "ultima_sincronizacao_clientes"])
            return {"status": "erro_api", "msg": msg}
        except Exception as e:
            msg = f"Erro de conexão ao buscar página {pagina}: {e}"
            config.log_sync_clientes = msg
            config.ultima_sincronizacao_clientes = timezone.now()
            config.save(update_fields=["log_sync_clientes", "ultima_sincronizacao_clientes"])
            return {"status": "erro_api", "msg": msg}

        data = resp.json()

        total_paginas = data.get("Paginacao", {}).get("TotalPagina", 1)
        lista         = data.get("ListaObjetos", [])

        for pessoa in lista:
            try:
                bimer_id = pessoa.get("Identificador", "")
                if not bimer_id:
                    continue

                nome   = (pessoa.get("Nome") or "").strip().upper()
                codigo = (str(pessoa.get("Codigo") or ""))[:6]

                # CPF/CNPJ: vem como inteiro ou string
                cpf_cnpj_raw = str(pessoa.get("CpfCnpjCompleto") or "").strip()
                digitos = "".join(c for c in cpf_cnpj_raw if c.isdigit())
                tipo_pessoa = "PF" if len(digitos) <= 11 else "PJ"

                # Endereço principal → cidade + contato
                end    = pessoa.get("EnderecoPrincipal") or {}
                cidade = str((end.get("Cidade") or {}).get("Nome") or "")[:100]
                contato = end.get("ContatoPrincipal") or {}
                telefone = str(contato.get("TelefoneCelular") or contato.get("TelefoneFixo") or "")[:20]
                email    = str(contato.get("Email") or "")[:254]

                # Já existe → atualiza dados (cidade sempre sincronizada; telefone/email só se vazios)
                existente = Cliente.objects.filter(bimer_id=bimer_id).first()
                if existente:
                    campos = {}
                    if cidade and existente.cidade != cidade:
                        campos["cidade"] = cidade
                    if telefone and not existente.telefone:
                        campos["telefone"] = telefone or None
                    if email and not existente.email:
                        campos["email"] = email or None
                    if campos:
                        for k, v in campos.items():
                            setattr(existente, k, v)
                        existente.save(update_fields=list(campos.keys()))
                    ignorados += 1
                    continue

                Cliente.objects.create(
                    bimer_id   = bimer_id,
                    nome       = nome,
                    codigo     = codigo or None,
                    cpf_cnpj   = cpf_cnpj_raw or None,
                    tipo_pessoa= tipo_pessoa,
                    telefone   = telefone or None,
                    email      = email or None,
                    cidade     = cidade,
                )
                importados += 1

            except Exception as e:
                erros.append(f"Pessoa {pessoa.get('Codigo', '?')}: {e}")

        if pagina >= total_paginas:
            break
        pagina += 1

    config.ultima_sincronizacao_clientes = timezone.now()
    config.log_sync_clientes = (
        f"{importados} importado(s). {ignorados} já existente(s). {len(erros)} erro(s).\n"
        + "\n".join(erros)
    )
    config.save(update_fields=["ultima_sincronizacao_clientes", "log_sync_clientes"])

    return {"status": "ok", "importados": importados, "ignorados": ignorados, "erros": erros}
