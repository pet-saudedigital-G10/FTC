"""
O mascaramento acontece na importação.
RegistroFila nunca guarda nome completo nem CNS completo, só
nome_mascarado e cns_mascarado. Por isso os seletores abaixo não mascaram
nada de novo: eles só filtram e devolvem os campos que já são mascarados.
"""
from django.db.models import QuerySet

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

    return RegistroFila.objects.filter(
        paciente=paciente,
        publicacao__status=PublicacaoFila.Status.PUBLICADA,
        situacao__in=SITUACOES_ATIVAS,
    ).select_related('paciente', 'publicacao__especialidade')


def somente_digitos(valor: str | None) -> str:
    return ''.join(c for c in str(valor or '') if c.isdigit())


def buscar_registros_fila(
    *,
    # --- especialidade / tipo de exame ---
    especialidade_id: int | None = None,
    especialidade_slug: str | None = None,
    especialidade_tipo: str | None = None,   # Especialidade.Tipo.EXAME / .CONSULTA
    especialidade_nome: str | None = None,   # busca parcial: "ultrassonografia", "cardiologia"...
    # --- qual publicação ---
    competencia=None,                        # date (dia 1); omitido = a publicada agora
    apenas_publicada: bool = True,           # False só em telas administrativas (histórico)
    # --- pessoa ---
    codigo_solicitacao: str | None = None,   # protocolo exato
    cpf: str | None = None,                  # documento completo, requer paciente vinculado
    cns: str | None = None,                  # completo (15 díg., requer paciente vinculado) OU só os 4 últimos
    ano_nascimento_de: int | None = None,
    ano_nascimento_ate: int | None = None,
    sexo: str | None = None,
    # --- outros filtros de fila ---
    situacao=None,                           # um valor ou uma lista de RegistroFila.Situacao
    tipo: str | None = None,                 # RegistroFila.Tipo
    prioridade: int | None = None,
) -> QuerySet[RegistroFila]:
    # Monta o queryset de registros de fila já mascarados (os campos vêm
    # prontos do banco). Mesma base de RegistroFilaListView.get_queryset
    # (views/fila.py

    qs = RegistroFila.objects.select_related('publicacao', 'publicacao__especialidade')

    if apenas_publicada:
        qs = qs.filter(publicacao__status=PublicacaoFila.Status.PUBLICADA)
    if competencia:
        qs = qs.filter(publicacao__competencia=competencia)

    if especialidade_id:
        qs = qs.filter(publicacao__especialidade_id=especialidade_id)
    if especialidade_slug:
        qs = qs.filter(publicacao__especialidade__slug=especialidade_slug)
    if especialidade_tipo:
        qs = qs.filter(publicacao__especialidade__tipo=especialidade_tipo)
    if especialidade_nome:
        qs = qs.filter(publicacao__especialidade__nome__icontains=especialidade_nome)

    if codigo_solicitacao:
        qs = qs.filter(codigo_solicitacao=somente_digitos(codigo_solicitacao))

    if cpf:
        # só encontra algo quando RegistroFila.paciente estiver vinculado
        qs = qs.filter(paciente__cpf=somente_digitos(cpf))
    if cns:
        digitos = somente_digitos(cns)
        if len(digitos) >= 15:
            qs = qs.filter(paciente__cns=digitos)      # requer paciente vinculado
        elif digitos:
            qs = qs.filter(cns_mascarado__endswith=digitos[-4:])  # funciona hoje

    if ano_nascimento_de:
        qs = qs.filter(ano_nascimento__gte=ano_nascimento_de)
    if ano_nascimento_ate:
        qs = qs.filter(ano_nascimento__lte=ano_nascimento_ate)
    if sexo:
        qs = qs.filter(sexo=sexo)

    if situacao:
        situacoes = situacao if isinstance(situacao, (list, tuple, set)) else [situacao]
        qs = qs.filter(situacao__in=situacoes)
    if tipo:
        qs = qs.filter(tipo=tipo)
    if prioridade:
        qs = qs.filter(prioridade=prioridade)

    return qs.order_by('publicacao__especialidade__nome', 'posicao')
