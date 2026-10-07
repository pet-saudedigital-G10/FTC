import unicodedata

from django.db.models import Q
from drf_spectacular.utils import OpenApiParameter, extend_schema
from rest_framework import status
from rest_framework.exceptions import ValidationError
from rest_framework.generics import ListAPIView
from rest_framework.parsers import FormParser, MultiPartParser
from rest_framework.permissions import AllowAny, IsAdminUser
from rest_framework.response import Response
from rest_framework.views import APIView

from ftc.models import Especialidade, Paciente, PublicacaoFila, RegistroFila
from ftc.permissions import IsCitizen
from ftc.selectors import get_posicoes_paciente_ativas, somente_digitos
from ftc.serializers import (
    AtualizacaoFilaRespostaSerializer,
    AtualizacaoFilaSerializer,
    EspecialidadeSerializer,
    FilaOpcoesSerializer,
    RegistroFilaSerializer,
    RegistroFilaPublicSerializer,
)
from ftc.services import ErroImportacaoPDF, atualizar_fila_por_pdf


class ConsultaPosicaoFilaAPIView(APIView):
    def post(self, request):
        cpf = request.data.get('cpf')

        if not isinstance(cpf, str) or len(cpf) != 11 or not cpf.isdigit():
            return Response(
                {'erro': 'CPF inválido ou não informado.'},
                status=status.HTTP_400_BAD_REQUEST,
            )

        registros = get_posicoes_paciente_ativas(cpf=cpf)
        serializer = RegistroFilaPublicSerializer(registros, many=True)

        return Response({
            'encontrado': registros.exists(),
            'filas': serializer.data,
        }, status=status.HTTP_200_OK)


def normalizar(valor):
    if valor is None:
        return ''
    texto = str(valor).strip()
    texto = unicodedata.normalize('NFKD', texto)
    texto = ''.join(char for char in texto if not unicodedata.combining(char))
    texto = texto.upper().replace('-', ' ').replace('_', ' ')
    return ' '.join(texto.split())


def resolver_choice(valor, choices, nome_parametro):
    if valor in (None, ''):
        return None

    alvo = normalizar(valor)
    for codigo, label in choices:
        if alvo in {normalizar(codigo), normalizar(label)}:
            return codigo

    opcoes = ', '.join(label for _, label in choices)
    raise ValidationError({
        nome_parametro: f'Valor invalido. Use uma destas opcoes: {opcoes}.'
    })


class RegistroFilaListView(ListAPIView):
    serializer_class = RegistroFilaSerializer
    permission_classes = [AllowAny]

    def get_queryset(self):
        queryset = (
            RegistroFila.objects
            .filter(publicacao__status=PublicacaoFila.Status.PUBLICADA)
            .select_related('publicacao', 'publicacao__especialidade')
            .order_by('publicacao__especialidade__nome', 'posicao')
        )
        params = self.request.query_params

        especialidade = params.get('especialidade')
        if especialidade:
            queryset = self._filtrar_especialidade(queryset, especialidade)

        especialidade_tipo = params.get('especialidade_tipo') or params.get('categoria')
        if especialidade_tipo:
            queryset = queryset.filter(
                publicacao__especialidade__tipo=resolver_choice(
                    especialidade_tipo,
                    Especialidade.Tipo.choices,
                    'especialidade_tipo',
                )
            )

        tipo = params.get('tipo')
        if tipo:
            queryset = queryset.filter(
                tipo=resolver_choice(tipo, RegistroFila.Tipo.choices, 'tipo')
            )

        situacao = params.get('situacao')
        if situacao:
            queryset = queryset.filter(
                situacao=resolver_choice(
                    situacao,
                    RegistroFila.Situacao.choices,
                    'situacao',
                )
            )

        prioridade = params.get('prioridade')
        if prioridade:
            try:
                prioridade = int(prioridade)
            except ValueError as exc:
                raise ValidationError({
                    'prioridade': 'Prioridade deve ser 1, 2 ou 3.'
                }) from exc

            if prioridade not in RegistroFila.Prioridade.values:
                raise ValidationError({
                    'prioridade': 'Prioridade deve ser 1, 2 ou 3.'
                })

            queryset = queryset.filter(prioridade=prioridade)

        codigo_solicitacao = params.get('codigo_solicitacao') or params.get('protocolo')
        if codigo_solicitacao:
            queryset = queryset.filter(
                codigo_solicitacao=somente_digitos(codigo_solicitacao)
            )

        # Busca completa (via Paciente) só funciona quando RegistroFila.paciente
        # estiver vinculado, hoje o importador não liga esse campo, então estes
        # dois filtros não encontram nada em produção ainda. Porém já estão prontos  prontos.
        cpf = params.get('cpf')
        if cpf:
            queryset = queryset.filter(paciente__cpf=somente_digitos(cpf))

        cns = params.get('cns')
        if cns:
            digitos = somente_digitos(cns)
            if len(digitos) >= 15:
                queryset = queryset.filter(paciente__cns=digitos)
            elif digitos:
                # só os últimos dígitos: funciona hoje, é o que está gravado
                queryset = queryset.filter(cns_mascarado__endswith=digitos[-4:])

        ano_nascimento_de = params.get('ano_nascimento_de')
        if ano_nascimento_de:
            queryset = queryset.filter(ano_nascimento__gte=ano_nascimento_de)

        ano_nascimento_ate = params.get('ano_nascimento_ate')
        if ano_nascimento_ate:
            queryset = queryset.filter(ano_nascimento__lte=ano_nascimento_ate)

        return queryset

    def _filtrar_especialidade(self, queryset, especialidade):
        if str(especialidade).isdigit():
            return queryset.filter(publicacao__especialidade_id=int(especialidade))

        return queryset.filter(
            Q(publicacao__especialidade__slug__iexact=especialidade)
            | Q(publicacao__especialidade__nome__iexact=especialidade)
        )

    @extend_schema(
        tags=['Fila Publica'],
        summary='Listar registros publicos da fila',
        parameters=[
            OpenApiParameter(
                'especialidade',
                str,
                description='ID, slug ou nome exato da especialidade.',
            ),
            OpenApiParameter(
                'especialidade_tipo',
                str,
                description='Consulta ou Exame. Alias: categoria.',
            ),
            OpenApiParameter(
                'tipo',
                str,
                description='Solicitadas, Pendentes ou Baixadas.',
            ),
            OpenApiParameter(
                'situacao',
                str,
                description='Situacao da solicitacao, como Solicitado ou Agendado.',
            ),
            OpenApiParameter(
                'prioridade',
                int,
                description='Prioridade 1, 2 ou 3.',
            ),
            OpenApiParameter(
                'codigo_solicitacao',
                str,
                description='Protocolo exato da solicitacao. Alias: protocolo.',
            ),
            OpenApiParameter(
                'cpf',
                str,
                description=(
                    'CPF completo do paciente. So encontra resultados quando o '
                    'registro estiver vinculado a um Paciente cadastrado.'
                ),
            ),
            OpenApiParameter(
                'cns',
                str,
                description=(
                    'CNS completo (15 digitos, requer Paciente vinculado) ou '
                    'apenas os ultimos digitos (busca parcial, funciona hoje).'
                ),
            ),
            OpenApiParameter(
                'ano_nascimento_de',
                int,
                description='Ano de nascimento minimo (inclusive).',
            ),
            OpenApiParameter(
                'ano_nascimento_ate',
                int,
                description='Ano de nascimento maximo (inclusive).',
            ),
        ],
    )
    def get(self, request, *args, **kwargs):
        return super().get(request, *args, **kwargs)


