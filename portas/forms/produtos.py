from django import forms
from django.core.exceptions import ValidationError
import re


class DecimalVirgula(forms.DecimalField):
    """Campo decimal que aceita vírgula como separador (padrão pt-BR)."""
    def to_python(self, value):
        if isinstance(value, str):
            value = value.replace(',', '.')
        return super().to_python(value)
from ..models import (
    Acabamento,
    PerfilPuxador,
    Puxador,
    Divisor,
    Perfil,
    VidroBase,
    EspessuraVidro,
)


class AcabamentoForm(forms.ModelForm):
    class Meta:
        model = Acabamento
        fields = ["nome"]
        widgets = {
            "nome": forms.TextInput(attrs={"class": "form-control"})
        }

    def clean_nome(self):
        nome = (self.cleaned_data.get("nome") or "").strip()
        if not nome:
            raise ValidationError("Informe o nome do acabamento.")
        qs = Acabamento.objects.filter(nome__iexact=nome)
        if self.instance.pk:
            qs = qs.exclude(pk=self.instance.pk)
        if qs.exists():
            raise ValidationError("Este acabamento já está cadastrado.")
        return nome


class PerfilPuxadorForm(forms.ModelForm):
    abatimento_mm = DecimalVirgula(
        max_digits=6, decimal_places=2, min_value=0, required=False,
        initial=0, label="Abatimento (mm)",
        widget=forms.TextInput(attrs={"class": "form-control", "placeholder": "Ex: 1,5"}),
    )

    class Meta:
        model = PerfilPuxador
        fields = ["ativo", "codigo", "descricao", "preco", "acabamento", "abatimento_mm", "modelo"]
        widgets = {
            "ativo": forms.CheckboxInput(attrs={"class": "form-check-input"}),
            "codigo": forms.TextInput(attrs={"class": "form-control", "maxlength": "6", "inputmode": "numeric"}),
            "descricao": forms.TextInput(attrs={"class": "form-control"}),
            "preco": forms.NumberInput(attrs={"class": "form-control", "step": "0.01"}),
            "acabamento": forms.Select(attrs={"class": "form-select"}),
            "modelo": forms.TextInput(attrs={"class": "form-control"}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if not self.instance.pk:
            self.fields["ativo"].initial = True

    def clean_codigo(self):
        codigo = (self.cleaned_data.get("codigo") or "").strip()
        codigo = re.sub(r"\D", "", codigo)
        if not codigo:
            raise ValidationError("Informe o código.")
        if len(codigo) > 6:
            raise ValidationError("O código deve ter no máximo 6 dígitos.")
        codigo = codigo.zfill(6)
        qs = PerfilPuxador.objects.filter(codigo=codigo)
        if self.instance.pk:
            qs = qs.exclude(pk=self.instance.pk)
        if qs.exists():
            raise ValidationError("Já existe um Perfil Puxador com este código.")
        return codigo


class PuxadorForm(forms.ModelForm):
    abatimento_mm = DecimalVirgula(
        max_digits=6, decimal_places=2, min_value=0, required=False,
        initial=0, label="Abatimento (mm)",
        widget=forms.TextInput(attrs={"class": "form-control", "placeholder": "Ex: 1,5"}),
    )

    class Meta:
        model = Puxador
        fields = ["ativo", "codigo", "descricao", "preco", "acabamento", "abatimento_mm", "modelo"]
        widgets = {
            "ativo": forms.CheckboxInput(attrs={"class": "form-check-input"}),
            "codigo": forms.TextInput(attrs={"class": "form-control", "maxlength": "6", "inputmode": "numeric"}),
            "descricao": forms.TextInput(attrs={"class": "form-control"}),
            "preco": forms.NumberInput(attrs={"class": "form-control", "step": "0.01"}),
            "acabamento": forms.Select(attrs={"class": "form-select"}),
            "modelo": forms.TextInput(attrs={"class": "form-control"}),
        }

    def clean_codigo(self):
        codigo = (self.cleaned_data.get("codigo") or "").strip()
        if not codigo.isdigit():
            raise ValidationError("O código deve conter apenas números.")
        if len(codigo) > 6:
            raise ValidationError("O código deve ter no máximo 6 dígitos.")
        codigo = codigo.zfill(6)
        qs = Puxador.objects.filter(codigo=codigo)
        if self.instance.pk:
            qs = qs.exclude(pk=self.instance.pk)
        if qs.exists():
            raise ValidationError("Já existe um puxador com este código.")
        return codigo


class DivisorForm(forms.ModelForm):
    abatimento_mm = DecimalVirgula(
        max_digits=6, decimal_places=2, min_value=0, required=False,
        initial=0, label="Abatimento (mm)",
        widget=forms.TextInput(attrs={"class": "form-control", "placeholder": "Ex: 1,5"}),
    )

    class Meta:
        model = Divisor
        fields = ["ativo", "codigo", "modelo", "descricao", "preco", "acabamento", "abatimento_mm", "encaixe"]
        widgets = {
            "ativo": forms.CheckboxInput(attrs={"class": "form-check-input"}),
            "codigo": forms.TextInput(attrs={"class": "form-control"}),
            "modelo": forms.TextInput(attrs={"class": "form-control"}),
            "descricao": forms.TextInput(attrs={"class": "form-control"}),
            "preco": forms.NumberInput(attrs={"class": "form-control", "step": "0.01"}),
            "acabamento": forms.Select(attrs={"class": "form-select"}),
            "encaixe": forms.Select(attrs={"class": "form-select"}),
        }


class PerfilForm(forms.ModelForm):
    abatimento_mm = DecimalVirgula(
        max_digits=6, decimal_places=2, min_value=0, required=False,
        initial=0, label="Abatimento (mm)",
        widget=forms.TextInput(attrs={"class": "form-control", "placeholder": "Ex: 1,5"}),
    )
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
    espessuras_vidro = forms.ModelMultipleChoiceField(
        queryset=EspessuraVidro.objects.all().order_by("valor_mm"),
        required=False,
        label="Espessuras do vidro",
        widget=forms.SelectMultiple(attrs={
            "class": "form-select",
            "hx-get": "/perfis/vidros-por-espessuras/",
            "hx-target": "#col-vidros",
            "hx-swap": "innerHTML",
            "hx-trigger": "change",
            "hx-include": "closest form",
        }),
    )

    class Meta:
        model = Perfil
        fields = [
            "codigo", "descricao", "preco", "acabamento", "abatimento_mm",
            "modelo", "fixacao_vidro", "vidro_polido",
            "puxadores_compativeis", "puxadores_simples_compativeis", "divisores_compativeis",
        ]
        widgets = {
            "codigo": forms.TextInput(attrs={"class": "form-control"}),
            "descricao": forms.TextInput(attrs={"class": "form-control"}),
            "preco": forms.NumberInput(attrs={"class": "form-control", "step": "0.01"}),
            "acabamento": forms.Select(attrs={"class": "form-select"}),
            "modelo": forms.TextInput(attrs={"class": "form-control"}),
            "fixacao_vidro": forms.Select(attrs={"class": "form-select"}),
            "vidro_polido": forms.CheckboxInput(attrs={"class": "form-check-input"}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        ac_id = None
        if self.instance and self.instance.pk:
            ac_id = self.instance.acabamento_id
        if "acabamento" in self.data and self.data.get("acabamento"):
            ac_id = self.data.get("acabamento")

        if ac_id:
            self.fields["puxadores_compativeis"].queryset = PerfilPuxador.objects.filter(acabamento_id=ac_id)
            self.fields["puxadores_simples_compativeis"].queryset = Puxador.objects.filter(acabamento_id=ac_id)
            self.fields["divisores_compativeis"].queryset = Divisor.objects.filter(acabamento_id=ac_id)
        else:
            self.fields["puxadores_compativeis"].queryset = PerfilPuxador.objects.none()
            self.fields["puxadores_simples_compativeis"].queryset = Puxador.objects.none()
            self.fields["divisores_compativeis"].queryset = Divisor.objects.none()

        esp_ids = []
        if self.data:
            esp_ids = self.data.getlist("espessuras_vidro")
        if (not esp_ids) and self.instance and self.instance.pk:
            esp_ids = list(self.instance.espessuras_vidro_compativeis.values_list("id", flat=True))
        if (not esp_ids) and self.instance and self.instance.pk:
            esp_ids = list(
                self.instance.vidros_compativeis.values_list("espessura_id", flat=True).distinct()
            )

        if self.instance and self.instance.pk and not self.data:
            self.initial["espessuras_vidro"] = esp_ids

        if esp_ids:
            self.fields["vidros_compativeis"].queryset = (
                VidroBase.objects.filter(espessura_id__in=esp_ids)
                .select_related("espessura")
                .order_by("descricao")
            )
        else:
            self.fields["vidros_compativeis"].queryset = VidroBase.objects.none()

        if self.instance and self.instance.pk and not self.data:
            self.initial["vidros_compativeis"] = list(
                self.instance.vidros_compativeis.values_list("id", flat=True)
            )


class EspessuraVidroForm(forms.ModelForm):
    class Meta:
        model = EspessuraVidro
        fields = ['valor_mm']
        widgets = {
            'valor_mm': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.1'}),
        }


class VidroBaseForm(forms.ModelForm):
    class Meta:
        model = VidroBase
        fields = ["ativo", "codigo", "descricao", "preco", "espessura", "chapa_largura_mm", "chapa_altura_mm"]
        widgets = {
            "ativo": forms.CheckboxInput(attrs={"class": "form-check-input"}),
            "codigo": forms.TextInput(attrs={"class": "form-control", "placeholder": "Ex: 000001"}),
            "descricao": forms.TextInput(attrs={"class": "form-control"}),
            "preco": forms.NumberInput(attrs={"class": "form-control", "step": "0.01"}),
            "espessura": forms.Select(attrs={"class": "form-select"}),
            "chapa_largura_mm": forms.NumberInput(attrs={"class": "form-control"}),
            "chapa_altura_mm": forms.NumberInput(attrs={"class": "form-control"}),
        }
