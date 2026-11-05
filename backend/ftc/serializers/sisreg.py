from rest_framework import serializers

from ftc.models import ConfiguracaoSisreg, Especialidade


codigo_grupo_field = {
    'regex': r'^[0-9A-Za-z]{1,20}$',
    'error_messages': {'invalid': 'Informe um codigo de grupo valido.'},
}


class SisregStatusSerializer(serializers.Serializer):
    habilitado = serializers.BooleanField()
    ambiente = serializers.CharField(allow_null=True)
    indice = serializers.CharField(allow_null=True)
    pode_configurar = serializers.BooleanField()


class SisregConfiguracaoSerializer(serializers.Serializer):
    exigir_credencial = False

    habilitado = serializers.BooleanField(default=False)
    ambiente = serializers.ChoiceField(
        choices=ConfiguracaoSisreg.Ambiente.choices,
    )
    client_id = serializers.RegexField(
        r'^\d{7}$',
        required=False,
        allow_blank=True,
        error_messages={'invalid': 'Informe o CNES com 7 digitos.'},
    )
    client_secret = serializers.CharField(
        write_only=True,
        required=False,
        allow_blank=True,
        max_length=512,
    )
    indice = serializers.RegexField(
        r'^solicitacao-ambulatorial-[a-z0-9_-]+$',
        required=False,
        allow_blank=True,
        max_length=120,
        error_messages={
            'invalid': 'Informe um indice solicitacao-ambulatorial-{uf}-{municipio}.',
        },
    )
    centrais_reguladoras = serializers.ListField(
        child=serializers.RegexField(
            r'^[0-9A-Za-z]{1,10}$',
            error_messages={'invalid': 'Informe codigos de central validos.'},
        ),
        required=False,
        default=list,
        max_length=100,
    )
    client_secret_configurado = serializers.BooleanField(read_only=True)
    atualizado_em = serializers.DateTimeField(read_only=True)

    def validate(self, attrs):
        if not (attrs['habilitado'] or self.exigir_credencial):
            return attrs

        erros = {}
        if not attrs.get('client_id'):
            erros['client_id'] = 'Informe o Client ID (CNES).'
        if not (attrs.get('client_secret') or self.instance.client_secret):
            erros['client_secret'] = 'Informe o Client Secret.'
        if not attrs.get('indice'):
            erros['indice'] = 'Informe o indice liberado na credencial.'
        if erros:
            raise serializers.ValidationError(erros)
        return attrs

    def aplicar(self, configuracao):
        """Copia os dados validados, mantendo o segredo se vier em branco."""
        dados = dict(self.validated_data)
        client_secret = dados.pop('client_secret', '')
        for campo, valor in dados.items():
            setattr(configuracao, campo, valor)
        if client_secret:
            configuracao.client_secret = client_secret
        return configuracao


class SisregTesteConexaoSerializer(SisregConfiguracaoSerializer):
    exigir_credencial = True


class SisregTesteRespostaSerializer(serializers.Serializer):
    total = serializers.IntegerField()


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
