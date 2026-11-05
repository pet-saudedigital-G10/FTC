import logging
from copy import copy

from drf_spectacular.utils import OpenApiParameter, extend_schema
from rest_framework import status
from rest_framework.exceptions import APIException, ValidationError
from rest_framework.permissions import IsAdminUser
from rest_framework.response import Response
from rest_framework.views import APIView

from ftc.models import ConfiguracaoSisreg
from ftc.permissions import IsSisregConfigurator, IsSisregEnabled
from ftc.serializers import (
    AtualizacaoFilaRespostaSerializer,
    SisregConfiguracaoSerializer,
    SisregFilaFiltroSerializer,
    SisregFilaRespostaSerializer,
    SisregGruposRespostaSerializer,
    SisregImportacaoSerializer,
    SisregStatusSerializer,
    SisregTesteConexaoSerializer,
    SisregTesteRespostaSerializer,
)
from ftc.services import (
    ErroImportacaoSisreg,
    ErroSisreg,
    consultar_fila_sisreg,
    importar_fila_sisreg,
    listar_grupos_sisreg,
    testar_conexao_sisreg,
)


logger = logging.getLogger(__name__)


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
        configuracao = ConfiguracaoSisreg.carregar()
        habilitado = configuracao.habilitado
        return Response({
            'habilitado': habilitado,
            'ambiente': configuracao.ambiente if habilitado else None,
            'indice': configuracao.indice if habilitado else None,
            'pode_configurar': request.user.is_superuser,
        })


class SisregConfiguracaoView(APIView):
    permission_classes = [IsSisregConfigurator]

    @extend_schema(
        tags=['Integracao SISREG'],
        summary='Consultar a configuracao da integracao, sem o Client Secret',
        responses=SisregConfiguracaoSerializer,
    )
    def get(self, request):
        return Response(
            SisregConfiguracaoSerializer(ConfiguracaoSisreg.carregar()).data
        )

    @extend_schema(
        tags=['Integracao SISREG'],
        summary='Salvar a configuracao da integracao',
        description='Um Client Secret em branco mantem o valor ja salvo.',
        request=SisregConfiguracaoSerializer,
        responses=SisregConfiguracaoSerializer,
    )
    def put(self, request):
        configuracao = ConfiguracaoSisreg.carregar()
        serializer = SisregConfiguracaoSerializer(
            configuracao,
            data=request.data,
        )
        serializer.is_valid(raise_exception=True)

        serializer.aplicar(configuracao)
        configuracao.atualizado_por = request.user
        configuracao.save()
        logger.info(
            'Configuracao do SISREG atualizada: habilitado=%s ambiente=%s usuario=%s',
            configuracao.habilitado,
            configuracao.ambiente,
            request.user.pk,
        )
        return Response(SisregConfiguracaoSerializer(configuracao).data)


class SisregTesteConexaoView(SisregAPIView):
    permission_classes = [IsSisregConfigurator]

    @extend_schema(
        tags=['Integracao SISREG'],
        summary='Testar os dados informados, sem salvar',
        description='Um Client Secret em branco usa o valor ja salvo.',
        request=SisregTesteConexaoSerializer,
        responses=SisregTesteRespostaSerializer,
    )
    def post(self, request):
        configuracao = ConfiguracaoSisreg.carregar()
        serializer = SisregTesteConexaoSerializer(
            configuracao,
            data=request.data,
        )
        serializer.is_valid(raise_exception=True)

        total = testar_conexao_sisreg(serializer.aplicar(copy(configuracao)))
        return Response(SisregTesteRespostaSerializer({'total': total}).data)


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
