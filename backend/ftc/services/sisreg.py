"""Integracao opcional com a API SISREG (Manual de Integracao v3.0, DATASUS)."""
import hashlib
import json
import logging
from collections import Counter
from datetime import date

import requests
from django.conf import settings
from django.core.cache import cache
from django.db import transaction
from django.db.models import Max
from django.utils import timezone

from ftc.models import Especialidade, Paciente, PublicacaoFila, RegistroFila
from ftc.services.importacao_fila import (
    ResultadoAtualizacaoFila,
    publicar_registros,
)
from ftc.utils.masking import mask_cns, mask_name


logger = logging.getLogger(__name__)

TOKEN_CACHE_KEY = 'sisreg:access_token'
TOKEN_MARGEM_SEGUNDOS = 30
SCROLL_VALIDADE = '5m'
TAMANHO_PAGINA = 50
# Limite de from + size do OpenSearch (manual, secao 7.4).
LIMITE_PAGINACAO = 10000
RISCO_NAO_INFORMADO = 9

# Status da "Fila de solicitacoes" (manual, secao 9.2).
SITUACOES_FILA = {
    'SOLICITAÇÃO / PENDENTE / FILA DE ESPERA': RegistroFila.Situacao.PENDENTE,
    'SOLICITAÇÃO / PENDENTE / REGULADOR': (
        RegistroFila.Situacao.AGUARDANDO_REGULACAO
    ),
    'SOLICITAÇÃO / REENVIADA / REGULADOR': RegistroFila.Situacao.REENVIADO,
}

# O SISREG tem quatro niveis e a FTC tres: os rotulos "Prioridade 1 a 3"
# coincidem e a "Prioridade 0" (emergencia) ocupa o nivel mais alto disponivel.
PRIORIDADES = {
    1: RegistroFila.Prioridade.NIVEL_1,
    2: RegistroFila.Prioridade.NIVEL_1,
    3: RegistroFila.Prioridade.NIVEL_2,
    4: RegistroFila.Prioridade.NIVEL_3,
}
CLASSIFICACOES_RISCO = {
    1: 'Prioridade 0 - Emergência',
    2: 'Prioridade 1 - Urgência',
    3: 'Prioridade 2 - Não urgente',
    4: 'Prioridade 3 - Eletivo',
}

# Somente o necessario: o indice tambem traz endereco, telefone e nome da mae.
CAMPOS_FILA = (
    'codigo_solicitacao',
    'data_solicitacao',
    'status_solicitacao',
    'codigo_classificacao_risco',
    'codigo_grupo_procedimento',
    'nome_grupo_procedimento',
    'no_usuario',
    'cns_usuario',
    'dt_nascimento_usuario',
    'sexo_usuario',
)
CAMPOS_GRUPOS = ('codigo_grupo_procedimento', 'nome_grupo_procedimento')
# O CPF so e lido para vincular pacientes ja cadastrados e nunca e gravado.
CAMPOS_IMPORTACAO = (*CAMPOS_FILA, 'cpf_usuario')

MENSAGENS_STATUS = {
    401: 'O SISREG recusou as credenciais configuradas.',
    403: 'A credencial não tem permissão para consultar este índice do SISREG.',
    404: 'O índice configurado não foi encontrado no SISREG.',
    429: 'O SISREG limitou as requisições; tente novamente mais tarde.',
}


class ErroSisreg(Exception):
    """Falha de comunicacao, com mensagem segura para o cliente da API."""


class ErroImportacaoSisreg(ErroSisreg):
    """Dados ou parametros que impedem a operacao solicitada."""


def _urls():
    return settings.SISREG_AMBIENTES[settings.SISREG_AMBIENTE]


def _enviar(metodo, url, **kwargs):
    try:
        # Sem redirecionamentos: o token e o client_secret nao podem seguir
        # para um host diferente do configurado.
        return requests.request(
            metodo,
            url,
            timeout=settings.SISREG_TIMEOUT_SECONDS,
            allow_redirects=False,
            **kwargs,
        )
    except requests.RequestException as exc:
        logger.warning('Falha de conexao com o SISREG: %s', type(exc).__name__)
        raise ErroSisreg('Não foi possível conectar ao SISREG.') from exc


