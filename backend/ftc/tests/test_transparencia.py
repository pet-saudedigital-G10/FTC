from datetime import date, timedelta
from unittest.mock import patch

from django.core.cache import cache
from django.urls import reverse
from django.utils import timezone
from rest_framework import status
from rest_framework.test import APITestCase
from rest_framework.throttling import ScopedRateThrottle

from ftc.models import Especialidade, Paciente, PublicacaoFila, RegistroFila


class TransparenciaTestCase(APITestCase):
    def setUp(self):
        cache.clear()
        self.hoje = timezone.localdate()
        self.cardiologia = Especialidade.objects.create(
            nome='Cardiologia',
            slug='consulta-cardiologia-transparencia',
            tipo=Especialidade.Tipo.CONSULTA,
        )
        self.ultrassom = Especialidade.objects.create(
            nome='Ultrassonografia',
            slug='exame-ultrassom-transparencia',
            tipo=Especialidade.Tipo.EXAME,
        )
        self.publicacao = self.publicar(self.cardiologia, date(2026, 5, 1), 'a')
        self.exames = self.publicar(self.ultrassom, date(2026, 5, 1), 'b')
        self.paciente = Paciente.objects.create(
            cpf='10000000001',
            cns='700000000000001',
            nome_completo='Maria da Silva',
        )
        self.registro(self.publicacao, '101', 1, 10, paciente=self.paciente)
        self.registro(self.publicacao, '102', 2, 20, prioridade=1)
        self.registro(
            self.exames,
            '201',
            1,
            60,
            situacao=RegistroFila.Situacao.PENDENTE,
        )

    def publicar(self, especialidade, competencia, letra, **campos):
        return PublicacaoFila.objects.create(
            especialidade=especialidade,
            competencia=competencia,
            hash_arquivo=letra * 64,
            status=PublicacaoFila.Status.PUBLICADA,
            publicada_em=timezone.now(),
            **campos,
        )

    def registro(self, publicacao, codigo, posicao, dias, **campos):
        dados = {
            'nome_mascarado': 'M**** d* S****',
            'cns_mascarado': '***********0001',
            'cpf_mascarado': '***.***.***-01',
            'ano_nascimento': 1990,
            'situacao': RegistroFila.Situacao.AGUARDANDO_REGULACAO,
            **campos,
        }
        return RegistroFila.objects.create(
            publicacao=publicacao,
            codigo_solicitacao=codigo,
            posicao=posicao,
            data_solicitacao=self.hoje - timedelta(days=dias),
            **dados,
        )


class IndicadoresTests(TransparenciaTestCase):
    url_nome = 'transparencia-indicadores'

    def indicadores(self):
        cache.clear()
        resposta = self.client.get(reverse(self.url_nome))
        self.assertEqual(resposta.status_code, status.HTTP_200_OK)
        return resposta.json()

    def test_calcula_quantidades_e_medias(self):
        dados = self.indicadores()

        self.assertEqual(dados['total_aguardando'], 3)
        self.assertEqual(dados['especialidades_com_fila'], 2)
        self.assertEqual(dados['espera_media_dias'], 30.0)
        self.assertEqual(dados['maior_espera_dias'], 60)
        self.assertEqual(dados['especialidades'], [
            {
                'nome': 'Cardiologia',
                'tipo': 'Consulta',
                'total': 2,
                'espera_media_dias': 15.0,
                'maior_espera_dias': 20,
            },
            {
                'nome': 'Ultrassonografia',
                'tipo': 'Exame',
                'total': 1,
                'espera_media_dias': 60.0,
                'maior_espera_dias': 60,
            },
        ])
        self.assertEqual(
            [(item['rotulo'], item['total']) for item in dados['por_tipo']],
            [('Consulta', 2), ('Exame', 1)],
        )
        self.assertEqual(
            [(item['valor'], item['total']) for item in dados['por_prioridade']],
            [(1, 1), (3, 2)],
        )
        self.assertEqual(
            {item['rotulo']: item['total'] for item in dados['por_situacao']},
            {'Aguardando regulação': 2, 'Pendente': 1},
        )

    def test_nao_expoe_dados_pessoais(self):
        resposta = self.client.get(reverse(self.url_nome))

        conteudo = resposta.content.decode()
        for dado in ('M****', '0001', '10000000001', '1990', 'codigo_solicitacao'):
            self.assertNotIn(dado, conteudo)

    def test_ignora_publicacao_arquivada_e_situacao_encerrada(self):
        arquivada = PublicacaoFila.objects.create(
            especialidade=self.cardiologia,
            competencia=date(2026, 4, 1),
            hash_arquivo='c' * 64,
            status=PublicacaoFila.Status.ARQUIVADA,
        )
        self.registro(arquivada, '301', 1, 500)
        self.registro(
            self.publicacao,
            '103',
            3,
            500,
            situacao=RegistroFila.Situacao.CANCELADO,
        )

        dados = self.indicadores()

        self.assertEqual(dados['total_aguardando'], 3)
        self.assertEqual(dados['maior_espera_dias'], 60)

    def test_conta_somente_a_publicacao_mais_recente(self):
        antiga = self.publicar(self.cardiologia, date(2026, 1, 1), 'd')
        self.registro(antiga, '401', 1, 900)

        dados = self.indicadores()

        self.assertEqual(dados['total_aguardando'], 3)

    def test_sem_filas_nao_quebra(self):
        RegistroFila.objects.all().delete()
        PublicacaoFila.objects.all().delete()

        dados = self.indicadores()

        self.assertEqual(dados['total_aguardando'], 0)
        self.assertIsNone(dados['espera_media_dias'])
        self.assertIsNone(dados['atualizado_em'])

    def test_resposta_fica_em_cache(self):
        url = reverse(self.url_nome)
        self.client.get(url)

        with self.assertNumQueries(0):
            resposta = self.client.get(url)

        self.assertEqual(resposta.status_code, status.HTTP_200_OK)

    def test_token_vencido_nao_bloqueia_painel(self):
        self.client.credentials(HTTP_AUTHORIZATION='Bearer token-vencido')

        resposta = self.client.get(reverse(self.url_nome))

        self.assertEqual(resposta.status_code, status.HTTP_200_OK)

    def test_muitos_visitantes_nao_sao_bloqueados(self):
        url = reverse(self.url_nome)

        respostas = [self.client.get(url).status_code for _ in range(150)]

        self.assertEqual(set(respostas), {status.HTTP_200_OK})


