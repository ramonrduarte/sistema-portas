"""
Testes unitários para portas/services/orcamento.py.
Todas as funções são puras — sem banco de dados.
"""
from decimal import Decimal
from django.test import SimpleTestCase

from portas.services.orcamento import (
    mm_para_m,
    area_m2,
    calc_valor_perfil_base,
    calc_valor_perfil_com_perfil_puxador,
    calc_valor_vidro,
    calc_valor_puxador,
    calc_valor_divisor,
    calc_total,
    calc_bases_servicos_porta,
    base_servico_porta,
    aplicar_desconto_e_adicional,
)


class MmParaMTest(SimpleTestCase):
    def test_basico(self):
        self.assertEqual(mm_para_m(1000), Decimal("1"))

    def test_fracao(self):
        self.assertEqual(mm_para_m(500), Decimal("0.5"))

    def test_zero(self):
        self.assertEqual(mm_para_m(0), Decimal("0"))


class AreaM2Test(SimpleTestCase):
    def test_quadrado_1m(self):
        self.assertEqual(area_m2(1000, 1000), Decimal("1"))

    def test_retangulo(self):
        # 600mm × 2100mm = 0.6 × 2.1 = 1.26 m²
        self.assertAlmostEqual(float(area_m2(600, 2100)), 1.26, places=6)


class CalcValorPerfilBaseTest(SimpleTestCase):
    """(L×2 + A×2) × preco_perfil"""

    def test_porta_simples(self):
        # L=900mm, A=2100mm, preco=10/m
        # perímetro = (0.9×2 + 2.1×2) × 10 = (1.8 + 4.2) × 10 = 60
        resultado = calc_valor_perfil_base(Decimal("10"), 900, 2100)
        self.assertEqual(resultado, Decimal("60"))

    def test_preco_zero(self):
        self.assertEqual(calc_valor_perfil_base(Decimal("0"), 900, 2100), Decimal("0"))


class CalcValorPerfilComPPTest(SimpleTestCase):
    """qtd_pp=1: perfil=(L×2+A)×p_perf, pp=A×p_pp | qtd_pp=2: perfil=L×2×p_perf, pp=A×2×p_pp"""

    def setUp(self):
        self.L, self.A = 900, 2100
        self.preco_perf = Decimal("10")
        self.preco_pp = Decimal("15")

    def test_qtd_1(self):
        perf, pp = calc_valor_perfil_com_perfil_puxador(
            self.preco_perf, self.preco_pp, self.L, self.A, 1
        )
        # perfil = (0.9×2 + 2.1) × 10 = 3.9 × 10 = 39
        self.assertEqual(perf, Decimal("39"))
        # pp    = 2.1 × 15 = 31.5
        self.assertEqual(pp, Decimal("31.5"))

    def test_qtd_2(self):
        perf, pp = calc_valor_perfil_com_perfil_puxador(
            self.preco_perf, self.preco_pp, self.L, self.A, 2
        )
        # perfil = 0.9×2 × 10 = 18
        self.assertEqual(perf, Decimal("18"))
        # pp    = 2.1×2 × 15 = 63
        self.assertEqual(pp, Decimal("63"))

    def test_qtd_invalido(self):
        with self.assertRaises(ValueError):
            calc_valor_perfil_com_perfil_puxador(
                self.preco_perf, self.preco_pp, self.L, self.A, 3
            )


class CalcValorVidroTest(SimpleTestCase):
    """A(m) × L(m) × preco_m2"""

    def test_porta_padrao(self):
        # 900×2100 mm, preco=100/m²
        # 0.9 × 2.1 × 100 = 189
        resultado = calc_valor_vidro(Decimal("100"), 900, 2100)
        self.assertAlmostEqual(float(resultado), 189.0, places=4)


class CalcValorPuxadorTest(SimpleTestCase):
    """tamanho(m) × preco_m × qtd"""

    def test_um_puxador(self):
        # 300mm, preco=50/m, qtd=1 → 0.3 × 50 = 15
        resultado = calc_valor_puxador(Decimal("50"), 300, 1)
        self.assertEqual(resultado, Decimal("15"))

    def test_dois_puxadores(self):
        resultado = calc_valor_puxador(Decimal("50"), 300, 2)
        self.assertEqual(resultado, Decimal("30"))


