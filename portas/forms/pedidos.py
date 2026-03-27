from django import forms
from ..models import (
    Cliente,
    Acabamento,
    Perfil,
    PerfilPuxador,
    Puxador,
    Divisor,
    VidroBase,
    Pedido,
    PedidoItem,
)

_QTD_CHOICES = [("", "—"), ("1", "1"), ("2", "2")]


class PedidoItemForm(forms.ModelForm):
    class Meta:
        model = PedidoItem
        fields = [
            "largura_mm", "altura_mm", "quantidade",
            "acabamento", "perfil",
            "perfil_puxador", "qtd_perfil_puxador",
            "puxador", "qtd_puxador", "puxador_tamanho_mm", "puxador_sobreposto",
            "divisor", "qtd_divisor",
            "vidro",
            "adicional_valor",  "adicional_obs",
            "adicional2_valor", "adicional2_obs",
            "adicional3_valor", "adicional3_obs",
            "adicional4_valor", "adicional4_obs",
            "desconto",
        ]
        widgets = {
            "largura_mm": forms.NumberInput(attrs={"class": "form-control", "min": 1}),
            "altura_mm": forms.NumberInput(attrs={"class": "form-control", "min": 1}),
            "quantidade": forms.NumberInput(attrs={"class": "form-control", "min": 1}),
            "acabamento": forms.Select(attrs={
                "class": "form-select",
                "hx-get": "/pedidos/htmx/perfis-por-acabamento/",
                "hx-target": "#col-perfil",
                "hx-swap": "innerHTML",
                "hx-trigger": "change",
                "hx-include": "closest form",
            }),
            "perfil": forms.Select(attrs={
                "class": "form-select",
                "hx-get": "/pedidos/htmx/opcoes-por-perfil/",
                "hx-target": "#col-opcoes",
                "hx-swap": "innerHTML",
                "hx-trigger": "change",
                "hx-include": "closest form",
            }),
            "perfil_puxador": forms.Select(attrs={"class": "form-select"}),
            "qtd_perfil_puxador": forms.Select(attrs={"class": "form-select"}),
            "puxador": forms.Select(attrs={"class": "form-select"}),
            "qtd_puxador": forms.Select(attrs={"class": "form-select"}),
            "puxador_tamanho_mm": forms.NumberInput(attrs={"class": "form-control", "min": 1}),
            "puxador_sobreposto": forms.CheckboxInput(attrs={"class": "form-check-input"}),
            "divisor": forms.Select(attrs={"class": "form-select"}),
            "qtd_divisor": forms.Select(attrs={"class": "form-select"}),
            "vidro": forms.Select(attrs={"class": "form-select"}),
            "adicional_valor":  forms.NumberInput(attrs={"class": "form-control", "min": "0", "step": "0.01", "placeholder": "0,00"}),
            "adicional_obs":    forms.TextInput(attrs={"class": "form-control", "placeholder": "Descrição..."}),
            "adicional2_valor": forms.NumberInput(attrs={"class": "form-control", "min": "0", "step": "0.01", "placeholder": "0,00"}),
            "adicional2_obs":   forms.TextInput(attrs={"class": "form-control", "placeholder": "Descrição..."}),
            "adicional3_valor": forms.NumberInput(attrs={"class": "form-control", "min": "0", "step": "0.01", "placeholder": "0,00"}),
            "adicional3_obs":   forms.TextInput(attrs={"class": "form-control", "placeholder": "Descrição..."}),
            "adicional4_valor": forms.NumberInput(attrs={"class": "form-control", "min": "0", "step": "0.01", "placeholder": "0,00"}),
            "adicional4_obs":   forms.TextInput(attrs={"class": "form-control", "placeholder": "Descrição..."}),
            "desconto": forms.NumberInput(attrs={"class": "form-control", "min": "0", "max": "100", "step": "0.01", "placeholder": "0,00"}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["qtd_perfil_puxador"].required = False
        self.fields["qtd_puxador"].required = False
        self.fields["qtd_divisor"].required = False
        self.fields["qtd_perfil_puxador"].choices = _QTD_CHOICES
        self.fields["qtd_puxador"].choices = _QTD_CHOICES
        self.fields["qtd_divisor"].choices = _QTD_CHOICES

        self.fields["perfil"].queryset = Perfil.objects.none()
        self.fields["perfil_puxador"].queryset = PerfilPuxador.objects.none()
        self.fields["puxador"].queryset = Puxador.objects.none()
        self.fields["divisor"].queryset = Divisor.objects.none()
        self.fields["vidro"].queryset = VidroBase.objects.none()

        ac_id = self.data.get("acabamento") or (self.instance.acabamento_id if self.instance.pk else None)
        if ac_id:
            self.fields["perfil"].queryset = Perfil.objects.filter(acabamento_id=ac_id, ativo=True).order_by("descricao")

        perfil_id = self.data.get("perfil") or (self.instance.perfil_id if self.instance.pk else None)
        if perfil_id:
            p = Perfil.objects.filter(pk=perfil_id).first()
            if p:
                self.fields["perfil_puxador"].queryset = p.puxadores_compativeis.filter(ativo=True).order_by("descricao")
                self.fields["puxador"].queryset = p.puxadores_simples_compativeis.filter(ativo=True).order_by("descricao")
                self.fields["divisor"].queryset = p.divisores_compativeis.filter(ativo=True).order_by("descricao")
                self.fields["vidro"].queryset = p.vidros_compativeis.filter(ativo=True).order_by("descricao")

    def clean(self):
        data = super().clean()
        pp = data.get("perfil_puxador")
        pux = data.get("puxador")
        div = data.get("divisor")

        if pp and pux:
            raise forms.ValidationError("Escolha apenas Perfil Puxador OU Puxador simples.")

        if pp:
            if str(data.get("qtd_perfil_puxador") or "") not in ("1", "2"):
                self.add_error("qtd_perfil_puxador", "Informe 1 ou 2.")
        if pux:
            if str(data.get("qtd_puxador") or "") not in ("1", "2"):
                self.add_error("qtd_puxador", "Informe 1 ou 2.")
            if not data.get("puxador_tamanho_mm"):
                self.add_error("puxador_tamanho_mm", "Informe o tamanho do puxador.")
        if div:
            if str(data.get("qtd_divisor") or "") not in ("1", "2"):
                self.add_error("qtd_divisor", "Informe 1 ou 2.")

        return data


class PedidoForm(forms.ModelForm):
    class Meta:
        model = Pedido
        fields = ["cliente"]
        widgets = {
            "cliente": forms.Select(attrs={"class": "form-select"}),
        }


class PedidoNovoOrcamentoForm(forms.Form):
    cliente = forms.ModelChoiceField(
        queryset=Cliente.objects.filter(ativo=True).order_by("nome"),
        required=True,
    )
    largura_mm = forms.IntegerField(min_value=1, required=True)
    altura_mm = forms.IntegerField(min_value=1, required=True)
    quantidade = forms.IntegerField(min_value=1, required=True, initial=1)

    acabamento = forms.ModelChoiceField(
        queryset=Acabamento.objects.all().order_by("nome"),
        required=True,
        widget=forms.Select(attrs={
            "class": "form-select",
            "hx-get": "/pedidos/htmx/perfis-por-acabamento/",
            "hx-target": "#col-perfil",
            "hx-swap": "innerHTML",
            "hx-trigger": "change",
            "hx-include": "closest form",
        })
    )
    perfil = forms.ModelChoiceField(
        queryset=Perfil.objects.none(),
        required=True,
        widget=forms.Select(attrs={
            "class": "form-select",
            "hx-get": "/pedidos/htmx/opcoes-por-perfil/",
            "hx-target": "#col-opcoes",
            "hx-swap": "innerHTML",
            "hx-trigger": "change",
            "hx-include": "closest form",
            "disabled": "disabled",
        })
    )

    perfil_puxador = forms.ModelChoiceField(queryset=PerfilPuxador.objects.none(), required=False)
    qtd_perfil_puxador = forms.ChoiceField(choices=_QTD_CHOICES, required=False)
    puxador = forms.ModelChoiceField(queryset=Puxador.objects.none(), required=False)
    qtd_puxador = forms.ChoiceField(choices=_QTD_CHOICES, required=False)
    puxador_tamanho_mm = forms.IntegerField(min_value=1, required=False)
    divisor = forms.ModelChoiceField(queryset=Divisor.objects.none(), required=False)
    qtd_divisor = forms.ChoiceField(choices=_QTD_CHOICES, required=False)
    vidro = forms.ModelChoiceField(queryset=VidroBase.objects.none(), required=False)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        _select_fields = ["perfil_puxador", "qtd_perfil_puxador", "puxador", "qtd_puxador",
                          "divisor", "qtd_divisor", "vidro"]
        _input_fields = ["puxador_tamanho_mm"]

        for f in _select_fields:
            self.fields[f].widget.attrs.update({"class": "form-select", "disabled": "disabled"})
        for f in _input_fields:
            self.fields[f].widget.attrs.update({"class": "form-control", "disabled": "disabled"})

        ac_id = self.data.get("acabamento")
        if ac_id:
            qs = Perfil.objects.filter(acabamento_id=ac_id, ativo=True).order_by("descricao")
            self.fields["perfil"].queryset = qs
            if qs.exists():
                self.fields["perfil"].widget.attrs.pop("disabled", None)

        perfil_id = self.data.get("perfil")
        if perfil_id:
            p = Perfil.objects.filter(pk=perfil_id).first()
            if p:
                self.fields["perfil_puxador"].queryset = p.puxadores_compativeis.filter(ativo=True).order_by("descricao")
                self.fields["puxador"].queryset = p.puxadores_simples_compativeis.filter(ativo=True).order_by("descricao")
                self.fields["divisor"].queryset = p.divisores_compativeis.filter(ativo=True).order_by("descricao")
                self.fields["vidro"].queryset = p.vidros_compativeis.filter(ativo=True).order_by("descricao")

                if self.fields["perfil_puxador"].queryset.exists():
                    self.fields["perfil_puxador"].widget.attrs.pop("disabled", None)
                    self.fields["qtd_perfil_puxador"].widget.attrs.pop("disabled", None)
                if self.fields["puxador"].queryset.exists():
                    self.fields["puxador"].widget.attrs.pop("disabled", None)
                    self.fields["qtd_puxador"].widget.attrs.pop("disabled", None)
                    self.fields["puxador_tamanho_mm"].widget.attrs.pop("disabled", None)
                if self.fields["divisor"].queryset.exists():
                    self.fields["divisor"].widget.attrs.pop("disabled", None)
                    self.fields["qtd_divisor"].widget.attrs.pop("disabled", None)
                if self.fields["vidro"].queryset.exists():
                    self.fields["vidro"].widget.attrs.pop("disabled", None)

    def clean(self):
        data = super().clean()
        pp = data.get("perfil_puxador")
        pux = data.get("puxador")
        div = data.get("divisor")

        if pp and pux:
            raise forms.ValidationError("Escolha apenas Perfil Puxador OU Puxador simples.")

        if pp:
            if data.get("qtd_perfil_puxador") not in ("1", "2"):
                self.add_error("qtd_perfil_puxador", "Informe 1 ou 2.")
        else:
            if data.get("qtd_perfil_puxador"):
                self.add_error("qtd_perfil_puxador", "Remova a quantidade (sem Perfil Puxador).")

        if pux:
            if data.get("qtd_puxador") not in ("1", "2"):
                self.add_error("qtd_puxador", "Informe 1 ou 2.")
            if not data.get("puxador_tamanho_mm"):
                self.add_error("puxador_tamanho_mm", "Informe o tamanho do puxador.")
        else:
            if data.get("qtd_puxador"):
                self.add_error("qtd_puxador", "Remova a quantidade (sem Puxador).")
            if data.get("puxador_tamanho_mm"):
                self.add_error("puxador_tamanho_mm", "Remova o tamanho (sem Puxador).")

        if div:
            if data.get("qtd_divisor") not in ("1", "2"):
                self.add_error("qtd_divisor", "Informe 1 ou 2.")
        else:
            if data.get("qtd_divisor"):
                self.add_error("qtd_divisor", "Remova a quantidade (sem Divisor).")

        return data
