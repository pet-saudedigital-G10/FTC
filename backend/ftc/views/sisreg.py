from django.conf import settings
from drf_spectacular.utils import OpenApiParameter, extend_schema
from rest_framework import status
from rest_framework.exceptions import APIException, ValidationError
from rest_framework.permissions import IsAdminUser
from rest_framework.response import Response
from rest_framework.views import APIView

from ftc.permissions import IsSisregEnabled
from ftc.serializers import (
    AtualizacaoFilaRespostaSerializer,
    SisregFilaFiltroSerializer,
    SisregFilaRespostaSerializer,
    SisregGruposRespostaSerializer,
    SisregImportacaoSerializer,
    SisregStatusSerializer,
)
from ftc.services import (
    ErroImportacaoSisreg,
    ErroSisreg,
    consultar_fila_sisreg,
    importar_fila_sisreg,
    listar_grupos_sisreg,
)


class SisregIndisponivel(APIException):
    status_code = status.HTTP_502_BAD_GATEWAY
    default_code = 'sisreg_indisponivel'


class SisregAPIView(APIView):
    permission_classes = [IsAdminUser, IsSisregEnabled]
    throttle_scope = 'sisreg'

    def handle_exception(self, exc):
        if isinstance(exc, ErroImportacaoSisreg):
            exc = ValidationError({'detail': [str(exc)]})
        elif isinstance(exc, ErroSisreg):
            exc = SisregIndisponivel(str(exc))
        return super().handle_exception(exc)


class SisregStatusView(APIView):
    permission_classes = [IsAdminUser]

    @extend_schema(
        tags=['Integracao SISREG'],
        summary='Informar se a integracao com o SISREG esta habilitada',
        responses=SisregStatusSerializer,
    )
    def get(self, request):
        habilitado = settings.SISREG_ENABLED
        return Response({
            'habilitado': habilitado,
            'ambiente': settings.SISREG_AMBIENTE if habilitado else None,
            'indice': settings.SISREG_INDICE if habilitado else None,
        })


class SisregGruposView(SisregAPIView):
    @extend_schema(
        tags=['Integracao SISREG'],
        summary='Resumir a fila do SISREG por grupo de procedimento',
        responses=SisregGruposRespostaSerializer,
    )
    def get(self, request):
        return Response(
            SisregGruposRespostaSerializer(listar_grupos_sisreg()).data
        )


class SisregFilaView(SisregAPIView):
    @extend_schema(
        tags=['Integracao SISREG'],
        summary='Consultar a fila de regulacao no SISREG, sem gravar',
        parameters=[
            OpenApiParameter(
                'grupo',
                str,
                description='Codigo do grupo de procedimento no SISREG.',
            ),
            OpenApiParameter('pagina', int, description='Pagina da consulta.'),
        ],
        responses=SisregFilaRespostaSerializer,
    )
    def get(self, request):
        filtro = SisregFilaFiltroSerializer(data=request.query_params)
        filtro.is_valid(raise_exception=True)
        dados = filtro.validated_data

        return Response(
            SisregFilaRespostaSerializer(
                consultar_fila_sisreg(
                    codigo_grupo=dados.get('grupo', ''),
                    pagina=dados['pagina'],
                )
            ).data
        )


class SisregImportacaoView(SisregAPIView):
    @extend_schema(
        tags=['Integracao SISREG'],
        summary='Publicar a fila de um grupo do SISREG em uma especialidade',
        description=(
            'Valida toda a fila antes de publicar. A publicacao anterior da '
            'especialidade e arquivada para auditoria.'
        ),
        request=SisregImportacaoSerializer,
        responses={201: AtualizacaoFilaRespostaSerializer},
    )
    def post(self, request):
        serializer = SisregImportacaoSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        dados = serializer.validated_data

        resultado = importar_fila_sisreg(
            especialidade=dados['especialidade'],
            codigo_grupo=dados['codigo_grupo_procedimento'],
            importado_por=request.user,
        )

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
