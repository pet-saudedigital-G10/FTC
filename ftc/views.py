from drf_spectacular.utils import OpenApiResponse, extend_schema
from rest_framework import status
from rest_framework.generics import CreateAPIView
from rest_framework.permissions import AllowAny, IsAdminUser
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework_simplejwt.views import TokenObtainPairView, TokenRefreshView

from .permissions import IsSuperUser
from .serializers import (
    AdminLogoutSerializer,
    AdminTokenObtainPairSerializer,
    AdminTokenRefreshResponseSerializer,
    AdminTokenRefreshSerializer,
    AdminTokenResponseSerializer,
    AdminUserCreateSerializer,
    AdminUserSerializer,
)

from .models import Paciente
from .serializers import PacienteSerializer


class PacienteListView(APIView):
    permission_classes = [AllowAny]

    @extend_schema(
        tags=['Pacientes'],
        summary='Listar pacientes',
        description='Retorna pacientes com dados sensíveis mascarados.',
        responses={200: PacienteSerializer(many=True)}
    )

    def get(self, request):
        pacientes = Paciente.objects.all()

        serializer = PacienteSerializer(
            pacientes,
            many=True
        )

        return Response(serializer.data)
    
class AdminUserCreateView(CreateAPIView):
    permission_classes = [IsSuperUser]
    serializer_class = AdminUserCreateSerializer

    @extend_schema(
        tags=['Admin Users'],
        summary='Cadastrar usuario administrativo',
        description=(
            'Cria um usuario staff. Apenas superusuarios podem acessar este endpoint; '
            'o email e opcional.'
        ),
        responses={status.HTTP_201_CREATED: AdminUserSerializer},
    )
    def post(self, request, *args, **kwargs):
        return super().post(request, *args, **kwargs)

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = serializer.save()
        return Response(
            AdminUserSerializer(user).data,
            status=status.HTTP_201_CREATED,
        )


class AdminTokenObtainPairView(TokenObtainPairView):
    permission_classes = [AllowAny]
    serializer_class = AdminTokenObtainPairSerializer
    throttle_scope = 'admin_login'

    @extend_schema(
        tags=['Admin Auth'],
        summary='Login administrativo',
        description='Autentica usuarios staff da secretaria e retorna tokens JWT.',
        responses={status.HTTP_200_OK: AdminTokenResponseSerializer},
    )
    def post(self, request, *args, **kwargs):
        return super().post(request, *args, **kwargs)


class AdminTokenRefreshView(TokenRefreshView):
    permission_classes = [AllowAny]
    serializer_class = AdminTokenRefreshSerializer
    throttle_scope = 'token_refresh'

    @extend_schema(
        tags=['Admin Auth'],
        summary='Renovar token administrativo',
        description='Renova o access token somente se o usuario continuar ativo e staff.',
        responses={status.HTTP_200_OK: AdminTokenRefreshResponseSerializer},
    )
    def post(self, request, *args, **kwargs):
        return super().post(request, *args, **kwargs)


class AdminLogoutView(APIView):
    permission_classes = [IsAdminUser]

    @extend_schema(
        tags=['Admin Auth'],
        summary='Logout administrativo',
        description='Invalida o refresh token informado usando a blacklist do SimpleJWT.',
        request=AdminLogoutSerializer,
        responses={
            status.HTTP_204_NO_CONTENT: OpenApiResponse(
                description='Logout realizado com sucesso.'
            )
        },
    )
    def post(self, request):
        serializer = AdminLogoutSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(status=status.HTTP_204_NO_CONTENT)


class AdminMeView(APIView):
    permission_classes = [IsAdminUser]

    @extend_schema(
        tags=['Admin Auth'],
        summary='Usuario administrativo autenticado',
        responses={status.HTTP_200_OK: AdminUserSerializer},
    )
    def get(self, request):
        return Response(AdminUserSerializer(request.user).data)
