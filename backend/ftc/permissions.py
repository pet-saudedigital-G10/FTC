from rest_framework.permissions import BasePermission

from ftc.models import ConfiguracaoSisreg, Paciente


class IsSuperUser(BasePermission):
    message = 'Apenas superusuarios podem cadastrar usuarios administrativos.'

    def has_permission(self, request, view):
        user = request.user
        return bool(
            user
            and user.is_authenticated
            and user.is_active
            and user.is_superuser
        )


class IsSisregConfigurator(IsSuperUser):
    message = 'Apenas superusuarios podem configurar a integracao com o SISREG.'


class IsSisregEnabled(BasePermission):
    message = 'A integracao com o SISREG nao esta habilitada.'

    def has_permission(self, request, view):
        return ConfiguracaoSisreg.carregar().habilitado


class IsCitizen(BasePermission):
    message = 'Acesso permitido apenas ao cidadao vinculado a este CPF.'

    def has_permission(self, request, view):
        user = request.user
        return bool(
            user
            and user.is_authenticated
            and user.is_active
            and not user.is_staff
            and Paciente.objects.filter(cpf=user.get_username()).exists()
        )
