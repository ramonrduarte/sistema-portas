from decimal import Decimal

from django.conf import settings
from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView

from portas.models import (
    Acabamento,
    ConfiguracaoEmpresa,
    Divisor,
    Perfil,
    PerfilPuxador,
    Puxador,
    VidroBase,
)
from portas.services.orcamento import calc_total

from .permissions import AssistenteThrottle, IsGPTAssistant
from .serializers import (
    AcabamentoSerializer,
    DivisorOpcoesSerializer,
    PerfilOpcoesSerializer,
    PerfilPuxadorOpcoesSerializer,
    PuxadorOpcoesSerializer,
    VidroOpcoesSerializer,
)


class OpcoesView(APIView):
    """
    GET /api/assistente/opcoes/

    Retorna catálogo ativo agrupado por categoria.

    Parâmetros opcionais:
      ?busca=des-198     → filtra todos os grupos pela descricao
      ?acabamento=preto  → filtra perfis/PPs/puxadores/divisores pelo acabamento
    """
    authentication_classes = []
    permission_classes = [IsGPTAssistant]
    throttle_classes = [AssistenteThrottle]

    def get(self, request):
        busca = request.query_params.get("busca", "").strip()
        acabamento_filtro = request.query_params.get("acabamento", "").strip()

        perfis_qs = (
            Perfil.objects.filter(ativo=True)
            .select_related("acabamento")
            .prefetch_related(
                "puxadores_compativeis",
                "puxadores_simples_compativeis",
                "divisores_compativeis",
                "vidros_compativeis__espessura",
            )
            .order_by("descricao")
        )
        pps_qs = (
            PerfilPuxador.objects.filter(ativo=True)
            .select_related("acabamento")
            .order_by("descricao")
        )
        puxadores_qs = (
            Puxador.objects.filter(ativo=True)
            .select_related("acabamento")
            .order_by("descricao")
        )
        divisores_qs = (
            Divisor.objects.filter(ativo=True)
            .select_related("acabamento")
            .order_by("descricao")
        )
        vidros_qs = (
            VidroBase.objects.filter(ativo=True)
            .select_related("espessura")
            .order_by("descricao")
        )

        if acabamento_filtro:
            perfis_qs = perfis_qs.filter(acabamento__nome__icontains=acabamento_filtro)
            pps_qs = pps_qs.filter(acabamento__nome__icontains=acabamento_filtro)
            puxadores_qs = puxadores_qs.filter(acabamento__nome__icontains=acabamento_filtro)
            divisores_qs = divisores_qs.filter(acabamento__nome__icontains=acabamento_filtro)

        if busca:
            perfis_qs = perfis_qs.filter(descricao__icontains=busca)
            pps_qs = pps_qs.filter(descricao__icontains=busca)
            puxadores_qs = puxadores_qs.filter(descricao__icontains=busca)
            divisores_qs = divisores_qs.filter(descricao__icontains=busca)
            vidros_qs = vidros_qs.filter(descricao__icontains=busca)

        return Response({
            "acabamentos": AcabamentoSerializer(
                Acabamento.objects.all().order_by("nome"), many=True
            ).data,
            "perfis": PerfilOpcoesSerializer(perfis_qs, many=True).data,
            "perfis_puxador": PerfilPuxadorOpcoesSerializer(pps_qs, many=True).data,
            "puxadores": PuxadorOpcoesSerializer(puxadores_qs, many=True).data,
            "divisores": DivisorOpcoesSerializer(divisores_qs, many=True).data,
            "vidros": VidroOpcoesSerializer(vidros_qs, many=True).data,
        })


