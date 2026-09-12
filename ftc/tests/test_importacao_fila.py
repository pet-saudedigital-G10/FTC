import shutil
import tempfile
from datetime import date
from pathlib import Path
from unittest.mock import MagicMock, patch

from django.contrib.auth import get_user_model
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import override_settings
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase

from ftc.models import Especialidade, PublicacaoFila, RegistroFila
from ftc.services import (
    ErroImportacaoPDF,
    atualizar_fila_por_pdf,
    extrair_registros_pdf,
)


def registros_extraidos():
    return [
        {
            'data_solicitacao': date(2026, 4, 1),
            'nome_mascarado': 'A. B.',
            'ano_nascimento': 1990,
            'cns_mascarado': '***********1234',
            'sexo': 'F',
            'codigo_solicitacao': '100000001',
            'posicao': 1,
        },
        {
            'data_solicitacao': date(2026, 4, 2),
            'nome_mascarado': 'C. D.',
            'ano_nascimento': 1985,
            'cns_mascarado': '***********5678',
            'sexo': 'M',
            'codigo_solicitacao': '100000002',
            'posicao': 2,
        },
    ]


class AtualizacaoFilaAPITests(APITestCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.media_dir = tempfile.mkdtemp(prefix='ftc-test-media-')
        cls.settings_override = override_settings(MEDIA_ROOT=cls.media_dir)
        cls.settings_override.enable()

    @classmethod
    def tearDownClass(cls):
        cls.settings_override.disable()
        shutil.rmtree(cls.media_dir, ignore_errors=True)
        super().tearDownClass()

    def setUp(self):
        User = get_user_model()
        self.staff = User.objects.create_user(
            username='servidora.importacao',
            password='SenhaForte123!',
            is_staff=True,
        )
        self.cidadao = User.objects.create_user(
            username='cidadao.importacao',
            password='SenhaForte123!',
        )
        self.especialidade = Especialidade.objects.create(
            nome='Pediatria',
            slug='consulta-pediatria-importacao',
            tipo=Especialidade.Tipo.CONSULTA,
        )
        self.anterior = PublicacaoFila.objects.create(
            especialidade=self.especialidade,
            competencia=date(2026, 3, 1),
            versao=1,
            arquivo_original='filas/anterior.pdf',
            hash_arquivo='a' * 64,
            status=PublicacaoFila.Status.PUBLICADA,
            importado_por=self.staff,
        )
        RegistroFila.objects.create(
            publicacao=self.anterior,
            data_solicitacao=date(2026, 3, 1),
            nome_mascarado='A. A.',
            ano_nascimento=1980,
            cns_mascarado='***********9999',
            sexo='F',
            codigo_solicitacao='ANTIGO-1',
            posicao=1,
        )

    def arquivo(self, conteudo=b'%PDF-arquivo-novo'):
        return SimpleUploadedFile(
            'fila-pediatria.pdf',
            conteudo,
            content_type='application/pdf',
        )

    @patch(
        'ftc.services.importacao_fila.extrair_registros_pdf',
        return_value=registros_extraidos(),
    )
    def test_staff_substitui_publicacao_e_preserva_historico(self, _extrair):
        self.client.force_authenticate(user=self.staff)

        resposta = self.client.post(
            reverse('admin-fila-atualizar'),
            {
                'arquivo': self.arquivo(),
                'especialidade': self.especialidade.pk,
                'competencia': '2026-04',
                'observacao': 'Atualizacao mensal.',
            },
            format='multipart',
        )

        self.assertEqual(resposta.status_code, status.HTTP_201_CREATED)
        self.assertEqual(resposta.data['registros_importados'], 2)
        self.assertEqual(
            resposta.data['publicacoes_substituidas'],
            [self.anterior.pk],
        )

        self.anterior.refresh_from_db()
        self.assertEqual(self.anterior.status, PublicacaoFila.Status.ARQUIVADA)

        atual = PublicacaoFila.objects.get(pk=resposta.data['publicacao_id'])
        self.assertEqual(atual.status, PublicacaoFila.Status.PUBLICADA)
        self.assertEqual(atual.competencia, date(2026, 4, 1))
        self.assertEqual(atual.importado_por, self.staff)
        self.assertEqual(atual.registros.count(), 2)

        publica = self.client.get(
            reverse('fila-registro-list'),
            {'especialidade': self.especialidade.pk},
        )
        self.assertEqual(publica.status_code, status.HTTP_200_OK)
        self.assertEqual(
            [item['codigo_solicitacao'] for item in publica.data],
            ['100000001', '100000002'],
        )

    @patch(
        'ftc.services.importacao_fila.extrair_registros_pdf',
        side_effect=ErroImportacaoPDF('PDF fora do formato esperado.'),
    )
    def test_pdf_invalido_nao_altera_publicacao_atual(self, _extrair):
        self.client.force_authenticate(user=self.staff)

        resposta = self.client.post(
            reverse('admin-fila-atualizar'),
            {
                'arquivo': self.arquivo(),
                'especialidade': self.especialidade.pk,
                'competencia': '2026-04',
            },
            format='multipart',
        )

        self.assertEqual(resposta.status_code, status.HTTP_400_BAD_REQUEST)
        self.anterior.refresh_from_db()
        self.assertEqual(self.anterior.status, PublicacaoFila.Status.PUBLICADA)
        self.assertEqual(PublicacaoFila.objects.count(), 1)

    @patch(
        'ftc.services.importacao_fila.extrair_registros_pdf',
        return_value=registros_extraidos(),
    )
    def test_mesmo_arquivo_nao_e_publicado_duas_vezes(self, _extrair):
        self.client.force_authenticate(user=self.staff)
        dados = {
            'arquivo': self.arquivo(),
            'especialidade': self.especialidade.pk,
            'competencia': '2026-04',
        }
        primeira = self.client.post(
            reverse('admin-fila-atualizar'),
            dados,
            format='multipart',
        )
        segunda = self.client.post(
            reverse('admin-fila-atualizar'),
            {**dados, 'arquivo': self.arquivo()},
            format='multipart',
        )

        self.assertEqual(primeira.status_code, status.HTTP_201_CREATED)
        self.assertEqual(segunda.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(PublicacaoFila.objects.count(), 2)
        self.assertEqual(
            PublicacaoFila.objects.get(status=PublicacaoFila.Status.PUBLICADA).pk,
            primeira.data['publicacao_id'],
        )

    def test_endpoint_exige_usuario_staff(self):
        dados = {
            'arquivo': self.arquivo(),
            'especialidade': self.especialidade.pk,
            'competencia': '2026-04',
        }
        anonima = self.client.post(
            reverse('admin-fila-atualizar'),
            dados,
            format='multipart',
        )
        self.client.force_authenticate(user=self.cidadao)
        cidadao = self.client.post(
            reverse('admin-fila-atualizar'),
            {**dados, 'arquivo': self.arquivo()},
            format='multipart',
        )

        self.assertEqual(anonima.status_code, status.HTTP_401_UNAUTHORIZED)
        self.assertEqual(cidadao.status_code, status.HTTP_403_FORBIDDEN)

    def test_rejeita_arquivo_que_nao_e_pdf(self):
        self.client.force_authenticate(user=self.staff)
        resposta = self.client.post(
            reverse('admin-fila-atualizar'),
            {
                'arquivo': SimpleUploadedFile('fila.pdf', b'conteudo invalido'),
                'especialidade': self.especialidade.pk,
                'competencia': '2026-04',
            },
            format='multipart',
        )

        self.assertEqual(resposta.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(PublicacaoFila.objects.count(), 1)

    @patch(
        'ftc.services.importacao_fila.extrair_registros_pdf',
        return_value=registros_extraidos(),
    )
    @patch(
        'ftc.services.importacao_fila.RegistroFila.objects.bulk_create',
        side_effect=RuntimeError('falha simulada no banco'),
    )
    def test_falha_na_gravacao_reverte_banco_e_remove_arquivo(
        self,
        _bulk_create,
        _extrair,
    ):
        with self.assertRaises(RuntimeError):
            atualizar_fila_por_pdf(
                arquivo=self.arquivo(b'%PDF-arquivo-com-falha'),
                especialidade=self.especialidade,
                competencia=date(2026, 4, 1),
                importado_por=self.staff,
            )

        self.anterior.refresh_from_db()
        self.assertEqual(self.anterior.status, PublicacaoFila.Status.PUBLICADA)
        self.assertEqual(PublicacaoFila.objects.count(), 1)
        arquivos = [item for item in Path(self.media_dir).rglob('*') if item.is_file()]
        self.assertEqual(arquivos, [])


class ExtracaoPDFTests(APITestCase):
    def setUp(self):
        self.especialidade = Especialidade(
            nome='Pediatria',
            tipo=Especialidade.Tipo.CONSULTA,
        )
        self.cabecalho = [
            'DATA DA SOLICITACAO',
            'NOME DO USUARIO',
            'ANO DE NASCIMENTO DO USUARIO',
            'CNS DO USUARIO',
            'SEXO DO USUARIO',
            'COD. SOLICITACAO',
            'POSICAO NA FILA',
        ]

    def documento(self, tabelas_por_pagina):
        paginas = []
        for tabelas in tabelas_por_pagina:
            pagina = MagicMock()
            pagina.extract_tables.return_value = tabelas
            paginas.append(pagina)
        documento = MagicMock()
        documento.pages = paginas
        contexto = MagicMock()
        contexto.__enter__.return_value = documento
        return contexto

    @patch('ftc.services.importacao_fila.pdfplumber.open')
    def test_extrai_tabela_multipagina_e_mascara_dados(self, abrir_pdf):
        abrir_pdf.return_value = self.documento([
            [[
                ['CONSULTA EM PEDIATRIA', '', '', '', '', '', ''],
                self.cabecalho,
                [
                    '01/04/2026', 'Ana Maria', '1990', '123456789012345',
                    'FEMININO', '100000001', '1',
                ],
            ]],
            [[[
                '02/04/2026', 'C.D.', '1985', '123********5678',
                'MASCULINO', '100000002', '2',
            ]]],
        ])

        registros = extrair_registros_pdf(
            SimpleUploadedFile('fila.pdf', b'%PDF-teste'),
            self.especialidade,
        )

        self.assertEqual(len(registros), 2)
        self.assertEqual(registros[0]['nome_mascarado'], 'A** M****')
        self.assertEqual(registros[0]['cns_mascarado'], '***********2345')
        self.assertEqual(registros[1]['posicao'], 2)

    @patch('ftc.services.importacao_fila.pdfplumber.open')
    def test_rejeita_especialidade_diferente_do_titulo(self, abrir_pdf):
        abrir_pdf.return_value = self.documento([[[
            ['CONSULTA EM CARDIOLOGIA', '', '', '', '', '', ''],
            self.cabecalho,
            [
                '01/04/2026', 'A.B.', '1990', '123********1234',
                'FEMININO', '100000001', '1',
            ],
        ]]])

        with self.assertRaisesMessage(
            ErroImportacaoPDF,
            'A especialidade selecionada nao corresponde ao titulo do PDF.',
        ):
            extrair_registros_pdf(
                SimpleUploadedFile('fila.pdf', b'%PDF-teste'),
                self.especialidade,
            )
