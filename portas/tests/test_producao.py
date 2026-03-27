"""
Testes unitários para portas/services/producao.py.

Foca em:
  - _calcular_dimensoes_vidro: lógica de divisor aparente e abatimentos
  - _ffd_1d: algoritmo de empacotamento 1D
  - _shelf_2d: algoritmo de empacotamento 2D
"""
from decimal import Decimal
from django.test import SimpleTestCase
from unittest.mock import MagicMock

from portas.services.producao import (
    _calcular_dimensoes_vidro,
    _ffd_1d,
    _shelf_2d,
)


# ── Helpers para criar mocks de item/perfil/divisor ──────────────────────────

def _perfil(abatimento=0, vidro_polido=False):
    p = MagicMock()
    p.abatimento_mm = abatimento
    p.vidro_polido = vidro_polido
    return p


def _divisor(encaixe="embutido", abatimento=0):
    d = MagicMock()
    d.encaixe = encaixe
    d.abatimento_mm = abatimento
    return d


def _item(
    largura_mm=900, altura_mm=2100,
    perfil=None, perfil_puxador=None, qtd_perfil_puxador=None,
    puxador=None, qtd_puxador=None, puxador_sobreposto=True,
    divisor=None, qtd_divisor=None,
    divisor_altura_1=None, divisor_altura_2=None,
):
    item = MagicMock()
    item.largura_mm = largura_mm
    item.altura_mm = altura_mm
    item.perfil = perfil or _perfil()
    item.perfil_puxador = perfil_puxador
    item.qtd_perfil_puxador = qtd_perfil_puxador
    item.puxador = puxador
    item.qtd_puxador = qtd_puxador
    item.puxador_sobreposto = puxador_sobreposto
    item.divisor = divisor
    item.qtd_divisor = qtd_divisor
    item.divisor_altura_1 = divisor_altura_1
    item.divisor_altura_2 = divisor_altura_2
    return item


# ── Testes de _calcular_dimensoes_vidro ──────────────────────────────────────

class CalcDimensoesVidroTest(SimpleTestCase):

    def test_peca_unica_sem_abatimento(self):
        """Sem divisor nem abatimento: 1 peça com dimensões iguais à porta."""
        item = _item(900, 2100, perfil=_perfil(abatimento=0))
        pecas = _calcular_dimensoes_vidro(item)
        self.assertEqual(len(pecas), 1)
        self.assertEqual(pecas[0], (900, 2100))

    def test_peca_unica_com_abatimento(self):
        """Com abatimento de 5mm no perfil: cada lado perde 5mm."""
        item = _item(900, 2100, perfil=_perfil(abatimento=5))
        pecas = _calcular_dimensoes_vidro(item)
        self.assertEqual(len(pecas), 1)
        # largura: 900 - 2×5 = 890; altura: 2100 - 2×5 = 2090
        self.assertEqual(pecas[0], (890, 2090))

    def test_polimento_adiciona_2mm(self):
        """vidro_polido=True adiciona 2mm em cada dimensão."""
        item = _item(900, 2100, perfil=_perfil(abatimento=0, vidro_polido=True))
        pecas = _calcular_dimensoes_vidro(item)
        # largura: 900+2=902; altura: 2100+2=2102
        self.assertEqual(pecas[0], (902, 2102))

    def test_perfil_puxador_qtd1_ajusta_largura(self):
        """Com 1 perfil puxador: largura perde abatimento_perfil + abatimento_pp."""
        pp = MagicMock()
        pp.abatimento_mm = 10
        item = _item(
            900, 2100,
            perfil=_perfil(abatimento=5),
            perfil_puxador=pp,
            qtd_perfil_puxador=1,
        )
        pecas = _calcular_dimensoes_vidro(item)
        # largura: 900 - 5 - 10 = 885; altura: 2100 - 2×5 = 2090
        self.assertEqual(pecas[0], (885, 2090))

    def test_perfil_puxador_qtd2_ajusta_largura(self):
        """Com 2 perfis puxador: largura perde 2×abatimento_pp."""
        pp = MagicMock()
        pp.abatimento_mm = 10
        item = _item(
            900, 2100,
            perfil=_perfil(abatimento=5),
            perfil_puxador=pp,
            qtd_perfil_puxador=2,
        )
        pecas = _calcular_dimensoes_vidro(item)
        # largura: 900 - 2×10 = 880; altura: 2100 - 2×5 = 2090
        self.assertEqual(pecas[0], (880, 2090))

    def test_divisor_embutido_nao_divide(self):
        """Divisor embutido: continua sendo 1 peça (sem divisão de altura)."""
        item = _item(
            900, 2100,
            divisor=_divisor(encaixe="embutido", abatimento=0),
            qtd_divisor=1,
            divisor_altura_1=1000,
        )
        pecas = _calcular_dimensoes_vidro(item)
        self.assertEqual(len(pecas), 1)

    def test_divisor_aparente_1_divide_em_2(self):
        """Divisor aparente com altura_1=1000mm: 2 peças de vidro."""
        item = _item(
            900, 2100,
            perfil=_perfil(abatimento=5),
            divisor=_divisor(encaixe="aparente", abatimento=4),
            qtd_divisor=1,
            divisor_altura_1=1000,
        )
        pecas = _calcular_dimensoes_vidro(item)
        self.assertEqual(len(pecas), 2)

    def test_divisor_aparente_1_largura_correta(self):
        """A largura do vidro não muda com divisor horizontal."""
        item = _item(
            900, 2100,
            perfil=_perfil(abatimento=5),
            divisor=_divisor(encaixe="aparente", abatimento=4),
            qtd_divisor=1,
            divisor_altura_1=1000,
        )
        w1, _ = _calcular_dimensoes_vidro(item)[0]
        w2, _ = _calcular_dimensoes_vidro(item)[1]
        # largura = 900 - 2×5 = 890 (sem polimento)
        self.assertEqual(w1, 890)
        self.assertEqual(w2, 890)

    def test_divisor_aparente_2_divide_em_3(self):
        """Divisor aparente com qtd=2: 3 peças de vidro."""
        item = _item(
            900, 2100,
            perfil=_perfil(abatimento=5),
            divisor=_divisor(encaixe="aparente", abatimento=4),
            qtd_divisor=2,
            divisor_altura_1=700,
            divisor_altura_2=1400,
        )
        pecas = _calcular_dimensoes_vidro(item)
        self.assertEqual(len(pecas), 3)

    def test_divisor_aparente_sem_altura_nao_divide(self):
        """Divisor aparente mas sem divisor_altura_1: 1 peça (sem split)."""
        item = _item(
            900, 2100,
            divisor=_divisor(encaixe="aparente", abatimento=4),
            qtd_divisor=1,
            divisor_altura_1=None,
        )
        pecas = _calcular_dimensoes_vidro(item)
        self.assertEqual(len(pecas), 1)