class CalcularPortaView(APIView):
    """
    POST /api/assistente/calcular-porta/

    Valida a combinação escolhida e retorna o valor calculado.
    Não cria pedido — apenas calcula.

    Corpo esperado:
    {
        "largura_mm": 1500,
        "altura_mm": 800,
        "quantidade": 1,
        "perfil_id": 3,
        "perfil_puxador_id": 5,       // opcional
        "qtd_perfil_puxador": 2,       // 1 ou 2, obrigatório se perfil_puxador_id
        "puxador_id": null,            // opcional, exclusivo com perfil_puxador
        "qtd_puxador": null,           // 1 ou 2
        "puxador_tamanho_mm": null,    // obrigatório se puxador_id
        "vidro_id": 8,                 // opcional
        "divisor_id": null,            // opcional
        "qtd_divisor": null            // obrigatório se divisor_id
    }
    """
    authentication_classes = []
    permission_classes = [IsGPTAssistant]
    throttle_classes = [AssistenteThrottle]

    def post(self, request):
        data = request.data
        erros = []

        # ── Campos obrigatórios ────────────────────────────────────────────────
        try:
            largura_mm = int(data["largura_mm"])
            altura_mm = int(data["altura_mm"])
            quantidade = int(data.get("quantidade", 1))
            perfil_id = int(data["perfil_id"])
        except (KeyError, TypeError, ValueError):
            return Response(
                {"erro": "perfil_id, largura_mm e altura_mm são obrigatórios e devem ser inteiros."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        if largura_mm <= 0 or altura_mm <= 0 or quantidade <= 0:
            return Response(
                {"erro": "largura_mm, altura_mm e quantidade devem ser maiores que zero."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        # ── Perfil ────────────────────────────────────────────────────────────
        try:
            perfil = (
                Perfil.objects
                .select_related("acabamento")
                .prefetch_related(
                    "puxadores_compativeis",
                    "puxadores_simples_compativeis",
                    "divisores_compativeis",
                    "vidros_compativeis",
                )
                .get(pk=perfil_id, ativo=True)
            )
        except Perfil.DoesNotExist:
            return Response(
                {"erro": f"Perfil ID {perfil_id} não encontrado ou inativo."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        # ── Perfil puxador (opcional) ─────────────────────────────────────────
        pp = None
        qtd_pp = int(data.get("qtd_perfil_puxador") or 0)
        pp_id = data.get("perfil_puxador_id")
        if pp_id:
            try:
                pp = PerfilPuxador.objects.get(pk=int(pp_id), ativo=True)
                if pp not in perfil.puxadores_compativeis.all():
                    erros.append(
                        f"Perfil puxador '{pp.descricao}' não é compatível com o perfil '{perfil.descricao}'."
                    )
            except PerfilPuxador.DoesNotExist:
                erros.append(f"Perfil puxador ID {pp_id} não encontrado ou inativo.")
            if pp and qtd_pp not in (1, 2):
                erros.append("qtd_perfil_puxador deve ser 1 ou 2.")

        # ── Puxador simples (opcional, exclusivo com perfil puxador) ──────────
        pux = None
        qtd_pux = int(data.get("qtd_puxador") or 0)
        pux_tam = int(data.get("puxador_tamanho_mm") or 0)
        pux_id = data.get("puxador_id")
        if pux_id:
            if pp:
                erros.append("Não é possível usar perfil puxador e puxador simples ao mesmo tempo.")
            else:
                try:
                    pux = Puxador.objects.get(pk=int(pux_id), ativo=True)
                    if pux not in perfil.puxadores_simples_compativeis.all():
                        erros.append(
                            f"Puxador '{pux.descricao}' não é compatível com o perfil '{perfil.descricao}'."
                        )
                except Puxador.DoesNotExist:
                    erros.append(f"Puxador ID {pux_id} não encontrado ou inativo.")
                if pux and qtd_pux not in (1, 2):
                    erros.append("qtd_puxador deve ser 1 ou 2.")
                if pux and not pux_tam:
                    erros.append("puxador_tamanho_mm é obrigatório quando há puxador simples.")

        # ── Divisor (opcional) ────────────────────────────────────────────────
        divisor = None
        qtd_div = int(data.get("qtd_divisor") or 0)
        div_id = data.get("divisor_id")
        if div_id:
            try:
                divisor = Divisor.objects.get(pk=int(div_id), ativo=True)
                if divisor not in perfil.divisores_compativeis.all():
                    erros.append(
                        f"Divisor '{divisor.descricao}' não é compatível com o perfil '{perfil.descricao}'."
                    )
            except Divisor.DoesNotExist:
                erros.append(f"Divisor ID {div_id} não encontrado ou inativo.")
            if divisor and qtd_div <= 0:
                erros.append("qtd_divisor deve ser maior que zero.")

        # ── Vidro (opcional) ──────────────────────────────────────────────────
        vidro = None
        vidro_id = data.get("vidro_id")
        if vidro_id:
            try:
                vidro = VidroBase.objects.select_related("espessura").get(
                    pk=int(vidro_id), ativo=True
                )
                if vidro not in perfil.vidros_compativeis.all():
                    erros.append(
                        f"Vidro '{vidro.descricao}' não é compatível com o perfil '{perfil.descricao}'."
                    )
            except VidroBase.DoesNotExist:
                erros.append(f"Vidro ID {vidro_id} não encontrado ou inativo.")

        if erros:
            return Response({"valido": False, "erros": erros})

        # ── Cálculo ───────────────────────────────────────────────────────────
        config = ConfiguracaoEmpresa.get()
        valor_base = calc_total(
            preco_perfil_m=perfil.preco,
            largura_mm=largura_mm,
            altura_mm=altura_mm,
            preco_pp_m=(pp.preco if pp else None),
            qtd_pp=(qtd_pp or None),
            preco_puxador_m=(pux.preco if pux else None),
            qtd_puxador=(qtd_pux or None),
            puxador_tamanho_mm=(pux_tam or None),
            preco_divisor_m=(divisor.preco if divisor else None),
            qtd_divisor=(qtd_div or None),
            preco_vidro_m2=(vidro.preco if vidro else None),
            custo_mao_obra=(config.custo_mao_obra if config.custo_mao_obra else None),
        )
        valor_total = valor_base * Decimal(quantidade)

        # ── Descrição ─────────────────────────────────────────────────────────
        modelos = [m for m in [
            perfil.modelo,
            pp.modelo if pp else None,
            pux.modelo if pux else None,
            divisor.modelo if divisor else None,
        ] if m]
        descricao = ("Porta " + "/".join(modelos)) if modelos else "Porta"
        if pux and pux_tam:
            cm = pux_tam / 10
            descricao += f" ({int(cm) if cm == int(cm) else cm}cm)"
        descricao += f" {perfil.acabamento.nome} {largura_mm}×{altura_mm}"
        if vidro:
            descricao += f" {vidro.descricao}"

        return Response({
            "valido": True,
            "descricao": descricao,
            "valor_unitario": f"{valor_base:.2f}",
            "valor_total": f"{valor_total:.2f}",
            "quantidade": quantidade,
            "erros": [],
        })


class SchemaView(APIView):
    """
    GET /api/assistente/schema.json

    Retorna o schema OpenAPI 3.1 para configurar o GPT Actions.
    Acesso público (sem token) para facilitar a configuração.
    """
    authentication_classes = []
    permission_classes = []

    def get(self, request):
        base_url = request.build_absolute_uri("/api/assistente").rstrip("/")
        schema = {
            "openapi": "3.1.0",
            "info": {
                "title": "Assistente de Orçamento de Esquadrias",
                "version": "1.0.0",
                "description": (
                    "API para o assistente GPT realizar orçamentos de portas e esquadrias. "
                    "Permite consultar opções de produtos ativos e calcular valores."
                ),
            },
            "servers": [{"url": base_url}],
            "security": [{"bearerAuth": []}],
            "components": {
                "securitySchemes": {
                    "bearerAuth": {
                        "type": "http",
                        "scheme": "bearer",
                    }
                },
                "schemas": {
                    "CalcularPortaInput": {
                        "type": "object",
                        "required": ["perfil_id", "largura_mm", "altura_mm"],
                        "properties": {
                            "perfil_id": {"type": "integer", "description": "ID do perfil principal"},
                            "largura_mm": {"type": "integer", "description": "Largura em milímetros"},
                            "altura_mm": {"type": "integer", "description": "Altura em milímetros"},
                            "quantidade": {"type": "integer", "default": 1},
                            "perfil_puxador_id": {"type": "integer", "nullable": True, "description": "ID do perfil puxador (exclusivo com puxador_id)"},
                            "qtd_perfil_puxador": {"type": "integer", "enum": [1, 2], "description": "Quantidade de perfis puxador (1 ou 2)"},
                            "puxador_id": {"type": "integer", "nullable": True, "description": "ID do puxador simples (exclusivo com perfil_puxador_id)"},
                            "qtd_puxador": {"type": "integer", "enum": [1, 2]},
                            "puxador_tamanho_mm": {"type": "integer", "nullable": True, "description": "Tamanho do puxador em mm (obrigatório se puxador_id)"},
                            "vidro_id": {"type": "integer", "nullable": True, "description": "ID do vidro"},
                            "divisor_id": {"type": "integer", "nullable": True, "description": "ID do divisor"},
                            "qtd_divisor": {"type": "integer", "nullable": True, "description": "Quantidade de divisores (obrigatório se divisor_id)"},
                        },
                    },
                    "ResultadoCalculo": {
                        "type": "object",
                        "properties": {
                            "valido": {"type": "boolean"},
                            "descricao": {"type": "string", "description": "Descrição completa da porta calculada"},
                            "valor_unitario": {"type": "string", "description": "Valor por unidade em R$"},
                            "valor_total": {"type": "string", "description": "Valor total (unitário × quantidade) em R$"},
                            "quantidade": {"type": "integer"},
                            "erros": {"type": "array", "items": {"type": "string"}},
                        },
                    },
                },
            },
            "paths": {
                "/opcoes/": {
                    "get": {
                        "operationId": "listar_opcoes",
                        "summary": "Lista os produtos disponíveis agrupados por categoria",
                        "description": (
                            "Retorna acabamentos, perfis, perfis puxador, puxadores simples, divisores e vidros ativos. "
                            "Use os IDs retornados para montar a chamada de cálculo. "
                            "A resposta de 'perfis' já inclui os itens compatíveis com cada perfil."
                        ),
                        "parameters": [
                            {
                                "name": "busca",
                                "in": "query",
                                "required": False,
                                "schema": {"type": "string"},
                                "description": "Filtra todos os grupos pelo nome/descrição. Ex: 'des-198', 'espelho prata'",
                            },
                            {
                                "name": "acabamento",
                                "in": "query",
                                "required": False,
                                "schema": {"type": "string"},
                                "description": "Filtra perfis e acessórios pelo nome do acabamento. Ex: 'preto', 'bronze'",
                            },
                        ],
                        "responses": {
                            "200": {
                                "description": "Catálogo agrupado por categoria",
                                "content": {
                                    "application/json": {
                                        "schema": {
                                            "type": "object",
                                            "properties": {
                                                "acabamentos": {"type": "array", "items": {"type": "object", "properties": {"id": {"type": "integer"}, "nome": {"type": "string"}}}},
                                                "perfis": {"type": "array", "items": {"type": "object"}},
                                                "perfis_puxador": {"type": "array", "items": {"type": "object"}},
                                                "puxadores": {"type": "array", "items": {"type": "object"}},
                                                "divisores": {"type": "array", "items": {"type": "object"}},
                                                "vidros": {"type": "array", "items": {"type": "object"}},
                                            },
                                        }
                                    }
                                },
                            },
                            "403": {"description": "Token inválido ou ausente"},
                        },
                    }
                },
                "/calcular-porta/": {
                    "post": {
                        "operationId": "calcular_porta",
                        "summary": "Calcula o valor de uma porta e valida a combinação de componentes",
                        "description": (
                            "Recebe os IDs dos componentes escolhidos (obtidos em /opcoes/) e as dimensões, "
                            "valida se a combinação é compatível e retorna o valor calculado. "
                            "Não cria nenhum pedido — apenas calcula."
                        ),
                        "requestBody": {
                            "required": True,
                            "content": {
                                "application/json": {
                                    "schema": {"$ref": "#/components/schemas/CalcularPortaInput"}
                                }
                            },
                        },
                        "responses": {
                            "200": {
                                "description": "Resultado do cálculo (valido=true) ou erros de compatibilidade (valido=false)",
                                "content": {
                                    "application/json": {
                                        "schema": {"$ref": "#/components/schemas/ResultadoCalculo"}
                                    }
                                },
                            },
                            "400": {"description": "Campos obrigatórios ausentes ou inválidos"},
                            "403": {"description": "Token inválido ou ausente"},
                        },
                    }
                },
            },
        }
        return Response(schema)
