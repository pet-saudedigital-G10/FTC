from django.contrib.auth import get_user_model
from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError as DjangoValidationError
from rest_framework import serializers
from rest_framework.exceptions import AuthenticationFailed
from rest_framework_simplejwt.exceptions import InvalidToken, TokenError
from rest_framework_simplejwt.serializers import (
    TokenObtainPairSerializer,
    TokenRefreshSerializer,
)
from rest_framework_simplejwt.settings import api_settings
from rest_framework_simplejwt.tokens import RefreshToken

from ftc.models import Paciente

ADMIN_AUTH_ERROR = 'Credenciais invalidas ou usuario sem permissao administrativa.'
CIDADAO_AUTH_ERROR = 'CPF ou senha invalidos, ou cadastro sem paciente vinculado.'


class AdminUserSerializer(serializers.ModelSerializer):
    full_name = serializers.SerializerMethodField()
    groups = serializers.SerializerMethodField()

    class Meta:
        model = get_user_model()
        fields = (
            'id',
            'username',
            'email',
            'first_name',
            'last_name',
            'full_name',
            'is_staff',
            'is_superuser',
            'groups',
        )
        read_only_fields = fields

    def get_full_name(self, obj) -> str:
        return obj.get_full_name()

    def get_groups(self, obj) -> list[str]:
        return list(obj.groups.values_list('name', flat=True))


class AdminUserCreateSerializer(serializers.ModelSerializer):
    email = serializers.EmailField(required=False, allow_blank=True, default='')
    first_name = serializers.CharField(required=False, allow_blank=True, default='')
    last_name = serializers.CharField(required=False, allow_blank=True, default='')
    password = serializers.CharField(
        write_only=True,
        trim_whitespace=False,
        style={'input_type': 'password'},
    )

    class Meta:
        model = get_user_model()
        fields = ('username', 'password', 'email', 'first_name', 'last_name')

    def validate(self, attrs):
        User = get_user_model()
        candidate = User(
            username=attrs['username'],
            email=attrs.get('email', ''),
            first_name=attrs.get('first_name', ''),
            last_name=attrs.get('last_name', ''),
        )

        try:
            validate_password(attrs['password'], user=candidate)
        except DjangoValidationError as exc:
            raise serializers.ValidationError(
                {'password': list(exc.messages)}
            ) from exc

        return attrs

    def create(self, validated_data):
        User = get_user_model()
        return User.objects.create_user(
            **validated_data,
            is_active=True,
            is_staff=True,
            is_superuser=False,
        )


class CidadaoUserCreateSerializer(serializers.Serializer):
    cpf = serializers.CharField(min_length=11, max_length=11)
    cns = serializers.CharField(min_length=15, max_length=15, write_only=True)
    password = serializers.CharField(
        write_only=True,
        trim_whitespace=False,
        style={'input_type': 'password'},
    )
    password_confirmation = serializers.CharField(
        write_only=True,
        trim_whitespace=False,
        style={'input_type': 'password'},
    )

    def validate(self, attrs):
        cpf = attrs['cpf']
        cns = attrs['cns']

        if not cpf.isdigit():
            raise serializers.ValidationError({
                'cpf': 'Informe o CPF com exatamente 11 digitos.',
            })
        if not cns.isdigit():
            raise serializers.ValidationError({
                'cns': 'Informe o CNS com exatamente 15 digitos.',
            })
        if attrs['password'] != attrs['password_confirmation']:
            raise serializers.ValidationError({
                'password_confirmation': 'As senhas nao conferem.',
            })

        try:
            paciente = Paciente.objects.get(cpf=cpf, cns=cns)
        except Paciente.DoesNotExist as exc:
            raise serializers.ValidationError(
                'CPF e CNS nao correspondem a um paciente cadastrado.'
            ) from exc

        User = get_user_model()
        if User.objects.filter(username=cpf).exists():
            raise serializers.ValidationError({
                'cpf': 'Ja existe uma conta cadastrada para este CPF.',
            })

        candidate = User(username=cpf)
        try:
            validate_password(attrs['password'], user=candidate)
        except DjangoValidationError as exc:
            raise serializers.ValidationError(
                {'password': list(exc.messages)}
            ) from exc

        attrs['paciente'] = paciente
        return attrs

    def create(self, validated_data):
        validated_data.pop('password_confirmation')
        validated_data.pop('paciente')
        validated_data.pop('cns')
        cpf = validated_data.pop('cpf')
        return get_user_model().objects.create_user(
            username=cpf,
            is_active=True,
            is_staff=False,
            is_superuser=False,
            **validated_data,
        )


