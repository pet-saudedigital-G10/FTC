"""Indicadores agregados e consulta de posicao para o link publico."""
from collections import defaultdict

from django.core.cache import cache
from django.db.models import Count, Max
from django.utils import timezone

from ftc.models import Especialidade, PublicacaoFila, RegistroFila
from ftc.selectors import get_registros_vigentes


INDICADORES_CACHE_KEY = 'transparencia:indicadores'
INDICADORES_CACHE_SEGUNDOS = 300


class _Acumulador:
    def __init__(self):
        self.total = 0
        self.dias = 0
        self.maior = 0

    def somar(self, total, dias):
        self.total += total
        self.dias += total * dias
        self.maior = max(self.maior, dias)

    @property
    def media(self):
        return round(self.dias / self.total, 1) if self.total else None


def _contagens(totais, choices):
    return [
        {'valor': valor, 'rotulo': rotulo, 'total': totais[valor]}
        for valor, rotulo in choices
        if totais[valor]
    ]


def _calcular_indicadores():
    hoje = timezone.localdate()
    linhas = (
        get_registros_vigentes()
        .order_by()
        .values(
            'publicacao__especialidade__nome',
            'publicacao__especialidade__tipo',
            'prioridade',
            'situacao',
            'data_solicitacao',
        )
        .annotate(total=Count('id'))
    )

    geral = _Acumulador()
    por_especialidade = defaultdict(_Acumulador)
    por_tipo = defaultdict(_Acumulador)
    por_prioridade = defaultdict(int)
    por_situacao = defaultdict(int)

    for linha in linhas:
        total = linha['total']
        dias = max((hoje - linha['data_solicitacao']).days, 0)
        tipo = linha['publicacao__especialidade__tipo']
        chave = (linha['publicacao__especialidade__nome'], tipo)

        geral.somar(total, dias)
        por_especialidade[chave].somar(total, dias)
        por_tipo[tipo].somar(total, dias)
        por_prioridade[linha['prioridade']] += total
        por_situacao[linha['situacao']] += total

    atualizado_em = (
        PublicacaoFila.objects
        .filter(status=PublicacaoFila.Status.PUBLICADA)
        .aggregate(ultima=Max('publicada_em'))['ultima']
    )
    return {
        'atualizado_em': atualizado_em,
        'total_aguardando': geral.total,
        'especialidades_com_fila': len(por_especialidade),
        'espera_media_dias': geral.media,
        'maior_espera_dias': geral.maior,
        'por_tipo': [
            {
                'valor': valor,
                'rotulo': rotulo,
                'total': por_tipo[valor].total,
                'espera_media_dias': por_tipo[valor].media,
            }
            for valor, rotulo in Especialidade.Tipo.choices
            if por_tipo[valor].total
        ],
        'por_prioridade': _contagens(
            por_prioridade,
            RegistroFila.Prioridade.choices,
        ),
        'por_situacao': _contagens(por_situacao, RegistroFila.Situacao.choices),
        'especialidades': sorted(
            (
                {
                    'nome': nome,
                    'tipo': Especialidade.Tipo(tipo).label,
                    'total': acumulado.total,
                    'espera_media_dias': acumulado.media,
                    'maior_espera_dias': acumulado.maior,
                }
                for (nome, tipo), acumulado in por_especialidade.items()
            ),
            key=lambda item: (-item['total'], item['nome']),
        ),
    }


def obter_indicadores():
    return cache.get_or_set(
        INDICADORES_CACHE_KEY,
        _calcular_indicadores,
        INDICADORES_CACHE_SEGUNDOS,
    )


def consultar_posicao(*, codigo_solicitacao, ano_nascimento):
    """Devolve a posicao sem dados pessoais; exige codigo e ano de nascimento."""
    hoje = timezone.localdate()
    registros = (
        get_registros_vigentes()
        .filter(
            codigo_solicitacao=codigo_solicitacao,
            ano_nascimento=ano_nascimento,
        )
        .select_related('publicacao__especialidade')
    )

    filas = []
    for registro in registros:
        publicacao = registro.publicacao
        filas.append({
            'especialidade': publicacao.especialidade.nome,
            'tipo': publicacao.especialidade.get_tipo_display(),
            'posicao': registro.posicao,
            'total_aguardando': (
                get_registros_vigentes()
                .filter(publicacao_id=publicacao.pk)
                .count()
            ),
            'situacao': registro.get_situacao_display(),
            'prioridade': registro.get_prioridade_display(),
            'data_solicitacao': registro.data_solicitacao,
            'dias_espera': max((hoje - registro.data_solicitacao).days, 0),
            'atualizado_em': publicacao.publicada_em,
        })
    return filas
