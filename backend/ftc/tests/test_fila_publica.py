from datetime import date

from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase

from ftc.models import Especialidade, Paciente, PublicacaoFila, RegistroFila
from ftc.utils.masking import mask_cpf, mask_name


class ConsultaPosicaoFilaTests(APITestCase):
    """Testes para o endpoint publico de consulta de posicao na fila.

    Verifica que nenhum dado pessoal identificavel e exposto —
    apenas os campos ja mascarados armazenados em RegistroFila.
    """

    def setUp(self):
        self.cpf = '10000000001'
        self.nome_real = 'Joao da Silva Santos'

        self.paciente = Paciente.objects.create(
            cpf=self.cpf,
            nome_completo=self.nome_real,
        )

        especialidade = Especialidade.objects.create(
            nome='Cardiologia',
            slug='consulta-cardiologia-pb13',
            tipo=Especialidade.Tipo.CONSULTA,
        )
        publicacao = PublicacaoFila.objects.create(
            especialidade=especialidade,
            competencia=date(2026, 6, 1),
            arquivo_original='filas/teste-pb13.csv',
            hash_arquivo='pb13' + 'a' * 60,
            status=PublicacaoFila.Status.PUBLICADA,
        )
        self.registro = RegistroFila.objects.create(
            publicacao=publicacao,
            paciente=self.paciente,
            data_solicitacao=date(2026, 6, 10),
            nome_mascarado=mask_name(self.nome_real),
            cpf_mascarado=mask_cpf(self.cpf),
            codigo_solicitacao='PB13-001',
            posicao=5,
            situacao=RegistroFila.Situacao.AGUARDANDO_REGULACAO,
        )
        self.url = reverse('fila-posicao')

    # ------------------------------------------------------------------
    # Acesso publico
    # ------------------------------------------------------------------

    def test_endpoint_acessivel_sem_autenticacao(self):
        response = self.client.post(self.url, {'cpf': self.cpf}, format='json')
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    # ------------------------------------------------------------------
    # Mascaramento de dados pessoais (PB13)
    # ------------------------------------------------------------------

    def test_nome_retornado_esta_mascarado(self):
        response = self.client.post(self.url, {'cpf': self.cpf}, format='json')

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertTrue(response.data['encontrado'])

        fila = response.data['filas'][0]

        # nome_mascarado deve existir e nao deve ser o nome real
        self.assertIn('nome_mascarado', fila)
        self.assertNotIn('nome_paciente', fila)
        self.assertNotIn('nome_completo', fila)
        self.assertNotEqual(fila['nome_mascarado'], self.nome_real)

        # Verifica formato mascarado: primeira letra + asteriscos por palavra
        nome_mascarado = fila['nome_mascarado']
        for palavra_real, palavra_mascarada in zip(
            self.nome_real.split(), nome_mascarado.split()
        ):
            self.assertEqual(palavra_mascarada[0], palavra_real[0])
            if len(palavra_real) > 1:
                self.assertTrue(
                    all(c == '*' for c in palavra_mascarada[1:]),
                    f'Palavra {palavra_mascarada!r} nao esta corretamente mascarada',
                )

    def test_cpf_nao_exposto_na_resposta(self):
        response = self.client.post(self.url, {'cpf': self.cpf}, format='json')

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        fila = response.data['filas'][0]

        # CPF bruto nao deve aparecer
        self.assertNotIn('cpf', fila)
        self.assertNotIn('cpf_mascarado', fila)

        # O CPF nao deve aparecer em nenhum valor da resposta
        response_str = str(response.data)
        self.assertNotIn(self.cpf, response_str)

    def test_campos_retornados_sao_apenas_os_esperados(self):
        response = self.client.post(self.url, {'cpf': self.cpf}, format='json')

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        fila = response.data['filas'][0]

        campos_permitidos = {
            'posicao',
            'prioridade',
            'prioridade_display',
            'situacao',
            'situacao_display',
            'especialidade',
            'tipo_especialidade',
            'competencia',
            'nome_mascarado',
            'data_solicitacao',
        }
        campos_retornados = set(fila.keys())
        self.assertEqual(
            campos_retornados,
            campos_permitidos,
            f'Campos inesperados na resposta: {campos_retornados - campos_permitidos}',
        )

    def test_display_fields_retornados(self):
        response = self.client.post(self.url, {'cpf': self.cpf}, format='json')

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        fila = response.data['filas'][0]

        self.assertIn('situacao_display', fila)
        self.assertIn('prioridade_display', fila)
        self.assertEqual(fila['situacao_display'], 'Aguardando regulação')

    # ------------------------------------------------------------------
    # Validacao de CPF
    # ------------------------------------------------------------------

    def test_cpf_invalido_retorna_400(self):
        for cpf_invalido in ['', '123', 'abcdefghijk', '1234567890']:
            with self.subTest(cpf=cpf_invalido):
                response = self.client.post(
                    self.url, {'cpf': cpf_invalido}, format='json'
                )
                self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_cpf_ausente_retorna_400(self):
        response = self.client.post(self.url, {}, format='json')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_cpf_inexistente_retorna_encontrado_false(self):
        response = self.client.post(
            self.url, {'cpf': '99999999999'}, format='json'
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertFalse(response.data['encontrado'])
        self.assertEqual(response.data['filas'], [])

