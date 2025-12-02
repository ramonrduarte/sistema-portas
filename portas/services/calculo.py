from decimal import Decimal
from portas.models import (
    Orcamento,
    ItemOrcamento,
    Perfil,
    PerfilPuxador,
    VidroBase,
)


def calcular_porta_1x_puxador(
    orcamento: Orcamento,
    largura_porta_m: float,
    altura_porta_m: float,
    quantidade: int,
    perfil_estrutura: Perfil,
    perfil_puxador: PerfilPuxador,
    vidro_base: VidroBase,
):
    largura = Decimal(str(largura_porta_m))
    altura = Decimal(str(altura_porta_m))
    qtd = Decimal(str(quantidade))

    # Perfis da estrutura (simplificado: 2 laterais + 1 superior + 1 base)
    metros_laterais = altura * 2
    metros_superior = largura
    metros_base = largura
    metros_total_estrutura = metros_laterais + metros_superior + metros_base

    custo_estrutura = metros_total_estrutura * perfil_estrutura.preco * qtd

    ItemOrcamento.objects.create(
        orcamento=orcamento,
        descricao=f"Estrutura Porta ({perfil_estrutura.descricao})",
        quantidade=qtd,
        largura_m=largura,
        altura_m=altura,
        perfil=perfil_estrutura,
        preco_unitario=perfil_estrutura.preco,
        total=custo_estrutura,
    )

    # Puxador (tamanho ≈ altura da porta)
    metros_puxador = altura
    custo_puxador = metros_puxador * perfil_puxador.preco * qtd

    ItemOrcamento.objects.create(
        orcamento=orcamento,
        descricao=f"Puxador ({perfil_puxador.descricao})",
        quantidade=qtd,
        altura_m=altura,
        perfil_puxador=perfil_puxador,
        preco_unitario=perfil_puxador.preco,
        total=custo_puxador,
    )

    # Vidro
    largura_vidro = largura
    altura_vidro = altura
    area_por_peca = largura_vidro * altura_vidro
    area_total = area_por_peca * qtd
    custo_vidro = area_total * vidro_base.preco

    ItemOrcamento.objects.create(
        orcamento=orcamento,
        descricao=f"Vidro ({vidro_base.descricao})",
        quantidade=qtd,
        largura_m=largura_vidro,
        altura_m=altura_vidro,
        vidro=vidro_base,
        preco_unitario=vidro_base.preco,
        total=custo_vidro,
    )

    total_geral = custo_estrutura + custo_puxador + custo_vidro

    return {
        "total_estrutura": custo_estrutura,
        "total_puxador": custo_puxador,
        "total_vidro": custo_vidro,
        "total_geral": total_geral,
    }