# ── Testes de _ffd_1d ─────────────────────────────────────────────────────────

class Ffd1dTest(SimpleTestCase):

    def test_lista_vazia(self):
        self.assertEqual(_ffd_1d([]), [])

    def test_peca_unica(self):
        barras = _ffd_1d([1000])
        self.assertEqual(len(barras), 1)
        self.assertEqual(barras[0], [1000])

    def test_varias_pecas_numa_barra(self):
        # 3 peças de 1000mm cabem em barra de 5850
        barras = _ffd_1d([1000, 1000, 1000], barra_mm=5850)
        self.assertEqual(len(barras), 1)
        self.assertEqual(sum(barras[0]), 3000)

    def test_pecas_grandes_exigem_mais_barras(self):
        # 4 peças de 2000mm: 2 cabem por barra (4000<5850); precisa de 2 barras
        barras = _ffd_1d([2000, 2000, 2000, 2000], barra_mm=5850)
        self.assertEqual(len(barras), 2)

    def test_peca_maior_que_barra(self):
        # Peça maior que barra fica sozinha
        barras = _ffd_1d([6000], barra_mm=5850)
        self.assertEqual(len(barras), 1)
        self.assertEqual(barras[0], [6000])

    def test_ffda_ordena_decrescente(self):
        # FFD deve colocar a maior peça primeiro — verificação indireta via aproveitamento
        barras = _ffd_1d([100, 5000, 200], barra_mm=5850)
        # [5000, 200, 100] em FFD: 5000+200+100=5300 ≤ 5850 → 1 barra
        self.assertEqual(len(barras), 1)


# ── Testes de _shelf_2d ───────────────────────────────────────────────────────

class Shelf2dTest(SimpleTestCase):

    def test_lista_vazia(self):
        chapas = _shelf_2d([], 3000, 2000)
        # retorna [[]] quando não há peças
        self.assertEqual(chapas, [[]])

    def test_peca_unica(self):
        chapas = _shelf_2d([(500, 800)], 3000, 2000)
        self.assertEqual(len(chapas), 1)
        self.assertIn((500, 800), chapas[0])

    def test_varias_pecas_numa_chapa(self):
        # Duas peças de 1000×800 cabem lado a lado numa chapa 3000×2000
        chapas = _shelf_2d([(1000, 800), (1000, 800)], 3000, 2000)
        self.assertEqual(len(chapas), 1)

    def test_pecas_exigem_nova_chapa(self):
        # 5 peças de 2000×1500 → não cabem 2 numa chapa 3000×2000 em altura
        chapas = _shelf_2d([(2000, 1500), (2000, 1500), (2000, 1500)], 3000, 2000)
        self.assertGreater(len(chapas), 1)

    def test_peca_maior_que_chapa_isolada(self):
        # Peça que não cabe em nenhuma chapa fica isolada em chapa própria
        chapas = _shelf_2d([(4000, 3000)], 3000, 2000)
        self.assertEqual(len(chapas), 1)
        self.assertEqual(chapas[0], [(4000, 3000)])
