from django.conf import settings
from django.core.validators import MaxValueValidator, MinValueValidator, RegexValidator
from django.db import models


cpf_validator = RegexValidator(
    regex=r'^\d{11}$',
    message='O CPF deve conter exatamente 11 digitos.',
)
cns_validator = RegexValidator(
    regex=r'^\d{15}$',
    message='O CNS deve conter exatamente 15 digitos.',
)


class Paciente(models.Model):
    class Sexo(models.TextChoices):
        MASCULINO = 'M', 'Masculino'
        FEMININO = 'F', 'Feminino'
        NAO_INFORMADO = 'N', 'Nao informado'

    cpf = models.CharField(
        max_length=11,
        unique=True,
        null=True,
        blank=True,
        validators=[cpf_validator],
        verbose_name='CPF',
    )
    cns = models.CharField(
        max_length=15,
        unique=True,
        null=True,
        blank=True,
        validators=[cns_validator],
        verbose_name='Cartao Nacional de Saude (CNS)',
    )
    nome_completo = models.CharField(max_length=255, blank=True)
    data_nascimento = models.DateField(null=True, blank=True)
    sexo = models.CharField(
        max_length=1,
        choices=Sexo.choices,
        default=Sexo.NAO_INFORMADO,
    )
    criado_em = models.DateTimeField(auto_now_add=True)
    atualizado_em = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'pacientes'
        verbose_name = 'Paciente'
        verbose_name_plural = 'Pacientes'
        ordering = ['nome_completo', 'id']
        constraints = [
            models.CheckConstraint(
                condition=(
                    (models.Q(cpf__isnull=False) & ~models.Q(cpf=''))
                    | (models.Q(cns__isnull=False) & ~models.Q(cns=''))
                ),
                name='paciente_tem_cpf_ou_cns',
            ),
        ]

    def __str__(self):
        return self.nome_completo or f'Paciente {self.pk}'


class Especialidade(models.Model):
    class Tipo(models.TextChoices):
        CONSULTA = 'CONSULTA', 'Consulta'
        EXAME = 'EXAME', 'Exame'

    nome = models.CharField(max_length=255)
    slug = models.SlugField(max_length=255, unique=True)
    tipo = models.CharField(
        max_length=10,
        choices=Tipo.choices,
        default=Tipo.CONSULTA,
    )
    ativo = models.BooleanField(default=True)

    class Meta:
        db_table = 'especialidades'
        verbose_name = 'Especialidade'
        verbose_name_plural = 'Especialidades'
        ordering = ['tipo', 'nome']
        constraints = [
            models.UniqueConstraint(
                fields=['tipo', 'nome'],
                name='especialidade_tipo_nome_unicos',
            ),
        ]

    def __str__(self):
        return f'{self.get_tipo_display()} - {self.nome}'


class PublicacaoFila(models.Model):
    class Status(models.TextChoices):
        RASCUNHO = 'RASCUNHO', 'Rascunho'
        PUBLICADA = 'PUBLICADA', 'Publicada'
        ARQUIVADA = 'ARQUIVADA', 'Arquivada'

    especialidade = models.ForeignKey(
        Especialidade,
        on_delete=models.PROTECT,
        related_name='publicacoes',
    )
    competencia = models.DateField(
        help_text='Use o primeiro dia do mes de referencia.',
    )
    versao = models.PositiveSmallIntegerField(
        default=1,
        validators=[MinValueValidator(1)],
    )
    arquivo_original = models.FileField(upload_to='filas/%Y/%m/')
    hash_arquivo = models.CharField(
        max_length=64,
        unique=True,
        help_text='SHA-256 do arquivo importado.',
    )
    status = models.CharField(
        max_length=10,
        choices=Status.choices,
        default=Status.RASCUNHO,
    )
    importado_por = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='filas_importadas',
    )
    importado_em = models.DateTimeField(auto_now_add=True)
    publicada_em = models.DateTimeField(null=True, blank=True)
    observacao = models.TextField(blank=True)

    class Meta:
        db_table = 'publicacoes_fila'
        verbose_name = 'Publicacao da fila'
        verbose_name_plural = 'Publicacoes das filas'
        ordering = ['-competencia', 'especialidade', '-versao']
        constraints = [
            models.UniqueConstraint(
                fields=['especialidade', 'competencia', 'versao'],
                name='publicacao_especialidade_competencia_versao_unicas',
            ),
            models.UniqueConstraint(
                fields=['especialidade', 'competencia'],
                condition=models.Q(status='PUBLICADA'),
                name='uma_publicacao_ativa_por_fila',
            ),
        ]

    def __str__(self):
        return (
            f'{self.especialidade} - '
            f'{self.competencia:%m/%Y} - v{self.versao}'
        )


