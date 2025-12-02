from django import forms
from .models import (
    Perfil,
    PerfilPuxador,
    Puxador,
    VidroBase,
    EspessuraVidro,
    Acabamento,
    Divisor,
    Cliente,
)

class AcabamentoForm(forms.ModelForm):
    class Meta:
        model = Acabamento
        fields = ["nome"]

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
        fields = [
            "codigo",
            "descricao",
            "preco",
            "acabamento",
            "tipo",
            "modelo",
        ]

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
        fields = [
            "codigo",
            "descricao",
            "preco",
            "espessura",  # 👈 escolhe a espessura aqui
        ]

class ClienteForm(forms.ModelForm):
    class Meta:
        model = Cliente
        fields = [
            "tipo_pessoa",
            "nome",
            "documento",
            "telefone",
            "email",
            "logradouro",
            "numero",
            "bairro",
            "cidade",
            "uf",
            "cep",
            "observacoes",
        ]

