from datetime import date

from django.contrib.auth import get_user_model
from django.core.cache import cache
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase

from ftc.models import Especialidade, Paciente, PublicacaoFila, RegistroFila


class CidadaoAuthTests(APITestCase):
    def setUp(self):
        cache.clear()
        self.password = 'SenhaCidadao123!'
        self.cpf = '12345678901'
        self.outro_cpf = '98765432100'
        self.paciente = Paciente.objects.create(
            cpf=self.cpf,
            nome_completo='Cidada Teste',
        )
        self.outro_paciente = Paciente.objects.create(
            cpf=self.outro_cpf,
            nome_completo='Outro Paciente',
        )
        User = get_user_model()
        self.user = User.objects.create_user(
            username=self.cpf,
            password=self.password,
        )
        self.outro_user = User.objects.create_user(
            username=self.outro_cpf,
            password=self.password,
        )
        self.staff_user = User.objects.create_user(
            username='admin-cidadao-test',
            password=self.password,
            is_staff=True,
        )

        especialidade = Especialidade.objects.create(
            nome='Pediatria',
            slug='cidadao-pediatria',
            tipo=Especialidade.Tipo.CONSULTA,
        )
        publicacao = PublicacaoFila.objects.create(
            especialidade=especialidade,
            competencia=date(2026, 8, 1),
            arquivo_original='filas/teste-cidadao.csv',
            hash_arquivo='d' * 64,
            status=PublicacaoFila.Status.PUBLICADA,
        )
        self._criar_registro(publicacao, self.paciente, 'CID-001', 1)
        self._criar_registro(publicacao, self.outro_paciente, 'OUT-001', 2)

    def _criar_registro(self, publicacao, paciente, codigo, posicao):
        return RegistroFila.objects.create(
            publicacao=publicacao,
            paciente=paciente,
            data_solicitacao=date(2026, 8, 10),
            nome_mascarado='C.T.',
            cpf_mascarado=f'{paciente.cpf[:3]}.***.***-{paciente.cpf[-2:]}',
            codigo_solicitacao=codigo,
            posicao=posicao,
        )

    def _login(self, cpf=None):
        return self.client.post(
            reverse('cidadao-login'),
            {'username': cpf or self.cpf, 'password': self.password},
            format='json',
        )

    def test_cidadao_vinculado_pode_entrar(self):
        response = self._login()

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn('access', response.data)
        self.assertIn('refresh', response.data)
        self.assertEqual(response.data['user']['cpf'], self.cpf)
        self.assertEqual(response.data['user']['nome_completo'], 'Cidada Teste')

    def test_staff_e_conta_sem_paciente_nao_podem_entrar(self):
        staff_response = self.client.post(
            reverse('cidadao-login'),
            {'username': self.staff_user.username, 'password': self.password},
            format='json',
        )
        sem_paciente = get_user_model().objects.create_user(
            username='11122233344',
            password=self.password,
        )
        sem_paciente_response = self._login(sem_paciente.username)

        self.assertEqual(staff_response.status_code, status.HTTP_401_UNAUTHORIZED)
        self.assertEqual(
            sem_paciente_response.status_code,
            status.HTTP_401_UNAUTHORIZED,
        )

    def test_me_e_filas_retornam_somente_dados_do_cidadao(self):
        login = self._login()
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {login.data['access']}")

        me_response = self.client.get(reverse('cidadao-me'))
        filas_response = self.client.get(reverse('cidadao-filas'))

        self.assertEqual(me_response.status_code, status.HTTP_200_OK)
        self.assertEqual(me_response.data['cpf'], self.cpf)
        self.assertEqual(filas_response.status_code, status.HTTP_200_OK)
        self.assertEqual(
            [item['codigo_solicitacao'] for item in filas_response.data],
            ['CID-001'],
        )

    def test_refresh_exige_vinculo_ativo_com_paciente(self):
        login = self._login()
        self.paciente.delete()

        response = self.client.post(
            reverse('cidadao-token-refresh'),
            {'refresh': login.data['refresh']},
            format='json',
        )

        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_logout_rejeita_refresh_de_outro_usuario(self):
        login = self._login()
        outro_login = self._login(self.outro_cpf)
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {login.data['access']}")

        response = self.client.post(
            reverse('cidadao-logout'),
            {'refresh': outro_login.data['refresh']},
            format='json',
        )

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_logout_invalida_refresh_do_proprio_usuario(self):
        login = self._login()
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {login.data['access']}")

        logout_response = self.client.post(
            reverse('cidadao-logout'),
            {'refresh': login.data['refresh']},
            format='json',
        )
        refresh_response = self.client.post(
            reverse('cidadao-token-refresh'),
            {'refresh': login.data['refresh']},
            format='json',
        )

        self.assertEqual(logout_response.status_code, status.HTTP_204_NO_CONTENT)
        self.assertEqual(refresh_response.status_code, status.HTTP_401_UNAUTHORIZED)