class CidadaoRegistroFilaListView(ListAPIView):
    serializer_class = RegistroFilaSerializer
    permission_classes = [IsCitizen]

    def get_queryset(self):
        paciente = Paciente.objects.get(cpf=self.request.user.get_username())
        return (
            RegistroFila.objects
            .filter(
                paciente=paciente,
                publicacao__status=PublicacaoFila.Status.PUBLICADA,
            )
            .select_related('publicacao', 'publicacao__especialidade')
            .order_by('publicacao__especialidade__nome', 'posicao')
        )

    @extend_schema(
        tags=['Cidadao'],
        summary='Listar registros de fila do cidadao autenticado',
    )
    def get(self, request, *args, **kwargs):
        return super().get(request, *args, **kwargs)


class EspecialidadeListView(ListAPIView):
    serializer_class = EspecialidadeSerializer
    permission_classes = [AllowAny]
    queryset = Especialidade.objects.filter(ativo=True).order_by('tipo', 'nome')

    @extend_schema(
        tags=['Fila Publica'],
        summary='Listar especialidades ativas',
    )
    def get(self, request, *args, **kwargs):
        return super().get(request, *args, **kwargs)


class FilaOpcoesView(APIView):
    permission_classes = [AllowAny]

    @extend_schema(
        tags=['Fila Publica'],
        summary='Listar opcoes de filtros da fila',
        responses=FilaOpcoesSerializer,
    )
    def get(self, request):
        return Response({
            'especialidade_tipos': [
                {'value': value, 'label': label}
                for value, label in Especialidade.Tipo.choices
            ],
            'tipos': [
                {'value': value, 'label': label}
                for value, label in RegistroFila.Tipo.choices
            ],
            'situacoes': [
                {'value': value, 'label': label}
                for value, label in RegistroFila.Situacao.choices
            ],
            'prioridades': [
                {'value': value, 'label': label}
                for value, label in RegistroFila.Prioridade.choices
            ],
        })


class AtualizacaoFilaView(APIView):
    permission_classes = [IsAdminUser]
    parser_classes = [MultiPartParser, FormParser]
    throttle_scope = 'fila_importacao'

    @extend_schema(
        tags=['Administracao da Fila'],
        summary='Substituir os registros publicados de uma fila por um PDF',
        description=(
            'Valida todo o PDF antes de publicar. A publicacao anterior da '
            'especialidade e arquivada para auditoria e deixa de aparecer na '
            'fila publica.'
        ),
        request=AtualizacaoFilaSerializer,
        responses={201: AtualizacaoFilaRespostaSerializer},
    )
    def post(self, request):
        serializer = AtualizacaoFilaSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        dados = serializer.validated_data

        try:
            resultado = atualizar_fila_por_pdf(
                arquivo=dados['arquivo'],
                especialidade=dados['especialidade'],
                competencia=dados['competencia'],
                observacao=dados.get('observacao', ''),
                importado_por=request.user,
            )
        except ErroImportacaoPDF as exc:
            raise ValidationError({'arquivo': [str(exc)]}) from exc

        publicacao = resultado.publicacao
        resposta = AtualizacaoFilaRespostaSerializer({
            'publicacao_id': publicacao.pk,
            'especialidade_id': publicacao.especialidade_id,
            'competencia': publicacao.competencia,
            'versao': publicacao.versao,
            'status': publicacao.status,
            'registros_importados': resultado.registros_importados,
            'publicacoes_substituidas': resultado.publicacoes_substituidas,
            'importado_em': publicacao.importado_em,
            'publicada_em': publicacao.publicada_em,
        })
        return Response(resposta.data, status=status.HTTP_201_CREATED)
