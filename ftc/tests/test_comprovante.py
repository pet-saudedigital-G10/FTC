from datetime import date

from django.contrib.auth import get_user_model
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase

from ftc.models import Especialidade, Paciente, PublicacaoFila, RegistroFila


class RegistroFilaComprovanteTests(APITestCase):
    def setUp(self):
        self.admin = get_user_model().objects.create_superuser(
            username='comprovante-admin',
            password='SenhaForte123!',
        )
        self.pediatria = Especialidade.objects.create(
            nome='Pediatria',
            slug='consulta-pediatria',
            tipo=Especialidade.Tipo.CONSULTA,
        )
        self.publicacao_publicada = PublicacaoFila.objects.create(
            especialidade=self.pediatria,
            competencia=date(2026, 4, 1),
            versao=1,
            arquivo_original='filas/teste-1.csv',
            hash_arquivo='1' * 64,
            status=PublicacaoFila.Status.PUBLICADA,
            importado_por=self.admin,
        )
        self.publicacao_rascunho = PublicacaoFila.objects.create(
            especialidade=self.pediatria,
            competencia=date(2026, 5, 1),
            versao=1,
            arquivo_original='filas/teste-2.csv',
            hash_arquivo='2' * 64,
            status=PublicacaoFila.Status.RASCUNHO,
            importado_por=self.admin,
        )
        self.paciente = Paciente.objects.create(
            cpf='12345678901',
            cns='700123456789012',
            nome_completo='João Silva',
            data_nascimento=date(1990, 5, 15),
            sexo=Paciente.Sexo.MASCULINO,
        )
        self.registro_publicado = RegistroFila.objects.create(
            publicacao=self.publicacao_publicada,
            paciente=self.paciente,
            data_solicitacao=date(2026, 4, 6),
            nome_mascarado='J.S.',
            ano_nascimento=1990,
            cpf_mascarado='123.***.***-01',
            cns_mascarado='700********9012',
            sexo=Paciente.Sexo.MASCULINO,
            codigo_solicitacao='PED-100',
            posicao=1,
            prioridade=RegistroFila.Prioridade.NIVEL_1,
            tipo=RegistroFila.Tipo.SOLICITADAS,
            situacao=RegistroFila.Situacao.SOLICITADO,
        )
        self.registro_rascunho = RegistroFila.objects.create(
            publicacao=self.publicacao_rascunho,
            paciente=self.paciente,
            data_solicitacao=date(2026, 5, 2),
            nome_mascarado='J.S.',
            ano_nascimento=1990,
            cpf_mascarado='123.***.***-01',
            codigo_solicitacao='PED-200',
            posicao=1,
            prioridade=RegistroFila.Prioridade.NIVEL_1,
            tipo=RegistroFila.Tipo.SOLICITADAS,
            situacao=RegistroFila.Situacao.SOLICITADO,
        )

    def test_retorna_200_e_dados_comprovante_para_registro_existente(self):
        url = reverse('fila-registro-comprovante', kwargs={'pk': self.registro_publicado.pk})
        response = self.client.get(url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        data = response.json()

        self.assertEqual(data['id'], self.registro_publicado.pk)
        self.assertEqual(data['codigo_solicitacao'], 'PED-100')
        self.assertEqual(data['posicao'], 1)
        self.assertEqual(data['especialidade_id'], self.pediatria.pk)
        self.assertEqual(data['especialidade_nome'], 'Pediatria')
        self.assertEqual(data['especialidade_slug'], 'consulta-pediatria')
        self.assertEqual(data['especialidade_tipo'], 'CONSULTA')
        self.assertEqual(data['especialidade_tipo_display'], 'Consulta')
        self.assertEqual(data['publicacao_id'], self.publicacao_publicada.pk)
        self.assertEqual(data['competencia'], '2026-04-01')
        self.assertEqual(data['versao'], 1)
        self.assertEqual(data['data_solicitacao'], '2026-04-06')
        self.assertEqual(data['nome_mascarado'], 'J.S.')
        self.assertEqual(data['cpf_mascarado'], '123.***.***-01')
        self.assertEqual(data['cns_mascarado'], '700********9012')
        self.assertEqual(data['ano_nascimento'], 1990)
        self.assertEqual(data['sexo'], 'M')
        self.assertEqual(data['prioridade'], 1)
        self.assertEqual(data['prioridade_display'], 'Prioridade 1')
        self.assertEqual(data['tipo'], 'SOLICITADAS')
        self.assertEqual(data['tipo_display'], 'Solicitadas')
        self.assertEqual(data['situacao'], 'SOLICITADO')
        self.assertEqual(data['situacao_display'], 'Solicitado')
        self.assertIn('emitido_em', data)

    def test_retorna_404_para_registro_inexistente(self):
        url = reverse('fila-registro-comprovante', kwargs={'pk': 999999})
        response = self.client.get(url)

        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_retorna_404_para_registro_de_publicacao_nao_publicada(self):
        url = reverse('fila-registro-comprovante', kwargs={'pk': self.registro_rascunho.pk})
        response = self.client.get(url)

        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)
