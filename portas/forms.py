from django import forms
from django.core.exceptions import ValidationError
import re
from django.contrib.auth.forms import UserCreationForm
from django.contrib.auth.models import User
from crispy_forms.helper import FormHelper
from crispy_forms.layout import Layout, Row, Column, Field
from .models import (
    Perfil,
    PerfilPuxador,
    Puxador,
    VidroBase,
    EspessuraVidro,
    Acabamento,
    Divisor,
    Cliente,
    UsuarioPerfil,
)

class AcabamentoForm(forms.ModelForm):
    class Meta:
        model = Acabamento
        fields = ["nome"]
        widgets = {
            "nome": forms.TextInput(attrs={
                "class": "form-control",
            })
        }

    def clean_nome(self):
        nome = (self.cleaned_data.get("nome") or "").strip()

        if not nome:
            raise ValidationError("Informe o nome do acabamento.")

        # evita duplicidade ignorando maiúsculas/minúsculas
        qs = Acabamento.objects.filter(nome__iexact=nome)
        if self.instance.pk:
            qs = qs.exclude(pk=self.instance.pk)

        if qs.exists():
            raise ValidationError("Este acabamento já está cadastrado.")

        return nome

class PerfilPuxadorForm(forms.ModelForm):
    class Meta:
        model = PerfilPuxador
        fields = [
            "codigo",
            "descricao",
            "preco",
            "acabamento",
            "tipo",
            "modelo",
        ]


class PuxadorForm(forms.ModelForm):
    class Meta:
        model = Puxador
        fields = ["codigo", "descricao", "preco", "acabamento", "tipo", "modelo"]
        widgets = {
            "codigo": forms.TextInput(attrs={
                "class": "form-control",
                "maxlength": "6",
                "inputmode": "numeric",
            }),
            "descricao": forms.TextInput(attrs={"class": "form-control"}),
            "preco": forms.NumberInput(attrs={"class": "form-control", "step": "0.01"}),
            "acabamento": forms.Select(attrs={"class": "form-select"}),
            "tipo": forms.TextInput(attrs={"class": "form-control"}),
            "modelo": forms.TextInput(attrs={"class": "form-control"}),
        }

    def clean_codigo(self):
        codigo = (self.cleaned_data.get("codigo") or "").strip()

        # aceita somente números
        if not codigo.isdigit():
            raise ValidationError("O código deve conter apenas números.")

        # no máximo 6 dígitos
        if len(codigo) > 6:
            raise ValidationError("O código deve ter no máximo 6 dígitos.")

        # completa com zeros à esquerda
        codigo = codigo.zfill(6)

        # evita duplicidade (ignorando o próprio registro na edição)
        qs = Puxador.objects.filter(codigo=codigo)
        if self.instance.pk:
            qs = qs.exclude(pk=self.instance.pk)

        if qs.exists():
            raise ValidationError("Já existe um puxador com este código.")

        return codigo

class DivisorForm(forms.ModelForm):
    class Meta:
        model = Divisor
        fields = [
            "codigo",
            "descricao",
            "preco",
            "acabamento",
            "tipo",
            "modelo",
            "encaixe",
        ]



class Porta1PuxadorForm(forms.Form):
    cliente_nome = forms.CharField(label="Cliente", required=False)

    largura_porta_m = forms.DecimalField(
        label="Largura da porta (m)", decimal_places=3
    )
    altura_porta_m = forms.DecimalField(
        label="Altura da porta (m)", decimal_places=3
    )
    quantidade = forms.IntegerField(
        label="Quantidade", initial=1, min_value=1
    )

    perfil_estrutura = forms.ModelChoiceField(
        label="Perfil Estrutura (PERFIl)",
        queryset=Perfil.objects.all(),
    )

    perfil_puxador = forms.ModelChoiceField(
        label="Perfil Puxador (PERFIL_PUXADOR)",
        queryset=PerfilPuxador.objects.none(),
        required=True,
    )

    vidro_base = forms.ModelChoiceField(
        label="Vidro (BASE_VIDROS)",
        queryset=VidroBase.objects.none(),
        required=True,
    )

    def __init__(self, *args, **kwargs):
        perfil_id = kwargs.pop("perfil_id", None)
        super().__init__(*args, **kwargs)

        if perfil_id:
            perfil = Perfil.objects.filter(id=perfil_id).first()
            if perfil:
                # Puxadores compatíveis (já estão filtrados por acabamento no cadastro)
                self.fields["perfil_puxador"].queryset = perfil.puxadores_compativeis.all()

                # Vidros filtrados por espessuras compatíveis
                self.fields["vidro_base"].queryset = VidroBase.objects.filter(
                    espessura__in=perfil.espessuras_vidro_compativeis.all()
                )
        else:
            self.fields["perfil_puxador"].queryset = PerfilPuxador.objects.all()
            self.fields["vidro_base"].queryset = VidroBase.objects.all()


