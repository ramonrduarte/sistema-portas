from django.db import models
from decimal import Decimal
from django.conf import settings
from django.contrib.auth.models import User
import re
from django.core.exceptions import ValidationError
from django.utils import timezone


# models.py
class Acabamento(models.Model):
    nome = models.CharField(max_length=100, unique=True)

    def save(self, *args, **kwargs):
        if self.nome:
            self.nome = self.nome.strip().capitalize()
        super().save(*args, **kwargs)
        
    def __str__(self):
        return self.nome
    
class EspessuraVidro(models.Model):
    valor_mm = models.DecimalField(max_digits=4, decimal_places=1, unique=True)

    def __str__(self):
        return f"{self.valor_mm} mm"
    
    
class AtivoModel(models.Model):
    ativo = models.BooleanField(default=True)
    criado_em = models.DateTimeField(auto_now_add=True)
    atualizado_em = models.DateTimeField(auto_now=True)

    class Meta:
        abstract = True
    

class ProdutoBase(AtivoModel):
    codigo = models.CharField(max_length=6, unique=True)
    descricao = models.CharField(max_length=255)
    preco = models.DecimalField(max_digits=10, decimal_places=2)
    acabamento = models.ForeignKey("Acabamento", on_delete=models.PROTECT)
    abatimento_mm = models.DecimalField(max_digits=6, decimal_places=2, default=0, help_text="Abate em mm na metragem do cálculo")
    modelo = models.CharField(max_length=50, blank=True, null=True)
    bimer_id = models.CharField(
        max_length=20, blank=True,
        verbose_name="ID interno Bimer",
        help_text="Identificador interno obtido automaticamente via API Bimer",
    )

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

    vidro_polido = models.BooleanField(
        default=False,
        verbose_name="Vidro polido",
        help_text="Se marcado, adiciona 2mm em cada dimensao do vidro",
    )
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


class VidroBase(models.Model):
    ativo = models.BooleanField(default=True)
    codigo = models.CharField(max_length=6, unique=True)
    descricao = models.CharField(max_length=200)
    preco = models.DecimalField(max_digits=10, decimal_places=2)
    espessura = models.ForeignKey(EspessuraVidro, on_delete=models.PROTECT)
    chapa_largura_mm = models.IntegerField(default=3000, verbose_name="Largura da chapa (mm)")
    chapa_altura_mm = models.IntegerField(default=2000, verbose_name="Altura da chapa (mm)")
    bimer_id = models.CharField(
        max_length=20, blank=True,
        verbose_name="ID interno Bimer",
        help_text="Identificador interno obtido automaticamente via API Bimer",
    )

    def save(self, *args, **kwargs):
        if self.codigo:
            codigo = re.sub(r"\D", "", str(self.codigo))
            if len(codigo) > 6:
                raise ValueError("Código deve ter no máximo 6 dígitos.")
            self.codigo = codigo.zfill(6)
        super().save(*args, **kwargs)


    def __str__(self):
        return f"{self.codigo} - {self.descricao} ({self.espessura})"


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
    bimer_id = models.CharField(
        max_length=20, blank=True,
        verbose_name="ID interno Bimer",
        help_text="Identificador obtido automaticamente via sincronização com o Bimer",
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
            self.nome = self.nome.capitalize()

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

    # ── Permissões granulares ─────────────────────────────────────────
    # Pedidos
    perm_pedidos_ver     = models.BooleanField(default=True,  verbose_name="Ver pedidos")
    perm_pedidos_criar   = models.BooleanField(default=True,  verbose_name="Criar pedidos")
    perm_pedidos_editar  = models.BooleanField(default=True,  verbose_name="Editar pedidos")
    perm_pedidos_excluir = models.BooleanField(default=False, verbose_name="Excluir pedidos")
    # Produção
    perm_producao_ver            = models.BooleanField(default=True,  verbose_name="Ver produção")
    perm_producao_alterar_status = models.BooleanField(default=False, verbose_name="Alterar status")
    # Clientes
    perm_clientes_ver     = models.BooleanField(default=True,  verbose_name="Ver clientes")
    perm_clientes_editar  = models.BooleanField(default=True,  verbose_name="Criar/editar clientes")
    perm_clientes_excluir = models.BooleanField(default=False, verbose_name="Excluir clientes")
    # Cadastros
    perm_cadastros_ver     = models.BooleanField(default=False, verbose_name="Ver cadastros")
    perm_cadastros_editar  = models.BooleanField(default=False, verbose_name="Criar/editar cadastros")
    perm_cadastros_excluir = models.BooleanField(default=False, verbose_name="Excluir cadastros")

    def save(self, *args, **kwargs):
        if self.codigo:
            num = re.sub(r"\D", "", str(self.codigo))
            self.codigo = num.zfill(6)
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.codigo} - {self.user.get_full_name() or self.user.username}"


