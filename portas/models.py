from django.db import models
from decimal import Decimal
from django.conf import settings
from django.contrib.auth.models import User
import re
from django.core.exceptions import ValidationError


# models.py
class Acabamento(models.Model):
    nome = models.CharField(max_length=100)

    def __str__(self):
        return self.nome

    
class EspessuraVidro(models.Model):
    valor_mm = models.DecimalField(max_digits=4, decimal_places=1)

    def __str__(self):
        return f"{self.valor_mm} mm"
    
class AtivoModel(models.Model):
    ativo = models.BooleanField(default=True)
    criado_em = models.DateTimeField(auto_now_add=True)
    atualizado_em = models.DateTimeField(auto_now=True)

    class Meta:
        abstract = True
    

class ProdutoBase(AtivoModel):
    codigo = models.CharField(max_length=6)
    descricao = models.CharField(max_length=255)
    preco = models.DecimalField(max_digits=10, decimal_places=2)
    acabamento = models.ForeignKey("Acabamento", on_delete=models.PROTECT, null=True, blank=True)
    abatimento_mm = models.IntegerField(default=0, help_text="Abate em mm na metragem do cálculo")
    modelo = models.CharField(max_length=50, blank=True, null=True)

    class Meta:
        abstract = True

    def save(self, *args, **kwargs):
        if self.codigo:
            codigo = str(self.codigo).strip()

            # remove tudo que não for número
            codigo = re.sub(r"\D", "", codigo)

            if not codigo:
                raise ValidationError("Código deve conter apenas números.")

            if len(codigo) > 6:
                raise ValidationError("Código deve ter no máximo 6 dígitos.")

            # completa com zeros à esquerda
            self.codigo = codigo.zfill(6)

        super().save(*args, **kwargs)    

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
    FIXACAO_VIDRO_CHOICES = [
        ("face", "Face"),
        ("canto", "Canto"),
    ]

    fixacao_vidro = models.CharField(
        max_length=10,
        choices=FIXACAO_VIDRO_CHOICES,
        default="canto",
        verbose_name="Fixação do vidro",
    )


class Puxador(ProdutoBase):
    codigo = models.CharField(max_length=6, unique=True)
    acabamento = models.ForeignKey(Acabamento, on_delete=models.PROTECT)
    modelo = models.CharField(max_length=100, blank=True)

    def __str__(self):
        return self.descricao
    


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
    ativo = models.BooleanField(default=True)
    codigo = models.CharField(max_length=6)
    descricao = models.CharField(max_length=200)
    preco = models.DecimalField(max_digits=10, decimal_places=2)
    espessura = models.ForeignKey(EspessuraVidro, on_delete=models.PROTECT)

    def save(self, *args, **kwargs):
        if self.codigo:
            codigo = re.sub(r"\D", "", str(self.codigo))
            if len(codigo) > 6:
                raise ValueError("Código deve ter no máximo 6 dígitos.")
            self.codigo = codigo.zfill(6)
        super().save(*args, **kwargs)


    def __str__(self):
        return f"{self.descricao} - {self.espessura}"



class ExtraServico(ProdutoBase):
    pass



class PessoaBase(AtivoModel):
    """Base para cadastros de pessoas/entidades simples."""
    nome = models.CharField(max_length=255)
    telefone = models.CharField(max_length=20, blank=True, null=True)
    email = models.EmailField(blank=True, null=True)

    class Meta:
        abstract = True

    def __str__(self):
        return self.nome


# portas/models.py

class Cliente(PessoaBase):
    TIPO_PESSOA_CHOICES = [
        ("PF", "Pessoa Física"),
        ("PJ", "Pessoa Jurídica"),
    ]

    codigo = models.CharField(
        max_length=6,  # 👈 agora limitado a 6 caracteres
        blank=True,
        null=True,
        unique=False,
        verbose_name="Código (sistema externo)",
    )
    tipo_pessoa = models.CharField(
        max_length=2,
        choices=TIPO_PESSOA_CHOICES,
        blank=True,
        null=True,
        verbose_name="Tipo de pessoa",
    )
    cpf_cnpj = models.CharField(
        max_length=18,  # suficiente pra armazenar com ou sem máscara
        blank=True,
        null=True,
        verbose_name="CPF/CNPJ",
    )

    class Meta:
        verbose_name = "Cliente"
        verbose_name_plural = "Clientes"

    def save(self, *args, **kwargs):
        # --- Código: só números + 6 dígitos com zero à esquerda ---
        if self.codigo:
            apenas_numeros = re.sub(r"\D", "", str(self.codigo))
            self.codigo = apenas_numeros.zfill(6)

        # --- Nome sempre maiúsculo ---
        if self.nome:
            self.nome = self.nome.upper()

        # --- CPF/CNPJ: guarda só números no banco ---
        if self.cpf_cnpj:
            self.cpf_cnpj = re.sub(r"\D", "", str(self.cpf_cnpj))

        super().save(*args, **kwargs)

    @property
    def cpf_cnpj_formatado(self):
        """
        Devolve CPF/CNPJ com máscara só para exibição.
        """
        if not self.cpf_cnpj:
            return ""

        numeros = re.sub(r"\D", "", self.cpf_cnpj)

        if len(numeros) == 11:
            # CPF → 000.000.000-00
            return f"{numeros[0:3]}.{numeros[3:6]}.{numeros[6:9]}-{numeros[9:11]}"
        elif len(numeros) == 14:
            # CNPJ → 00.000.000/0000-00
            return f"{numeros[0:2]}.{numeros[2:5]}.{numeros[5:8]}/{numeros[8:12]}-{numeros[12:14]}"
        else:
            # Se estiver estranho, devolve como está
            return self.cpf_cnpj




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


class UsuarioPerfil(AtivoModel):
    TIPO_USUARIO_CHOICES = [
        ("ADMIN", "Administrador"),
        ("COMUM", "Usuário comum"),
    ]

    user = models.OneToOneField(
        User,
        on_delete=models.CASCADE,
        related_name="perfil",
    )
    codigo = models.CharField(max_length=6, unique=True)
    tipo_usuario = models.CharField(
        max_length=10,
        choices=TIPO_USUARIO_CHOICES,
        default="COMUM",
    )

    def save(self, *args, **kwargs):
        if self.codigo:
            num = re.sub(r"\D", "", str(self.codigo))
            self.codigo = num.zfill(6)
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.codigo} - {self.user.get_full_name() or self.user.username}"