class PerfilForm(forms.ModelForm):
    puxadores_compativeis = forms.ModelMultipleChoiceField(
        label="Perfis Puxadores compatíveis (mesmo acabamento)",
        queryset=PerfilPuxador.objects.none(),
        required=False,
        widget=forms.CheckboxSelectMultiple,
    )
    puxadores_simples_compativeis = forms.ModelMultipleChoiceField(
        label="Puxadores simples compatíveis",
        queryset=Puxador.objects.none(),
        required=False,
        widget=forms.CheckboxSelectMultiple,
    )
    divisores_compativeis = forms.ModelMultipleChoiceField(
        label="Divisores compatíveis",
        queryset=Divisor.objects.none(),
        required=False,
        widget=forms.CheckboxSelectMultiple,
    )
    vidros_compativeis = forms.ModelMultipleChoiceField(
        queryset=VidroBase.objects.none(),
        widget=forms.CheckboxSelectMultiple,
        required=False,
        label="Vidros compatíveis:",
    )
    espessura_vidro = forms.ModelChoiceField(
        queryset=EspessuraVidro.objects.all(),
        required=False,
        label="Espessura do vidro"
    )


    class Meta:
        model = Perfil
        fields = [
            "codigo",
            "descricao",
            "preco",
            "acabamento",
            "tipo",
            "modelo",
            "puxadores_compativeis",
            "puxadores_simples_compativeis",
            "divisores_compativeis",
            "espessuras_vidro_compativeis",
        ]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        ac_id = None
        if self.instance and self.instance.pk:
            ac_id = self.instance.acabamento_id

        if "acabamento" in self.data and self.data.get("acabamento"):
            ac_id = self.data.get("acabamento")

        if ac_id:
            self.fields["puxadores_compativeis"].queryset = PerfilPuxador.objects.filter(
                acabamento_id=ac_id
            )
            self.fields["puxadores_simples_compativeis"].queryset = Puxador.objects.filter(
                acabamento_id=ac_id
            )
            self.fields["divisores_compativeis"].queryset = Divisor.objects.filter(
                acabamento_id=ac_id
            )
        else:
            self.fields["puxadores_compativeis"].queryset = PerfilPuxador.objects.none()
            self.fields["puxadores_simples_compativeis"].queryset = Puxador.objects.none()
            self.fields["divisores_compativeis"].queryset = Divisor.objects.none()
         # --------- ESPESSURA / VIDROS ----------
        esp_id = None

        # se veio do POST/HTMX, usa o valor enviado
        if "espessura_vidro" in self.data and self.data.get("espessura_vidro"):
            esp_id = self.data.get("espessura_vidro")

        # se está carregando edição (GET, sem data), usa a que já está salva
        elif self.instance and self.instance.pk:
            esp_vals = list(
                self.instance.espessuras_vidro_compativeis.values_list("id", flat=True)
            )
            if esp_vals:
                esp_id = esp_vals[0]  # estamos usando só 1 espessura

        # define o queryset dos vidros com base na espessura
        if esp_id:
            self.fields["vidros_compativeis"].queryset = VidroBase.objects.filter(
                espessura_id=esp_id
            )
            # preenche o select de espessura na tela de edição
            if not self.data:
                self.initial.setdefault("espessura_vidro", esp_id)
        else:
            self.fields["vidros_compativeis"].queryset = VidroBase.objects.none()

        # marca os vidros que já estavam salvos no perfil (só na edição GET)
        if self.instance and self.instance.pk and not self.data:
            self.initial.setdefault(
                "vidros_compativeis",
                list(self.instance.vidros_compativeis.values_list("id", flat=True)),
            )


