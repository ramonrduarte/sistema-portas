from django import forms
from django.core.exceptions import ValidationError
from ..models import ConfiguracaoEmpresa

_LOGO_MAX_MB = 5


def _validate_logo_size(file):
    if file and file.size > _LOGO_MAX_MB * 1024 * 1024:
        raise ValidationError(f"O arquivo não pode ultrapassar {_LOGO_MAX_MB} MB.")


class ConfiguracaoEmpresaForm(forms.ModelForm):
    limpar_logo = forms.BooleanField(
        required=False,
        label="Remover logo atual",
        widget=forms.CheckboxInput(attrs={"class": "form-check-input"}),
    )
    limpar_logo_claro = forms.BooleanField(
        required=False,
        label="Remover logo (fundo claro) atual",
        widget=forms.CheckboxInput(attrs={"class": "form-check-input"}),
    )

    logo = forms.ImageField(
        required=False,
        validators=[_validate_logo_size],
        widget=forms.ClearableFileInput(attrs={"class": "form-control"}),
        label="Logo principal (PNG, JPG — para fundo escuro/navbar)",
    )
    logo_claro = forms.ImageField(
        required=False,
        validators=[_validate_logo_size],
        widget=forms.ClearableFileInput(attrs={"class": "form-control"}),
        label="Logo para impressão (PNG, JPG — para fundo branco)",
    )

    class Meta:
        model = ConfiguracaoEmpresa
        fields = ["nome_empresa", "logo", "logo_claro", "custo_mao_obra",
                  "dias_expiracao_orcamento", "horario_limpeza_orcamento"]
        widgets = {
            "nome_empresa": forms.TextInput(attrs={"class": "form-control"}),
            "custo_mao_obra": forms.NumberInput(attrs={"class": "form-control", "step": "0.01"}),
            "dias_expiracao_orcamento": forms.NumberInput(attrs={"class": "form-control", "min": "0"}),
            "horario_limpeza_orcamento": forms.TimeInput(attrs={"class": "form-control", "type": "time"}),
        }
        labels = {
            "nome_empresa": "Nome da empresa",
            "custo_mao_obra": "Custo mão de obra por porta (R$)",
            "dias_expiracao_orcamento": "Expiração de orçamentos (dias)",
            "horario_limpeza_orcamento": "Horário da limpeza automática",
        }

    def save(self, commit=True):
        obj = super().save(commit=False)
        if self.cleaned_data.get("limpar_logo") and obj.logo:
            obj.logo.delete(save=False)
            obj.logo = None
        if self.cleaned_data.get("limpar_logo_claro") and obj.logo_claro:
            obj.logo_claro.delete(save=False)
            obj.logo_claro = None
        if commit:
            obj.save()
        return obj
