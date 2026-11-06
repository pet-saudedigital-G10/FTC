from datetime import datetime

from django.conf import settings
from django.utils import timezone
from rest_framework import serializers

from ftc.models import Especialidade, PublicacaoFila, RegistroFila
from ftc.utils.masking import mask_cns, mask_cpf, mask_name


SISTEMA_IDENTIFICACAO_FTC = 'Fila Transparente Cidadã (FTC)'
ORIENTACAO_COMPROVANTE_POSICAO = (
    'A posição apresentada corresponde à publicação identificada neste comprovante. '
    'A ordem de atendimento poderá sofrer alterações em razão de novas solicitações, '
    'critérios de prioridade clínica e movimentações da regulação.'
)


class RegistroFilaPublicSerializer(serializers.ModelSerializer):

    especialidade = serializers.CharField(source='publicacao.especialidade.nome')
    tipo_especialidade = serializers.CharField(source='publicacao.especialidade.get_tipo_display')
    competencia = serializers.DateField(source='publicacao.competencia')


    situacao_display = serializers.CharField(source='get_situacao_display', read_only=True)
    prioridade_display = serializers.CharField(source='get_prioridade_display', read_only=True)

    class Meta:
        model = RegistroFila
        fields = [
            'posicao',
            'prioridade',
            'prioridade_display',
            'situacao',
            'situacao_display',
            'especialidade',
            'tipo_especialidade',
            'competencia',
            'nome_mascarado',
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
    publicada_em = serializers.DateTimeField(
        source='publicacao.publicada_em',
        read_only=True,
    )
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
            'publicada_em',
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


class RegistroFilaComprovanteSerializer(RegistroFilaSerializer):
    sistema = serializers.SerializerMethodField()
    nome_mascarado = serializers.SerializerMethodField()
    cpf_mascarado = serializers.SerializerMethodField()
    cns_mascarado = serializers.SerializerMethodField()
    emitido_em = serializers.SerializerMethodField()
    orientacao = serializers.SerializerMethodField()

    class Meta(RegistroFilaSerializer.Meta):
        fields = (
            ('sistema',)
            + RegistroFilaSerializer.Meta.fields
            + ('emitido_em', 'orientacao')
        )
        read_only_fields = fields

    def get_sistema(self, obj: RegistroFila) -> str:
        return SISTEMA_IDENTIFICACAO_FTC

    def get_nome_mascarado(self, obj: RegistroFila) -> str:
        if obj.paciente and obj.paciente.nome_completo:
            return mask_name(obj.paciente.nome_completo)
        return mask_name(obj.nome_mascarado)

    def get_cpf_mascarado(self, obj: RegistroFila) -> str:
        if obj.paciente and obj.paciente.cpf:
            return mask_cpf(obj.paciente.cpf)
        return mask_cpf(obj.cpf_mascarado) or obj.cpf_mascarado

    def get_cns_mascarado(self, obj: RegistroFila) -> str:
        if obj.paciente and obj.paciente.cns:
            return mask_cns(obj.paciente.cns)
        return mask_cns(obj.cns_mascarado) or obj.cns_mascarado

    def get_emitido_em(self, obj: RegistroFila):
        return timezone.now()

    def get_orientacao(self, obj: RegistroFila) -> str:
        return ORIENTACAO_COMPROVANTE_POSICAO


class FiltroOpcaoSerializer(serializers.Serializer):
    value = serializers.JSONField()
    label = serializers.CharField()


class FilaOpcoesSerializer(serializers.Serializer):
    especialidade_tipos = FiltroOpcaoSerializer(many=True)
    tipos = FiltroOpcaoSerializer(many=True)
    situacoes = FiltroOpcaoSerializer(many=True)
    prioridades = FiltroOpcaoSerializer(many=True)


class AtualizacaoFilaSerializer(serializers.Serializer):
    arquivo = serializers.FileField(write_only=True)
    especialidade = serializers.PrimaryKeyRelatedField(
        queryset=Especialidade.objects.filter(ativo=True),
    )
    competencia = serializers.CharField(
        help_text='Mes de referencia no formato AAAA-MM.',
    )
    observacao = serializers.CharField(
        required=False,
        allow_blank=True,
        max_length=2000,
    )

    def validate_arquivo(self, arquivo):
        limite = settings.FILA_PDF_MAX_SIZE_BYTES
        if arquivo.size > limite:
            limite_mb = limite // (1024 * 1024)
            raise serializers.ValidationError(
                f'O arquivo excede o limite de {limite_mb} MB.'
            )
        if not arquivo.name.lower().endswith('.pdf'):
            raise serializers.ValidationError('Envie um arquivo com extensao .pdf.')

        arquivo.seek(0)
        assinatura = arquivo.read(5)
        arquivo.seek(0)
        if assinatura != b'%PDF-':
            raise serializers.ValidationError('O arquivo enviado nao e um PDF valido.')
        return arquivo

    def validate_competencia(self, valor):
        try:
            return datetime.strptime(valor, '%Y-%m').date().replace(day=1)
        except ValueError as exc:
            raise serializers.ValidationError(
                'Use o formato AAAA-MM para a competencia.'
            ) from exc


class AtualizacaoFilaRespostaSerializer(serializers.Serializer):
    publicacao_id = serializers.IntegerField()
    especialidade_id = serializers.IntegerField()
    competencia = serializers.DateField()
    versao = serializers.IntegerField()
    status = serializers.ChoiceField(choices=PublicacaoFila.Status.choices)
    registros_importados = serializers.IntegerField()
    publicacoes_substituidas = serializers.ListField(
        child=serializers.IntegerField(),
    )
    importado_em = serializers.DateTimeField()
    publicada_em = serializers.DateTimeField()