def _obter_token(*, renovar=False):
    if not renovar:
        token = cache.get(TOKEN_CACHE_KEY)
        if token:
            return token

    resposta = _enviar(
        'POST',
        f'{_urls()["sso"]}/realms/portal-servicos/protocol/openid-connect/token',
        data={
            'grant_type': 'client_credentials',
            'client_id': settings.SISREG_CLIENT_ID,
            'client_secret': settings.SISREG_CLIENT_SECRET,
        },
    )
    if resposta.status_code != 200:
        logger.warning('Token do SISREG recusado: status=%s', resposta.status_code)
        raise ErroSisreg('O SISREG recusou as credenciais configuradas.')

    try:
        corpo = resposta.json()
        token = corpo['access_token']
        validade = int(corpo.get('expires_in', 60))
    except (KeyError, TypeError, ValueError) as exc:
        raise ErroSisreg('O SISREG devolveu um token inválido.') from exc

    cache.set(
        TOKEN_CACHE_KEY,
        token,
        max(validade - TOKEN_MARGEM_SEGUNDOS, 1),
    )
    return token


def _extrair_dados(resposta):
    if resposta.status_code != 200:
        logger.warning('Erro na API SISREG: status=%s', resposta.status_code)
        raise ErroSisreg(
            MENSAGENS_STATUS.get(
                resposta.status_code,
                'O SISREG não concluiu a consulta.',
            )
        )

    try:
        envelope = resposta.json()
    except ValueError as exc:
        raise ErroSisreg('O SISREG devolveu uma resposta inválida.') from exc

    # O gateway encapsula a resposta do OpenSearch no campo data.
    dados = envelope.get('data', envelope) if isinstance(envelope, dict) else None
    if not isinstance(dados, dict):
        raise ErroSisreg('O SISREG devolveu uma resposta inválida.')

    # Uma fila parcial publicaria posicoes erradas: exige a resposta completa.
    if dados.get('timed_out') or (dados.get('_shards') or {}).get('failed'):
        raise ErroSisreg('O SISREG devolveu uma resposta incompleta.')
    return dados


def _requisitar(metodo, caminho, *, params=None, corpo=None):
    url = f'{_urls()["api"]}/SISREG/{caminho}'
    for renovar in (False, True):
        token = _obter_token(renovar=renovar)
        resposta = _enviar(
            metodo,
            url,
            params=params,
            json=corpo,
            headers={'SSOAuthorization': f'Bearer {token}'},
        )
        if resposta.status_code != 401:
            break
    return _extrair_dados(resposta)


def _consulta_fila(codigo_grupo=''):
    filtros = [
        {'terms': {'status_solicitacao.keyword': list(SITUACOES_FILA)}},
        {'terms': {'codigo_tipo_regulacao': ['R', 'F']}},
    ]
    if settings.SISREG_CENTRAIS_REGULADORAS:
        filtros.append({
            'terms': {
                'codigo_central_reguladora': settings.SISREG_CENTRAIS_REGULADORAS,
            },
        })
    if codigo_grupo:
        filtros.append({'terms': {'codigo_grupo_procedimento': [codigo_grupo]}})
    return {'bool': {'must': filtros}}


def _fontes(dados):
    hits = (dados.get('hits') or {}).get('hits') or []
    return [hit.get('_source') or {} for hit in hits]


def _percorrer_fila(campos, codigo_grupo=''):
    """Recupera a fila inteira em lotes, conforme a secao 7.5 do manual."""
    dados = _requisitar(
        'GET',
        f'{settings.SISREG_INDICE}/_search',
        params={'scroll': SCROLL_VALIDADE},
        corpo={
            'size': settings.SISREG_PAGE_SIZE,
            '_source': list(campos),
            'query': _consulta_fila(codigo_grupo),
        },
    )

    fontes = []
    while True:
        lote = _fontes(dados)
        if not lote:
            return fontes

        fontes.extend(lote)
        if len(fontes) > settings.SISREG_MAX_RECORDS:
            raise ErroImportacaoSisreg(
                'A fila excede o limite de '
                f'{settings.SISREG_MAX_RECORDS} registros.'
            )

        scroll_id = dados.get('_scroll_id')
        if not scroll_id:
            raise ErroSisreg('O SISREG devolveu uma resposta incompleta.')
        dados = _requisitar(
            'POST',
            '_search/scroll',
            corpo={'scroll': SCROLL_VALIDADE, 'scroll_id': scroll_id},
        )


def _converter_risco(fonte):
    try:
        return int(fonte.get('codigo_classificacao_risco'))
    except (TypeError, ValueError):
        return RISCO_NAO_INFORMADO


def _converter_data(valor):
    # Usa a data como informada: o sufixo Z nao garante que o horario esteja em
    # UTC, e converter o fuso poderia recuar um dia nas datas a meia-noite.
    try:
        return date.fromisoformat(str(valor or '')[:10])
    except ValueError as exc:
        raise ErroImportacaoSisreg(
            'O SISREG devolveu uma solicitação com data inválida.'
        ) from exc


