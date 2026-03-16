from rest_framework import serializers
from portas.models import (
    Acabamento,
    EspessuraVidro,
    VidroBase,
    Puxador,
    Divisor,
    Perfil,
    PerfilPuxador,
    Cliente
)


class AcabamentoSerializer(serializers.ModelSerializer):
    class Meta:
        model = Acabamento
        fields = ["id", "nome"]


class EspessuraVidroSerializer(serializers.ModelSerializer):
    class Meta:
        model = EspessuraVidro
        fields = ["id", "valor_mm"]


class VidroBaseSerializer(serializers.ModelSerializer):
    class Meta:
        model = VidroBase
        fields = [
            "id",
            "codigo",
            "descricao",
            "preco",
            "espessura",
            "ativo",
        ]


class PuxadorSerializer(serializers.ModelSerializer):
    acabamento_nome = serializers.CharField(source="acabamento.nome", read_only=True)

    class Meta:
        model = Puxador
        fields = [
            "id",
            "codigo",
            "descricao",
            "preco",
            "acabamento",
            "acabamento_nome",
            "ativo",
        ]


class DivisorSerializer(serializers.ModelSerializer):
    acabamento_nome = serializers.CharField(source="acabamento.nome", read_only=True)
    encaixe_display = serializers.CharField(
        source="get_encaixe_display", read_only=True
    )

    class Meta:
        model = Divisor
        fields = [
            "id",
            "codigo",
            "descricao",
            "preco",
            "acabamento",
            "acabamento_nome",
            "encaixe",
            "encaixe_display",
            "ativo",
        ]


class PerfilSerializer(serializers.ModelSerializer):
    acabamento_nome = serializers.CharField(source="acabamento.nome", read_only=True)

    class Meta:
        model = Perfil
        fields = [
            "id",
            "ativo",
            "codigo",
            "descricao",
            "preco",
            "acabamento",
            "acabamento_nome",
            "abatimento_mm",
            "modelo",
            "puxadores_compativeis",
            "puxadores_simples_compativeis",
            "divisores_compativeis",
            "vidros_compativeis",
            "espessuras_vidro_compativeis",
        ]


class PerfilPuxadorSerializer(serializers.ModelSerializer):
    acabamento_nome = serializers.CharField(source="acabamento.nome", read_only=True)

    class Meta:
        model = PerfilPuxador
        fields = [
            "id",
            "ativo",
            "codigo",
            "descricao",
            "preco",
            "acabamento",
            "acabamento_nome",
            "abatimento_mm",
            "modelo",
        ]


class ClienteSerializer(serializers.ModelSerializer):
    cpf_cnpj_formatado = serializers.CharField(read_only=True)

    class Meta:
        model = Cliente
        fields = [
            "id",
            "ativo",
            "codigo",
            "tipo_pessoa",
            "cpf_cnpj",
            "cpf_cnpj_formatado",
            "nome",
            "telefone",
            "email",
        ]        