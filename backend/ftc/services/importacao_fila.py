import hashlib
import logging
import re
import unicodedata
from dataclasses import dataclass
from datetime import datetime

import pdfplumber
from django.conf import settings
from django.db import transaction
from django.db.models import Max
from django.utils import timezone

from ftc.models import Especialidade, PublicacaoFila, RegistroFila


logger = logging.getLogger(__name__)


class ErroImportacaoPDF(ValueError):
    """Erro seguro para ser devolvido ao cliente da API."""


@dataclass(frozen=True)
class ResultadoAtualizacaoFila:
    publicacao: PublicacaoFila
    registros_importados: int
    publicacoes_substituidas: tuple[int, ...]


def _normalizar_texto(valor):
    texto = unicodedata.normalize('NFKD', str(valor or ''))
    texto = ''.join(char for char in texto if not unicodedata.combining(char))
    texto = texto.upper().replace('\ufffd', '')
    return ' '.join(texto.split())


def _somente_digitos(valor):
    return ''.join(char for char in str(valor or '') if char.isdigit())


def _mascarar_nome(valor):
    partes = re.findall(r"[A-Za-zÀ-ÖØ-öø-ÿ*]+", str(valor or '').strip())
    if not partes:
        raise ErroImportacaoPDF('O PDF possui um registro sem nome de usuario.')

    mascaradas = []
    for parte in partes:
        if '*' in parte:
            mascaradas.append(parte.upper())
        elif len(parte) == 1:
            mascaradas.append(f'{parte.upper()}.')
        else:
            mascaradas.append(f'{parte[0].upper()}{"*" * (len(parte) - 1)}')
    return ' '.join(mascaradas)


def _mascarar_cns(valor):
    digitos = _somente_digitos(valor)
    if len(digitos) < 4:
        raise ErroImportacaoPDF('O PDF possui um registro com CNS invalido.')
    return f'***********{digitos[-4:]}'


def _converter_sexo(valor):
    sexo = _normalizar_texto(valor)
    if sexo in {'M', 'MASCULINO'}:
        return 'M'
    if sexo in {'F', 'FEMININO'}:
        return 'F'
    if sexo in {'N', 'NAO INFORMADO', 'NAO INFORMADA'}:
        return 'N'
    raise ErroImportacaoPDF('O PDF possui um registro com sexo invalido.')


def _converter_data(valor):
    try:
        return datetime.strptime(str(valor or '').strip(), '%d/%m/%Y').date()
    except ValueError as exc:
        raise ErroImportacaoPDF(
            'O PDF possui uma data de solicitacao invalida; use DD/MM/AAAA.'
        ) from exc


def _linha_cabecalho(celulas):
    texto = ' | '.join(_normalizar_texto(celula) for celula in celulas)
    campos = (
        'DATA DA SOLICITACAO',
        'NOME DO USUARIO',
        'ANO DE NASCIMENTO',
        'CNS DO USUARIO',
        'SEXO DO USUARIO',
        'COD. SOLICITACAO',
        'POSICAO NA FILA',
    )
    return all(campo in texto for campo in campos)


def _titulo_compativel(titulos, especialidade):
    nome = _normalizar_texto(especialidade.nome)
    tipo = _normalizar_texto(especialidade.tipo)
    return any(nome in titulo and tipo in titulo for titulo in titulos)


def _converter_linha(celulas, numero_pagina, numero_linha):
    local = f'pagina {numero_pagina}, linha {numero_linha}'
    if len(celulas) < 7:
        raise ErroImportacaoPDF(
            f'Tabela invalida na {local}: eram esperadas 7 colunas.'
        )

    try:
        ano_nascimento = int(_somente_digitos(celulas[2]))
        codigo = _somente_digitos(celulas[5])
        posicao = int(_somente_digitos(celulas[6]))
    except ValueError as exc:
        raise ErroImportacaoPDF(f'Registro invalido na {local}.') from exc

    ano_atual = timezone.localdate().year
    if not 1900 <= ano_nascimento <= ano_atual:
        raise ErroImportacaoPDF(f'Ano de nascimento invalido na {local}.')
    if not codigo:
        raise ErroImportacaoPDF(f'Codigo de solicitacao ausente na {local}.')
    if posicao < 1:
        raise ErroImportacaoPDF(f'Posicao invalida na {local}.')

    try:
        return {
            'data_solicitacao': _converter_data(celulas[0]),
            'nome_mascarado': _mascarar_nome(celulas[1]),
            'ano_nascimento': ano_nascimento,
            'cns_mascarado': _mascarar_cns(celulas[3]),
            'sexo': _converter_sexo(celulas[4]),
            'codigo_solicitacao': codigo,
            'posicao': posicao,
        }
    except ErroImportacaoPDF as exc:
        raise ErroImportacaoPDF(f'{exc} Local: {local}.') from exc