def _converter_ano_nascimento(valor):
    ano = str(valor or '')[:4]
    return int(ano) if ano.isdigit() else None


def _converter_sexo(valor):
    sexo = str(valor or '').strip().upper()
    if sexo == 'MASCULINO':
        return 'M'
    if sexo == 'FEMININO':
        return 'F'
    return 'N'


def _converter_registro(fonte):
    codigo = str(fonte.get('codigo_solicitacao') or '').strip()
    if not codigo:
        raise ErroImportacaoSisreg(
            'O SISREG devolveu uma solicitação sem código.'
        )

    situacao = SITUACOES_FILA.get(fonte.get('status_solicitacao'))
    if situacao is None:
        raise ErroImportacaoSisreg(
            f'A solicitação {codigo} possui um status fora da fila.'
        )

    return {
        'codigo_solicitacao': codigo,
        'data_solicitacao': _converter_data(fonte.get('data_solicitacao')),
        'nome_mascarado': mask_name(fonte.get('no_usuario')),
        'ano_nascimento': _converter_ano_nascimento(
            fonte.get('dt_nascimento_usuario')
        ),
        'cns_mascarado': mask_cns(fonte.get('cns_usuario')),
        'sexo': _converter_sexo(fonte.get('sexo_usuario')),
        'prioridade': PRIORIDADES.get(
            _converter_risco(fonte),
            RegistroFila.Prioridade.NIVEL_3,
        ),
        'tipo': RegistroFila.Tipo.PENDENTES,
        'situacao': situacao,
    }


def _chave_ordenacao(fonte):
    return (
        _converter_risco(fonte),
        str(fonte.get('data_solicitacao') or ''),
        str(fonte.get('codigo_solicitacao') or '').zfill(20),
    )


def _ids_pacientes(fontes):
    """Relaciona cada solicitacao a um paciente ja cadastrado, por CNS ou CPF."""
    por_cns = {}
    por_cpf = {}
    for paciente_id, cns, cpf in Paciente.objects.values_list('id', 'cns', 'cpf'):
        if cns:
            por_cns[cns] = paciente_id
        if cpf:
            por_cpf[cpf] = paciente_id

    return [
        por_cns.get(fonte.get('cns_usuario'))
        or por_cpf.get(fonte.get('cpf_usuario'))
        for fonte in fontes
    ]


def _montar_registros(fontes):
    """Valida a fila inteira e calcula as posicoes antes de qualquer gravacao."""
    # A API nao informa a posicao: ela e derivada do risco e da antiguidade.
    unicas = {}
    for fonte in sorted(fontes, key=_chave_ordenacao):
        unicas.setdefault(str(fonte.get('codigo_solicitacao') or '').strip(), fonte)
    if len(unicas) != len(fontes):
        logger.warning(
            'SISREG devolveu %s solicitacoes repetidas.',
            len(fontes) - len(unicas),
        )

    ordenadas = list(unicas.values())
    return [
        {**_converter_registro(fonte), 'posicao': posicao, 'paciente_id': paciente_id}
        for posicao, (fonte, paciente_id) in enumerate(
            zip(ordenadas, _ids_pacientes(ordenadas)),
            start=1,
        )
    ]


def _calcular_hash(registros, especialidade, competencia, versao):
    # A versao entra no hash porque hash_arquivo e unico e uma fila pode voltar
    # a um estado ja publicado; sem ela, essa publicacao seria rejeitada.
    conteudo = json.dumps(
        {
            'especialidade': especialidade.pk,
            'competencia': competencia,
            'versao': versao,
            'registros': registros,
        },
        default=str,
        sort_keys=True,
    )
    return hashlib.sha256(conteudo.encode('utf-8')).hexdigest()


def listar_grupos_sisreg():
    """Resume a fila por grupo de procedimento, o agrupamento usado na importacao."""
    fontes = _percorrer_fila(CAMPOS_GRUPOS)
    totais = Counter(fonte.get('codigo_grupo_procedimento') for fonte in fontes)
    nomes = {
        fonte.get('codigo_grupo_procedimento'): fonte.get('nome_grupo_procedimento')
        for fonte in fontes
    }
    grupos = [
        {'codigo': codigo, 'nome': nomes[codigo] or codigo, 'total': total}
        for codigo, total in totais.items()
        if codigo
    ]
    return {
        'total': len(fontes),
        'grupos': sorted(grupos, key=lambda grupo: grupo['nome']),
    }


