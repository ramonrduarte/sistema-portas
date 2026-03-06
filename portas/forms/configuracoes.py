from django import forms
from ..models import ConfiguracaoEmpresa


class ConfiguracaoEmpresaForm(forms.ModelForm):
    limpar_logo = forms.BooleanField(
        required=False,
        label="Remover logo atual",
        widget=forms.CheckboxInput(attrs={"class": "form-check-input"}),
    )

    class Meta:
        model = ConfiguracaoEmpresa
        fields = ["nome_empresa", "logo", "custo_mao_obra"]
        widgets = {
            "nome_empresa": forms.TextInput(attrs={"class": "form-control"}),
            "logo": forms.ClearableFileInput(attrs={"class": "form-control"}),
            "custo_mao_obra": forms.NumberInput(attrs={"class": "form-control", "step": "0.01"}),
        }
        labels = {
            "nome_empresa": "Nome da empresa",
            "logo": "Logo (PNG, JPG — recomendado: fundo transparente)",
            "custo_mao_obra": "Custo mão de obra por porta (R$)",
        }

    def save(self, commit=True):
        obj = super().save(commit=False)
        if self.cleaned_data.get("limpar_logo") and obj.logo:
            obj.logo.delete(save=False)
            obj.logo = None
        if commit:
            obj.save()
        return obj