class CidadaoUserSerializer(serializers.Serializer):
    id = serializers.IntegerField(read_only=True)
    cpf = serializers.CharField(read_only=True)
    nome_completo = serializers.CharField(read_only=True)


class CidadaoTokenResponseSerializer(serializers.Serializer):
    access = serializers.CharField(read_only=True)
    refresh = serializers.CharField(read_only=True)
    user = CidadaoUserSerializer(read_only=True)


class CidadaoTokenRefreshResponseSerializer(serializers.Serializer):
    access = serializers.CharField(read_only=True)
    refresh = serializers.CharField(read_only=True, required=False)
    user = CidadaoUserSerializer(read_only=True)


class AdminTokenResponseSerializer(serializers.Serializer):
    access = serializers.CharField(read_only=True)
    refresh = serializers.CharField(read_only=True)
    user = AdminUserSerializer(read_only=True)


class AdminTokenRefreshResponseSerializer(serializers.Serializer):
    access = serializers.CharField(read_only=True)
    refresh = serializers.CharField(read_only=True, required=False)
    user = AdminUserSerializer(read_only=True)


class AdminTokenObtainPairSerializer(TokenObtainPairSerializer):
    default_error_messages = {
        'no_active_account': ADMIN_AUTH_ERROR,
    }

    @classmethod
    def get_token(cls, user):
        token = super().get_token(user)
        token['username'] = user.get_username()
        token['is_staff'] = user.is_staff
        return token

    def validate(self, attrs):
        data = super().validate(attrs)

        if not self.user.is_staff:
            raise AuthenticationFailed(ADMIN_AUTH_ERROR, code='admin_access_denied')

        data['user'] = AdminUserSerializer(self.user).data
        return data


class CidadaoTokenObtainPairSerializer(TokenObtainPairSerializer):
    default_error_messages = {
        'no_active_account': CIDADAO_AUTH_ERROR,
    }

    def validate(self, attrs):
        data = super().validate(attrs)
        paciente = self._get_paciente(self.user)
        data['user'] = CidadaoUserSerializer({
            'id': self.user.pk,
            'cpf': paciente.cpf,
            'nome_completo': paciente.nome_completo,
        }).data
        return data

    def _get_paciente(self, user):
        cpf = user.get_username()
        if user.is_staff or len(cpf) != 11 or not cpf.isdigit():
            raise AuthenticationFailed(CIDADAO_AUTH_ERROR, code='citizen_access_denied')

        try:
            return Paciente.objects.get(cpf=cpf)
        except Paciente.DoesNotExist as exc:
            raise AuthenticationFailed(
                CIDADAO_AUTH_ERROR,
                code='citizen_access_denied',
            ) from exc


