from rest_framework import serializers

from ftc.models import Especialidade, RegistroFila


class RegistroFilaPublicSerializer(serializers.ModelSerializer):

    especialidade = serializers.CharField(source='publicacao.especialidade.nome')
    tipo_especialidade = serializers.CharField(source='publicacao.especialidade.get_tipo_display')
    competencia = serializers.DateField(source='publicacao.competencia')

    nome_paciente = serializers.CharField(source='paciente.nome_completo')

    class Meta:
        model = RegistroFila
        fields = [
            'posicao',
            'prioridade',
            'situacao',
            'especialidade',
            'tipo_especialidade',
            'competencia',
            'nome_paciente',
            'data_solicitacao',
        ]


class EspecialidadeSerializer(serializers.ModelSerializer):
    tipo_display = serializers.CharField(source='get_tipo_display', read_only=True)

    class Meta:
        model = Especialidade
        fields = ('id', 'nome', 'slug', 'tipo', 'tipo_display', 'ativo')
        read_only_fields = fields


class RegistroFilaSerializer(serializers.ModelSerializer):
    especialidade_id = serializers.IntegerField(
        source='publicacao.especialidade_id',
        read_only=True,
    )
    especialidade_nome = serializers.CharField(
        source='publicacao.especialidade.nome',
        read_only=True,
    )
    especialidade_slug = serializers.CharField(
        source='publicacao.especialidade.slug',
        read_only=True,
    )
    especialidade_tipo = serializers.CharField(
        source='publicacao.especialidade.tipo',
        read_only=True,
    )
    especialidade_tipo_display = serializers.CharField(
        source='publicacao.especialidade.get_tipo_display',
        read_only=True,
    )
    publicacao_id = serializers.IntegerField(source='publicacao.id', read_only=True)
    competencia = serializers.DateField(source='publicacao.competencia', read_only=True)
    versao = serializers.IntegerField(source='publicacao.versao', read_only=True)
    tipo_display = serializers.CharField(source='get_tipo_display', read_only=True)
    situacao_display = serializers.CharField(
        source='get_situacao_display',
        read_only=True,
    )
    prioridade_display = serializers.CharField(
        source='get_prioridade_display',
        read_only=True,
    )

    class Meta:
        model = RegistroFila
        fields = (
            'id',
            'publicacao_id',
            'competencia',
            'versao',
            'especialidade_id',
            'especialidade_nome',
            'especialidade_slug',
            'especialidade_tipo',
            'especialidade_tipo_display',
            'data_solicitacao',
            'nome_mascarado',
            'ano_nascimento',
            'cpf_mascarado',
            'cns_mascarado',
            'sexo',
            'codigo_solicitacao',
            'posicao',
            'prioridade',
            'prioridade_display',
            'tipo',
            'tipo_display',
            'situacao',
            'situacao_display',
        )
        read_only_fields = fields


class FiltroOpcaoSerializer(serializers.Serializer):
    value = serializers.JSONField()
    label = serializers.CharField()


class FilaOpcoesSerializer(serializers.Serializer):
    especialidade_tipos = FiltroOpcaoSerializer(many=True)
    tipos = FiltroOpcaoSerializer(many=True)
    situacoes = FiltroOpcaoSerializer(many=True)
    prioridades = FiltroOpcaoSerializer(many=True)