class EspessuraVidroForm(forms.ModelForm):
    class Meta:
        model = EspessuraVidro
        fields = ["valor_mm"]


class VidroBaseForm(forms.ModelForm):
    class Meta:
        model = VidroBase
        fields = ["codigo", "descricao", "preco", "espessura"]
        widgets = {
            "codigo": forms.TextInput(
                attrs={
                    "class": "form-control",
                    "placeholder": "Ex: 000001",
                }
            ),
            "descricao": forms.TextInput(
                attrs={"class": "form-control"}
            ),
            "preco": forms.NumberInput(
                attrs={
                    "class": "form-control",
                    "step": "0.01",
                }
            ),
            "espessura": forms.Select(
                attrs={"class": "form-select"}
            ),
        }


class ClienteForm(forms.ModelForm):
    # Campo sobrescrito → dois rádios PF / PJ
    tipo_pessoa = forms.ChoiceField(
        choices=[("PF", "PF"), ("PJ", "PJ")],
        widget=forms.RadioSelect,
        label="Tipo",
    )

    class Meta:
        model = Cliente
        fields = ["codigo", "tipo_pessoa", "ativo", "cpf_cnpj", "nome", "telefone", "email"]
        widgets = {
            "codigo": forms.TextInput(attrs={
                "class": "form-control",
                "maxlength": "6",
                "inputmode": "numeric",
                "placeholder": "Ex: 000123",
            }),
            "cpf_cnpj": forms.TextInput(attrs={"class": "form-control"}),
            "nome": forms.TextInput(attrs={
                "class": "form-control",
                "style": "text-transform: uppercase;",  # 👈 aparece em maiúsculo no front
            }),
            "telefone": forms.TextInput(attrs={"class": "form-control"}),
            "email": forms.EmailInput(attrs={"class": "form-control"}),
            "ativo": forms.CheckboxInput(attrs={"class": "form-check-input"}),
        }
        labels = {
            "codigo": "Código*",
            "cpf_cnpj": "CPF/CNPJ*",
            "ativo": "Ativo",
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        # obrigatórios
        self.fields["codigo"].required = True
        self.fields["nome"].required = True
        self.fields["tipo_pessoa"].required = True
        self.fields["cpf_cnpj"].required = True

        self.helper = FormHelper()
        self.helper.form_show_labels = True
        # importante: como já existe <form> no template, não deixa o crispy criar outro
        self.helper.form_tag = False

        # 🚩 AQUI está a ordem das linhas 🚩
        self.helper.layout = Layout(
            # 1ª linha → Tipo (PF/PJ) + Ativo à direita
            Row(
                Column("tipo_pessoa", css_class="col-md-8"),
                Column(
                    "ativo",
                    css_class="col-md-4 d-flex align-items-center justify-content-end"
                ),
            ),

            # 2ª linha → Código + CPF/CNPJ (lado a lado)
            Row(
                Column("codigo", css_class="col-md-6"),
                Column("cpf_cnpj", css_class="col-md-6"),
            ),

            # 3ª linha → Nome sozinho
            Row(
                Column("nome", css_class="col-md-12"),
            ),

            # 4ª linha → Telefone + Email
            Row(
                Column("telefone", css_class="col-md-4"),
                Column("email", css_class="col-md-8"),
            ),
        )

    def clean_codigo(self):
        codigo = self.cleaned_data.get("codigo") or ""
        apenas_numeros = re.sub(r"\D", "", codigo)

        if not apenas_numeros:
            raise ValidationError("Informe o código do cliente.")

        if len(apenas_numeros) > 6:
            raise ValidationError("Código deve ter no máximo 6 dígitos.")

        # já devolve com zeros à esquerda
        return apenas_numeros.zfill(6)

    def clean_nome(self):
        nome = self.cleaned_data.get("nome") or ""
        return nome.upper()

    
    def clean_cpf_cnpj(self):
        """Validação simples de quantidade de dígitos conforme PF/PJ."""
        tipo = self.cleaned_data.get("tipo_pessoa")
        valor = self.cleaned_data.get("cpf_cnpj") or ""
        apenas_numeros = re.sub(r"\D", "", valor)

        if not tipo:
            raise ValidationError("Informe se o cliente é PF ou PJ.")

        if tipo == "PF":
            if len(apenas_numeros) != 11:
                raise ValidationError("CPF deve ter 11 dígitos.")
        elif tipo == "PJ":
            if len(apenas_numeros) != 14:
                raise ValidationError("CNPJ deve ter 14 dígitos.")

        return valor


class UsuarioPerfilForm(forms.ModelForm):
    username = forms.CharField(
        label="Nome de usuário",
        widget=forms.TextInput(attrs={"class": "form-control"}),
    )
    nome = forms.CharField(
        label="Nome",
        widget=forms.TextInput(
            attrs={"class": "form-control", "style": "text-transform: uppercase;"}
        ),
    )
    password1 = forms.CharField(
        label="Senha",
        widget=forms.PasswordInput(attrs={"class": "form-control"}),
        required=False,
    )
    password2 = forms.CharField(
        label="Confirmar senha",
        widget=forms.PasswordInput(attrs={"class": "form-control"}),
        required=False,
    )

    class Meta:
        model = UsuarioPerfil
        fields = ["codigo", "tipo_usuario", "ativo"]
        widgets = {
            "codigo": forms.TextInput(
                attrs={
                    "class": "form-control",
                    "maxlength": "6",
                    "placeholder": "Ex: 000001",
                }
            ),
            "tipo_usuario": forms.Select(attrs={"class": "form-select"}),
            "ativo": forms.CheckboxInput(attrs={"class": "form-check-input"}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        # edição → preenche campos com dados do User
        if self.instance and self.instance.pk:
            user = self.instance.user
            self.fields["username"].initial = user.username
            self.fields["nome"].initial = user.first_name or user.get_full_name()

        self.helper = FormHelper()
        self.helper.form_show_labels = True
        self.helper.form_tag = False  # form já vem do template

        self.helper.layout = Layout(
        # 1ª linha → somente "Ativo" à direita
            Row(
                Column(
                    "ativo",
                    css_class="col-12 d-flex justify-content-end align-items-center",
                ),
            ),

            # 2ª linha → Código, Nome de usuário, Tipo usuário
            Row(
                Column("codigo", css_class="col-md-3"),
                Column("username", css_class="col-md-4"),
                Column("tipo_usuario", css_class="col-md-5"),
            ),

            # 3ª linha → Nome
            Row(
                Column("nome", css_class="col-md-12"),
            ),

            # 4ª linha → Senha / Confirmar senha
            Row(
                Column("password1", css_class="col-md-6"),
                Column("password2", css_class="col-md-6"),
            ),
        )


    def clean_codigo(self):
        codigo = self.cleaned_data.get("codigo") or ""
        num = re.sub(r"\D", "", codigo)
        if not num:
            raise ValidationError("Informe o código.")
        if len(num) > 6:
            raise ValidationError("Código deve ter no máximo 6 dígitos.")
        return num.zfill(6)

    def clean_nome(self):
        nome = self.cleaned_data.get("nome") or ""
        return nome.upper()

    def clean(self):
        cleaned = super().clean()
        pw1 = cleaned.get("password1")
        pw2 = cleaned.get("password2")

        if self.instance.pk:
            # edição → senha opcional
            if pw1 or pw2:
                if pw1 != pw2:
                    raise ValidationError("As senhas não conferem.")
        else:
            # cadastro → senha obrigatória
            if not pw1 or not pw2:
                raise ValidationError("Informe a senha duas vezes.")
            if pw1 != pw2:
                raise ValidationError("As senhas não conferem.")
        return cleaned

    def save(self, commit=True):
        perfil = super().save(commit=False)
        data = self.cleaned_data

        if perfil.pk:
            user = perfil.user
        else:
            user = User()

        user.username = data["username"]
        user.first_name = data["nome"]

        # define se é admin (staff)
        if data["tipo_usuario"] == "ADMIN":
            user.is_staff = True
        else:
            user.is_staff = False

        pw1 = data.get("password1")
        if pw1:
            user.set_password(pw1)

        if commit:
            user.save()
            perfil.user = user
            perfil.save()

        return perfil