class Pedido(models.Model):
    STATUS_CHOICES = [
        ("aberto", "Aberto"),
        ("cancelado", "Cancelado"),
        ("producao", "Em produção"),
        ("concluido", "Concluído"),
    ]

    data = models.DateField(auto_now_add=True)
    cliente = models.ForeignKey(
        "Cliente",
        on_delete=models.PROTECT,
        related_name="pedidos"
    )
    usuario = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="pedidos",
    )
    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default="aberto"
    )
    observacoes = models.TextField(blank=True, null=True)

    def __str__(self):
        return f"Pedido #{self.id}"

    @property
    def numero(self):
        return f"{self.id:06d}"


class PedidoItem(models.Model):
    pedido = models.ForeignKey(
        Pedido,
        on_delete=models.CASCADE,
        related_name="itens"
    )

    # Medidas
    largura_mm = models.PositiveIntegerField()
    altura_mm = models.PositiveIntegerField()
    quantidade = models.PositiveIntegerField(default=1)

    # Estrutura
    acabamento = models.ForeignKey("Acabamento", on_delete=models.PROTECT)
    perfil = models.ForeignKey("Perfil", on_delete=models.PROTECT)

    # Opcionais (regras que você descreveu)
    perfil_puxador = models.ForeignKey(
        "PerfilPuxador",
        on_delete=models.PROTECT,
        null=True,
        blank=True
    )
    qtd_perfil_puxador = models.PositiveSmallIntegerField(null=True, blank=True)

    puxador = models.ForeignKey(
        "Puxador",
        on_delete=models.PROTECT,
        null=True,
        blank=True
    )
    qtd_puxador = models.PositiveSmallIntegerField(null=True, blank=True)
    puxador_tamanho_mm = models.PositiveIntegerField(null=True, blank=True)
    puxador_sobreposto = models.BooleanField(
        default=True,
        verbose_name="Puxador sobreposto",
    )

    vidro = models.ForeignKey(
        "VidroBase",
        on_delete=models.PROTECT,
        null=True,
        blank=True
    )

    divisor = models.ForeignKey(
        "Divisor",
        on_delete=models.PROTECT,
        null=True,
        blank=True
    )
    qtd_divisor = models.PositiveSmallIntegerField(null=True, blank=True)
    divisor_altura_1 = models.PositiveIntegerField(
        null=True, blank=True,
        verbose_name="Altura divisor 1 (mm)",
        help_text="Posicao do 1o divisor a partir da base (mm)",
    )
    divisor_altura_2 = models.PositiveIntegerField(
        null=True, blank=True,
        verbose_name="Altura divisor 2 (mm)",
        help_text="Posicao do 2o divisor a partir da base (mm)",
    )

    # Adicionais livres (até 4 itens avulsos por item do pedido)
    adicional_valor = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True, default=None)
    adicional_obs   = models.CharField(max_length=255, blank=True, default="")
    adicional2_valor = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True, default=None)
    adicional2_obs   = models.CharField(max_length=255, blank=True, default="")
    adicional3_valor = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True, default=None)
    adicional3_obs   = models.CharField(max_length=255, blank=True, default="")
    adicional4_valor = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True, default=None)
    adicional4_obs   = models.CharField(max_length=255, blank=True, default="")

    # Valores
    valor_unitario = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=0
    )
    valor_total = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=0
    )

    @property
    def adicionais_list(self):
        """Retorna lista de (valor, obs) para todos os adicionais preenchidos."""
        result = []
        for val, obs in [
            (self.adicional_valor,  self.adicional_obs),
            (self.adicional2_valor, self.adicional2_obs),
            (self.adicional3_valor, self.adicional3_obs),
            (self.adicional4_valor, self.adicional4_obs),
        ]:
            if val:
                result.append((val, obs))
        return result

    @property
    def descricao(self):
        """Porta modelo1/modelo2 Acabamento LxA Vidro"""
        modelos = [m for m in [
            self.perfil.modelo,
            self.perfil_puxador.modelo if self.perfil_puxador_id else None,
            self.puxador.modelo if self.puxador_id else None,
            self.divisor.modelo if self.divisor_id else None,
        ] if m]
        desc = "Porta " + "/".join(modelos)
        desc += " " + self.acabamento.nome
        desc += " " + f"{self.largura_mm}×{self.altura_mm}"
        if self.vidro_id:
            desc += " " + self.vidro.descricao
        return desc

    def __str__(self):
        return f"Item {self.id} do Pedido {self.pedido.id}"


