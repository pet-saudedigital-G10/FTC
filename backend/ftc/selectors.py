from django.db.models import OuterRef, QuerySet, Subquery

from ftc.models import Paciente, PublicacaoFila, RegistroFila


SITUACOES_ATIVAS = (
    RegistroFila.Situacao.SOLICITADO,
    RegistroFila.Situacao.AGENDADO,
    RegistroFila.Situacao.AGUARDANDO_REGULACAO,
    RegistroFila.Situacao.PENDENTE,
    RegistroFila.Situacao.REENVIADO,
    RegistroFila.Situacao.AGUARDANDO_TRANSPORTE,
    RegistroFila.Situacao.SOLICITADO_CRL,
    RegistroFila.Situacao.AGUARDANDO_LEITO,
)

STATUS_PUBLICACOES_HISTORICO = (
    PublicacaoFila.Status.PUBLICADA,
    PublicacaoFila.Status.ARQUIVADA,
)


def get_posicoes_paciente_ativas(*, cpf: str) -> QuerySet[RegistroFila]:
    try:
        paciente = Paciente.objects.get(cpf=cpf)
    except Paciente.DoesNotExist:
        return RegistroFila.objects.none()

    publicacao_mais_recente = (
        PublicacaoFila.objects
        .filter(
            especialidade_id=OuterRef('publicacao__especialidade_id'),
            status=PublicacaoFila.Status.PUBLICADA,
        )
        .order_by('-competencia', '-versao')
        .values('pk')[:1]
    )

    return RegistroFila.objects.filter(
        paciente=paciente,
        publicacao_id=Subquery(publicacao_mais_recente),
        situacao__in=SITUACOES_ATIVAS,
    ).select_related('paciente', 'publicacao__especialidade')


def get_registros_elegiveis_historico_paciente(*, cpf: str) -> QuerySet[RegistroFila]:
    try:
        paciente = Paciente.objects.get(cpf=cpf)
    except Paciente.DoesNotExist:
        return RegistroFila.objects.none()

    return (
        RegistroFila.objects
        .filter(
            paciente=paciente,
            publicacao__status__in=STATUS_PUBLICACOES_HISTORICO,
        )
        .select_related('paciente', 'publicacao', 'publicacao__especialidade')
    )


def get_historico_solicitacao_paciente(
    *,
    registro: RegistroFila,
) -> QuerySet[RegistroFila]:
    if (
        registro.paciente_id is None
        or registro.publicacao.status not in STATUS_PUBLICACOES_HISTORICO
    ):
        return RegistroFila.objects.none()

    return (
        RegistroFila.objects
        .filter(
            paciente_id=registro.paciente_id,
            publicacao__especialidade_id=registro.publicacao.especialidade_id,
            codigo_solicitacao=registro.codigo_solicitacao,
            publicacao__status__in=STATUS_PUBLICACOES_HISTORICO,
        )
        .select_related('paciente', 'publicacao', 'publicacao__especialidade')
        .order_by(
            'publicacao__competencia',
            'publicacao__versao',
            'publicacao__publicada_em',
            'id',
        )
    )

