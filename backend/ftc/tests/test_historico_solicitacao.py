import shutil
import tempfile
from datetime import date, datetime, timezone as dt_timezone
from unittest.mock import MagicMock, patch

from django.contrib.auth import get_user_model
from django.core.cache import cache
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import override_settings
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase

from ftc.models import Especialidade, Paciente, PublicacaoFila, RegistroFila
from ftc.utils.masking import mask_cns, mask_cpf, mask_name


CABECALHO_PDF = [
    'DATA DA SOLICITACAO',
    'NOME DO USUARIO',
    'ANO DE NASCIMENTO DO USUARIO',
    'CNS DO USUARIO',
    'SEXO DO USUARIO',
    'COD. SOLICITACAO',
    'POSICAO NA FILA',
]


def _mock_documento_pdf(linhas_dados, titulo='CONSULTA EM PEDIATRIA'):
    pagina = MagicMock()
    pagina.extract_tables.return_value = [[
        [titulo, '', '', '', '', '', ''],
        CABECALHO_PDF,
        *linhas_dados,
    ]]
    documento = MagicMock()
    documento.pages = [pagina]
    contexto = MagicMock()
    contexto.__enter__.return_value = documento
    return contexto


class AssociacaoPacienteImportacaoPDFTests(APITestCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.media_dir = tempfile.mkdtemp(prefix='ftc-test-hist-media-')
        cls.settings_override = override_settings(MEDIA_ROOT=cls.media_dir)
        cls.settings_override.enable()

    @classmethod
    def tearDownClass(cls):
        cls.settings_override.disable()
        shutil.rmtree(cls.media_dir, ignore_errors=True)
        super().tearDownClass()

    def setUp(self):
        cache.clear()
        User = get_user_model()
        self.staff = User.objects.create_user(
            username='servidor.regulacao',
            password='SenhaForte123!',
            is_staff=True,
        )
        self.pediatria = Especialidade.objects.create(
            nome='Pediatria',
            slug='consulta-pediatria-hist',
            tipo=Especialidade.Tipo.CONSULTA,
        )
        self.cardiologia = Especialidade.objects.create(
            nome='Cardiologia',
            slug='consulta-cardiologia-hist',
            tipo=Especialidade.Tipo.CONSULTA,
        )
        self.paciente_1 = Paciente.objects.create(
            cpf='11122233344',
            cns='700000000001234',
            nome_completo='Maria José da Silva',
            sexo=Paciente.Sexo.FEMININO,
        )
        self.paciente_2 = Paciente.objects.create(
            cpf='55566677788',
            cns='800000000001234',
            nome_completo='Marta Joana de Souza',
            sexo=Paciente.Sexo.FEMININO,
        )
        self.user_cidadao_1 = User.objects.create_user(
            username=self.paciente_1.cpf,
            password='SenhaCidadao123!',
        )

    def _arquivo_pdf(self, sufixo='1'):
        return SimpleUploadedFile(
            f'fila-{sufixo}.pdf',
            f'%PDF-conteudo-{sufixo}'.encode('utf-8'),
            content_type='application/pdf',
        )

    @patch('ftc.services.importacao_fila.pdfplumber.open')
    def test_associacao_por_cns_completo_15_digitos_antes_do_mascaramento(
        self,
        abrir_pdf,
    ):
        abrir_pdf.return_value = _mock_documento_pdf([
            [
                '10/03/2026',
                'Maria Jose da Silva',
                '1990',
                '700000000001234',
                'FEMININO',
                '100001001',
                '1',
            ],
        ])
        self.client.force_authenticate(user=self.staff)

        resposta = self.client.post(
            reverse('admin-fila-atualizar'),
            {
                'arquivo': self._arquivo_pdf('cns-completo'),
                'especialidade': self.pediatria.pk,
                'competencia': '2026-04',
            },
            format='multipart',
        )

        self.assertEqual(resposta.status_code, status.HTTP_201_CREATED)
        registro = RegistroFila.objects.get(
            publicacao_id=resposta.data['publicacao_id'],
            codigo_solicitacao='100001001',
        )
        self.assertEqual(registro.paciente, self.paciente_1)
        self.assertEqual(registro.cns_mascarado, '***********1234')
        self.assertEqual(registro.cpf_mascarado, mask_cpf(self.paciente_1.cpf))

    @patch('ftc.services.importacao_fila.pdfplumber.open')
    def test_heranca_segura_de_vinculo_entre_publicacoes_com_cns_mascarado(
        self,
        abrir_pdf,
    ):
        pub_anterior = PublicacaoFila.objects.create(
            especialidade=self.pediatria,
            competencia=date(2026, 3, 1),
            versao=1,
            arquivo_original='filas/marco.pdf',
            hash_arquivo='1' * 64,
            status=PublicacaoFila.Status.PUBLICADA,
            importado_por=self.staff,
        )
        reg_anterior = RegistroFila.objects.create(
            publicacao=pub_anterior,
            paciente=self.paciente_1,
            data_solicitacao=date(2026, 3, 10),
            nome_mascarado=mask_name(self.paciente_1.nome_completo),
            ano_nascimento=1990,
            cpf_mascarado=mask_cpf(self.paciente_1.cpf),
            cns_mascarado=mask_cns(self.paciente_1.cns),
            sexo=Paciente.Sexo.FEMININO,
            codigo_solicitacao='100001001',
            posicao=5,
            situacao=RegistroFila.Situacao.SOLICITADO,
        )

        abrir_pdf.return_value = _mock_documento_pdf([
            [
                '10/03/2026',
                'M. J. D. S.',
                '1990',
                '700********1234',
                'FEMININO',
                '100001001',
                '2',
            ],
        ])
        self.client.force_authenticate(user=self.staff)

        resposta = self.client.post(
            reverse('admin-fila-atualizar'),
            {
                'arquivo': self._arquivo_pdf('heranca-segura'),
                'especialidade': self.pediatria.pk,
                'competencia': '2026-04',
            },
            format='multipart',
        )

        self.assertEqual(resposta.status_code, status.HTTP_201_CREATED)
        reg_novo = RegistroFila.objects.get(
            publicacao_id=resposta.data['publicacao_id'],
            codigo_solicitacao='100001001',
        )
        self.assertEqual(reg_novo.paciente, self.paciente_1)
        self.assertEqual(reg_novo.posicao, 2)

        # Verifica preservacao do registro anterior e arquivamento da publicacao
        pub_anterior.refresh_from_db()
        reg_anterior.refresh_from_db()
        self.assertEqual(pub_anterior.status, PublicacaoFila.Status.ARQUIVADA)
        self.assertEqual(reg_anterior.paciente, self.paciente_1)
        self.assertEqual(reg_anterior.posicao, 5)
        self.assertEqual(reg_anterior.situacao, RegistroFila.Situacao.SOLICITADO)

    @patch('ftc.services.importacao_fila.pdfplumber.open')
    def test_ausencia_de_associacao_por_dados_mascarados_sem_vinculo_anterior(
        self,
        abrir_pdf,
    ):
        # Mesmo com cns_mascarado final 1234, iniciais, ano e sexo compativeis
        # com paciente_1 e paciente_2, nunca deve associar sem vinculo anterior
        abrir_pdf.return_value = _mock_documento_pdf([
            [
                '10/03/2026',
                'M. J. D. S.',
                '1990',
                '***********1234',
                'FEMININO',
                '100001002',
                '1',
            ],
        ])
        self.client.force_authenticate(user=self.staff)

        resposta = self.client.post(
            reverse('admin-fila-atualizar'),
            {
                'arquivo': self._arquivo_pdf('sem-hist'),
                'especialidade': self.pediatria.pk,
                'competencia': '2026-04',
            },
            format='multipart',
        )

        self.assertEqual(resposta.status_code, status.HTTP_201_CREATED)
        registro = RegistroFila.objects.get(
            publicacao_id=resposta.data['publicacao_id'],
            codigo_solicitacao='100001002',
        )
        self.assertIsNone(registro.paciente)

    @patch('ftc.services.importacao_fila.pdfplumber.open')
    def test_ausencia_de_associacao_quando_houver_ambiguidade_entre_publicacoes(
        self,
        abrir_pdf,
    ):
        pub_1 = PublicacaoFila.objects.create(
            especialidade=self.pediatria,
            competencia=date(2026, 2, 1),
            versao=1,
            arquivo_original='filas/fev.pdf',
            hash_arquivo='2' * 64,
            status=PublicacaoFila.Status.ARQUIVADA,
            importado_por=self.staff,
        )
        pub_2 = PublicacaoFila.objects.create(
            especialidade=self.pediatria,
            competencia=date(2026, 3, 1),
            versao=1,
            arquivo_original='filas/mar.pdf',
            hash_arquivo='3' * 64,
            status=PublicacaoFila.Status.PUBLICADA,
            importado_por=self.staff,
        )
        # Dois pacientes distintos associados ao mesmo codigo na mesma especialidade
        RegistroFila.objects.create(
            publicacao=pub_1,
            paciente=self.paciente_1,
            data_solicitacao=date(2026, 2, 10),
            nome_mascarado='M. J.',
            cns_mascarado='***********1234',
            codigo_solicitacao='100001003',
            posicao=4,
        )
        RegistroFila.objects.create(
            publicacao=pub_2,
            paciente=self.paciente_2,
            data_solicitacao=date(2026, 2, 10),
            nome_mascarado='M. J.',
            cns_mascarado='***********1234',
            codigo_solicitacao='100001003',
            posicao=2,
        )

        abrir_pdf.return_value = _mock_documento_pdf([
            [
                '10/02/2026',
                'M. J.',
                '1990',
                '***********1234',
                'FEMININO',
                '100001003',
                '1',
            ],
        ])
        self.client.force_authenticate(user=self.staff)

        resposta = self.client.post(
            reverse('admin-fila-atualizar'),
            {
                'arquivo': self._arquivo_pdf('ambigua'),
                'especialidade': self.pediatria.pk,
                'competencia': '2026-04',
            },
            format='multipart',
        )

        self.assertEqual(resposta.status_code, status.HTTP_201_CREATED)
        novo_registro = RegistroFila.objects.get(
            publicacao_id=resposta.data['publicacao_id'],
            codigo_solicitacao='100001003',
        )
        self.assertIsNone(novo_registro.paciente)

    @patch('ftc.services.importacao_fila.pdfplumber.open')
    def test_ausencia_de_associacao_quando_registro_anterior_for_de_outra_especialidade(
        self,
        abrir_pdf,
    ):
        pub_cardio = PublicacaoFila.objects.create(
            especialidade=self.cardiologia,
            competencia=date(2026, 3, 1),
            versao=1,
            arquivo_original='filas/cardio.pdf',
            hash_arquivo='4' * 64,
            status=PublicacaoFila.Status.PUBLICADA,
            importado_por=self.staff,
        )
        RegistroFila.objects.create(
            publicacao=pub_cardio,
            paciente=self.paciente_1,
            data_solicitacao=date(2026, 3, 10),
            nome_mascarado='M. J.',
            cns_mascarado='***********1234',
            codigo_solicitacao='100001004',
            posicao=1,
        )

        abrir_pdf.return_value = _mock_documento_pdf([
            [
                '10/03/2026',
                'M. J.',
                '1990',
                '***********1234',
                'FEMININO',
                '100001004',
                '1',
            ],
        ])
        self.client.force_authenticate(user=self.staff)

        resposta = self.client.post(
            reverse('admin-fila-atualizar'),
            {
                'arquivo': self._arquivo_pdf('outra-esp'),
                'especialidade': self.pediatria.pk,
                'competencia': '2026-04',
            },
            format='multipart',
        )

        self.assertEqual(resposta.status_code, status.HTTP_201_CREATED)
        novo_registro = RegistroFila.objects.get(
            publicacao_id=resposta.data['publicacao_id'],
            codigo_solicitacao='100001004',
        )
        self.assertIsNone(novo_registro.paciente)

    @patch('ftc.services.importacao_fila.pdfplumber.open')
    def test_ausencia_de_associacao_quando_houver_divergencia_de_cns_ou_data(
        self,
        abrir_pdf,
    ):
        pub_anterior = PublicacaoFila.objects.create(
            especialidade=self.pediatria,
            competencia=date(2026, 3, 1),
            versao=1,
            arquivo_original='filas/marco-div.pdf',
            hash_arquivo='5' * 64,
            status=PublicacaoFila.Status.PUBLICADA,
            importado_por=self.staff,
        )
        RegistroFila.objects.create(
            publicacao=pub_anterior,
            paciente=self.paciente_1,
            data_solicitacao=date(2026, 3, 10),
            nome_mascarado='M. J.',
            cns_mascarado='***********1234',
            codigo_solicitacao='100001005',
            posicao=1,
        )
        RegistroFila.objects.create(
            publicacao=pub_anterior,
            paciente=self.paciente_1,
            data_solicitacao=date(2026, 3, 10),
            nome_mascarado='M. J.',
            cns_mascarado='***********1234',
            codigo_solicitacao='100001006',
            posicao=2,
        )
        RegistroFila.objects.create(
            publicacao=pub_anterior,
            paciente=self.paciente_1,
            data_solicitacao=date(2026, 3, 10),
            nome_mascarado='M. J.',
            cns_mascarado='***********1234',
            codigo_solicitacao='100001007',
            posicao=3,
        )

        abrir_pdf.return_value = _mock_documento_pdf([
            # Divergencia de data_solicitacao (11/03/2026 vs 10/03/2026)
            [
                '11/03/2026',
                'M. J.',
                '1990',
                '***********1234',
                'FEMININO',
                '100001005',
                '1',
            ],
            # Divergencia de cns_mascarado (9999 vs 1234)
            [
                '10/03/2026',
                'M. J.',
                '1990',
                '***********9999',
                'FEMININO',
                '100001006',
                '2',
            ],
            # Conflito de vinculo: CNS completo de paciente_2 para solicitacao de paciente_1
            [
                '10/03/2026',
                'M. J.',
                '1990',
                '800000000001234',
                'FEMININO',
                '100001007',
                '3',
            ],
        ])
        self.client.force_authenticate(user=self.staff)

        resposta = self.client.post(
            reverse('admin-fila-atualizar'),
            {
                'arquivo': self._arquivo_pdf('divergencias'),
                'especialidade': self.pediatria.pk,
                'competencia': '2026-04',
            },
            format='multipart',
        )

        self.assertEqual(resposta.status_code, status.HTTP_201_CREATED)
        pub_nova_id = resposta.data['publicacao_id']
        for codigo in ('100001005', '100001006', '100001007'):
            reg = RegistroFila.objects.get(
                publicacao_id=pub_nova_id,
                codigo_solicitacao=codigo,
            )
            self.assertIsNone(reg.paciente, f'{codigo} nao deveria associar paciente.')

        # Garante que o vinculo anterior nao foi sobrescrito
        reg_antigo = RegistroFila.objects.get(
            publicacao=pub_anterior,
            codigo_solicitacao='100001007',
        )
        self.assertEqual(reg_antigo.paciente, self.paciente_1)

    @patch('ftc.services.importacao_fila.pdfplumber.open')
    def test_regressao_endpoints_cidadao_e_consulta_posicao_apos_importacao_pdf(
        self,
        abrir_pdf,
    ):
        pub_marco = PublicacaoFila.objects.create(
            especialidade=self.pediatria,
            competencia=date(2026, 3, 1),
            versao=1,
            arquivo_original='filas/marco-reg.pdf',
            hash_arquivo='6' * 64,
            status=PublicacaoFila.Status.PUBLICADA,
            importado_por=self.staff,
        )
        RegistroFila.objects.create(
            publicacao=pub_marco,
            paciente=self.paciente_1,
            data_solicitacao=date(2026, 3, 5),
            nome_mascarado=mask_name(self.paciente_1.nome_completo),
            cpf_mascarado=mask_cpf(self.paciente_1.cpf),
            cns_mascarado=mask_cns(self.paciente_1.cns),
            codigo_solicitacao='100001008',
            posicao=10,
            situacao=RegistroFila.Situacao.SOLICITADO,
        )

        abrir_pdf.return_value = _mock_documento_pdf([
            [
                '05/03/2026',
                'M. J. D. S.',
                '1990',
                '***********1234',
                'FEMININO',
                '100001008',
                '3',
            ],
        ])
        self.client.force_authenticate(user=self.staff)
        import_resp = self.client.post(
            reverse('admin-fila-atualizar'),
            {
                'arquivo': self._arquivo_pdf('abril-reg'),
                'especialidade': self.pediatria.pk,
                'competencia': '2026-04',
            },
            format='multipart',
        )
        self.assertEqual(import_resp.status_code, status.HTTP_201_CREATED)

        # 1. Consulta publica de posicao por CPF (POST /api/filas/posicao/)
        self.client.force_authenticate(user=None)
        pos_resp = self.client.post(
            reverse('fila-posicao'),
            {'cpf': self.paciente_1.cpf},
            format='json',
        )
        self.assertEqual(pos_resp.status_code, status.HTTP_200_OK)
        self.assertTrue(pos_resp.data['encontrado'])
        self.assertEqual(len(pos_resp.data['filas']), 1)
        self.assertEqual(pos_resp.data['filas'][0]['posicao'], 3)

        # 2. Listagem de filas do cidadao autenticado (GET /api/cidadao/filas/)
        self.client.force_authenticate(user=self.user_cidadao_1)
        cid_resp = self.client.get(reverse('cidadao-filas'))
        self.assertEqual(cid_resp.status_code, status.HTTP_200_OK)
        self.assertEqual(len(cid_resp.data), 1)
        self.assertEqual(cid_resp.data[0]['codigo_solicitacao'], '100001008')
        self.assertEqual(cid_resp.data[0]['posicao'], 3)

        # 3. Comprovante de posicao (GET /api/filas/registros/<pk>/comprovante/)
        novo_reg_id = cid_resp.data[0]['id']
        comp_resp = self.client.get(
            reverse('fila-registro-comprovante', kwargs={'pk': novo_reg_id})
        )
        self.assertEqual(comp_resp.status_code, status.HTTP_200_OK)
        self.assertEqual(comp_resp.data['posicao'], 3)


class HistoricoSolicitacaoAPITests(APITestCase):
    def setUp(self):
        cache.clear()
        self.password = 'SenhaCidadao123!'
        self.cpf = '12345678901'
        self.outro_cpf = '98765432100'

        self.paciente = Paciente.objects.create(
            cpf=self.cpf,
            cns='700123456789012',
            nome_completo='Maria José da Silva',
            sexo=Paciente.Sexo.FEMININO,
        )
        self.outro_paciente = Paciente.objects.create(
            cpf=self.outro_cpf,
            cns='700987654321098',
            nome_completo='João Carlos Pereira',
            sexo=Paciente.Sexo.MASCULINO,
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
            username='servidor.historico',
            password=self.password,
            is_staff=True,
        )
        self.sem_paciente_user = User.objects.create_user(
            username='11122233344',
            password=self.password,
        )

        self.pediatria = Especialidade.objects.create(
            nome='Pediatria',
            slug='consulta-pediatria-historico',
            tipo=Especialidade.Tipo.CONSULTA,
        )
        self.cardiologia = Especialidade.objects.create(
            nome='Cardiologia',
            slug='consulta-cardiologia-historico',
            tipo=Especialidade.Tipo.CONSULTA,
        )

        self.pub_marco = PublicacaoFila.objects.create(
            especialidade=self.pediatria,
            competencia=date(2026, 3, 1),
            versao=1,
            arquivo_original='filas/ped-2026-03-v1.pdf',
            hash_arquivo='a' * 64,
            status=PublicacaoFila.Status.ARQUIVADA,
            importado_por=self.staff_user,
            publicada_em=datetime(2026, 3, 2, 10, 0, tzinfo=dt_timezone.utc),
            observacao='Observacao interna administrativa de marco.',
        )
        self.pub_abril_v1 = PublicacaoFila.objects.create(
            especialidade=self.pediatria,
            competencia=date(2026, 4, 1),
            versao=1,
            arquivo_original='filas/ped-2026-04-v1.pdf',
            hash_arquivo='b' * 64,
            status=PublicacaoFila.Status.ARQUIVADA,
            importado_por=self.staff_user,
            publicada_em=datetime(2026, 4, 2, 10, 0, tzinfo=dt_timezone.utc),
            observacao='Observacao interna administrativa de abril v1.',
        )
        self.pub_abril_v2 = PublicacaoFila.objects.create(
            especialidade=self.pediatria,
            competencia=date(2026, 4, 1),
            versao=2,
            arquivo_original='filas/ped-2026-04-v2.pdf',
            hash_arquivo='c' * 64,
            status=PublicacaoFila.Status.ARQUIVADA,
            importado_por=self.staff_user,
            publicada_em=datetime(2026, 4, 15, 14, 30, tzinfo=dt_timezone.utc),
            observacao='Observacao interna administrativa de abril v2.',
        )
        self.pub_maio = PublicacaoFila.objects.create(
            especialidade=self.pediatria,
            competencia=date(2026, 5, 1),
            versao=1,
            arquivo_original='filas/ped-2026-05-v1.pdf',
            hash_arquivo='d' * 64,
            status=PublicacaoFila.Status.PUBLICADA,
            importado_por=self.staff_user,
            publicada_em=datetime(2026, 5, 2, 9, 0, tzinfo=dt_timezone.utc),
            observacao='Observacao interna administrativa de maio.',
        )
        self.pub_junho_rascunho = PublicacaoFila.objects.create(
            especialidade=self.pediatria,
            competencia=date(2026, 6, 1),
            versao=1,
            arquivo_original='filas/ped-2026-06-v1.pdf',
            hash_arquivo='e' * 64,
            status=PublicacaoFila.Status.RASCUNHO,
            importado_por=self.staff_user,
            publicada_em=None,
            observacao='Rascunho interno.',
        )

        # Cria registros fora de ordem de insercao no banco para provar ordenacao
        # cronologica crescente (mais antiga -> mais recente)
        self.reg_maio = self._criar_registro(
            publicacao=self.pub_maio,
            paciente=self.paciente,
            codigo='PED-SOL-001',
            posicao=2,
            prioridade=RegistroFila.Prioridade.NIVEL_1,
            tipo=RegistroFila.Tipo.PENDENTES,
            situacao=RegistroFila.Situacao.AGUARDANDO_REGULACAO,
        )
        self.reg_marco = self._criar_registro(
            publicacao=self.pub_marco,
            paciente=self.paciente,
            codigo='PED-SOL-001',
            posicao=15,
            prioridade=RegistroFila.Prioridade.NIVEL_2,
            tipo=RegistroFila.Tipo.SOLICITADAS,
            situacao=RegistroFila.Situacao.SOLICITADO,
        )
        self.reg_abril_v2 = self._criar_registro(
            publicacao=self.pub_abril_v2,
            paciente=self.paciente,
            codigo='PED-SOL-001',
            posicao=5,
            prioridade=RegistroFila.Prioridade.NIVEL_1,
            tipo=RegistroFila.Tipo.PENDENTES,
            situacao=RegistroFila.Situacao.REENVIADO,
        )
        self.reg_abril_v1 = self._criar_registro(
            publicacao=self.pub_abril_v1,
            paciente=self.paciente,
            codigo='PED-SOL-001',
            posicao=9,
            prioridade=RegistroFila.Prioridade.NIVEL_2,
            tipo=RegistroFila.Tipo.PENDENTES,
            situacao=RegistroFila.Situacao.PENDENTE,
        )
        self.reg_rascunho = self._criar_registro(
            publicacao=self.pub_junho_rascunho,
            paciente=self.paciente,
            codigo='PED-SOL-001',
            posicao=1,
            prioridade=RegistroFila.Prioridade.NIVEL_1,
            tipo=RegistroFila.Tipo.BAIXADAS,
            situacao=RegistroFila.Situacao.AGENDADO,
        )

    def _criar_registro(
        self,
        *,
        publicacao,
        paciente,
        codigo,
        posicao,
        prioridade=RegistroFila.Prioridade.NIVEL_2,
        tipo=RegistroFila.Tipo.SOLICITADAS,
        situacao=RegistroFila.Situacao.SOLICITADO,
        data_solicitacao=date(2026, 2, 20),
    ):
        return RegistroFila.objects.create(
            publicacao=publicacao,
            paciente=paciente,
            data_solicitacao=data_solicitacao,
            nome_mascarado=(
                mask_name(paciente.nome_completo)
                if paciente
                else 'P******* S** V******'
            ),
            ano_nascimento=1990,
            cpf_mascarado=mask_cpf(paciente.cpf) if paciente else '***.***.***-00',
            cns_mascarado=mask_cns(paciente.cns) if paciente else '***********0000',
            sexo=paciente.sexo if paciente else Paciente.Sexo.NAO_INFORMADO,
            codigo_solicitacao=codigo,
            posicao=posicao,
            prioridade=prioridade,
            tipo=tipo,
            situacao=situacao,
        )

    def _url(self, pk):
        return reverse('fila-registro-historico', kwargs={'pk': pk})

    def test_historico_retorna_multiplas_publicacoes_em_ordem_cronologica_crescente(self):
        self.client.force_authenticate(user=self.user)

        response = self.client.get(self._url(self.reg_maio.pk))

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['id'], self.reg_maio.pk)
        self.assertEqual(response.data['codigo_solicitacao'], 'PED-SOL-001')
        self.assertEqual(response.data['data_solicitacao'], '2026-02-20')
        self.assertEqual(response.data['especialidade_id'], self.pediatria.pk)
        self.assertEqual(response.data['especialidade_nome'], 'Pediatria')
        self.assertEqual(response.data['especialidade_slug'], 'consulta-pediatria-historico')
        self.assertEqual(response.data['especialidade_tipo'], 'CONSULTA')
        self.assertEqual(response.data['especialidade_tipo_display'], 'Consulta')
        self.assertEqual(
            response.data['nome_mascarado'],
            mask_name(self.paciente.nome_completo),
        )
        self.assertEqual(
            response.data['cpf_mascarado'],
            mask_cpf(self.paciente.cpf),
        )
        self.assertEqual(
            response.data['cns_mascarado'],
            mask_cns(self.paciente.cns),
        )

        historico = response.data['historico']
        # Deve conter as 4 publicacoes oficiais (3 arquivadas + 1 publicada),
        # excluindo o rascunho de junho, na ordem mais antiga -> mais recente
        self.assertEqual(len(historico), 4)
        self.assertEqual(
            [item['id'] for item in historico],
            [
                self.reg_marco.pk,
                self.reg_abril_v1.pk,
                self.reg_abril_v2.pk,
                self.reg_maio.pk,
            ],
        )
        self.assertEqual(
            [(item['competencia'], item['versao'], item['posicao']) for item in historico],
            [
                ('2026-03-01', 1, 15),
                ('2026-04-01', 1, 9),
                ('2026-04-01', 2, 5),
                ('2026-05-01', 1, 2),
            ],
        )
        self.assertEqual(
            [item['situacao'] for item in historico],
            [
                RegistroFila.Situacao.SOLICITADO,
                RegistroFila.Situacao.PENDENTE,
                RegistroFila.Situacao.REENVIADO,
                RegistroFila.Situacao.AGUARDANDO_REGULACAO,
            ],
        )
        self.assertEqual(
            [item['status_publicacao'] for item in historico],
            [
                PublicacaoFila.Status.ARQUIVADA,
                PublicacaoFila.Status.ARQUIVADA,
                PublicacaoFila.Status.ARQUIVADA,
                PublicacaoFila.Status.PUBLICADA,
            ],
        )

        # Diferenciacao clara entre data_solicitacao e publicada_em
        for item in historico:
            self.assertEqual(item['data_solicitacao'], '2026-02-20')
            self.assertIsNotNone(item['publicada_em'])
            self.assertNotEqual(item['publicada_em'][:10], item['data_solicitacao'])

    def test_exclusao_de_rascunhos_na_consulta_direta_e_na_lista_de_historico(self):
        self.client.force_authenticate(user=self.user)

        # Consultar diretamente o pk de um registro em RASCUNHO deve retornar 404
        rascunho_resp = self.client.get(self._url(self.reg_rascunho.pk))
        self.assertEqual(rascunho_resp.status_code, status.HTTP_404_NOT_FOUND)

        # E o rascunho nunca deve aparecer no historico da solicitacao
        ok_resp = self.client.get(self._url(self.reg_maio.pk))
        ids_publicacoes = [item['publicacao_id'] for item in ok_resp.data['historico']]
        self.assertNotIn(self.pub_junho_rascunho.pk, ids_publicacoes)

    def test_solicitacoes_finalizadas_ou_inativas_preservam_visualizacao_do_historico(self):
        self.client.force_authenticate(user=self.user)

        situacoes_finais = (
            RegistroFila.Situacao.AGENDADO,
            RegistroFila.Situacao.CANCELADO,
            RegistroFila.Situacao.NEGADO,
            RegistroFila.Situacao.DEVOLVIDO,
            RegistroFila.Situacao.BAIXADO_INTERNADO_CRL,
            RegistroFila.Situacao.NEGADO_CRL,
        )

        for indice, situacao_final in enumerate(situacoes_finais, start=20):
            with self.subTest(situacao=situacao_final):
                codigo = f'SOL-FINAL-{indice}'
                reg_antigo = self._criar_registro(
                    publicacao=self.pub_abril_v2,
                    paciente=self.paciente,
                    codigo=codigo,
                    posicao=indice + 10,
                    situacao=RegistroFila.Situacao.AGUARDANDO_REGULACAO,
                )
                reg_final = self._criar_registro(
                    publicacao=self.pub_maio,
                    paciente=self.paciente,
                    codigo=codigo,
                    posicao=indice,
                    tipo=RegistroFila.Tipo.BAIXADAS,
                    situacao=situacao_final,
                )

                response = self.client.get(self._url(reg_final.pk))
                self.assertEqual(response.status_code, status.HTTP_200_OK)
                self.assertEqual(
                    [item['id'] for item in response.data['historico']],
                    [reg_antigo.pk, reg_final.pk],
                )
                self.assertEqual(
                    response.data['historico'][-1]['situacao'],
                    situacao_final,
                )

    def test_isolamento_entre_cidadaos_e_registros_sem_paciente(self):
        # Registro de outro paciente na mesma publicacao
        reg_outro = self._criar_registro(
            publicacao=self.pub_maio,
            paciente=self.outro_paciente,
            codigo='OUTRO-SOL-001',
            posicao=30,
        )
        # Registro sem paciente (paciente=None) com mesmo codigo_solicitacao em outra publicacao
        pub_fev = PublicacaoFila.objects.create(
            especialidade=self.pediatria,
            competencia=date(2026, 2, 1),
            versao=1,
            arquivo_original='filas/ped-2026-02.pdf',
            hash_arquivo='f' * 64,
            status=PublicacaoFila.Status.ARQUIVADA,
            importado_por=self.staff_user,
        )
        reg_orfao_mesmo_codigo = self._criar_registro(
            publicacao=pub_fev,
            paciente=None,
            codigo='PED-SOL-001',
            posicao=40,
        )
        # Registro de outro paciente em outra publicacao com mesmo codigo_solicitacao
        pub_jan = PublicacaoFila.objects.create(
            especialidade=self.pediatria,
            competencia=date(2026, 1, 1),
            versao=1,
            arquivo_original='filas/ped-2026-01.pdf',
            hash_arquivo='9' * 64,
            status=PublicacaoFila.Status.ARQUIVADA,
            importado_por=self.staff_user,
        )
        reg_colisao_outro_paciente = self._criar_registro(
            publicacao=pub_jan,
            paciente=self.outro_paciente,
            codigo='PED-SOL-001',
            posicao=50,
        )

        self.client.force_authenticate(user=self.user)

        # 1. Nao pode acessar registro inicial de outro cidadao
        resp_outro = self.client.get(self._url(reg_outro.pk))
        self.assertEqual(resp_outro.status_code, status.HTTP_404_NOT_FOUND)

        # 2. Nao pode acessar registro inicial orfao (paciente=None)
        resp_orfao = self.client.get(self._url(reg_orfao_mesmo_codigo.pk))
        self.assertEqual(resp_orfao.status_code, status.HTTP_404_NOT_FOUND)

        # 3. Ao consultar sua propria solicitacao (PED-SOL-001), o historico exige
        # paciente_id igual ao cidadao autenticado em TODOS os registros retornados
        resp_proprio = self.client.get(self._url(self.reg_maio.pk))
        self.assertEqual(resp_proprio.status_code, status.HTTP_200_OK)
        ids_retornados = [item['id'] for item in resp_proprio.data['historico']]
        self.assertNotIn(reg_orfao_mesmo_codigo.pk, ids_retornados)
        self.assertNotIn(reg_colisao_outro_paciente.pk, ids_retornados)

        # 4. Nao mistura registros com mesmo codigo_solicitacao de outra especialidade
        pub_cardio = PublicacaoFila.objects.create(
            especialidade=self.cardiologia,
            competencia=date(2026, 3, 1),
            versao=1,
            arquivo_original='filas/cardio-2026-03.pdf',
            hash_arquivo='8' * 64,
            status=PublicacaoFila.Status.PUBLICADA,
            importado_por=self.staff_user,
        )
        reg_outra_esp = self._criar_registro(
            publicacao=pub_cardio,
            paciente=self.paciente,
            codigo='PED-SOL-001',
            posicao=1,
        )
        resp_proprio_apos_cardio = self.client.get(self._url(self.reg_maio.pk))
        ids_apos_cardio = [item['id'] for item in resp_proprio_apos_cardio.data['historico']]
        self.assertNotIn(reg_outra_esp.pk, ids_apos_cardio)

    def test_autenticacao_e_autorizacao_exigem_is_citizen(self):
        # Anonimo -> 401
        anon_resp = self.client.get(self._url(self.reg_maio.pk))
        self.assertEqual(anon_resp.status_code, status.HTTP_401_UNAUTHORIZED)

        # Staff -> 403
        self.client.force_authenticate(user=self.staff_user)
        staff_resp = self.client.get(self._url(self.reg_maio.pk))
        self.assertEqual(staff_resp.status_code, status.HTTP_403_FORBIDDEN)

        # Usuario sem Paciente vinculado -> 403
        self.client.force_authenticate(user=self.sem_paciente_user)
        sem_pac_resp = self.client.get(self._url(self.reg_maio.pk))
        self.assertEqual(sem_pac_resp.status_code, status.HTTP_403_FORBIDDEN)

    def test_nao_expoe_dados_administrativos_ou_documentos_sem_mascaramento(self):
        self.client.force_authenticate(user=self.user)
        response = self.client.get(self._url(self.reg_maio.pk))

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        payload_str = str(response.data)

        # Dados pessoais em texto claro nao podem aparecer
        self.assertNotIn(self.paciente.cpf, payload_str)
        self.assertNotIn(self.paciente.cns, payload_str)
        self.assertNotIn(self.paciente.nome_completo, payload_str)

        # Metadados administrativos da publicacao nao podem aparecer
        campos_proibidos = {
            'importado_por',
            'importado_em',
            'arquivo_original',
            'hash_arquivo',
            'observacao',
            'paciente',
            'paciente_id',
        }
        self.assertTrue(campos_proibidos.isdisjoint(response.data.keys()))
        for item in response.data['historico']:
            self.assertTrue(campos_proibidos.isdisjoint(item.keys()))
        self.assertNotIn('Observacao interna administrativa', payload_str)

    def test_endpoint_e_somente_leitura(self):
        self.client.force_authenticate(user=self.user)
        url = self._url(self.reg_maio.pk)

        for metodo in ('post', 'put', 'patch', 'delete'):
            with self.subTest(metodo=metodo):
                resposta = getattr(self.client, metodo)(url, {}, format='json')
                self.assertEqual(
                    resposta.status_code,
                    status.HTTP_405_METHOD_NOT_ALLOWED,
                )
