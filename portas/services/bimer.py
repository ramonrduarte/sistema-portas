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
import requests
from datetime import datetime, timedelta, timezone as dt_tz

from django.utils import timezone


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

_TIMEOUT = 30  # segundos para chamadas de auth
_TIMEOUT_PRECO = 15  # segundos para chamadas de preço


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
            pass
    return obter_token(config)


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

def _obter_bimer_id(config, obj, headers):
    """
    Etapa 1: busca o identificador interno do produto no Bimer pelo código local.

    GET /api/produtos?codigo={codigo}
    Resposta esperada: { "identificador": "XXXXXXXXXX", ... }
    (ou lista com um item contendo "identificador")

    Salva o identificador em obj.bimer_id para evitar buscas futuras.
    Retorna o identificador ou None se não encontrado.
    """
    url  = f"{config.base_url.rstrip('/')}/api/produtos"
    resp = requests.get(url, params={"codigo": obj.codigo}, headers=headers, timeout=_TIMEOUT_PRECO)
    resp.raise_for_status()
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


def _buscar_preco_bimer(config, obj, headers):
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
    bimer_id = obj.bimer_id or _obter_bimer_id(config, obj, headers)
    if not bimer_id:
        raise ValueError(f"Produto {obj.codigo} não encontrado no Bimer.")

    # Etapa 2: buscar preço
    base = config.base_url.rstrip("/")
    url  = f"{base}/api/empresas/{config.identificador_empresa}/produtos/{bimer_id}/precos/{config.identificador_tabela_precos}"
    resp = requests.get(url, headers=headers, timeout=_TIMEOUT_PRECO)
    resp.raise_for_status()
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
            f"URL: {url}"
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

    try:
        token = get_valid_token(config)
    except Exception as e:
        config.log_sync = f"Falha na autenticação: {e}"
        config.ultima_sincronizacao = timezone.now()
        config.save(update_fields=["log_sync", "ultima_sincronizacao"])
        return {"status": "erro_auth", "msg": str(e)}

    headers     = {"Authorization": f"Bearer {token}"}
    erros       = []
    atualizados = 0

    for model_cls in [Perfil, PerfilPuxador, Puxador, Divisor, VidroBase]:
        for obj in model_cls.objects.filter(ativo=True):
            try:
                novo_preco = _buscar_preco_bimer(config, obj, headers)
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