def extrair_registros_pdf(arquivo, especialidade):
    """Extrai e valida por inteiro o relatorio tabular antes da publicacao."""
    registros = []
    titulos = []
    cabecalho_encontrado = False
    max_paginas = settings.FILA_PDF_MAX_PAGES
    max_registros = settings.FILA_PDF_MAX_RECORDS

    try:
        arquivo.seek(0)
        with pdfplumber.open(arquivo) as documento:
            if len(documento.pages) > max_paginas:
                raise ErroImportacaoPDF(
                    f'O PDF excede o limite de {max_paginas} paginas.'
                )

            for numero_pagina, pagina in enumerate(documento.pages, start=1):
                tabelas = pagina.extract_tables()
                for tabela in tabelas:
                    for numero_linha, linha in enumerate(tabela, start=1):
                        celulas = [str(celula or '').strip() for celula in linha]
                        if not any(celulas):
                            continue
                        if _linha_cabecalho(celulas):
                            cabecalho_encontrado = True
                            continue

                        primeiro_campo = celulas[0]
                        if not re.fullmatch(r'\d{2}/\d{2}/\d{4}', primeiro_campo):
                            titulo = _normalizar_texto(' '.join(celulas))
                            campos_preenchidos = sum(bool(celula) for celula in celulas)
                            if campos_preenchidos == 1 and any(
                                tipo in titulo for tipo in ('CONSULTA', 'EXAME')
                            ):
                                titulos.append(titulo)
                                continue
                            raise ErroImportacaoPDF(
                                'Foi encontrada uma linha inesperada na tabela da '
                                f'pagina {numero_pagina}, linha {numero_linha}.'
                            )

                        registros.append(
                            _converter_linha(celulas, numero_pagina, numero_linha)
                        )
                        if len(registros) > max_registros:
                            raise ErroImportacaoPDF(
                                f'O PDF excede o limite de {max_registros} registros.'
                            )
    except ErroImportacaoPDF:
        raise
    except Exception as exc:
        raise ErroImportacaoPDF(
            'Nao foi possivel ler o PDF. Confirme que o arquivo nao esta '
            'corrompido, protegido ou digitalizado como imagem.'
        ) from exc
    finally:
        arquivo.seek(0)

    if not cabecalho_encontrado:
        raise ErroImportacaoPDF(
            'O PDF nao contem o cabecalho esperado da lista de regulacao.'
        )
    if not registros:
        raise ErroImportacaoPDF('O PDF nao contem registros de fila validos.')
    if not _titulo_compativel(titulos, especialidade):
        raise ErroImportacaoPDF(
            'A especialidade selecionada nao corresponde ao titulo do PDF.'
        )

    codigos = set()
    posicoes = set()
    for registro in registros:
        codigo = registro['codigo_solicitacao']
        posicao = registro['posicao']
        if codigo in codigos:
            raise ErroImportacaoPDF(
                f'O codigo de solicitacao {codigo} aparece mais de uma vez no PDF.'
            )
        if posicao in posicoes:
            raise ErroImportacaoPDF(
                f'A posicao {posicao} aparece mais de uma vez no PDF.'
            )
        codigos.add(codigo)
        posicoes.add(posicao)

    return registros


def calcular_hash_arquivo(arquivo):
    digest = hashlib.sha256()
    arquivo.seek(0)
    for bloco in arquivo.chunks():
        digest.update(bloco)
    arquivo.seek(0)
    return digest.hexdigest()


def atualizar_fila_por_pdf(
    *,
    arquivo,
    especialidade,
    competencia,
    importado_por,
    observacao='',
    prioridade=RegistroFila.Prioridade.NIVEL_3,
    tipo=RegistroFila.Tipo.PENDENTES,
    situacao=RegistroFila.Situacao.AGUARDANDO_REGULACAO,
):
    registros = extrair_registros_pdf(arquivo, especialidade)
    hash_arquivo = calcular_hash_arquivo(arquivo)
    nome_armazenado = None
    publicacao = None

    try:
        with transaction.atomic():
            try:
                especialidade = Especialidade.objects.select_for_update().get(
                    pk=especialidade.pk,
                    ativo=True,
                )
            except Especialidade.DoesNotExist as exc:
                raise ErroImportacaoPDF(
                    'A especialidade selecionada nao esta mais ativa.'
                ) from exc

            if PublicacaoFila.objects.filter(hash_arquivo=hash_arquivo).exists():
                raise ErroImportacaoPDF('Este mesmo arquivo ja foi importado.')

            maior_versao = (
                PublicacaoFila.objects
                .filter(especialidade=especialidade, competencia=competencia)
                .aggregate(maior=Max('versao'))['maior']
                or 0
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

            publicacao = PublicacaoFila(
                especialidade=especialidade,
                competencia=competencia,
                versao=maior_versao + 1,
                arquivo_original=arquivo,
                hash_arquivo=hash_arquivo,
                status=PublicacaoFila.Status.RASCUNHO,
                importado_por=importado_por,
                observacao=observacao,
            )
            publicacao.save(force_insert=True)
            nome_armazenado = publicacao.arquivo_original.name

            RegistroFila.objects.bulk_create([
                RegistroFila(
                    publicacao=publicacao,
                    prioridade=prioridade,
                    tipo=tipo,
                    situacao=situacao,
                    **registro,
                )
                for registro in registros
            ])

            PublicacaoFila.objects.filter(id__in=anteriores).update(
                status=PublicacaoFila.Status.ARQUIVADA,
            )
            publicacao.status = PublicacaoFila.Status.PUBLICADA
            publicacao.publicada_em = timezone.now()
            publicacao.save(update_fields=['status', 'publicada_em'])
    except Exception:
        if (
            not nome_armazenado
            and publicacao is not None
            and publicacao.arquivo_original._committed
        ):
            nome_armazenado = publicacao.arquivo_original.name
        if nome_armazenado:
            try:
                publicacao.arquivo_original.storage.delete(nome_armazenado)
            except Exception:
                logger.exception(
                    'Falha ao remover arquivo de uma importacao revertida: %s',
                    nome_armazenado,
                )
        raise

    logger.info(
        'Fila atualizada: publicacao=%s especialidade=%s registros=%s '
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
