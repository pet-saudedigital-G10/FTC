from django.contrib.auth import get_user_model
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APIClient, APITestCase

from datetime import date

# testando rota /pacientes
from ftc.models import Paciente

class PacienteViewTest(APITestCase):

    def test_retorna_dados_mascarados(self):

        Paciente.objects.create(
            cns="123456789012345",
            nome_completo="Testando Marques Melo",
            data_nascimento=date(2000, 1, 1),
            sexo="M"
        )

        response = self.client.get(reverse("pacientes"))

        self.assertEqual(response.status_code, 200)

        self.assertEqual(
            response.data[0]["cns"],
            "***********2345"
        )

        self.assertEqual(
            response.data[0]["nome_completo"],
            "T******* M****** M***"
        )

class AdminAuthTests(APITestCase):
    def setUp(self):
        User = get_user_model()
        self.password = 'SenhaForte123!'
        self.staff_user = User.objects.create_user(
            username='servidora.saude',
            email='servidora@example.com',
            password=self.password,
            is_staff=True,
        )
        self.common_user = User.objects.create_user(
            username='cidadao',
            email='cidadao@example.com',
            password=self.password,
        )
        self.superuser = User.objects.create_superuser(
            username='ftcadmin',
            email='ftcadmin@example.com',
            password=self.password,
        )

    def test_staff_user_can_login(self):
        response = self.client.post(
            reverse('admin-login'),
            {'username': self.staff_user.username, 'password': self.password},
            format='json',
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn('access', response.data)
        self.assertIn('refresh', response.data)
        self.assertEqual(response.data['user']['username'], self.staff_user.username)

    def test_csrf_endpoint_issues_cookie_for_frontend_origin(self):
        client = APIClient(enforce_csrf_checks=True)

        response = client.get(
            reverse('csrf-token'),
            HTTP_ORIGIN='http://localhost:3000',
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn('csrfToken', response.json())
        self.assertIn('csrftoken', response.cookies)
        self.assertEqual(
            response['Access-Control-Allow-Origin'],
            'http://localhost:3000',
        )
        self.assertEqual(response['Access-Control-Allow-Credentials'], 'true')

    def test_session_login_requires_csrf_and_creates_session(self):
        client = APIClient(enforce_csrf_checks=True)
        csrf_response = client.get(
            reverse('csrf-token'),
            HTTP_ORIGIN='http://localhost:3000',
        )
        csrf_token = csrf_response.json()['csrfToken']

        response = client.post(
            reverse('admin-session-login'),
            {'username': self.staff_user.username, 'password': self.password},
            format='json',
            HTTP_ORIGIN='http://localhost:3000',
            HTTP_X_CSRFTOKEN=csrf_token,
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.json()['user']['username'], self.staff_user.username)
        self.assertIn('sessionid', response.cookies)
        self.assertIn('csrftoken', response.cookies)

    def test_session_login_returns_json_when_csrf_token_is_missing(self):
        client = APIClient(enforce_csrf_checks=True)

        response = client.post(
            reverse('admin-session-login'),
            {'username': self.staff_user.username, 'password': self.password},
            format='json',
            HTTP_ORIGIN='http://localhost:3000',
        )

        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
        self.assertEqual(response.json()['detail'], 'Falha na verificacao CSRF.')

    def test_common_user_cannot_login_to_admin_dashboard(self):
        response = self.client.post(
            reverse('admin-login'),
            {'username': self.common_user.username, 'password': self.password},
            format='json',
        )

        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_refresh_requires_user_to_remain_staff(self):
        login_response = self.client.post(
            reverse('admin-login'),
            {'username': self.staff_user.username, 'password': self.password},
            format='json',
        )
        refresh = login_response.data['refresh']

        self.staff_user.is_staff = False
        self.staff_user.save(update_fields=['is_staff'])

        response = self.client.post(
            reverse('admin-token-refresh'),
            {'refresh': refresh},
            format='json',
        )

        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_authenticated_staff_user_can_read_me(self):
        login_response = self.client.post(
            reverse('admin-login'),
            {'username': self.staff_user.username, 'password': self.password},
            format='json',
        )
        access = login_response.data['access']

        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {access}')
        response = self.client.get(reverse('admin-me'))

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['username'], self.staff_user.username)

    def test_superuser_can_create_admin_without_email(self):
        self.client.force_authenticate(user=self.superuser)

        response = self.client.post(
            reverse('admin-user-create'),
            {
                'username': 'gestora.saude',
                'password': 'OutraSenhaForte123!',
            },
            format='json',
        )

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        created_user = get_user_model().objects.get(username='gestora.saude')
        self.assertEqual(created_user.email, '')
        self.assertTrue(created_user.is_staff)
        self.assertFalse(created_user.is_superuser)
        self.assertTrue(created_user.check_password('OutraSenhaForte123!'))
        self.assertNotIn('password', response.data)

    def test_admin_registration_accepts_optional_email(self):
        self.client.force_authenticate(user=self.superuser)

        response = self.client.post(
            reverse('admin-user-create'),
            {
                'username': 'gestora.com.email',
                'password': 'OutraSenhaForte123!',
                'email': 'gestora@example.com',
            },
            format='json',
        )

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data['email'], 'gestora@example.com')

    def test_staff_user_cannot_create_another_admin(self):
        self.client.force_authenticate(user=self.staff_user)

        response = self.client.post(
            reverse('admin-user-create'),
            {
                'username': 'admin.indevido',
                'password': 'OutraSenhaForte123!',
            },
            format='json',
        )

        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