def enviar_pedido_bimer(config, pedido):
    """
    Envia um Pedido para o Bimer ao mover para status 'wise'.

    TODO: ajustar endpoint e estrutura do payload conforme documentação da API Bimer.

    Retorna (True, msg) em caso de sucesso ou (False, msg) em caso de erro.
    """
    if not config.ativo:
        return False, "Integração Bimer desativada."

    if not config.identificador_empresa:
        return False, "Configure o Identificador da empresa no Bimer."

    if not pedido.cliente.bimer_id:
        return False, f"Cliente '{pedido.cliente.nome}' não possui identificador Bimer. Sincronize os clientes primeiro."

    try:
        token = get_valid_token(config)
    except Exception as e:
        return False, f"Falha na autenticação Bimer: {e}"

    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json",
    }

    # ── Monta itens do pedido ────────────────────────────────────────────────
    # Cada PedidoItem é uma porta composta de vários produtos.
    # Enviamos cada produto como uma linha separada no Bimer.
    itens_bimer = []
    itens = pedido.itens.select_related(
        "perfil", "perfil_puxador", "puxador", "divisor", "vidro"
    ).all()

    for item in itens:
        qtd = item.quantidade

        # Perfil (obrigatório)
        itens_bimer.append({
            # TODO: confirmar campos exatos exigidos pela API Bimer
            "identificadorProduto": item.perfil.bimer_id or item.perfil.codigo,
            "quantidade": qtd,
            "valorUnitario": float(item.valor_unitario),
            "descricao": item.descricao,
        })

        # Puxador (opcional)
        if item.puxador_id and item.puxador.bimer_id:
            itens_bimer.append({
                "identificadorProduto": item.puxador.bimer_id or item.puxador.codigo,
                "quantidade": qtd,
                "valorUnitario": 0,
                "descricao": f"Puxador {item.puxador.modelo}",
            })

        # Divisor (opcional)
        if item.divisor_id and item.divisor.bimer_id:
            itens_bimer.append({
                "identificadorProduto": item.divisor.bimer_id or item.divisor.codigo,
                "quantidade": qtd,
                "valorUnitario": 0,
                "descricao": f"Divisor {item.divisor.modelo}",
            })

        # Vidro (opcional)
        if item.vidro_id and item.vidro.bimer_id:
            itens_bimer.append({
                "identificadorProduto": item.vidro.bimer_id or item.vidro.codigo,
                "quantidade": qtd,
                "valorUnitario": 0,
                "descricao": f"Vidro {item.vidro.descricao}",
            })

    # ── Payload principal ────────────────────────────────────────────────────
    # TODO: confirmar endpoint e campos exatos da API Bimer para criação de pedido
    payload = {
        "identificadorEmpresa": config.identificador_empresa,
        "identificadorCliente": pedido.cliente.bimer_id,
        "numeroPedido": pedido.numero,
        "data": pedido.data.strftime("%Y-%m-%d"),
        "observacoes": pedido.observacoes or "",
        "itens": itens_bimer,
    }

    # TODO: confirmar endpoint correto (ex: /api/pedidos, /api/vendas, /api/empresas/{id}/pedidos)
    url = f"{config.base_url.rstrip('/')}/api/pedidos"

    try:
        resp = requests.post(url, json=payload, headers=headers, timeout=_TIMEOUT)
        resp.raise_for_status()
        data = resp.json()

        # TODO: confirmar campo do identificador retornado pelo Bimer
        bimer_pedido_id = (
            data.get("Identificador")
            or data.get("identificador")
            or data.get("id")
            or ""
        )
        msg = f"Pedido enviado ao Bimer com sucesso. ID Bimer: {bimer_pedido_id}"
        return True, msg

    except requests.HTTPError as e:
        corpo = e.response.text[:400] if e.response is not None else ""
        return False, f"Erro HTTP {e.response.status_code}: {corpo}"
    except requests.ConnectionError:
        return False, "Não foi possível conectar ao Bimer. Verifique a URL base."
    except Exception as e:
        return False, str(e)


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

    try:
        token = get_valid_token(config)
    except Exception as e:
        config.log_sync_clientes = f"Falha na autenticação: {e}"
        config.ultima_sincronizacao_clientes = timezone.now()
        config.save(update_fields=["log_sync_clientes", "ultima_sincronizacao_clientes"])
        return {"status": "erro_auth", "msg": str(e)}

    headers   = {"Authorization": f"Bearer {token}"}
    erros     = []
    importados = 0
    ignorados  = 0
    url_base  = f"{config.base_url.rstrip('/')}/api/pessoas/porCaracteristica"

    pagina = 1
    while True:
        try:
            resp = requests.get(
                url_base,
                params={
                    "identificadorCaracteristica": config.identificador_caracteristica_clientes,
                    "limite": 30,
                    "pagina": pagina,
                },
                headers=headers,
                timeout=_TIMEOUT,
            )
            resp.raise_for_status()
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

                # Já existe → pula
                if Cliente.objects.filter(bimer_id=bimer_id).exists():
                    ignorados += 1
                    continue

                nome   = (pessoa.get("Nome") or "").strip().upper()
                codigo = (str(pessoa.get("Codigo") or ""))[:6]

                # CPF/CNPJ: vem como inteiro ou string
                cpf_cnpj_raw = str(pessoa.get("CpfCnpjCompleto") or "").strip()
                digitos = "".join(c for c in cpf_cnpj_raw if c.isdigit())
                tipo_pessoa = "PF" if len(digitos) <= 11 else "PJ"

                # Contato principal do endereço principal
                end     = pessoa.get("EnderecoPrincipal") or {}
                contato = end.get("ContatoPrincipal") or {}
                telefone = str(contato.get("TelefoneCelular") or contato.get("TelefoneFixo") or "")[:20]
                email    = str(contato.get("Email") or "")[:254]

                Cliente.objects.create(
                    bimer_id   = bimer_id,
                    nome       = nome,
                    codigo     = codigo or None,
                    cpf_cnpj   = cpf_cnpj_raw or None,
                    tipo_pessoa= tipo_pessoa,
                    telefone   = telefone or None,
                    email      = email or None,
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
