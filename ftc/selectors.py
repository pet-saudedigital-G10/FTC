from django.db.models import QuerySet
from ftc.models import Paciente, Especialidade, PublicacaoFila, RegistroFila

def get_posicoes_paciente_ativas(*, cpf: str) -> QuerySet[RegistroFila]:

    try:
        paciente = Paciente.objects.get(cpf=cpf)
    except Paciente.DoesNotExist:
        return RegistroFila.objects.none()
    
    publicados_recentes = PublicacaoFila.objects.filter(status=PublicacaoFila.Status.PUBLICADA).order_by('especialidade', '-competencia', '-versao').distinct('especialidade')

    estar_na_fila_status = [
        'SOLICITADO', 'AGENDADO', 'AGUARDANDO_REGULACAO', 'PENDENTE', 
        'REENVIADO', 'AGUARDANDO_TRANSPORTE', 'SOLICITADO_CRL', 'AGUARDANDO_LEITO'
    ]

    registros = RegistroFila.objects.filter(
        paciente=paciente,
        publicacao__in=publicados_recentes,
        situacao__in=estar_na_fila_status,

    ).select_related('publicacao__especialidade')

    return registros