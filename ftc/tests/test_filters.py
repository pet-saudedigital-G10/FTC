from datetime import date

from django.contrib.auth import get_user_model
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase

from ftc.models import Especialidade, Paciente, PublicacaoFila, RegistroFila


class RegistroFilaFilterTests(APITestCase):
    def setUp(self):
        self.admin = get_user_model().objects.create_superuser(
            username='filter-admin',
            password='SenhaForte123!',
        )
        self.pediatria = Especialidade.objects.create(
            nome='Pediatria',
            slug='consulta-pediatria',
            tipo=Especialidade.Tipo.CONSULTA,
        )
        self.cardiologia = Especialidade.objects.create(
            nome='Cardiologia',
            slug='consulta-cardiologia',
            tipo=Especialidade.Tipo.CONSULTA,
        )
        self.ultrassom = Especialidade.objects.create(
            nome='Ultrassonografia',
            slug='exame-ultrassonografia',
            tipo=Especialidade.Tipo.EXAME,
        )

        self.publicacao_pediatria = self.criar_publicacao(
            self.pediatria,
            hash_arquivo='1' * 64,
        )
        self.publicacao_cardiologia = self.criar_publicacao(
            self.cardiologia,
            hash_arquivo='2' * 64,
        )
        self.publicacao_ultrassom = self.criar_publicacao(
            self.ultrassom,
            hash_arquivo='3' * 64,
        )
        self.publicacao_rascunho = self.criar_publicacao(
            self.pediatria,
            competencia=date(2026, 5, 1),
            status=PublicacaoFila.Status.RASCUNHO,
            hash_arquivo='4' * 64,
        )

        paciente = Paciente.objects.create(cpf='12345678901')
        self.criar_registro(
            self.publicacao_pediatria,
            paciente=paciente,
            codigo='PED-1',
            posicao=1,
            prioridade=RegistroFila.Prioridade.NIVEL_1,
            tipo=RegistroFila.Tipo.SOLICITADAS,
            situacao=RegistroFila.Situacao.SOLICITADO,
        )
        self.criar_registro(
            self.publicacao_pediatria,
            codigo='PED-2',
            posicao=2,
            prioridade=RegistroFila.Prioridade.NIVEL_2,
            tipo=RegistroFila.Tipo.PENDENTES,
            situacao=RegistroFila.Situacao.AGUARDANDO_REGULACAO,
        )
        self.criar_registro(
            self.publicacao_cardiologia,
            codigo='CAR-1',
            posicao=1,
            prioridade=RegistroFila.Prioridade.NIVEL_1,
            tipo=RegistroFila.Tipo.PENDENTES,
            situacao=RegistroFila.Situacao.PENDENTE,
        )
        self.criar_registro(
            self.publicacao_ultrassom,
            codigo='USG-1',
            posicao=1,
            prioridade=RegistroFila.Prioridade.NIVEL_3,
            tipo=RegistroFila.Tipo.BAIXADAS,
            situacao=RegistroFila.Situacao.BAIXADO_INTERNADO_CRL,
        )
        self.criar_registro(
            self.publicacao_rascunho,
            codigo='DRAFT-1',
            posicao=1,
            prioridade=RegistroFila.Prioridade.NIVEL_1,
            tipo=RegistroFila.Tipo.SOLICITADAS,
            situacao=RegistroFila.Situacao.SOLICITADO,
        )

    def criar_publicacao(
        self,
        especialidade,
        *,
        competencia=date(2026, 4, 1),
        status=PublicacaoFila.Status.PUBLICADA,
        hash_arquivo,
    ):
        return PublicacaoFila.objects.create(
            especialidade=especialidade,
            competencia=competencia,
            versao=1,
            arquivo_original=f'filas/teste-{hash_arquivo[:4]}.csv',
            hash_arquivo=hash_arquivo,
            status=status,
            importado_por=self.admin,
        )

    def criar_registro(
        self,
        publicacao,
        *,
        codigo,
        posicao,
        prioridade,
        tipo,
        situacao,
        paciente=None,
    ):
        return RegistroFila.objects.create(
            publicacao=publicacao,
            paciente=paciente,
            data_solicitacao=date(2026, 4, 6),
            nome_mascarado='P.T.',
            ano_nascimento=1990,
            cpf_mascarado='123.***.***-01',
            codigo_solicitacao=codigo,
            posicao=posicao,
            prioridade=prioridade,
            tipo=tipo,
            situacao=situacao,
        )

    def test_lista_apenas_registros_publicados(self):
        response = self.client.get(reverse('fila-registro-list'))

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 4)
        codigos = {item['codigo_solicitacao'] for item in response.data}
        self.assertNotIn('DRAFT-1', codigos)

    def test_filtra_por_especialidade_slug(self):
        response = self.client.get(
            reverse('fila-registro-list'),
            {'especialidade': 'consulta-pediatria'},
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(
            {item['codigo_solicitacao'] for item in response.data},
            {'PED-1', 'PED-2'},
        )

    def test_filtra_por_tipo_e_prioridade(self):
        response = self.client.get(
            reverse('fila-registro-list'),
            {'tipo': 'Pendentes', 'prioridade': '1'},
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(
            [item['codigo_solicitacao'] for item in response.data],
            ['CAR-1'],
        )

    def test_filtra_por_situacao_com_label(self):
        response = self.client.get(
            reverse('fila-registro-list'),
            {'situacao': 'Aguardando regulacao'},
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(
            [item['codigo_solicitacao'] for item in response.data],
            ['PED-2'],
        )

    def test_filtra_por_especialidade_tipo_e_demais_parametros(self):
        response = self.client.get(
            reverse('fila-registro-list'),
            {
                'categoria': 'Exame',
                'especialidade': 'exame-ultrassonografia',
                'tipo': 'Baixadas',
                'situacao': 'Baixado - Internado CRL',
                'prioridade': '3',
            },
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(
            [item['codigo_solicitacao'] for item in response.data],
            ['USG-1'],
        )

    def test_prioridade_invalida_retorna_400(self):
        response = self.client.get(
            reverse('fila-registro-list'),
            {'prioridade': 'alta'},
        )

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
