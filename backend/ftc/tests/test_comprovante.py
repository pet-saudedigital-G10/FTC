from datetime import date, datetime

from django.contrib.auth import get_user_model
from django.core.cache import cache
from django.urls import reverse
from django.utils import timezone
from rest_framework import status
from rest_framework.test import APITestCase

from ftc.models import Especialidade, Paciente, PublicacaoFila, RegistroFila
from ftc.selectors import SITUACOES_ATIVAS
from ftc.serializers import (
    ORIENTACAO_COMPROVANTE_POSICAO,
    RegistroFilaComprovanteSerializer,
    SISTEMA_IDENTIFICACAO_FTC,
)
from ftc.utils.masking import mask_cns, mask_cpf, mask_name


class RegistroFilaComprovanteTests(APITestCase):
    def setUp(self):
        cache.clear()
        User = get_user_model()
        self.password = 'SenhaForte123!'

        self.admin = User.objects.create_superuser(
            username='comprovante-admin',
            password=self.password,
        )
        self.staff_user = User.objects.create_user(
            username='servidor-comprovante',
            password=self.password,
            is_staff=True,
        )
        self.user_sem_paciente = User.objects.create_user(
            username='11122233344',
            password=self.password,
        )

        self.cpf_cidadao = '12345678901'
        self.cns_cidadao = '700123456789012'
        self.paciente = Paciente.objects.create(
            cpf=self.cpf_cidadao,
            cns=self.cns_cidadao,
            nome_completo='Joao da Silva',
            data_nascimento=date(1990, 5, 15),
            sexo=Paciente.Sexo.MASCULINO,
        )
        self.cidadao_user = User.objects.create_user(
            username=self.cpf_cidadao,
            password=self.password,
        )

        self.outro_cpf = '98765432100'
        self.outro_paciente = Paciente.objects.create(
            cpf=self.outro_cpf,
            cns='700987654321000',
            nome_completo='Maria Oliveira',
            data_nascimento=date(1985, 8, 20),
            sexo=Paciente.Sexo.FEMININO,
        )
        self.outro_cidadao_user = User.objects.create_user(
            username=self.outro_cpf,
            password=self.password,
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

        self.momento_publicacao = timezone.now()
        self.publicacao_arquivada = PublicacaoFila.objects.create(
            especialidade=self.pediatria,
            competencia=date(2026, 3, 1),
            versao=1,
            arquivo_original='filas/teste-arquivada.pdf',
            hash_arquivo='0' * 64,
            status=PublicacaoFila.Status.ARQUIVADA,
            importado_por=self.admin,
            publicada_em=self.momento_publicacao,
        )
        self.publicacao_publicada = PublicacaoFila.objects.create(
            especialidade=self.pediatria,
            competencia=date(2026, 4, 1),
            versao=2,
            arquivo_original='filas/teste-1.pdf',
            hash_arquivo='1' * 64,
            status=PublicacaoFila.Status.PUBLICADA,
            importado_por=self.admin,
            publicada_em=self.momento_publicacao,
        )
        self.publicacao_rascunho = PublicacaoFila.objects.create(
            especialidade=self.pediatria,
            competencia=date(2026, 5, 1),
            versao=1,
            arquivo_original='filas/teste-2.pdf',
            hash_arquivo='2' * 64,
            status=PublicacaoFila.Status.RASCUNHO,
            importado_por=self.admin,
        )

        self.registro_publicado = self._criar_registro(
            publicacao=self.publicacao_publicada,
            paciente=self.paciente,
            codigo='PED-100',
            posicao=1,
            situacao=RegistroFila.Situacao.SOLICITADO,
        )
        self.registro_rascunho = self._criar_registro(
            publicacao=self.publicacao_rascunho,
            paciente=self.paciente,
            codigo='PED-200',
            posicao=1,
            situacao=RegistroFila.Situacao.SOLICITADO,
        )
        self.registro_arquivado = self._criar_registro(
            publicacao=self.publicacao_arquivada,
            paciente=self.paciente,
            codigo='PED-050',
            posicao=1,
            situacao=RegistroFila.Situacao.SOLICITADO,
        )

        self.client.force_authenticate(user=self.cidadao_user)

    def _criar_registro(
        self,
        *,
        publicacao,
        paciente,
        codigo,
        posicao,
        situacao=RegistroFila.Situacao.SOLICITADO,
        prioridade=RegistroFila.Prioridade.NIVEL_1,
        tipo=RegistroFila.Tipo.SOLICITADAS,
        nome_mascarado=None,
        cpf_mascarado=None,
        cns_mascarado=None,
    ):
        nome = (
            nome_mascarado
            if nome_mascarado is not None
            else (
                mask_name(paciente.nome_completo)
                if paciente
                else mask_name('Paciente Sem Vinculo')
            )
        )
        cpf = (
            cpf_mascarado
            if cpf_mascarado is not None
            else (mask_cpf(paciente.cpf) if paciente and paciente.cpf else '')
        )
        cns = (
            cns_mascarado
            if cns_mascarado is not None
            else (
                mask_cns(paciente.cns)
                if paciente and paciente.cns
                else mask_cns('700000000009999')
            )
        )
        return RegistroFila.objects.create(
            publicacao=publicacao,
            paciente=paciente,
            data_solicitacao=date(2026, 4, 6),
            nome_mascarado=nome,
            ano_nascimento=1990,
            cpf_mascarado=cpf,
            cns_mascarado=cns,
            sexo=Paciente.Sexo.MASCULINO,
            codigo_solicitacao=codigo,
            posicao=posicao,
            prioridade=prioridade,
            tipo=tipo,
            situacao=situacao,
        )

    def _url(self, pk):
        return reverse('fila-registro-comprovante', kwargs={'pk': pk})

    # 1. Emissão para uma solicitação ativa com posição válida
    def test_emite_comprovante_para_solicitacao_ativa_com_posicao_valida(self):
        response = self.client.get(self._url(self.registro_publicado.pk))

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        data = response.json()

        self.assertEqual(data['sistema'], SISTEMA_IDENTIFICACAO_FTC)
        self.assertEqual(data['id'], self.registro_publicado.pk)
        self.assertEqual(data['codigo_solicitacao'], 'PED-100')
        self.assertEqual(data['posicao'], 1)
        self.assertEqual(data['especialidade_id'], self.pediatria.pk)
        self.assertEqual(data['especialidade_nome'], 'Pediatria')
        self.assertEqual(data['especialidade_slug'], 'consulta-pediatria')
        self.assertEqual(data['especialidade_tipo'], 'CONSULTA')
        self.assertEqual(data['especialidade_tipo_display'], 'Consulta')
        self.assertEqual(data['data_solicitacao'], '2026-04-06')
        self.assertEqual(data['prioridade'], 1)
        self.assertEqual(data['prioridade_display'], 'Prioridade 1')
        self.assertEqual(data['tipo'], 'SOLICITADAS')
        self.assertEqual(data['tipo_display'], 'Solicitadas')
        self.assertEqual(data['situacao'], 'SOLICITADO')
        self.assertEqual(data['situacao_display'], 'Solicitado')
        self.assertEqual(data['orientacao'], ORIENTACAO_COMPROVANTE_POSICAO)

    def test_emite_comprovante_para_situacoes_ativas_aguardando_atendimento(self):
        situacoes_elegiveis = [
            s for s in SITUACOES_ATIVAS if s != RegistroFila.Situacao.AGENDADO
        ]
        for indice, situacao_ativa in enumerate(situacoes_elegiveis, start=10):
            registro = self._criar_registro(
                publicacao=self.publicacao_publicada,
                paciente=self.paciente,
                codigo=f'ATIVO-{indice}',
                posicao=indice,
                situacao=situacao_ativa,
            )
            response = self.client.get(self._url(registro.pk))
            self.assertEqual(
                response.status_code,
                status.HTTP_200_OK,
                msg=f'Falha ao emitir comprovante para situacao ativa {situacao_ativa}',
            )
            self.assertEqual(response.data['posicao'], indice)
            self.assertEqual(response.data['situacao'], situacao_ativa)

    # 2. Bloqueio de solicitação cancelada
    def test_bloqueia_comprovante_para_solicitacao_cancelada(self):
        registro = self._criar_registro(
            publicacao=self.publicacao_publicada,
            paciente=self.paciente,
            codigo='PED-CANCELADO',
            posicao=2,
            situacao=RegistroFila.Situacao.CANCELADO,
        )

        response = self.client.get(self._url(registro.pk))

        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    # 3. Bloqueio de solicitação agendada
    def test_bloqueia_comprovante_para_solicitacao_agendada(self):
        registro = self._criar_registro(
            publicacao=self.publicacao_publicada,
            paciente=self.paciente,
            codigo='PED-AGENDADO',
            posicao=3,
            situacao=RegistroFila.Situacao.AGENDADO,
        )

        response = self.client.get(self._url(registro.pk))

        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    # 4. Bloqueio de solicitação indeferida (NEGADO e NEGADO_CRL)
    def test_bloqueia_comprovante_para_solicitacao_indeferida(self):
        registro_negado = self._criar_registro(
            publicacao=self.publicacao_publicada,
            paciente=self.paciente,
            codigo='PED-NEGADO',
            posicao=4,
            situacao=RegistroFila.Situacao.NEGADO,
        )
        registro_negado_crl = self._criar_registro(
            publicacao=self.publicacao_publicada,
            paciente=self.paciente,
            codigo='PED-NEGADO-CRL',
            posicao=5,
            situacao=RegistroFila.Situacao.NEGADO_CRL,
        )

        resp_negado = self.client.get(self._url(registro_negado.pk))
        resp_negado_crl = self.client.get(self._url(registro_negado_crl.pk))

        self.assertEqual(resp_negado.status_code, status.HTTP_404_NOT_FOUND)
        self.assertEqual(resp_negado_crl.status_code, status.HTTP_404_NOT_FOUND)

    # 5. Bloqueio de solicitação devolvida
    def test_bloqueia_comprovante_para_solicitacao_devolvida(self):
        registro = self._criar_registro(
            publicacao=self.publicacao_publicada,
            paciente=self.paciente,
            codigo='PED-DEVOLVIDO',
            posicao=6,
            situacao=RegistroFila.Situacao.DEVOLVIDO,
        )

        response = self.client.get(self._url(registro.pk))

        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    # 6. Bloqueio de qualquer outra situação não considerada ativa
    def test_bloqueia_comprovante_para_outras_situacoes_inativas(self):
        situacoes_inativas = set(RegistroFila.Situacao.values) - set(SITUACOES_ATIVAS)
        self.assertIn(RegistroFila.Situacao.BAIXADO_INTERNADO_CRL, situacoes_inativas)

        for indice, situacao_inativa in enumerate(sorted(situacoes_inativas), start=30):
            registro = self._criar_registro(
                publicacao=self.publicacao_publicada,
                paciente=self.paciente,
                codigo=f'INATIVO-{indice}',
                posicao=indice,
                situacao=situacao_inativa,
            )
            response = self.client.get(self._url(registro.pk))
            self.assertEqual(
                response.status_code,
                status.HTTP_404_NOT_FOUND,
                msg=f'Situacao inativa {situacao_inativa} nao deveria gerar comprovante',
            )

    # 7. Registro inexistente
    def test_retorna_404_para_registro_inexistente(self):
        response = self.client.get(self._url(999999))

        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    # 8. Registro sem posição válida
    def test_bloqueia_registro_sem_posicao_valida(self):
        registro_posicao_zero = self._criar_registro(
            publicacao=self.publicacao_publicada,
            paciente=self.paciente,
            codigo='PED-POS-ZERO',
            posicao=0,
            situacao=RegistroFila.Situacao.SOLICITADO,
        )

        response = self.client.get(self._url(registro_posicao_zero.pk))

        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    # 9. Registro associado a publicação em rascunho
    def test_retorna_404_para_registro_de_publicacao_em_rascunho(self):
        response = self.client.get(self._url(self.registro_rascunho.pk))

        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    # 10. Registro associado a publicação arquivada ou superada por publicação vigente
    def test_retorna_404_para_registro_de_publicacao_arquivada_ou_nao_vigente(self):
        resp_arquivada = self.client.get(self._url(self.registro_arquivado.pk))
        self.assertEqual(resp_arquivada.status_code, status.HTTP_404_NOT_FOUND)

        publicacao_antiga_publicada = PublicacaoFila.objects.create(
            especialidade=self.cardiologia,
            competencia=date(2026, 3, 1),
            versao=1,
            arquivo_original='filas/cardio-marco.pdf',
            hash_arquivo='3' * 64,
            status=PublicacaoFila.Status.PUBLICADA,
            importado_por=self.admin,
            publicada_em=self.momento_publicacao,
        )
        publicacao_vigente_cardio = PublicacaoFila.objects.create(
            especialidade=self.cardiologia,
            competencia=date(2026, 4, 1),
            versao=1,
            arquivo_original='filas/cardio-abril.pdf',
            hash_arquivo='4' * 64,
            status=PublicacaoFila.Status.PUBLICADA,
            importado_por=self.admin,
            publicada_em=self.momento_publicacao,
        )
        registro_antigo = self._criar_registro(
            publicacao=publicacao_antiga_publicada,
            paciente=self.paciente,
            codigo='CAR-ANTIGO',
            posicao=1,
            situacao=RegistroFila.Situacao.PENDENTE,
        )
        registro_vigente = self._criar_registro(
            publicacao=publicacao_vigente_cardio,
            paciente=self.paciente,
            codigo='CAR-VIGENTE',
            posicao=1,
            situacao=RegistroFila.Situacao.PENDENTE,
        )

        resp_antigo = self.client.get(self._url(registro_antigo.pk))
        resp_vigente = self.client.get(self._url(registro_vigente.pk))

        self.assertEqual(resp_antigo.status_code, status.HTTP_404_NOT_FOUND)
        self.assertEqual(resp_vigente.status_code, status.HTTP_200_OK)

    # 11. Cidadão tentando acessar solicitação de outro cidadão
    def test_bloqueia_cidadao_tentando_acessar_solicitacao_de_outro_cidadao(self):
        registro_outro = self._criar_registro(
            publicacao=self.publicacao_publicada,
            paciente=self.outro_paciente,
            codigo='PED-OUTRO',
            posicao=50,
            situacao=RegistroFila.Situacao.AGUARDANDO_REGULACAO,
        )

        response = self.client.get(self._url(registro_outro.pk))

        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    # 12. Usuário sem permissão
    def test_bloqueia_usuario_sem_permissao(self):
        self.client.force_authenticate(user=None)
        resp_anonimo = self.client.get(self._url(self.registro_publicado.pk))
        self.assertEqual(resp_anonimo.status_code, status.HTTP_401_UNAUTHORIZED)

        self.client.force_authenticate(user=self.staff_user)
        resp_staff = self.client.get(self._url(self.registro_publicado.pk))
        self.assertEqual(resp_staff.status_code, status.HTTP_403_FORBIDDEN)

        self.client.force_authenticate(user=self.user_sem_paciente)
        resp_sem_paciente = self.client.get(self._url(self.registro_publicado.pk))
        self.assertEqual(resp_sem_paciente.status_code, status.HTTP_403_FORBIDDEN)

    # 13. Registro importado sem paciente vinculado (paciente=None)
    def test_registro_importado_sem_paciente_vinculado(self):
        nome_esperado = mask_name('Ana Maria')
        cns_esperado = mask_cns('700000000001234')
        registro_sem_paciente = self._criar_registro(
            publicacao=self.publicacao_publicada,
            paciente=None,
            codigo='PDF-IMPORT-001',
            posicao=60,
            situacao=RegistroFila.Situacao.AGUARDANDO_REGULACAO,
            nome_mascarado=nome_esperado,
            cpf_mascarado='',
            cns_mascarado=cns_esperado,
        )

        response = self.client.get(self._url(registro_sem_paciente.pk))
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

        dados_serializados = RegistroFilaComprovanteSerializer(registro_sem_paciente).data
        self.assertEqual(dados_serializados['nome_mascarado'], nome_esperado)
        self.assertEqual(dados_serializados['cpf_mascarado'], '')
        self.assertEqual(dados_serializados['cns_mascarado'], cns_esperado)

    # 14. Dados pessoais retornados pelo endpoint (privacidade / mascaramento)
    def test_protege_dados_pessoais_e_nao_expoe_cpf_cns_ou_nome_completo(self):
        registro_dados_brutos = self._criar_registro(
            publicacao=self.publicacao_publicada,
            paciente=self.paciente,
            codigo='PED-PRIVACIDADE',
            posicao=70,
            situacao=RegistroFila.Situacao.SOLICITADO,
            nome_mascarado='Joao da Silva',
            cpf_mascarado='',
            cns_mascarado='',
        )

        response = self.client.get(self._url(registro_dados_brutos.pk))

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        data = response.json()

        self.assertNotIn('cpf', data)
        self.assertNotIn('cns', data)
        self.assertNotIn('nome_completo', data)
        self.assertNotIn('nome_paciente', data)

        self.assertEqual(data['nome_mascarado'], mask_name('Joao da Silva'))
        self.assertEqual(data['cpf_mascarado'], mask_cpf(self.cpf_cidadao))
        self.assertEqual(data['cns_mascarado'], mask_cns(self.cns_cidadao))
        self.assertNotIn(self.cpf_cidadao, str(data))
        self.assertNotIn(self.cns_cidadao, str(data))
        self.assertNotIn('Joao da Silva', str(data))

    # 15. Competência, versão e datas da publicação
    def test_retorna_competencia_versao_e_data_da_publicacao(self):
        response = self.client.get(self._url(self.registro_publicado.pk))

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        data = response.json()

        self.assertEqual(data['publicacao_id'], self.publicacao_publicada.pk)
        self.assertEqual(data['competencia'], '2026-04-01')
        self.assertEqual(data['versao'], 2)
        self.assertIsNotNone(data['publicada_em'])
        publicada_em = datetime.fromisoformat(data['publicada_em'])
        self.assertEqual(
            int(publicada_em.timestamp()),
            int(self.momento_publicacao.timestamp()),
        )

    # 16. Data e hora de emissão
    def test_retorna_data_e_hora_de_emissao_atual(self):
        antes = timezone.now()
        response = self.client.get(self._url(self.registro_publicado.pk))
        depois = timezone.now()

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        data = response.json()

        self.assertIn('emitido_em', data)
        emitido_em = datetime.fromisoformat(data['emitido_em'])
        self.assertGreaterEqual(emitido_em, antes)
        self.assertLessEqual(emitido_em, depois)
        self.assertNotIn('total_registros_fila', data)
        self.assertNotIn('total_ativos_fila', data)
