from rest_framework import serializers

from ftc.models import Especialidade


codigo_grupo_field = {
    'regex': r'^[0-9A-Za-z]{1,20}$',
    'error_messages': {'invalid': 'Informe um codigo de grupo valido.'},
}


class SisregStatusSerializer(serializers.Serializer):
    habilitado = serializers.BooleanField()
    ambiente = serializers.CharField(allow_null=True)
    indice = serializers.CharField(allow_null=True)


class SisregGrupoSerializer(serializers.Serializer):
    codigo = serializers.CharField()
    nome = serializers.CharField()
    total = serializers.IntegerField()


class SisregGruposRespostaSerializer(serializers.Serializer):
    total = serializers.IntegerField()
    grupos = SisregGrupoSerializer(many=True)


class SisregFilaFiltroSerializer(serializers.Serializer):
    grupo = serializers.RegexField(required=False, **codigo_grupo_field)
    pagina = serializers.IntegerField(required=False, min_value=1, default=1)


class SisregRegistroSerializer(serializers.Serializer):
    codigo_solicitacao = serializers.CharField()
    data_solicitacao = serializers.DateField()
    nome_mascarado = serializers.CharField()
    cns_mascarado = serializers.CharField()
    codigo_grupo_procedimento = serializers.CharField()
    nome_grupo_procedimento = serializers.CharField()
    classificacao_risco = serializers.CharField()
    situacao = serializers.CharField()
    situacao_display = serializers.CharField()


class SisregFilaRespostaSerializer(serializers.Serializer):
    total = serializers.IntegerField()
    pagina = serializers.IntegerField()
    tamanho_pagina = serializers.IntegerField()
    registros = SisregRegistroSerializer(many=True)


class SisregImportacaoSerializer(serializers.Serializer):
    especialidade = serializers.PrimaryKeyRelatedField(
        queryset=Especialidade.objects.filter(ativo=True),
    )
    codigo_grupo_procedimento = serializers.RegexField(**codigo_grupo_field)