class AdminTokenRefreshSerializer(TokenRefreshSerializer):
    default_error_messages = {
        'no_active_account': ADMIN_AUTH_ERROR,
    }

    def validate(self, attrs):
        try:
            refresh = self.token_class(attrs['refresh'])
        except TokenError as exc:
            raise InvalidToken(str(exc)) from exc

        user_id = refresh.payload.get(api_settings.USER_ID_CLAIM)
        user = self._get_admin_user(user_id)

        data = super().validate(attrs)
        data['user'] = AdminUserSerializer(user).data
        return data

    def _get_admin_user(self, user_id):
        if user_id is None:
            raise AuthenticationFailed(ADMIN_AUTH_ERROR, code='no_active_account')

        User = get_user_model()
        try:
            user = User.objects.get(**{api_settings.USER_ID_FIELD: user_id})
        except (TypeError, ValueError, User.DoesNotExist) as exc:
            raise AuthenticationFailed(
                ADMIN_AUTH_ERROR,
                code='no_active_account',
            ) from exc

        if not user.is_active or not user.is_staff:
            raise AuthenticationFailed(ADMIN_AUTH_ERROR, code='admin_access_denied')

        return user


class CidadaoTokenRefreshSerializer(TokenRefreshSerializer):
    default_error_messages = {
        'no_active_account': CIDADAO_AUTH_ERROR,
    }

    def validate(self, attrs):
        try:
            refresh = self.token_class(attrs['refresh'])
        except TokenError as exc:
            raise InvalidToken(str(exc)) from exc

        user_id = refresh.payload.get(api_settings.USER_ID_CLAIM)
        user = self._get_cidadao_user(user_id)

        data = super().validate(attrs)
        paciente = Paciente.objects.get(cpf=user.get_username())
        data['user'] = CidadaoUserSerializer({
            'id': user.pk,
            'cpf': paciente.cpf,
            'nome_completo': paciente.nome_completo,
        }).data
        return data

    def _get_cidadao_user(self, user_id):
        if user_id is None:
            raise AuthenticationFailed(CIDADAO_AUTH_ERROR, code='no_active_account')

        User = get_user_model()
        try:
            user = User.objects.get(**{api_settings.USER_ID_FIELD: user_id})
        except (TypeError, ValueError, User.DoesNotExist) as exc:
            raise AuthenticationFailed(
                CIDADAO_AUTH_ERROR,
                code='no_active_account',
            ) from exc

        cpf = user.get_username()
        if (
            not user.is_active
            or user.is_staff
            or len(cpf) != 11
            or not cpf.isdigit()
            or not Paciente.objects.filter(cpf=cpf).exists()
        ):
            raise AuthenticationFailed(
                CIDADAO_AUTH_ERROR,
                code='citizen_access_denied',
            )

        return user


class AdminLogoutSerializer(serializers.Serializer):
    refresh = serializers.CharField(write_only=True)

    def validate_refresh(self, value):
        try:
            token = RefreshToken(value)
        except TokenError as exc:
            raise serializers.ValidationError(
                'Refresh token invalido ou expirado.'
            ) from exc

        request = self.context.get('request')
        token_user_id = token.payload.get(api_settings.USER_ID_CLAIM)
        if request is None or str(token_user_id) != str(request.user.pk):
            raise serializers.ValidationError(
                'O refresh token nao pertence ao usuario autenticado.'
            )

        self.refresh_token = token
        return value

    def save(self, **kwargs):
        self.refresh_token.blacklist()
        
class PacienteSerializer(serializers.ModelSerializer):
    cpf = serializers.SerializerMethodField()
    cns = serializers.SerializerMethodField()
    nome_completo = serializers.SerializerMethodField()

    class Meta:
        model = Paciente
        fields = '__all__'

    def get_cpf(self, obj: Paciente) -> str:
        return self._mascarar_documento(obj.cpf)

    def get_cns(self, obj: Paciente) -> str:
        return self._mascarar_documento(obj.cns)

    def _mascarar_documento(self, valor: str | None) -> str:
        if not valor:
            return ''
        return f"{'*' * max(len(valor) - 4, 0)}{valor[-4:]}"

    def get_nome_completo(self, obj: Paciente) -> str:
        partes = obj.nome_completo.split()

        resultado = []

        for parte in partes:
            resultado.append(
                parte[0] + "*" * (len(parte) - 1)
            )

        return " ".join(resultado)
