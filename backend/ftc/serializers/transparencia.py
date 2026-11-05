from rest_framework import serializers


class TransparenciaContagemSerializer(serializers.Serializer):
    valor = serializers.JSONField()
    rotulo = serializers.CharField()
    total = serializers.IntegerField()


class TransparenciaTipoSerializer(TransparenciaContagemSerializer):
    espera_media_dias = serializers.FloatField(allow_null=True)


class TransparenciaEspecialidadeSerializer(serializers.Serializer):
    nome = serializers.CharField()
    tipo = serializers.CharField()
    total = serializers.IntegerField()
    espera_media_dias = serializers.FloatField(allow_null=True)
    maior_espera_dias = serializers.IntegerField()


class TransparenciaIndicadoresSerializer(serializers.Serializer):
    atualizado_em = serializers.DateTimeField(allow_null=True)
    total_aguardando = serializers.IntegerField()
    especialidades_com_fila = serializers.IntegerField()
    espera_media_dias = serializers.FloatField(allow_null=True)
    maior_espera_dias = serializers.IntegerField()
    por_tipo = TransparenciaTipoSerializer(many=True)
    por_prioridade = TransparenciaContagemSerializer(many=True)
    por_situacao = TransparenciaContagemSerializer(many=True)
    especialidades = TransparenciaEspecialidadeSerializer(many=True)


class TransparenciaPosicaoSerializer(serializers.Serializer):
    codigo_solicitacao = serializers.RegexField(
        r'^[0-9A-Za-z-]{1,50}$',
        error_messages={'invalid': 'Informe um codigo de solicitacao valido.'},
    )
    ano_nascimento = serializers.IntegerField(min_value=1900, max_value=2100)


class TransparenciaFilaSerializer(serializers.Serializer):
    especialidade = serializers.CharField()
    tipo = serializers.CharField()
    posicao = serializers.IntegerField()
    total_aguardando = serializers.IntegerField()
    situacao = serializers.CharField()
    prioridade = serializers.CharField()
    data_solicitacao = serializers.DateField()
    dias_espera = serializers.IntegerField()
    atualizado_em = serializers.DateTimeField(allow_null=True)


class TransparenciaPosicaoRespostaSerializer(serializers.Serializer):
    encontrado = serializers.BooleanField()
    filas = TransparenciaFilaSerializer(many=True)
