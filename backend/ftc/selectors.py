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