class PosicaoTests(TransparenciaTestCase):
    def consultar(self, **dados):
        return self.client.post(
            reverse('transparencia-posicao'),
            {'codigo_solicitacao': '101', 'ano_nascimento': 1990, **dados},
            format='json',
        )

    def test_consulta_por_codigo_e_ano_de_nascimento(self):
        resposta = self.consultar()

        self.assertEqual(resposta.status_code, status.HTTP_200_OK)
        self.assertIs(resposta.data['encontrado'], True)
        fila = resposta.data['filas'][0]
        self.assertEqual(fila['especialidade'], 'Cardiologia')
        self.assertEqual(fila['posicao'], 1)
        self.assertEqual(fila['total_aguardando'], 2)
        self.assertEqual(fila['dias_espera'], 10)
        self.assertEqual(fila['situacao'], 'Aguardando regulação')

    def test_resposta_nao_tem_dados_pessoais(self):
        conteudo = self.consultar().content.decode()

        for dado in ('M****', 'Maria', '0001', '10000000001', '1990'):
            self.assertNotIn(dado, conteudo)

    def test_funciona_sem_paciente_vinculado(self):
        resposta = self.consultar(codigo_solicitacao='102')

        self.assertIs(resposta.data['encontrado'], True)

    def test_respostas_negativas_sao_identicas(self):
        ano_errado = self.consultar(ano_nascimento=1991)
        codigo_errado = self.consultar(codigo_solicitacao='999')

        self.assertEqual(ano_errado.status_code, status.HTTP_200_OK)
        self.assertEqual(ano_errado.data, {'encontrado': False, 'filas': []})
        self.assertEqual(ano_errado.data, codigo_errado.data)

    def test_cpf_nao_consulta_posicao(self):
        resposta = self.consultar(codigo_solicitacao='10000000001')

        self.assertIs(resposta.data['encontrado'], False)

    def test_nao_encontra_solicitacao_encerrada_ou_arquivada(self):
        self.registro(
            self.publicacao,
            '103',
            3,
            5,
            situacao=RegistroFila.Situacao.CANCELADO,
        )
        arquivada = PublicacaoFila.objects.create(
            especialidade=self.cardiologia,
            competencia=date(2026, 4, 1),
            hash_arquivo='c' * 64,
            status=PublicacaoFila.Status.ARQUIVADA,
        )
        self.registro(arquivada, '301', 1, 5)

        for codigo in ('103', '301'):
            self.assertIs(
                self.consultar(codigo_solicitacao=codigo).data['encontrado'],
                False,
            )

    def test_rejeita_entradas_invalidas(self):
        casos = (
            {'codigo_solicitacao': ''},
            {'codigo_solicitacao': "1' OR '1'='1"},
            {'ano_nascimento': 'abc'},
            {'ano_nascimento': 1500},
        )
        for dados in casos:
            with self.subTest(dados=dados):
                self.assertEqual(
                    self.consultar(**dados).status_code,
                    status.HTTP_400_BAD_REQUEST,
                )

    def test_corpo_que_nao_e_objeto_nao_gera_erro_500(self):
        resposta = self.client.post(
            reverse('transparencia-posicao'),
            [],
            format='json',
        )

        self.assertEqual(resposta.status_code, status.HTTP_400_BAD_REQUEST)

    def test_limita_tentativas(self):
        with patch.dict(
            ScopedRateThrottle.THROTTLE_RATES,
            {'transparencia_posicao': '3/minute'},
        ):
            respostas = [self.consultar().status_code for _ in range(4)]

        self.assertEqual(respostas[-1], status.HTTP_429_TOO_MANY_REQUESTS)
