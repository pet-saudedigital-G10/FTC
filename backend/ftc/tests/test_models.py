from datetime import date

from django.contrib.auth import get_user_model
from django.db import IntegrityError, transaction
from django.test import TestCase

from ftc.models import Especialidade, Paciente, PublicacaoFila, RegistroFila
from ftc.utils.masking import mask_cns, mask_name


class FilaModelsTests(TestCase):
    def setUp(self):
        self.admin = get_user_model().objects.create_superuser(
            username='model-admin',
            password='SenhaForte123!',
        )
        self.pediatria = Especialidade.objects.create(
            nome='Pediatria',
            slug='consulta-pediatria',
            tipo=Especialidade.Tipo.CONSULTA,
        )

    def criar_publicacao(
        self,
        *,
        especialidade=None,
        competencia=date(2026, 4, 1),
        versao=1,
        status=PublicacaoFila.Status.RASCUNHO,
        hash_arquivo='a' * 64,
    ):
        return PublicacaoFila.objects.create(
            especialidade=especialidade or self.pediatria,
            competencia=competencia,
            versao=versao,
            arquivo_original=f'filas/fila-{hash_arquivo[:4]}.csv',
            hash_arquivo=hash_arquivo,
            status=status,
            importado_por=self.admin,
        )

    def test_paciente_usa_id_interno_e_documentos_unicos(self):
        paciente = Paciente.objects.create(
            cpf='12345678901',
            cns='700123456789012',
            nome_completo='Paciente Teste',
        )

        self.assertIsInstance(paciente.id, int)
        self.assertNotEqual(str(paciente.id), paciente.cpf)

        with self.assertRaises(IntegrityError), transaction.atomic():
            Paciente.objects.create(cpf=paciente.cpf)

        with self.assertRaises(IntegrityError), transaction.atomic():
            Paciente.objects.create(cns=paciente.cns)

    def test_paciente_precisa_ter_cpf_ou_cns(self):
        with self.assertRaises(IntegrityError), transaction.atomic():
            Paciente.objects.create(nome_completo='Sem documento')

    def test_especialidade_possui_varias_publicacoes(self):
        abril = self.criar_publicacao()
        maio = self.criar_publicacao(
            competencia=date(2026, 5, 1),
            hash_arquivo='b' * 64,
        )

        self.assertEqual(self.pediatria.publicacoes.count(), 2)
        self.assertEqual({abril.competencia, maio.competencia}, {
            date(2026, 4, 1),
            date(2026, 5, 1),
        })

    def test_registro_preserva_retrato_publico_da_fila(self):
        paciente = Paciente.objects.create(
            cpf='12345678901',
            cns='700123456787953',
            nome_completo='Nome Longo Da Silva',
        )
        publicacao = self.criar_publicacao()
        registro = RegistroFila.objects.create(
            publicacao=publicacao,
            paciente=paciente,
            data_solicitacao=date(2026, 4, 6),
            nome_mascarado=mask_name(paciente.nome_completo),
            ano_nascimento=2024,
            cns_mascarado=mask_cns(paciente.cns),
            sexo=Paciente.Sexo.MASCULINO,
            codigo_solicitacao='660399858',
            posicao=1,
            prioridade=RegistroFila.Prioridade.NIVEL_1,
            tipo=RegistroFila.Tipo.SOLICITADAS,
            situacao=RegistroFila.Situacao.SOLICITADO,
        )

        self.assertEqual(registro.publicacao.especialidade, self.pediatria)
        self.assertEqual(registro.paciente, paciente)
        self.assertEqual(registro.cns_mascarado, mask_cns(paciente.cns))
        self.assertEqual(registro.nome_mascarado, mask_name(paciente.nome_completo))
        self.assertEqual(registro.prioridade, RegistroFila.Prioridade.NIVEL_1)
        self.assertEqual(registro.tipo, RegistroFila.Tipo.SOLICITADAS)
        self.assertEqual(registro.situacao, RegistroFila.Situacao.SOLICITADO)

    def test_posicao_e_codigo_sao_unicos_em_cada_publicacao(self):
        publicacao = self.criar_publicacao()
        dados = {
            'publicacao': publicacao,
            'data_solicitacao': date(2026, 4, 6),
            'nome_mascarado': mask_name('Nome Longo Da Silva'),
            'codigo_solicitacao': '660399858',
            'posicao': 1,
        }
        RegistroFila.objects.create(**dados)


        with self.assertRaises(IntegrityError), transaction.atomic():
            RegistroFila.objects.create(**dados)

    def test_so_existe_uma_publicacao_ativa_por_competencia(self):
        self.criar_publicacao(status=PublicacaoFila.Status.PUBLICADA)

        with self.assertRaises(IntegrityError), transaction.atomic():
            self.criar_publicacao(
                versao=2,
                status=PublicacaoFila.Status.PUBLICADA,
                hash_arquivo='c' * 64,
            )