class RegistroFila(models.Model):
    class Prioridade(models.IntegerChoices):
        NIVEL_1 = 1, 'Prioridade 1'
        NIVEL_2 = 2, 'Prioridade 2'
        NIVEL_3 = 3, 'Prioridade 3'

    class Tipo(models.TextChoices):
        SOLICITADAS = 'SOLICITADAS', 'Solicitadas'
        PENDENTES = 'PENDENTES', 'Pendentes'
        BAIXADAS = 'BAIXADAS', 'Baixadas'

    class Situacao(models.TextChoices):
        SOLICITADO = 'SOLICITADO', 'Solicitado'
        AGENDADO = 'AGENDADO', 'Agendado'
        DEVOLVIDO = 'DEVOLVIDO', 'Devolvido'
        AGUARDANDO_REGULACAO = 'AGUARDANDO_REGULACAO', 'Aguardando regulação'
        PENDENTE = 'PENDENTE', 'Pendente'
        REENVIADO = 'REENVIADO', 'Reenviado'
        NEGADO = 'NEGADO', 'Negado'
        CANCELADO = 'CANCELADO', 'Cancelado'
        BAIXADO_INTERNADO_CRL = (
            'BAIXADO_INTERNADO_CRL',
            'Baixado - Internado CRL',
        )
        AGUARDANDO_TRANSPORTE = 'AGUARDANDO_TRANSPORTE', 'Aguardando Transporte'
        SOLICITADO_CRL = 'SOLICITADO_CRL', 'Solicitado CRL'
        NEGADO_CRL = 'NEGADO_CRL', 'Negado CRL'
        AGUARDANDO_LEITO = 'AGUARDANDO_LEITO', 'Aguardando Leito'

    publicacao = models.ForeignKey(
        PublicacaoFila,
        on_delete=models.CASCADE,
        related_name='registros',
    )
    paciente = models.ForeignKey(
        Paciente,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='registros_fila',
    )
    data_solicitacao = models.DateField()
    nome_mascarado = models.CharField(max_length=255)
    ano_nascimento = models.PositiveSmallIntegerField(null=True, blank=True)
    cpf_mascarado = models.CharField(max_length=20, blank=True)
    cns_mascarado = models.CharField(max_length=20, blank=True)
    sexo = models.CharField(
        max_length=1,
        choices=Paciente.Sexo.choices,
        default=Paciente.Sexo.NAO_INFORMADO,
    )
    codigo_solicitacao = models.CharField(max_length=50)
    posicao = models.PositiveIntegerField(validators=[MinValueValidator(1)])
    prioridade = models.PositiveSmallIntegerField(
        choices=Prioridade.choices,
        default=Prioridade.NIVEL_3,
        validators=[MinValueValidator(1), MaxValueValidator(3)],
    )
    tipo = models.CharField(
        max_length=20,
        choices=Tipo.choices,
        default=Tipo.SOLICITADAS,
    )
    situacao = models.CharField(
        max_length=30,
        choices=Situacao.choices,
        default=Situacao.SOLICITADO,
        verbose_name='Situação',
    )
    criado_em = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'registros_fila'
        verbose_name = 'Registro da fila'
        verbose_name_plural = 'Registros das filas'
        ordering = ['publicacao', 'posicao']
        constraints = [
            models.UniqueConstraint(
                fields=['publicacao', 'codigo_solicitacao'],
                name='codigo_unico_por_publicacao',
            ),
            models.UniqueConstraint(
                fields=['publicacao', 'posicao'],
                name='posicao_unica_por_publicacao',
            ),
        ]
        indexes = [
            models.Index(
                fields=['publicacao', 'posicao'],
                name='reg_pub_pos_idx',
            ),
            models.Index(
                fields=['publicacao', 'data_solicitacao'],
                name='reg_pub_data_idx',
            ),
            models.Index(
                fields=['tipo', 'situacao', 'prioridade'],
                name='reg_tipo_sit_pri_idx',
            ),
        ]

    def __str__(self):
        return (
            f'{self.publicacao} - posicao {self.posicao} - '
            f'{self.codigo_solicitacao}'
        )
