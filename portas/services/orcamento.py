from decimal import Decimal

MM_POR_METRO = Decimal("1000")


def mm_para_m(mm) -> Decimal:
    if not mm:
        return Decimal("0")
    return Decimal(mm) / MM_POR_METRO


def area_m2(largura_mm, altura_mm) -> Decimal:
    if not largura_mm or not altura_mm:
        return Decimal("0")
    return mm_para_m(largura_mm) * mm_para_m(altura_mm)


# ── Fórmulas de perfil ────────────────────────────────────────────────────────

def calc_valor_perfil_base(preco_m: Decimal, largura_mm: int, altura_mm: int) -> Decimal:
    """
    Apenas perfil (4 lados): (L×2 + A×2) × preço_perfil
    """
    L = mm_para_m(largura_mm)
    A = mm_para_m(altura_mm)
    return (L * 2 + A * 2) * preco_m


def calc_valor_perfil_com_perfil_puxador(
    preco_perfil_m: Decimal,
    preco_pp_m: Decimal,
    largura_mm: int,
    altura_mm: int,
    qtd_pp: int,
) -> tuple[Decimal, Decimal]:
    """
    Retorna (valor_perfil, valor_perfil_puxador).

    qtd_pp == 1:
        perfil         = (L×2 + A×1) × preço_perfil
        perfil_puxador =  A×1        × preço_pp

    qtd_pp == 2:
        perfil         =  L×2        × preço_perfil
        perfil_puxador =  A×2        × preço_pp
    """
    L = mm_para_m(largura_mm)
    A = mm_para_m(altura_mm)

    if qtd_pp == 1:
        return (L * 2 + A) * preco_perfil_m, A * preco_pp_m

    if qtd_pp == 2:
        return L * 2 * preco_perfil_m, A * 2 * preco_pp_m

    raise ValueError("qtd_pp deve ser 1 ou 2")


# ── Fórmulas de itens opcionais ───────────────────────────────────────────────

def calc_valor_vidro(preco_m2: Decimal, largura_mm: int, altura_mm: int) -> Decimal:
    """
    Vidro: A(m) × L(m) × preço_m2
    """
    return area_m2(largura_mm, altura_mm) * preco_m2


def calc_valor_puxador(preco_m: Decimal, tamanho_mm: int, qtd: int) -> Decimal:
    """
    Puxador simples: tamanho(m) × preço_m × qtd
      qtd == 1 → tamanho × preço
      qtd == 2 → tamanho × preço × 2
    """
    return mm_para_m(tamanho_mm) * preco_m * Decimal(qtd)


def calc_valor_divisor(preco_m: Decimal, largura_mm: int, qtd: int) -> Decimal:
    """
    Divisor: qtd × L(m) × preço_m
    """
    return Decimal(qtd) * mm_para_m(largura_mm) * preco_m


# ── Função principal ──────────────────────────────────────────────────────────

def calc_total(
    *,
    preco_perfil_m: Decimal,
    largura_mm: int,
    altura_mm: int,

    # perfil puxador (opcional, exclusivo com puxador simples)
    preco_pp_m: Decimal | None = None,
    qtd_pp: int | None = None,

    # puxador simples (opcional, exclusivo com perfil puxador)
    preco_puxador_m: Decimal | None = None,
    qtd_puxador: int | None = None,
    puxador_tamanho_mm: int | None = None,

    # divisor (opcional)
    preco_divisor_m: Decimal | None = None,
    qtd_divisor: int | None = None,

    # vidro (opcional)
    preco_vidro_m2: Decimal | None = None,

    # mao de obra (fixo por porta)
    custo_mao_obra: Decimal | None = None,
) -> Decimal:
    """
    PERFIL (obrigatório):
      Só perfil:          (L×2 + A×2) × preço_perfil
      + 1 perfil puxador: (L×2 + A×1) × perfil  +  A×1 × pp
      + 2 perfis puxador:  L×2        × perfil  +  A×2 × pp
      + 1 puxador:        (L×2 + A×2) × perfil  +  tamanho × preço_pux
      + 2 puxadores:      (L×2 + A×2) × perfil  +  tamanho × preço_pux × 2

    DIVISOR (opcional): qtd × L(m) × preço_divisor
    VIDRO   (opcional): A(m) × L(m) × preço_vidro_m2
    """
    total = Decimal("0")

    tem_pp = bool(preco_pp_m is not None and qtd_pp)
    tem_pux = bool(preco_puxador_m is not None and qtd_puxador and puxador_tamanho_mm)

    if tem_pp:
        valor_perfil, valor_pp = calc_valor_perfil_com_perfil_puxador(
            preco_perfil_m, preco_pp_m, largura_mm, altura_mm, int(qtd_pp)
        )
        total += valor_perfil + valor_pp
    else:
        total += calc_valor_perfil_base(preco_perfil_m, largura_mm, altura_mm)
        if tem_pux:
            total += calc_valor_puxador(
                preco_puxador_m, int(puxador_tamanho_mm), int(qtd_puxador)
            )

    if preco_divisor_m is not None and qtd_divisor:
        total += calc_valor_divisor(preco_divisor_m, largura_mm, int(qtd_divisor))

    if preco_vidro_m2 is not None:
        total += calc_valor_vidro(preco_vidro_m2, largura_mm, altura_mm)

    if custo_mao_obra:
        total += custo_mao_obra

    return total


