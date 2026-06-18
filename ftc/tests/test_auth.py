from django.contrib.auth import get_user_model
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase


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
