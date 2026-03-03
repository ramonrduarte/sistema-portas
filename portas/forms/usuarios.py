from django import forms
from django.core.exceptions import ValidationError
from django.contrib.auth.models import User
import re
from ..models import UsuarioPerfil


class UsuarioPerfilForm(forms.ModelForm):
    username = forms.CharField(
        label="Nome de usuário",
        widget=forms.TextInput(attrs={"class": "form-control"}),
    )
    nome = forms.CharField(
        label="Nome completo",
        widget=forms.TextInput(attrs={"class": "form-control", "style": "text-transform: uppercase;"}),
    )
    password1 = forms.CharField(
        label="Senha",
        widget=forms.PasswordInput(attrs={"class": "form-control", "autocomplete": "new-password"}),
        required=False,
    )
    password2 = forms.CharField(
        label="Confirmar senha",
        widget=forms.PasswordInput(attrs={"class": "form-control", "autocomplete": "new-password"}),
        required=False,
    )

    class Meta:
        model = UsuarioPerfil
        fields = [
            "codigo", "tipo_usuario", "ativo",
            "perm_pedidos_ver", "perm_pedidos_criar", "perm_pedidos_editar", "perm_pedidos_excluir",
            "perm_producao_ver", "perm_producao_alterar_status",
            "perm_clientes_ver", "perm_clientes_editar", "perm_clientes_excluir",
            "perm_cadastros_ver", "perm_cadastros_editar", "perm_cadastros_excluir",
        ]

        _sw = {"class": "form-check-input perm-check", "role": "switch"}
        widgets = {
            "codigo":                      forms.TextInput(attrs={"class": "form-control"}),
            "tipo_usuario":                forms.Select(attrs={"class": "form-select", "id": "id_tipo_usuario"}),
            "ativo":                       forms.CheckboxInput(attrs={"class": "form-check-input"}),
            "perm_pedidos_ver":            forms.CheckboxInput(attrs=_sw),
            "perm_pedidos_criar":          forms.CheckboxInput(attrs=_sw),
            "perm_pedidos_editar":         forms.CheckboxInput(attrs=_sw),
            "perm_pedidos_excluir":        forms.CheckboxInput(attrs=_sw),
            "perm_producao_ver":           forms.CheckboxInput(attrs=_sw),
            "perm_producao_alterar_status":forms.CheckboxInput(attrs=_sw),
            "perm_clientes_ver":           forms.CheckboxInput(attrs=_sw),
            "perm_clientes_editar":        forms.CheckboxInput(attrs=_sw),
            "perm_clientes_excluir":       forms.CheckboxInput(attrs=_sw),
            "perm_cadastros_ver":          forms.CheckboxInput(attrs=_sw),
            "perm_cadastros_editar":       forms.CheckboxInput(attrs=_sw),
            "perm_cadastros_excluir":      forms.CheckboxInput(attrs=_sw),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if self.instance and self.instance.pk:
            user = self.instance.user
            self.fields["username"].initial = user.username
            self.fields["nome"].initial = user.first_name or user.get_full_name()

    def clean_codigo(self):
        codigo = self.cleaned_data.get("codigo") or ""
        num = re.sub(r"\D", "", codigo)
        if not num:
            raise ValidationError("Informe o código.")
        if len(num) > 6:
            raise ValidationError("Código deve ter no máximo 6 dígitos.")
        return num.zfill(6)

    def clean_nome(self):
        return (self.cleaned_data.get("nome") or "").upper()

    def clean(self):
        cleaned = super().clean()
        pw1 = cleaned.get("password1")
        pw2 = cleaned.get("password2")
        if self.instance.pk:
            if pw1 or pw2:
                if pw1 != pw2:
                    raise ValidationError("As senhas não conferem.")
        else:
            if not pw1 or not pw2:
                raise ValidationError("Informe a senha duas vezes.")
            if pw1 != pw2:
                raise ValidationError("As senhas não conferem.")
        return cleaned

    def save(self, commit=True):
        perfil = super().save(commit=False)
        data = self.cleaned_data

        user = perfil.user if perfil.pk else User()
        user.username = data["username"]
        user.first_name = data["nome"]
        user.is_staff = data["tipo_usuario"] == "ADMIN"

        pw1 = data.get("password1")
        if pw1:
            user.set_password(pw1)

        if commit:
            user.save()
            perfil.user = user
            perfil.save()

        return perfil