def consultar_fila_sisreg(*, codigo_grupo='', pagina=1):
    """Consulta uma pagina da fila sem gravar nada; os dados saem mascarados."""
    inicio = (pagina - 1) * TAMANHO_PAGINA
    if inicio + TAMANHO_PAGINA > LIMITE_PAGINACAO:
        raise ErroImportacaoSisreg(
            f'A consulta está limitada aos primeiros {LIMITE_PAGINACAO} registros.'
        )

    dados = _requisitar(
        'GET',
        f'{settings.SISREG_INDICE}/_search',
        params={'track_total_hits': 'true'},
        corpo={
            'from': inicio,
            'size': TAMANHO_PAGINA,
            '_source': list(CAMPOS_FILA),
            'query': _consulta_fila(codigo_grupo),
            'sort': [
                {'codigo_classificacao_risco': {'order': 'asc'}},
                {'data_solicitacao': {'order': 'asc'}},
                {'codigo_solicitacao': {'order': 'asc'}},
            ],
        },
    )

    total = (dados.get('hits') or {}).get('total') or 0
    registros = []
    for fonte in _fontes(dados):
        registro = _converter_registro(fonte)
        registros.append({
            'codigo_solicitacao': registro['codigo_solicitacao'],
            'data_solicitacao': registro['data_solicitacao'],
            'nome_mascarado': registro['nome_mascarado'],
            'cns_mascarado': registro['cns_mascarado'],
            'codigo_grupo_procedimento': fonte.get('codigo_grupo_procedimento') or '',
            'nome_grupo_procedimento': fonte.get('nome_grupo_procedimento') or '',
            'classificacao_risco': CLASSIFICACOES_RISCO.get(
                _converter_risco(fonte),
                'Não informada',
            ),
            'situacao': registro['situacao'],
            'situacao_display': RegistroFila.Situacao(registro['situacao']).label,
        })

    return {
        'total': total.get('value', 0) if isinstance(total, dict) else total,
        'pagina': pagina,
        'tamanho_pagina': TAMANHO_PAGINA,
        'registros': registros,
    }


def importar_fila_sisreg(*, especialidade, codigo_grupo, importado_por):
    """Publica a fila de um grupo do SISREG no lugar da publicacao vigente."""
    fontes = _percorrer_fila(CAMPOS_IMPORTACAO, codigo_grupo)
    if not fontes:
        raise ErroImportacaoSisreg(
            'O SISREG não possui solicitações na fila para este grupo.'
        )

    registros = _montar_registros(fontes)
    competencia = timezone.localdate().replace(day=1)

    with transaction.atomic():
        try:
            especialidade = Especialidade.objects.select_for_update().get(
                pk=especialidade.pk,
                ativo=True,
            )
        except Especialidade.DoesNotExist as exc:
            raise ErroImportacaoSisreg(
                'A especialidade selecionada não está mais ativa.'
            ) from exc

        maior_versao = (
            PublicacaoFila.objects
            .filter(especialidade=especialidade, competencia=competencia)
            .aggregate(maior=Max('versao'))['maior']
            or 0
        )
        if PublicacaoFila.objects.filter(
            hash_arquivo=_calcular_hash(
                registros,
                especialidade,
                competencia,
                maior_versao,
            ),
            status=PublicacaoFila.Status.PUBLICADA,
        ).exists():
            raise ErroImportacaoSisreg(
                'A fila publicada já está igual à do SISREG.'
            )

        anteriores = list(
            PublicacaoFila.objects
            .select_for_update()
            .filter(
                especialidade=especialidade,
                status=PublicacaoFila.Status.PUBLICADA,
            )
            .values_list('id', flat=True)
        )
        publicacao = PublicacaoFila.objects.create(
            especialidade=especialidade,
            competencia=competencia,
            versao=maior_versao + 1,
            origem=PublicacaoFila.Origem.SISREG,
            hash_arquivo=_calcular_hash(
                registros,
                especialidade,
                competencia,
                maior_versao + 1,
            ),
            status=PublicacaoFila.Status.RASCUNHO,
            importado_por=importado_por,
            observacao=(
                f'Importado do SISREG: {settings.SISREG_INDICE}, '
                f'grupo {codigo_grupo}.'
            ),
        )
        publicar_registros(publicacao, registros, anteriores)

    logger.info(
        'Fila importada do SISREG: publicacao=%s especialidade=%s registros=%s '
        'substituidas=%s usuario=%s',
        publicacao.pk,
        especialidade.pk,
        len(registros),
        anteriores,
        importado_por.pk,
    )
    return ResultadoAtualizacaoFila(
        publicacao=publicacao,
        registros_importados=len(registros),
        publicacoes_substituidas=tuple(anteriores),
    )