class CalcValorDivisorTest(SimpleTestCase):
    """qtd × L(m) × preco_m"""

    def test_um_divisor(self):
        # 900mm, preco=20/m, qtd=1 → 1 × 0.9 × 20 = 18
        resultado = calc_valor_divisor(Decimal("20"), 900, 1)
        self.assertEqual(resultado, Decimal("18"))

    def test_dois_divisores(self):
        resultado = calc_valor_divisor(Decimal("20"), 900, 2)
        self.assertEqual(resultado, Decimal("36"))


class CalcTotalTest(SimpleTestCase):
    """Testa a função principal calc_total."""

    def _total(self, **kwargs):
        defaults = dict(
            preco_perfil_m=Decimal("10"),
            largura_mm=900,
            altura_mm=2100,
        )
        defaults.update(kwargs)
        return calc_total(**defaults)

    def test_so_perfil(self):
        # (0.9×2 + 2.1×2) × 10 = 60
        self.assertEqual(self._total(), Decimal("60"))

    def test_perfil_mais_pp_qtd1(self):
        # perfil=(0.9×2+2.1)×10=39, pp=2.1×15=31.5 → 70.5
        resultado = self._total(preco_pp_m=Decimal("15"), qtd_pp=1)
        self.assertEqual(resultado, Decimal("70.5"))

    def test_perfil_mais_pp_qtd2(self):
        # perfil=0.9×2×10=18, pp=2.1×2×15=63 → 81
        resultado = self._total(preco_pp_m=Decimal("15"), qtd_pp=2)
        self.assertEqual(resultado, Decimal("81"))

    def test_perfil_mais_puxador_simples(self):
        # perfil=60, puxador=0.3×50×1=15 → 75
        resultado = self._total(
            preco_puxador_m=Decimal("50"),
            qtd_puxador=1,
            puxador_tamanho_mm=300,
        )
        self.assertEqual(resultado, Decimal("75"))

    def test_com_vidro(self):
        # perfil=60, vidro=0.9×2.1×100=189 → 249
        resultado = self._total(preco_vidro_m2=Decimal("100"))
        self.assertAlmostEqual(float(resultado), 249.0, places=4)

    def test_com_divisor(self):
        # perfil=60, divisor=1×0.9×20=18 → 78
        resultado = self._total(preco_divisor_m=Decimal("20"), qtd_divisor=1)
        self.assertEqual(resultado, Decimal("78"))

    def test_com_mao_de_obra(self):
        # perfil=60, mao_obra=25 → 85
        resultado = self._total(custo_mao_obra=Decimal("25"))
        self.assertEqual(resultado, Decimal("85"))

    def test_pp_tem_prioridade_sobre_puxador(self):
        """Se tem perfil_puxador, puxador simples é ignorado no cálculo do perfil."""
        # Com pp: perfil=(0.9×2+2.1)×10=39, pp=2.1×15=31.5 → 70.5
        # Puxador simples é excluído quando há pp
        resultado = self._total(
            preco_pp_m=Decimal("15"),
            qtd_pp=1,
            preco_puxador_m=Decimal("50"),
            qtd_puxador=1,
            puxador_tamanho_mm=300,
        )
        self.assertEqual(resultado, Decimal("70.5"))

    def test_vidro_sem_preco_ignorado(self):
        # preco_vidro_m2=None → sem vidro
        resultado = self._total(preco_vidro_m2=None)
        self.assertEqual(resultado, Decimal("60"))

    def test_divisor_sem_qtd_ignorado(self):
        resultado = self._total(preco_divisor_m=Decimal("20"), qtd_divisor=None)
        self.assertEqual(resultado, Decimal("60"))

    def test_completo(self):
        # perfil=60, pp=31.5, divisor=18, vidro=189, mao_obra=25 → 323.5
        resultado = self._total(
            preco_pp_m=Decimal("15"),
            qtd_pp=1,
            preco_divisor_m=Decimal("20"),
            qtd_divisor=1,
            preco_vidro_m2=Decimal("100"),
            custo_mao_obra=Decimal("25"),
        )
        # perfil com pp qtd=1: (0.9×2+2.1)×10=39, pp=2.1×15=31.5
        # divisor=0.9×20=18, vidro=0.9×2.1×100=189, mao=25
        # total = 39+31.5+18+189+25 = 302.5
        self.assertAlmostEqual(float(resultado), 302.5, places=4)


