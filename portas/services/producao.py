"""
Serviços para controle de produção: cálculo de insumos e plano de corte.
"""
from collections import defaultdict
from decimal import Decimal

from ..models import PedidoItem, PedidoItemVidro


# ── Dimensões reais do perfil ─────────────────────────────────────────────────

def _calcular_largura_perfil(item) -> int:
    """
    Largura de corte das peças horizontais do perfil estrutural.
    Com PP, o encaixe desconta ab_pp e soma ab_perf por lado de PP.
    Puxador avulso sobreposto: desconta abatimento_mm do puxador (1 lado).
    """
    L = item.largura_mm
    pp = item.perfil_puxador
    qtd_pp = item.qtd_perfil_puxador or 0
    result = L
    if pp and qtd_pp >= 1:
        ab_perf = item.perfil.abatimento_mm
        result = L - qtd_pp * pp.abatimento_mm + qtd_pp * ab_perf
    if item.puxador_id and item.puxador_sobreposto and item.qtd_puxador:
        result = result - item.qtd_puxador * item.puxador.abatimento_mm
    return int(round(float(result)))


# ── Dimensões reais do vidro ──────────────────────────────────────────────────

def _calcular_dimensoes_vidro(item) -> list:
    """
    Retorna lista de (largura_mm, altura_mm) de cada peca de vidro.

    Polimento: vidro_polido=True adiciona 2mm por cada lado onde o vidro encosta,
    independente do tipo (perfil, PP ou divisor). Com 2 lados por dimensao,
    o resultado e sempre +4mm em largura e +4mm em altura.
    """
    L, A = item.largura_mm, item.altura_mm
    perfil = item.perfil
    pp = item.perfil_puxador
    pux = item.puxador
    divisor = item.divisor
    qtd_pp = item.qtd_perfil_puxador or 0
    qtd_pux = item.qtd_puxador or 0
    ab_perf = perfil.abatimento_mm
    pol = 4 if perfil.vidro_polido else 0  # 2mm por lado x 2 lados = 4mm por dimensao

    pux_sobreposto = getattr(item, 'puxador_sobreposto', True)

    # Largura: abatimento varia por configuracao de PP; polimento sempre +4mm
    if pp and qtd_pp == 1:
        glass_w = L - ab_perf - pp.abatimento_mm + pol
    elif pp and qtd_pp == 2:
        glass_w = L - 2 * pp.abatimento_mm + pol
    elif pux and qtd_pux == 1:
        glass_w = L - 2 * ab_perf - (pux.abatimento_mm if pux_sobreposto else 0) + pol
    elif pux and qtd_pux >= 2:
        glass_w = L - 2 * ab_perf - (2 * pux.abatimento_mm if pux_sobreposto else 0) + pol
    else:
        glass_w = L - 2 * ab_perf + pol

    # Divisor aparente com alturas -> multiplas pecas de vidro
    h1 = getattr(item, 'divisor_altura_1', None)
    h2 = getattr(item, 'divisor_altura_2', None)
    qtd_div = item.qtd_divisor or 0
    tem_divisor_aparente = bool(
        divisor and
        getattr(divisor, 'encaixe', None) == 'aparente' and
        h1
    )

    if tem_divisor_aparente:
        ab_div = divisor.abatimento_mm
        pol_lado = Decimal(pol // 2)  # 2mm por lado (perfil ou divisor)
        # peca 1 lado perfil + 1 lado divisor: cada lado recebe polimento
        h_peca_perf_div = lambda span: int(span) - ab_perf + pol_lado - ab_div + pol_lado
        # peca 2 lados divisor: cada lado recebe polimento
        h_peca_div_div  = lambda span: int(span) - 2 * ab_div + 2 * pol_lado

        if qtd_div == 2 and h2:
            return [
                (glass_w, h_peca_perf_div(h1)),
                (glass_w, h_peca_div_div(int(h2) - int(h1))),
                (glass_w, h_peca_perf_div(A - int(h2))),
            ]
        else:
            return [
                (glass_w, h_peca_perf_div(h1)),
                (glass_w, h_peca_perf_div(A - int(h1))),
            ]

    # Peca unica: altura com 2 lados → +pol
    glass_h = A - 2 * ab_perf + pol
    # Divisor aparente: cada divisor desconta abatimento e acrescenta 4mm de polimento
    # (o lado do vidro que toca o divisor aparente é sempre polido)
    if divisor and getattr(divisor, 'encaixe', None) == 'aparente' and qtd_div:
        glass_h += qtd_div * (4 - divisor.abatimento_mm)
    return [(glass_w, glass_h)]


# ── Cálculo de insumos ────────────────────────────────────────────────────────

def calcular_insumos(pedido_ids: list) -> dict:
    """
    Retorna totais de material agrupados por tipo para os pedidos informados.

    Retorna:
        {
          "perfis":    [{"obj": Perfil, "metros": Decimal}, ...],
          "pps":       [{"obj": PerfilPuxador, "metros": Decimal}, ...],
          "puxadores": [{"obj": Puxador, "metros": Decimal}, ...],
          "divisores": [{"obj": Divisor, "metros": Decimal}, ...],
          "vidros":    [{"obj": VidroBase, "area_m2": Decimal}, ...],
        }
    """
    itens = (
        PedidoItem.objects
        .filter(pedido_id__in=pedido_ids)
        .select_related(
            "perfil__acabamento",
            "perfil_puxador__acabamento",
            "puxador__acabamento",
            "divisor__acabamento",
            "vidro__espessura",
        )
    )

    perfis_m = defaultdict(Decimal)
    pps_m = defaultdict(Decimal)
    puxadores_m = defaultdict(Decimal)
    divisores_m = defaultdict(Decimal)
    vidros_area = defaultdict(Decimal)

    obj_perfis = {}
    obj_pps = {}
    obj_puxadores = {}
    obj_divisores = {}
    obj_vidros = {}

    total_portas = 0

    for item in itens:
        qtd = item.quantidade
        L = item.largura_mm
        A = item.altura_mm
        qtd_pp = item.qtd_perfil_puxador or 0

        total_portas += qtd

        # Metros lineares de perfil estrutural
        if qtd_pp == 1:
            metros_perfil = (L * 2 + A) * qtd
        elif qtd_pp == 2:
            metros_perfil = L * 2 * qtd
        else:
            metros_perfil = (L * 2 + A * 2) * qtd

        perfis_m[item.perfil_id] += Decimal(metros_perfil) / 1000
        obj_perfis[item.perfil_id] = item.perfil

        # Metros lineares de perfil puxador
        if item.perfil_puxador_id:
            if qtd_pp == 1:
                metros_pp = A * qtd
            elif qtd_pp == 2:
                metros_pp = A * 2 * qtd
            else:
                metros_pp = 0
            if metros_pp:
                pps_m[item.perfil_puxador_id] += Decimal(metros_pp) / 1000
                obj_pps[item.perfil_puxador_id] = item.perfil_puxador

        # Metros lineares de puxador simples
        if item.puxador_id and item.puxador_tamanho_mm and item.qtd_puxador:
            metros_pux = item.puxador_tamanho_mm * item.qtd_puxador * qtd
            puxadores_m[item.puxador_id] += Decimal(metros_pux) / 1000
            obj_puxadores[item.puxador_id] = item.puxador

        # Metros lineares de divisor
        if item.divisor_id and item.qtd_divisor:
            metros_div = L * item.qtd_divisor * qtd
            divisores_m[item.divisor_id] += Decimal(metros_div) / 1000
            obj_divisores[item.divisor_id] = item.divisor

        # Área de vidro em m² — usa dimensões reais após abatimentos
        if item.vidro_id:
            for gw, gh in _calcular_dimensoes_vidro(item):
                area = Decimal(gw) * Decimal(gh) / Decimal(1_000_000) * qtd
                vidros_area[item.vidro_id] += area
            obj_vidros[item.vidro_id] = item.vidro

    return {
        "total_portas": total_portas,
        "perfis":    [{"obj": obj_perfis[k],    "metros":  v} for k, v in sorted(perfis_m.items())],
        "pps":       [{"obj": obj_pps[k],        "metros":  v} for k, v in sorted(pps_m.items())],
        "puxadores": [{"obj": obj_puxadores[k],  "metros":  v} for k, v in sorted(puxadores_m.items())],
        "divisores": [{"obj": obj_divisores[k],  "metros":  v} for k, v in sorted(divisores_m.items())],
        "vidros":    [{"obj": obj_vidros[k],     "area_m2": v} for k, v in sorted(vidros_area.items())],
    }


# ── Algoritmos de empacotamento ───────────────────────────────────────────────

def _ffd_1d(pecas: list, barra_mm: int = 5850) -> list:
    """
    First Fit Decreasing para corte 1D em barras.
    Recebe lista de tuplas (mm, label) e retorna lista de barras,
    cada uma sendo lista de tuplas (mm, label).
    """
    barras = []
    for peca in sorted(pecas, key=lambda p: -p[0]):
        colocado = False
        for barra in barras:
            if sum(p[0] for p in barra) + peca[0] <= barra_mm:
                barra.append(peca)
                colocado = True
                break
        if not colocado:
            barras.append([peca])
    return barras


def _shelf_2d(pecas: list, chapa_l: int, chapa_a: int) -> list:
    """
    Shelf (strip) packing 2D: empacota peças (largura, altura, label) em chapas.
    Ordena por altura desc. Abre nova faixa horizontal quando a largura se esgota.
    Abre nova chapa quando a altura se esgota.
    Retorna lista de chapas, cada uma sendo lista de tuplas (largura, altura, label).
    """
    chapas = []
    chapa_atual = []
    x = 0
    y = 0
    h_faixa = 0

    for peca in sorted(pecas, key=lambda p: (-p[1], -p[0])):
        l, a = peca[0], peca[1]
        # Peça não cabe nem em uma chapa vazia — adiciona isolada
        if l > chapa_l or a > chapa_a:
            if chapa_atual:
                chapas.append(chapa_atual)
                chapa_atual = []
            chapas.append([peca])
            x = 0
            y = 0
            h_faixa = 0
            continue

        # Não cabe na faixa atual (largura) → nova faixa
        if h_faixa and x + l > chapa_l:
            y += h_faixa
            x = 0
            h_faixa = 0

        # Não cabe na chapa atual (altura) → nova chapa
        if y + a > chapa_a:
            chapas.append(chapa_atual)
            chapa_atual = []
            x = 0
            y = 0
            h_faixa = 0

        if not h_faixa:
            h_faixa = a

        chapa_atual.append(peca)
        x += l

    if chapa_atual:
        chapas.append(chapa_atual)

    return chapas or [[]]


# ── Plano de corte ────────────────────────────────────────────────────────────

_BARRA_MM = 5850


def calcular_plano_corte(pedido_ids: list, *, item_ids=None, item_vidro_ids=None) -> dict:
    """
    Calcula o plano de corte para perfis e vidros dos pedidos informados.

    Retorna:
        {
          "perfis": [
            {"perfil": Perfil, "barra_mm": 5850,
             "barras": [[peca_mm, ...], ...], "aproveitamento_pct": Decimal,
             "total_barras": int, "sobra_mm": int},
            ...
          ],
          "pps": [...],   # mesmo formato
          "vidros": [
            {"espessura": EspessuraVidro, "chapa_l": int, "chapa_a": int,
             "chapas": [[(l,a), ...], ...], "aproveitamento_pct": Decimal,
             "total_chapas": int},
            ...
          ]
        }
    """
    itens_qs = PedidoItem.objects.filter(pedido_id__in=pedido_ids)
    if item_ids is not None:
        itens_qs = itens_qs.filter(pk__in=item_ids)
    itens = list(
        itens_qs
        .select_related(
            "pedido",
            "perfil__acabamento",
            "perfil_puxador__acabamento",
            "puxador__acabamento",
            "divisor__acabamento",
            "vidro__espessura",
        )
        .order_by("pedido_id", "id")
    )

    # Atribui índice 1-base por pedido para cada item
    pedido_item_idx: dict = defaultdict(int)
    item_labels: dict = {}
    for item in itens:
        pedido_item_idx[item.pedido_id] += 1
        item_labels[item.id] = f"#{item.pedido.numero}-{pedido_item_idx[item.pedido_id]}"

    # Peças por perfil (pk → lista de (mm, label))
    pecas_perfil = defaultdict(list)
    pecas_pp = defaultdict(list)
    pecas_puxador = defaultdict(list)
    pecas_divisor = defaultdict(list)
    # Peças de vidro agrupadas por tipo de vidro (vidro.pk → lista de (l, a))
    pecas_vidro = defaultdict(list)

    obj_perfis = {}
    obj_pps = {}
    obj_puxadores_plano = {}
    obj_divisores_plano = {}
    obj_vidros_plano = {}

    for item in itens:
        qtd = item.quantidade
        L = item.largura_mm
        A = item.altura_mm
        qtd_pp = item.qtd_perfil_puxador or 0
        lbl = item_labels[item.id]

        # Peças de perfil estrutural por porta
        L_perf = _calcular_largura_perfil(item)
        if qtd_pp == 1:
            peca_perfil = [(L_perf, lbl), (L_perf, lbl), (A, lbl)] * qtd
        elif qtd_pp == 2:
            peca_perfil = [(L_perf, lbl), (L_perf, lbl)] * qtd
        else:
            peca_perfil = [(L_perf, lbl), (L_perf, lbl), (A, lbl), (A, lbl)] * qtd

        pecas_perfil[item.perfil_id].extend(peca_perfil)
        obj_perfis[item.perfil_id] = item.perfil

        # Peças de perfil puxador por porta
        if item.perfil_puxador_id:
            if qtd_pp == 1:
                peca_pp = [(A, lbl)] * qtd
            elif qtd_pp == 2:
                peca_pp = [(A, lbl), (A, lbl)] * qtd
            else:
                peca_pp = []
            if peca_pp:
                pecas_pp[item.perfil_puxador_id].extend(peca_pp)
                obj_pps[item.perfil_puxador_id] = item.perfil_puxador

        # Peças de puxador simples por porta (comprimento = tamanho do puxador)
        if item.puxador_id and item.puxador_tamanho_mm and item.qtd_puxador:
            peca_pux = [(item.puxador_tamanho_mm, lbl)] * (item.qtd_puxador * qtd)
            pecas_puxador[item.puxador_id].extend(peca_pux)
            obj_puxadores_plano[item.puxador_id] = item.puxador

        # Peças de divisor por porta (comprimento = largura da porta)
        if item.divisor_id and item.qtd_divisor:
            peca_div = [(L, lbl)] * (item.qtd_divisor * qtd)
            pecas_divisor[item.divisor_id].extend(peca_div)
            obj_divisores_plano[item.divisor_id] = item.divisor

        # Peças de vidro por tipo de vidro — usa dimensões reais após abatimentos
        if item.vidro_id:
            for gw, gh in _calcular_dimensoes_vidro(item):
                for _ in range(qtd):
                    pecas_vidro[item.vidro_id].append((gw, gh, lbl))
            obj_vidros_plano[item.vidro_id] = item.vidro

    # PedidoItemVidro: dimensões especificadas diretamente, sem abatimentos
    itens_vidro_qs = PedidoItemVidro.objects.filter(pedido_id__in=pedido_ids)
    if item_vidro_ids is not None:
        itens_vidro_qs = itens_vidro_qs.filter(pk__in=item_vidro_ids)
    itens_vidro_direct = list(
        itens_vidro_qs
        .select_related("pedido", "vidro__espessura")
        .order_by("pedido_id", "id")
    )
    for item in itens_vidro_direct:
        pedido_item_idx[item.pedido_id] += 1
        lbl = f"#{item.pedido.numero}-{pedido_item_idx[item.pedido_id]}"
        for _ in range(item.quantidade):
            pecas_vidro[item.vidro_id].append((item.largura_mm, item.altura_mm, lbl))
        obj_vidros_plano[item.vidro_id] = item.vidro

    def _totais(barras):
        usado = sum(sum(p[0] for p in b) for b in barras)
        disponivel = len(barras) * _BARRA_MM
        sobra = disponivel - usado
        aprov = Decimal(usado) / Decimal(disponivel) * 100 if disponivel else Decimal(0)
        return usado, disponivel, sobra, aprov

    # Montar resultado para perfis
    resultado_perfis = []
    for pk, pecas in sorted(pecas_perfil.items()):
        barras = _ffd_1d(pecas, _BARRA_MM)
        _, _, sobra, aprov = _totais(barras)
        resultado_perfis.append({
            "perfil": obj_perfis[pk],
            "barra_mm": _BARRA_MM,
            "barras": barras,
            "total_barras": len(barras),
            "sobra_mm": sobra,
            "aproveitamento_pct": aprov.quantize(Decimal("0.1")),
        })

    # Montar resultado para perfis puxadores
    resultado_pps = []
    for pk, pecas in sorted(pecas_pp.items()):
        barras = _ffd_1d(pecas, _BARRA_MM)
        _, _, sobra, aprov = _totais(barras)
        resultado_pps.append({
            "perfil": obj_pps[pk],
            "barra_mm": _BARRA_MM,
            "barras": barras,
            "total_barras": len(barras),
            "sobra_mm": sobra,
            "aproveitamento_pct": aprov.quantize(Decimal("0.1")),
        })

    # Montar resultado para puxadores simples
    resultado_puxadores = []
    for pk, pecas in sorted(pecas_puxador.items()):
        barras = _ffd_1d(pecas, _BARRA_MM)
        _, _, sobra, aprov = _totais(barras)
        resultado_puxadores.append({
            "puxador": obj_puxadores_plano[pk],
            "barra_mm": _BARRA_MM,
            "barras": barras,
            "total_barras": len(barras),
            "sobra_mm": sobra,
            "aproveitamento_pct": aprov.quantize(Decimal("0.1")),
        })

    # Montar resultado para divisores
    resultado_divisores = []
    for pk, pecas in sorted(pecas_divisor.items()):
        barras = _ffd_1d(pecas, _BARRA_MM)
        _, _, sobra, aprov = _totais(barras)
        resultado_divisores.append({
            "divisor": obj_divisores_plano[pk],
            "barra_mm": _BARRA_MM,
            "barras": barras,
            "total_barras": len(barras),
            "sobra_mm": sobra,
            "aproveitamento_pct": aprov.quantize(Decimal("0.1")),
        })

    # Montar resultado para vidros
    resultado_vidros = []
    for pk, pecas in sorted(pecas_vidro.items()):
        vidro = obj_vidros_plano[pk]
        chapa_l = vidro.chapa_largura_mm
        chapa_a = vidro.chapa_altura_mm
        chapas = _shelf_2d(pecas, chapa_l, chapa_a)
        total_area_pecas = sum(p[0] * p[1] for chapa in chapas for p in chapa)
        total_area_chapas = len(chapas) * chapa_l * chapa_a
        aprov = Decimal(total_area_pecas) / Decimal(total_area_chapas) * 100 if total_area_chapas else Decimal(0)
        resultado_vidros.append({
            "vidro": vidro,
            "chapa_l": chapa_l,
            "chapa_a": chapa_a,
            "chapas": chapas,
            "total_chapas": len(chapas),
            "aproveitamento_pct": aprov.quantize(Decimal("0.1")),
        })

    return {
        "perfis": resultado_perfis,
        "pps": resultado_pps,
        "puxadores": resultado_puxadores,
        "divisores": resultado_divisores,
        "vidros": resultado_vidros,
    }
