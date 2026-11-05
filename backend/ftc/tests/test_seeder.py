from io import StringIO

from django.contrib.auth import get_user_model
from django.core.management import call_command
from django.test import TestCase

from ftc.management.commands.database_seeder import (
    ADMIN_PASSWORD_SEED,
    ADMIN_USERNAME_SEED,
    CIDADAO_CPF_SEED,
    CIDADAO_PASSWORD_SEED,
)
from ftc.models import Paciente


class DatabaseSeederTests(TestCase):
    def test_cria_usuarios_administrativo_e_cidadao(self):
        call_command('database_seeder', stdout=StringIO(), stderr=StringIO())

        User = get_user_model()
        admin = User.objects.get(username=ADMIN_USERNAME_SEED)
        cidadao = User.objects.get(username=CIDADAO_CPF_SEED)

        self.assertTrue(admin.is_active)
        self.assertTrue(admin.is_staff)
        self.assertTrue(admin.check_password(ADMIN_PASSWORD_SEED))

        self.assertTrue(cidadao.is_active)
        self.assertFalse(cidadao.is_staff)
        self.assertFalse(cidadao.is_superuser)
        self.assertTrue(cidadao.check_password(CIDADAO_PASSWORD_SEED))
        self.assertTrue(Paciente.objects.filter(cpf=CIDADAO_CPF_SEED).exists())
