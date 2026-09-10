import unicodedata

from django.db.models import Q
from drf_spectacular.utils import OpenApiParameter, extend_schema
from rest_framework.exceptions import ValidationError
from rest_framework.generics import ListAPIView, RetrieveAPIView
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.views import APIView

from ftc.models import Especialidade, PublicacaoFila, RegistroFila
from ftc.serializers import (
    EspecialidadeSerializer,
    FilaOpcoesSerializer,
    RegistroFilaComprovanteSerializer,
    RegistroFilaSerializer,
)



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
        ],
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


class RegistroFilaComprovanteView(RetrieveAPIView):
    serializer_class = RegistroFilaComprovanteSerializer
    permission_classes = [AllowAny]
    queryset = (
        RegistroFila.objects
        .filter(publicacao__status=PublicacaoFila.Status.PUBLICADA)
        .select_related('publicacao', 'publicacao__especialidade')
    )

    @extend_schema(
        tags=['Fila Publica'],
        summary='Gerar comprovante de posicao da fila',
        description='Retorna em formato JSON as informacoes detalhadas e o comprovante de posicao de um registro da fila.',
        responses={200: RegistroFilaComprovanteSerializer},
    )
    def get(self, request, *args, **kwargs):
        return super().get(request, *args, **kwargs)

