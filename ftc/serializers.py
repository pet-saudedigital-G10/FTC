from rest_framework import serializers
from .models import Paciente

class PacienteSerializer(serializers.ModelSerializer):
    cns = serializers.SerializerMethodField()
    nome = serializers.SerializerMethodField()

    class Meta:
        model = Paciente
        fields = '__all__'

    def get_cns(self, obj):
        return f"{'*' * (len(obj.cns)-4)}{obj.cns[-4:]}"

    def get_nome(self, obj):
        partes = obj.nome.split()

        resultado = []

        for parte in partes:
            resultado.append(
                parte[0] + "*" * (len(parte) - 1)
            )

        return " ".join(resultado)