# ── Bases de cálculo para serviços de porta ──────────────────────────────────

def calc_bases_servicos_porta(
    *,
    largura_mm: int,
    altura_mm: int,
    perfil_abatimento_mm: Decimal = Decimal("0"),
    pp_abatimento_mm: Decimal | None = None,
    qtd_pp: int = 0,
    pux_abatimento_mm: Decimal | None = None,
    qtd_pux: int = 0,
    pux_tamanho_mm: int = 0,
    pux_sobreposto: bool = True,
    qtd_divisor: int = 0,
) -> tuple[Decimal, Decimal, Decimal]:
    """
    Retorna (metro_linear_perfil, m2_vidro, metro_linear_vidro) — as três bases
    possíveis de cálculo para ServicoPorta.tipo_calculo.

    metro_linear_perfil considera abatimentos de PP/puxador sobreposto, o
    comprimento do(s) puxador(es) e o comprimento do(s) divisor(es).
    """
    L_perf = Decimal(largura_mm)
    if pp_abatimento_mm is not None and qtd_pp:
        L_perf = L_perf - qtd_pp * pp_abatimento_mm + qtd_pp * perfil_abatimento_mm
    if pux_abatimento_mm is not None and qtd_pux and pux_sobreposto:
        L_perf = L_perf - qtd_pux * pux_abatimento_mm

    metro_linear_perfil = (L_perf * 2 + Decimal(altura_mm) * 2) / MM_POR_METRO
    if qtd_pux and pux_tamanho_mm:
        metro_linear_perfil += Decimal(qtd_pux * pux_tamanho_mm) / MM_POR_METRO
    if qtd_divisor:
        metro_linear_perfil += Decimal(qtd_divisor * largura_mm) / MM_POR_METRO

    m2_vidro = area_m2(largura_mm, altura_mm)
    metro_linear_vidro = (Decimal(largura_mm) * 2 + Decimal(altura_mm) * 2) / MM_POR_METRO

    return metro_linear_perfil, m2_vidro, metro_linear_vidro


def base_servico_porta(
    tipo_calculo: str,
    metro_linear_perfil: Decimal,
    m2_vidro: Decimal,
    metro_linear_vidro: Decimal,
) -> Decimal:
    """Seleciona a base de cálculo correta conforme ServicoPorta.tipo_calculo."""
    if tipo_calculo == "metro_linear_perfil":
        return metro_linear_perfil
    if tipo_calculo == "m2_vidro":
        return m2_vidro
    return metro_linear_vidro


# ── Desconto e adicionais ─────────────────────────────────────────────────────

def aplicar_desconto_e_adicional(
    valor_base: Decimal,
    desconto_pct: Decimal | None = None,
    adicional: Decimal | None = None,
) -> Decimal:
    """
    valor_unitário = valor_base × (1 - desconto% / 100) + adicional

    O desconto incide sobre o valor base (perfil + acessórios + serviços);
    o adicional é somado depois, sem sofrer desconto.
    """
    desconto_pct = desconto_pct or Decimal("0")
    adicional = adicional or Decimal("0")
    return valor_base * (1 - desconto_pct / 100) + adicional
