from django.db import models
from decimal import Decimal


class Acabamento(models.Model):
    nome = models.CharField(max_length=100, unique=True)

    # opcionalmente você pode ter um código interno
    # codigo = models.CharField(max_length=50, unique=True)

    def __str__(self):
        return self.nome
    
class EspessuraVidro(models.Model):
    valor_mm = models.DecimalField(max_digits=4, decimal_places=1)

    def __str__(self):
        return f"{self.valor_mm} mm"
    


class ProdutoBase(models.Model):
    codigo = models.CharField(max_length=50)
    descricao = models.CharField(max_length=255)
    preco = models.DecimalField(max_digits=10, decimal_places=2)
    acabamento = models.ForeignKey("Acabamento", on_delete=models.PROTECT, null=True, blank=True)
    tipo = models.CharField(max_length=50, blank=True, null=True)
    modelo = models.CharField(max_length=50, blank=True, null=True)

    class Meta:
        abstract = True

    def __str__(self):
        if self.acabamento:
            return f"{self.codigo} - {self.descricao} ({self.acabamento.nome})"
        return f"{self.codigo} - {self.descricao}"



class Perfil(ProdutoBase):

    puxadores_compativeis = models.ManyToManyField(
        'PerfilPuxador', blank=True, related_name='perfis_estrutura_compativeis'
    )

    espessuras_vidro_compativeis = models.ManyToManyField(
        'EspessuraVidro', blank=True, related_name='perfis_compativeis'
    )

    puxadores_simples_compativeis = models.ManyToManyField(
        'Puxador', blank=True, related_name='perfis_estrutura_puxador'
    )

    divisores_compativeis = models.ManyToManyField(
        'Divisor', blank=True, related_name='perfis_estrutura_divisor'
    )

    vidros_compativeis = models.ManyToManyField(
        'VidroBase', blank=True, related_name='perfis_compatíveis'
    )


class PerfilPuxador(ProdutoBase):
    pass


class Puxador(ProdutoBase):
    pass


class Divisor(ProdutoBase):
    ENCAIXE_CHOICES = [
        ("embutido", "Embutido"),
        ("aparente", "Aparente"),
    ]

    encaixe = models.CharField(max_length=20, choices=ENCAIXE_CHOICES)

    def __str__(self):
        if self.acabamento:
            return f"{self.codigo} - {self.descricao} ({self.acabamento.nome})"
        return f"{self.codigo} - {self.descricao}"


class VidroBase(models.Model):
    codigo = models.CharField(max_length=50)
    descricao = models.CharField(max_length=200)
    preco = models.DecimalField(max_digits=10, decimal_places=2)
    espessura = models.ForeignKey(EspessuraVidro, on_delete=models.PROTECT)

    def __str__(self):
        return f"{self.descricao} - {self.espessura}"



class ExtraServico(ProdutoBase):
    pass

class Cliente(models.Model):
    TIPO_PESSOA_CHOICES = [
        ("PF", "Pessoa Física"),
        ("PJ", "Pessoa Jurídica"),
    ]

    tipo_pessoa = models.CharField(
        max_length=2,
        choices=TIPO_PESSOA_CHOICES,
        default="PF",
    )
    nome = models.CharField(max_length=255)
    documento = models.CharField(
        max_length=20,
        blank=True,
        null=True,
        help_text="CPF ou CNPJ (somente números ou formatado).",
    )
    telefone = models.CharField(max_length=30, blank=True, null=True)
    email = models.EmailField(blank=True, null=True)

    # endereço (bem simples por enquanto)
    logradouro = models.CharField(max_length=255, blank=True, null=True)
    numero = models.CharField(max_length=20, blank=True, null=True)
    bairro = models.CharField(max_length=100, blank=True, null=True)
    cidade = models.CharField(max_length=100, blank=True, null=True)
    uf = models.CharField(max_length=2, blank=True, null=True)
    cep = models.CharField(max_length=10, blank=True, null=True)

    observacoes = models.TextField(blank=True, null=True)

    def __str__(self):
        return self.nome



class Orcamento(models.Model):
    TIPO_PORTA_CHOICES = (
        ('AVULSO', 'Avulso'),
        ('1P_PUXADOR', '1x Perfil Puxador'),
        ('2P_PUXADOR', '2x Perfil Puxador'),
        ('LINHA_1000', 'Linha 1000'),
        ('VIDRO', 'Vidros'),
    )

    cliente = models.ForeignKey(
        Cliente,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="orcamentos",
    )

    cliente_nome = models.CharField(max_length=255, blank=True, null=True)
    tipo_porta = models.CharField(max_length=20, choices=TIPO_PORTA_CHOICES)
    data_criacao = models.DateTimeField(auto_now_add=True)
    observacoes = models.TextField(blank=True, null=True)

    def total(self):
        return sum(item.total for item in self.itens.all())


class ItemOrcamento(models.Model):
    orcamento = models.ForeignKey(Orcamento, related_name='itens', on_delete=models.CASCADE)
    descricao = models.CharField(max_length=255)

    quantidade = models.DecimalField(max_digits=10, decimal_places=3, default=1)
    largura_m = models.DecimalField(max_digits=10, decimal_places=3, blank=True, null=True)
    altura_m = models.DecimalField(max_digits=10, decimal_places=3, blank=True, null=True)

    perfil = models.ForeignKey(Perfil, blank=True, null=True, on_delete=models.SET_NULL)
    perfil_puxador = models.ForeignKey(PerfilPuxador, blank=True, null=True, on_delete=models.SET_NULL)
    divisor = models.ForeignKey(Divisor, blank=True, null=True, on_delete=models.SET_NULL)
    vidro = models.ForeignKey(VidroBase, blank=True, null=True, on_delete=models.SET_NULL)
    extra = models.ForeignKey(ExtraServico, blank=True, null=True, on_delete=models.SET_NULL)

    preco_unitario = models.DecimalField(max_digits=10, decimal_places=2)
    total = models.DecimalField(max_digits=12, decimal_places=2)