class CalcBasesServicosPortaTest(SimpleTestCase):
    """Bases de cálculo para ServicoPorta: metro_linear_perfil, m2_vidro, metro_linear_vidro."""

    def test_so_perfil(self):
        # 900×2100mm, sem PP/puxador/divisor
        # metro_linear_perfil = (0.9×2 + 2.1×2) = 6.0
        ml_perfil, m2_vidro, ml_vidro = calc_bases_servicos_porta(largura_mm=900, altura_mm=2100)
        self.assertEqual(ml_perfil, Decimal("6.0"))
        self.assertAlmostEqual(float(m2_vidro), 1.89, places=4)
        self.assertEqual(ml_vidro, Decimal("6.0"))

    def test_com_perfil_puxador_abate_largura(self):
        # L=900, abate 10mm de PP e soma 5mm de perfil por unidade de qtd_pp=1
        # L_perf = 900 - 1×10 + 1×5 = 895 → (0.895×2 + 2.1×2) = 5.99
        ml_perfil, _, _ = calc_bases_servicos_porta(
            largura_mm=900, altura_mm=2100,
            perfil_abatimento_mm=Decimal("5"),
            pp_abatimento_mm=Decimal("10"), qtd_pp=1,
        )
        self.assertEqual(ml_perfil, Decimal("5.99"))

    def test_puxador_sobreposto_abate_e_soma_tamanho(self):
        # L_perf = 900 - 1×8 = 892 → perímetro (0.892×2 + 2.1×2) = 5.984
        # + tamanho do puxador 1×300mm = 0.3 → 6.284
        ml_perfil, _, _ = calc_bases_servicos_porta(
            largura_mm=900, altura_mm=2100,
            pux_abatimento_mm=Decimal("8"), qtd_pux=1,
            pux_tamanho_mm=300, pux_sobreposto=True,
        )
        self.assertEqual(ml_perfil, Decimal("6.284"))

    def test_puxador_nao_sobreposto_nao_abate(self):
        # sem abatimento, só soma o tamanho: 6.0 + 0.3 = 6.3
        ml_perfil, _, _ = calc_bases_servicos_porta(
            largura_mm=900, altura_mm=2100,
            pux_abatimento_mm=Decimal("8"), qtd_pux=1,
            pux_tamanho_mm=300, pux_sobreposto=False,
        )
        self.assertEqual(ml_perfil, Decimal("6.3"))

    def test_divisor_soma_largura_por_quantidade(self):
        # 6.0 + 2 × 0.9 = 7.8
        ml_perfil, _, _ = calc_bases_servicos_porta(
            largura_mm=900, altura_mm=2100, qtd_divisor=2,
        )
        self.assertEqual(ml_perfil, Decimal("7.8"))


class BaseServicoPortaTest(SimpleTestCase):
    def test_seleciona_pela_chave(self):
        ml_perfil, m2_vidro, ml_vidro = Decimal("6"), Decimal("1.89"), Decimal("6")
        self.assertEqual(base_servico_porta("metro_linear_perfil", ml_perfil, m2_vidro, ml_vidro), ml_perfil)
        self.assertEqual(base_servico_porta("m2_vidro", ml_perfil, m2_vidro, ml_vidro), m2_vidro)
        self.assertEqual(base_servico_porta("metro_linear_vidro", ml_perfil, m2_vidro, ml_vidro), ml_vidro)


class AplicarDescontoEAdicionalTest(SimpleTestCase):
    """valor_unitario = valor_base × (1 - desconto% / 100) + adicional"""

    def test_sem_desconto_nem_adicional(self):
        self.assertEqual(aplicar_desconto_e_adicional(Decimal("100")), Decimal("100"))

    def test_so_desconto(self):
        # 100 × (1 - 10/100) = 90
        resultado = aplicar_desconto_e_adicional(Decimal("100"), desconto_pct=Decimal("10"))
        self.assertEqual(resultado, Decimal("90"))

    def test_so_adicional(self):
        self.assertEqual(
            aplicar_desconto_e_adicional(Decimal("100"), adicional=Decimal("25")),
            Decimal("125"),
        )

    def test_desconto_e_adicional(self):
        # desconto incide sobre o valor base; adicional é somado depois, sem desconto
        # 100 × 0.9 + 25 = 115
        resultado = aplicar_desconto_e_adicional(
            Decimal("100"), desconto_pct=Decimal("10"), adicional=Decimal("25")
        )
        self.assertEqual(resultado, Decimal("115"))
