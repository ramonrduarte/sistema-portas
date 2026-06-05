from rest_framework import serializers
from portas.models import Acabamento, Perfil, PerfilPuxador, Puxador, Divisor, VidroBase


class AcabamentoSerializer(serializers.ModelSerializer):
    class Meta:
        model = Acabamento
        fields = ["id", "nome"]


class PerfilPuxadorResumidoSerializer(serializers.ModelSerializer):
    class Meta:
        model = PerfilPuxador
        fields = ["id", "descricao"]


class PuxadorResumidoSerializer(serializers.ModelSerializer):
    class Meta:
        model = Puxador
        fields = ["id", "descricao"]


class DivisorResumidoSerializer(serializers.ModelSerializer):
    encaixe_label = serializers.CharField(source="get_encaixe_display", read_only=True)

    class Meta:
        model = Divisor
        fields = ["id", "descricao", "encaixe_label"]


class VidroResumidoSerializer(serializers.ModelSerializer):
    espessura_mm = serializers.DecimalField(
        source="espessura.valor_mm", max_digits=4, decimal_places=1, read_only=True
    )

    class Meta:
        model = VidroBase
        fields = ["id", "descricao", "espessura_mm"]


class PerfilOpcoesSerializer(serializers.ModelSerializer):
    acabamento_nome = serializers.CharField(source="acabamento.nome", read_only=True)
    puxadores_compativeis = PerfilPuxadorResumidoSerializer(many=True, read_only=True)
    puxadores_simples_compativeis = PuxadorResumidoSerializer(many=True, read_only=True)
    divisores_compativeis = DivisorResumidoSerializer(many=True, read_only=True)
    vidros_compativeis = VidroResumidoSerializer(many=True, read_only=True)

    class Meta:
        model = Perfil
        fields = [
            "id",
            "descricao",
            "acabamento_id",
            "acabamento_nome",
            "puxadores_compativeis",
            "puxadores_simples_compativeis",
            "divisores_compativeis",
            "vidros_compativeis",
        ]


class PerfilPuxadorOpcoesSerializer(serializers.ModelSerializer):
    acabamento_nome = serializers.CharField(source="acabamento.nome", read_only=True)

    class Meta:
        model = PerfilPuxador
        fields = ["id", "descricao", "acabamento_id", "acabamento_nome"]


class PuxadorOpcoesSerializer(serializers.ModelSerializer):
    acabamento_nome = serializers.CharField(source="acabamento.nome", read_only=True)

    class Meta:
        model = Puxador
        fields = ["id", "descricao", "acabamento_id", "acabamento_nome"]


class DivisorOpcoesSerializer(serializers.ModelSerializer):
    acabamento_nome = serializers.CharField(source="acabamento.nome", read_only=True)
    encaixe_label = serializers.CharField(source="get_encaixe_display", read_only=True)

    class Meta:
        model = Divisor
        fields = ["id", "descricao", "acabamento_id", "acabamento_nome", "encaixe_label"]


class VidroOpcoesSerializer(serializers.ModelSerializer):
    espessura_mm = serializers.DecimalField(
        source="espessura.valor_mm", max_digits=4, decimal_places=1, read_only=True
    )

    class Meta:
        model = VidroBase
        fields = ["id", "descricao", "espessura_mm"]