# ── Integração Bimer ──────────────────────────────────────────────────────────

class BimerConfig(models.Model):
    """
    Configuração singleton para integração com a API do Bimer (Alterdata).
    Apenas um registro (pk=1) é permitido.
    Credenciais sensíveis nunca são exibidas no template.
    """
    base_url  = models.URLField(verbose_name="URL base da API", blank=True)
    username  = models.CharField(max_length=255, blank=True, verbose_name="Usuário")
    _password = models.CharField(max_length=255, blank=True, db_column="password",
                                 verbose_name="Senha")

    # Tokens gerenciados automaticamente — nunca exibir no template
    access_token     = models.TextField(blank=True)
    refresh_token    = models.TextField(blank=True)
    token_expires_at = models.DateTimeField(null=True, blank=True)

    # Agendamento automático
    sync_horarios    = models.CharField(
        max_length=100, default="7,14",
        verbose_name="Horários",
        help_text="Horas do dia separadas por vírgula (ex: 7,14 = 07:00 e 14:00)",
    )
    sync_dias_semana = models.CharField(
        max_length=100, default="mon,tue,wed,thu,fri,sat,sun",
        verbose_name="Dias da semana",
        help_text="Abreviações separadas por vírgula: mon tue wed thu fri sat sun",
    )

    # Parâmetros de clientes
    identificador_caracteristica_clientes = models.CharField(
        max_length=50, blank=True,
        verbose_name="Identificador da característica (clientes)",
        help_text="Filtra pessoas no Bimer por esta característica para importar como clientes",
    )
    ultima_sincronizacao_clientes = models.DateTimeField(null=True, blank=True)
    log_sync_clientes             = models.TextField(blank=True)

    # Parâmetros de preço
    identificador_empresa      = models.CharField(
        max_length=50, blank=True,
        verbose_name="Identificador da empresa",
        help_text="Código da empresa no Bimer (parâmetro identificadorEmpresa)",
    )
    identificador_tabela_precos = models.CharField(
        max_length=50, blank=True,
        verbose_name="Identificador da tabela de preços",
        help_text="Código da tabela de preços no Bimer (parâmetro identificadorTabelaPrecos)",
    )

    # Status
    ativo                = models.BooleanField(default=False, verbose_name="Integração ativa")
    ultima_sincronizacao = models.DateTimeField(null=True, blank=True)
    log_sync             = models.TextField(blank=True)

    class Meta:
        verbose_name = "Configuração Bimer"

    def save(self, *args, **kwargs):
        self.pk = 1  # garante singleton
        super().save(*args, **kwargs)
        # Reagenda o job no APScheduler com os novos horários/dias
        from portas import scheduler as _sched
        _sched.reagendar(self.sync_horarios, self.sync_dias_semana)

    @classmethod
    def get(cls):
        obj, _ = cls.objects.get_or_create(pk=1)
        return obj

    @property
    def password(self):
        return self._password

    @password.setter
    def password(self, value):
        self._password = value

    def senha_configurada(self):
        return bool(self._password)

    def token_valido(self):
        if not self.access_token:
            return False
        if self.token_expires_at:
            from django.utils import timezone
            return self.token_expires_at > timezone.now()
        return True

    def __str__(self):
        return "Configuração Bimer"


# ── Configuração da Empresa ────────────────────────────────────────────────────

class ConfiguracaoEmpresa(models.Model):
    """
    Configuração singleton com nome e logo da empresa.
    Apenas um registro (pk=1) é permitido.
    """
    nome_empresa = models.CharField(
        max_length=100,
        default="Sistema Portas",
        verbose_name="Nome da empresa",
    )
    logo = models.ImageField(
        upload_to="empresa/",
        blank=True,
        null=True,
        verbose_name="Logo",
    )
    logo_claro = models.ImageField(
        upload_to="empresa/",
        blank=True,
        null=True,
        verbose_name="Logo (fundo claro/impressão)",
        help_text="Versão do logo para uso em fundo branco (impressão). Opcional — se não preenchido, usa o logo principal com fundo escuro.",
    )
    custo_mao_obra = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=0,
        verbose_name="Custo m�o de obra (por porta)",
        help_text="Valor fixo adicionado em cada porta calculada",
    )

    class Meta:
        verbose_name = "Configuração da Empresa"

    def save(self, *args, **kwargs):
        self.pk = 1
        super().save(*args, **kwargs)

    @classmethod
    def get(cls):
        obj, _ = cls.objects.get_or_create(pk=1, defaults={"nome_empresa": "Sistema Portas"})
        return obj

    def __str__(self):
        return self.nome_empresa
