from django import forms
from django.core.exceptions import ValidationError
import re
from crispy_forms.helper import FormHelper
from crispy_forms.layout import Layout, Row, Column
from ..models import Cliente


class ClienteForm(forms.ModelForm):
    tipo_pessoa = forms.ChoiceField(
        choices=[("PF", "PF"), ("PJ", "PJ")],
        widget=forms.RadioSelect,
        label="Tipo",
    )

    class Meta:
        model = Cliente
        fields = ["codigo", "tipo_pessoa", "ativo", "cpf_cnpj", "nome", "cidade", "telefone", "email"]
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
                "style": "text-transform: uppercase;",
            }),
            "cidade": forms.TextInput(attrs={"class": "form-control"}),
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
        self.fields["codigo"].required = True
        self.fields["nome"].required = True
        self.fields["tipo_pessoa"].required = True
        self.fields["cpf_cnpj"].required = True

        self.helper = FormHelper()
        self.helper.form_show_labels = True
        self.helper.form_tag = False
        self.helper.layout = Layout(
            Row(
                Column("tipo_pessoa", css_class="col-md-8"),
                Column("ativo", css_class="col-md-4 d-flex align-items-center justify-content-end"),
            ),
            Row(
                Column("codigo", css_class="col-md-6"),
                Column("cpf_cnpj", css_class="col-md-6"),
            ),
            Row(Column("nome", css_class="col-md-12")),
            Row(Column("cidade", css_class="col-md-12")),
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
        return apenas_numeros.zfill(6)

    def clean_nome(self):
        nome = (self.cleaned_data.get("nome") or "").strip()
        return nome.capitalize()

    def clean_cpf_cnpj(self):
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
