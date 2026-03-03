from django import forms

from ..models import BimerConfig

_DIAS_CHOICES = [
    ("mon", "Seg"),
    ("tue", "Ter"),
    ("wed", "Qua"),
    ("thu", "Qui"),
    ("fri", "Sex"),
    ("sat", "Sáb"),
    ("sun", "Dom"),
]

_HORAS_CHOICES = [(str(h), f"{h:02d}:00") for h in range(24)]


class BimerConfigForm(forms.ModelForm):
    """
    Formulário de configuração da integração Bimer.
    - password: write-only (nunca pré-preenchido)
    - sync_dias / sync_horas: checkboxes que serializam para campos CharField do model
    """
    password = forms.CharField(
        required=False,
        label="Senha",
        widget=forms.PasswordInput(attrs={
            "class": "form-control",
            "autocomplete": "new-password",
            "placeholder": "••••••• (deixe em branco para manter a senha atual)",
        }),
    )

    sync_dias = forms.MultipleChoiceField(
        choices=_DIAS_CHOICES,
        required=False,
        label="Dias da semana",
        widget=forms.CheckboxSelectMultiple,
    )

    sync_horas = forms.MultipleChoiceField(
        choices=_HORAS_CHOICES,
        required=False,
        label="Horários de sincronização",
        widget=forms.CheckboxSelectMultiple,
    )

    class Meta:
        model  = BimerConfig
        fields = ["base_url", "username", "password", "identificador_empresa",
                  "identificador_tabela_precos", "identificador_caracteristica_clientes", "ativo"]
        widgets = {
            "base_url": forms.URLInput(attrs={
                "class": "form-control",
                "placeholder": "https://api.suaempresa.bimer.com.br",
            }),
            "username": forms.TextInput(attrs={
                "class": "form-control",
                "autocomplete": "off",
            }),
            "identificador_empresa": forms.TextInput(attrs={
                "class": "form-control",
                "placeholder": "Ex.: 1",
            }),
            "identificador_tabela_precos": forms.TextInput(attrs={
                "class": "form-control",
                "placeholder": "Ex.: 00A0000003",
            }),
            "identificador_caracteristica_clientes": forms.TextInput(attrs={
                "class": "form-control",
                "placeholder": "Ex.: 00A000000N",
            }),
            "ativo": forms.CheckboxInput(attrs={"class": "form-check-input"}),
        }
        labels = {
            "base_url": "URL base da API",
            "username": "Usuário",
            "ativo":    "Integração ativa",
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Pré-preenche checkboxes com os valores salvos no model
        if self.instance and self.instance.pk:
            self.fields["sync_dias"].initial = [
                d.strip() for d in self.instance.sync_dias_semana.split(",") if d.strip()
            ]
            self.fields["sync_horas"].initial = [
                h.strip() for h in self.instance.sync_horarios.split(",") if h.strip()
            ]

    def save(self, commit=True):
        obj = super().save(commit=False)

        # Senha write-only
        novo_password = self.cleaned_data.get("password")
        if novo_password:
            obj._password = novo_password
        else:
            obj._password = BimerConfig.get()._password

        # Serializa checkboxes para os campos CharField do model
        dias  = self.cleaned_data.get("sync_dias", [])
        horas = self.cleaned_data.get("sync_horas", [])
        obj.sync_dias_semana = ",".join(dias) if dias else "mon,tue,wed,thu,fri,sat,sun"
        obj.sync_horarios    = ",".join(sorted(horas, key=int)) if horas else "7,14"

        if commit:
            obj.save()
        return obj
