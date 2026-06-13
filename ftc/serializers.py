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


ADMIN_AUTH_ERROR = 'Credenciais invalidas ou usuario sem permissao administrativa.'


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


class AdminLogoutSerializer(serializers.Serializer):
    refresh = serializers.CharField(write_only=True)

    def save(self, **kwargs):
        try:
            RefreshToken(self.validated_data['refresh']).blacklist()
        except TokenError as exc:
            raise serializers.ValidationError(
                {'refresh': 'Refresh token invalido ou expirado.'}
            ) from exc
