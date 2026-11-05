from drf_spectacular.utils import extend_schema
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.throttling import ScopedRateThrottle
from rest_framework.views import APIView

from ftc.serializers import (
    TransparenciaIndicadoresSerializer,
    TransparenciaPosicaoRespostaSerializer,
    TransparenciaPosicaoSerializer,
)
from ftc.services import consultar_posicao, obter_indicadores


class TransparenciaAPIView(APIView):
    # Rotas publicas: um token vencido no navegador nao deve recusar a consulta.
    authentication_classes = []
    permission_classes = [AllowAny]


class TransparenciaIndicadoresView(TransparenciaAPIView):
    # A resposta fica em cache e nao tem dados pessoais. O limite anonimo geral
    # derrubaria o painel, pois atras de proxy os visitantes dividem o mesmo IP.
    throttle_classes = []

    @extend_schema(
        tags=['Transparencia'],
        summary='Indicadores agregados das filas, sem dados pessoais',
        responses=TransparenciaIndicadoresSerializer,
    )
    def get(self, request):
        return Response(
            TransparenciaIndicadoresSerializer(obter_indicadores()).data
        )


class TransparenciaPosicaoView(TransparenciaAPIView):
    throttle_classes = [ScopedRateThrottle]
    throttle_scope = 'transparencia_posicao'

    @extend_schema(
        tags=['Transparencia'],
        summary='Consultar a posicao por codigo da solicitacao e ano de nascimento',
        description='A resposta nao contem nome, CPF ou CNS.',
        request=TransparenciaPosicaoSerializer,
        responses=TransparenciaPosicaoRespostaSerializer,
    )
    def post(self, request):
        serializer = TransparenciaPosicaoSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        filas = consultar_posicao(**serializer.validated_data)
        return Response(
            TransparenciaPosicaoRespostaSerializer({
                'encontrado': bool(filas),
                'filas': filas,
            }).data
        )
