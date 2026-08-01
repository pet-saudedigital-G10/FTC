import json

from django.conf import settings
from django.contrib.auth import authenticate, login
from django.http import JsonResponse
from django.middleware.csrf import get_token
from django.views.csrf import csrf_failure as django_csrf_failure
from django.views.decorators.csrf import ensure_csrf_cookie
from django.views.decorators.http import require_GET, require_POST
from drf_spectacular.utils import OpenApiResponse, extend_schema
from rest_framework import status
from rest_framework.generics import CreateAPIView
from rest_framework.permissions import AllowAny, IsAdminUser
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework_simplejwt.views import TokenObtainPairView, TokenRefreshView

from ftc.permissions import IsSuperUser
from ftc.serializers import (
    AdminLogoutSerializer,
    AdminTokenObtainPairSerializer,
    AdminTokenRefreshResponseSerializer,
    AdminTokenRefreshSerializer,
    AdminTokenResponseSerializer,
    AdminUserCreateSerializer,
    AdminUserSerializer,
    PacienteSerializer,
)
from ftc.models import Paciente


def csrf_failure(request, reason=''):
    """Return JSON CSRF errors for the API and preserve the Django Admin UI."""
    if not request.path.startswith('/api/'):
        return django_csrf_failure(request, reason=reason)

    payload = {'detail': 'Falha na verificacao CSRF.'}
    if settings.DEBUG:
        payload['reason'] = reason
    return JsonResponse(payload, status=status.HTTP_403_FORBIDDEN)


@require_GET
@ensure_csrf_cookie
def csrf_token_view(request):
    """Issue a CSRF cookie and expose its masked token to the frontend."""
    return JsonResponse({'csrfToken': get_token(request)})


@require_POST
def admin_session_login_view(request):
    """Authenticate a staff user into a Django session, with CSRF protection on."""
    try:
        payload = json.loads(request.body.decode('utf-8'))
    except (UnicodeDecodeError, json.JSONDecodeError):
        return JsonResponse({'detail': 'JSON invalido.'}, status=status.HTTP_400_BAD_REQUEST)

    if not isinstance(payload, dict):
        return JsonResponse({'detail': 'JSON invalido.'}, status=status.HTTP_400_BAD_REQUEST)

    username = payload.get('username')
    password = payload.get('password')
    if not username or not password:
        return JsonResponse(
            {'detail': 'Usuario e senha sao obrigatorios.'},
            status=status.HTTP_400_BAD_REQUEST,
        )

    user = authenticate(request, username=username, password=password)
    if user is None or not user.is_staff:
        return JsonResponse(
            {'detail': 'Credenciais invalidas ou usuario sem permissao administrativa.'},
            status=status.HTTP_401_UNAUTHORIZED,
        )

    login(request, user)
    # login() rotates the CSRF secret; return a token for the newly issued cookie.
    return JsonResponse(
        {
            'detail': 'Login realizado com sucesso.',
            'csrfToken': get_token(request),
            'user': AdminUserSerializer(user).data,
        }
    )


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
