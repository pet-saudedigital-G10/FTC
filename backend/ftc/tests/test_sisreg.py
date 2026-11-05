from datetime import date
from unittest.mock import MagicMock, patch

import requests
from django.contrib.auth import get_user_model
from django.core.cache import cache
from django.test import override_settings
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase

from ftc.models import Especialidade, Paciente, PublicacaoFila, RegistroFila


INDICE = 'solicitacao-ambulatorial-es-vitoria'
PENDENTE_REGULADOR = 'SOLICITAÇÃO / PENDENTE / REGULADOR'
PENDENTE_FILA = 'SOLICITAÇÃO / PENDENTE / FILA DE ESPERA'
REENVIADA = 'SOLICITAÇÃO / REENVIADA / REGULADOR'

sisreg_habilitado = override_settings(
    SISREG_ENABLED=True,
    SISREG_AMBIENTE='homologacao',
    SISREG_CLIENT_ID='1234567',
    SISREG_CLIENT_SECRET='segredo-de-teste',
    SISREG_INDICE=INDICE,
    SISREG_CENTRAIS_REGULADORAS=['32C164'],
    SISREG_PAGE_SIZE=2,
    SISREG_MAX_RECORDS=5,
)


def fonte(codigo, **campos):
    return {
        'codigo_solicitacao': codigo,
        'data_solicitacao': '2026-04-01T00:00:00.000000Z',
        'status_solicitacao': PENDENTE_REGULADOR,
        'codigo_classificacao_risco': 4,
        'codigo_grupo_procedimento': '0701001',
        'nome_grupo_procedimento': 'CONSULTA EM CARDIOLOGIA',
        'no_usuario': 'Maria da Silva',
        'cns_usuario': '700000000000001',
        'dt_nascimento_usuario': '1990-05-20T00:00:00.000000Z',
        'sexo_usuario': 'FEMININO',
        **campos,
    }


def resposta_http(status_code=200, corpo=None):
    resposta = MagicMock(status_code=status_code)
    resposta.json.return_value = corpo
    return resposta


def resposta_token(token='token-1', expires_in=300):
    return resposta_http(corpo={
        'access_token': token,
        'expires_in': expires_in,
        'token_type': 'Bearer',
    })


def resposta_busca(fontes, scroll_id='scroll-1', total=None, **dados):
    return resposta_http(corpo={
        'statusCode': 200,
        'message': 'Search result',
        'data': {
            'timed_out': False,
            '_shards': {'total': 6, 'successful': 6, 'skipped': 0, 'failed': 0},
            '_scroll_id': scroll_id,
            'hits': {
                'total': {
                    'value': len(fontes) if total is None else total,
                    'relation': 'eq',
                },
                'hits': [{'_id': str(i), '_source': f} for i, f in enumerate(fontes)],
            },
            **dados,
        },
    })


class SisregAPITestCase(APITestCase):
    def setUp(self):
        cache.clear()
        User = get_user_model()
        self.staff = User.objects.create_user(
            username='servidora.sisreg',
            password='SenhaForte123!',
            is_staff=True,
        )
        self.cidadao = User.objects.create_user(
            username='cidadao.sisreg',
            password='SenhaForte123!',
        )
        self.especialidade = Especialidade.objects.create(
            nome='Cardiologia',
            slug='consulta-cardiologia-sisreg',
            tipo=Especialidade.Tipo.CONSULTA,
        )
        self.client.force_authenticate(self.staff)

        patcher = patch('ftc.services.sisreg.requests.request')
        self.request = patcher.start()
        self.addCleanup(patcher.stop)

    def importar(self):
        return self.client.post(
            reverse('admin-sisreg-importar'),
            {
                'especialidade': self.especialidade.pk,
                'codigo_grupo_procedimento': '0701001',
            },
            format='json',
        )

    def fila_em_lote(self, *lotes):
        """Simula token, inicio do scroll, continuacoes e o lote final vazio."""
        return [
            resposta_token(),
            *[resposta_busca(lote) for lote in lotes],
            resposta_busca([]),
        ]


class SisregDesabilitadoTests(SisregAPITestCase):
    def test_vem_desabilitado_por_padrao(self):
        resposta = self.client.get(reverse('admin-sisreg-status'))

        self.assertEqual(resposta.status_code, status.HTTP_200_OK)
        self.assertEqual(
            resposta.data,
            {'habilitado': False, 'ambiente': None, 'indice': None},
        )

    def test_nao_chama_api_externa_quando_desabilitado(self):
        for nome in ('admin-sisreg-grupos', 'admin-sisreg-fila'):
            resposta = self.client.get(reverse(nome))
            self.assertEqual(resposta.status_code, status.HTTP_403_FORBIDDEN)

        self.assertEqual(self.importar().status_code, status.HTTP_403_FORBIDDEN)
        self.request.assert_not_called()


@sisreg_habilitado
class SisregPermissaoTests(SisregAPITestCase):
    def test_cidadao_nao_acessa(self):
        self.client.force_authenticate(self.cidadao)

        for nome in ('admin-sisreg-status', 'admin-sisreg-grupos', 'admin-sisreg-fila'):
            resposta = self.client.get(reverse(nome))
            self.assertEqual(resposta.status_code, status.HTTP_403_FORBIDDEN)

        self.assertEqual(self.importar().status_code, status.HTTP_403_FORBIDDEN)
        self.request.assert_not_called()

    def test_anonimo_nao_acessa(self):
        self.client.force_authenticate(None)

        resposta = self.client.get(reverse('admin-sisreg-fila'))

        self.assertEqual(resposta.status_code, status.HTTP_401_UNAUTHORIZED)
        self.request.assert_not_called()

    def test_status_nao_expoe_credenciais(self):
        resposta = self.client.get(reverse('admin-sisreg-status'))

        self.assertEqual(
            resposta.data,
            {'habilitado': True, 'ambiente': 'homologacao', 'indice': INDICE},
        )
        self.assertNotIn('segredo-de-teste', str(resposta.content))


@sisreg_habilitado
class SisregClienteTests(SisregAPITestCase):
    def test_autentica_conforme_o_manual(self):
        self.request.side_effect = [resposta_token(), resposta_busca([fonte(1)])]

        resposta = self.client.get(reverse('admin-sisreg-fila'))

        self.assertEqual(resposta.status_code, status.HTTP_200_OK)
        token, busca = self.request.call_args_list
        self.assertEqual(token.args[0], 'POST')
        self.assertEqual(
            token.args[1],
            'https://sso-hom.saude.gov.br/realms/portal-servicos/protocol/'
            'openid-connect/token',
        )
        self.assertEqual(token.kwargs['data'], {
            'grant_type': 'client_credentials',
            'client_id': '1234567',
            'client_secret': 'segredo-de-teste',
        })
        self.assertEqual(busca.args[0], 'GET')
        self.assertEqual(
            busca.args[1],
            f'https://servicos-es-hmg.saude.gov.br/SISREG/{INDICE}/_search',
        )
        self.assertEqual(
            busca.kwargs['headers'],
            {'SSOAuthorization': 'Bearer token-1'},
        )

    def test_nao_segue_redirecionamentos(self):
        self.request.side_effect = [resposta_token(), resposta_busca([])]

        self.client.get(reverse('admin-sisreg-fila'))

        for chamada in self.request.call_args_list:
            self.assertIs(chamada.kwargs['allow_redirects'], False)
            self.assertEqual(chamada.kwargs['timeout'], 30)

    def test_reutiliza_token_valido(self):
        self.request.side_effect = [
            resposta_token(),
            resposta_busca([]),
            resposta_busca([]),
        ]

        self.client.get(reverse('admin-sisreg-fila'))
        self.client.get(reverse('admin-sisreg-fila'))

        self.assertEqual(self.request.call_count, 3)

    def test_renova_token_expirado_uma_vez(self):
        self.request.side_effect = [
            resposta_token('token-1'),
            resposta_http(401),
            resposta_token('token-2'),
            resposta_busca([]),
        ]

        resposta = self.client.get(reverse('admin-sisreg-fila'))

        self.assertEqual(resposta.status_code, status.HTTP_200_OK)
        self.assertEqual(
            self.request.call_args.kwargs['headers'],
            {'SSOAuthorization': 'Bearer token-2'},
        )

    def test_nao_repete_quando_401_persiste(self):
        self.request.side_effect = [
            resposta_token('token-1'),
            resposta_http(401),
            resposta_token('token-2'),
            resposta_http(401),
        ]

        resposta = self.client.get(reverse('admin-sisreg-fila'))

        self.assertEqual(resposta.status_code, status.HTTP_502_BAD_GATEWAY)
        self.assertEqual(self.request.call_count, 4)

    def test_credencial_recusada_nao_vaza_resposta_externa(self):
        self.request.return_value = resposta_http(400, {'error': 'segredo-externo'})

        resposta = self.client.get(reverse('admin-sisreg-fila'))

        self.assertEqual(resposta.status_code, status.HTTP_502_BAD_GATEWAY)
        self.assertEqual(
            resposta.data['detail'],
            'O SISREG recusou as credenciais configuradas.',
        )
        self.assertNotIn('segredo-externo', str(resposta.content))

    def test_falha_de_conexao_vira_erro_seguro(self):
        self.request.side_effect = requests.ConnectionError('sso-hom:443 recusou')

        resposta = self.client.get(reverse('admin-sisreg-fila'))

        self.assertEqual(resposta.status_code, status.HTTP_502_BAD_GATEWAY)
        self.assertEqual(
            resposta.data['detail'],
            'Não foi possível conectar ao SISREG.',
        )

    def test_credencial_sem_permissao_no_indice(self):
        self.request.side_effect = [resposta_token(), resposta_http(403)]

        resposta = self.client.get(reverse('admin-sisreg-fila'))

        self.assertEqual(resposta.status_code, status.HTTP_502_BAD_GATEWAY)
        self.assertIn('permissão', resposta.data['detail'])


@sisreg_habilitado
class SisregConsultaTests(SisregAPITestCase):
    def test_consulta_usa_filtros_da_fila_e_minimiza_campos(self):
        self.request.side_effect = [resposta_token(), resposta_busca([fonte(1)])]

        self.client.get(reverse('admin-sisreg-fila'), {'grupo': '0701001', 'pagina': 2})

        corpo = self.request.call_args.kwargs['json']
        filtros = corpo['query']['bool']['must']
        self.assertEqual(corpo['from'], 50)
        self.assertEqual(corpo['size'], 50)
        self.assertIn(
            {
                'terms': {
                    'status_solicitacao.keyword': [
                        PENDENTE_FILA,
                        PENDENTE_REGULADOR,
                        REENVIADA,
                    ],
                },
            },
            filtros,
        )
        self.assertIn({'terms': {'codigo_tipo_regulacao': ['R', 'F']}}, filtros)
        self.assertIn({'terms': {'codigo_central_reguladora': ['32C164']}}, filtros)
        self.assertIn({'terms': {'codigo_grupo_procedimento': ['0701001']}}, filtros)
        for campo in ('cpf_usuario', 'no_mae_usuario', 'telefone'):
            self.assertNotIn(campo, corpo['_source'])

    def test_devolve_dados_mascarados(self):
        self.request.side_effect = [
            resposta_token(),
            resposta_busca([fonte(101, codigo_classificacao_risco=2)], total=120),
        ]

        resposta = self.client.get(reverse('admin-sisreg-fila'))

        self.assertEqual(resposta.data['total'], 120)
        registro = resposta.data['registros'][0]
        self.assertEqual(registro['codigo_solicitacao'], '101')
        self.assertEqual(registro['nome_mascarado'], 'M**** d* S****')
        self.assertEqual(registro['cns_mascarado'], '***********0001')
        self.assertEqual(registro['data_solicitacao'], '2026-04-01')
        self.assertEqual(registro['classificacao_risco'], 'Prioridade 1 - Urgência')
        self.assertEqual(registro['situacao_display'], 'Aguardando regulação')
        self.assertNotIn('Maria', str(resposta.content))
        self.assertNotIn('700000000000001', str(resposta.content))

    def test_consulta_nao_grava_registros(self):
        self.request.side_effect = [resposta_token(), resposta_busca([fonte(1)])]

        self.client.get(reverse('admin-sisreg-fila'))

        self.assertFalse(PublicacaoFila.objects.exists())

    def test_rejeita_grupo_invalido_sem_chamar_api(self):
        resposta = self.client.get(
            reverse('admin-sisreg-fila'),
            {'grupo': '0701001"}]'},
        )

        self.assertEqual(resposta.status_code, status.HTTP_400_BAD_REQUEST)
        self.request.assert_not_called()

    def test_rejeita_pagina_alem_do_limite_do_opensearch(self):
        resposta = self.client.get(reverse('admin-sisreg-fila'), {'pagina': 201})

        self.assertEqual(resposta.status_code, status.HTTP_400_BAD_REQUEST)
        self.request.assert_not_called()

    def test_resposta_parcial_e_rejeitada(self):
        self.request.side_effect = [
            resposta_token(),
            resposta_busca(
                [fonte(1)],
                _shards={'total': 6, 'successful': 5, 'skipped': 0, 'failed': 1},
            ),
        ]

        resposta = self.client.get(reverse('admin-sisreg-fila'))

        self.assertEqual(resposta.status_code, status.HTTP_502_BAD_GATEWAY)

    def test_lista_grupos_percorrendo_o_scroll(self):
        self.request.side_effect = self.fila_em_lote(
            [
                fonte(1),
                fonte(
                    2,
                    codigo_grupo_procedimento='0701002',
                    nome_grupo_procedimento='CONSULTA EM ALERGOLOGIA',
                ),
            ],
            [fonte(3)],
        )

        resposta = self.client.get(reverse('admin-sisreg-grupos'))

        self.assertEqual(resposta.data['total'], 3)
        self.assertEqual(
            [dict(grupo) for grupo in resposta.data['grupos']],
            [
                {
                    'codigo': '0701002',
                    'nome': 'CONSULTA EM ALERGOLOGIA',
                    'total': 1,
                },
                {
                    'codigo': '0701001',
                    'nome': 'CONSULTA EM CARDIOLOGIA',
                    'total': 2,
                },
            ],
        )
        continuacao = self.request.call_args
        self.assertEqual(continuacao.args[0], 'POST')
        self.assertEqual(
            continuacao.args[1],
            'https://servicos-es-hmg.saude.gov.br/SISREG/_search/scroll',
        )
        self.assertEqual(
            continuacao.kwargs['json'],
            {'scroll': '5m', 'scroll_id': 'scroll-1'},
        )


@sisreg_habilitado
class SisregImportacaoTests(SisregAPITestCase):
    def publicada_atual(self):
        return PublicacaoFila.objects.get(
            especialidade=self.especialidade,
            status=PublicacaoFila.Status.PUBLICADA,
        )

    def test_publica_fila_com_posicoes_por_risco_e_antiguidade(self):
        self.request.side_effect = self.fila_em_lote([
            fonte(10, data_solicitacao='2026-01-10T00:00:00.000000Z'),
            fonte(
                20,
                data_solicitacao='2026-03-01T00:00:00.000000Z',
                codigo_classificacao_risco=1,
            ),
        ], [
            fonte(
                30,
                data_solicitacao='2026-02-01T00:00:00.000000Z',
                codigo_classificacao_risco=3,
                status_solicitacao=PENDENTE_FILA,
            ),
            fonte(
                40,
                data_solicitacao='2026-01-20T00:00:00.000000Z',
                codigo_classificacao_risco=3,
                status_solicitacao=REENVIADA,
            ),
        ])

        resposta = self.importar()

        self.assertEqual(resposta.status_code, status.HTTP_201_CREATED)
        self.assertEqual(resposta.data['registros_importados'], 4)
        publicacao = self.publicada_atual()
        self.assertEqual(publicacao.origem, PublicacaoFila.Origem.SISREG)
        self.assertEqual(publicacao.importado_por, self.staff)
        self.assertFalse(publicacao.arquivo_original)

        registros = list(publicacao.registros.order_by('posicao'))
        self.assertEqual(
            [
                (r.posicao, r.codigo_solicitacao, r.prioridade, r.situacao)
                for r in registros
            ],
            [
                (1, '20', 1, RegistroFila.Situacao.AGUARDANDO_REGULACAO),
                (2, '40', 2, RegistroFila.Situacao.REENVIADO),
                (3, '30', 2, RegistroFila.Situacao.PENDENTE),
                (4, '10', 3, RegistroFila.Situacao.AGUARDANDO_REGULACAO),
            ],
        )
        self.assertEqual(registros[0].data_solicitacao, date(2026, 3, 1))
        self.assertEqual(registros[0].tipo, RegistroFila.Tipo.PENDENTES)

    def test_filtra_pelo_grupo_e_pede_scroll(self):
        self.request.side_effect = self.fila_em_lote([fonte(1)])

        self.importar()

        inicio = self.request.call_args_list[1]
        self.assertEqual(inicio.kwargs['params'], {'scroll': '5m'})
        self.assertEqual(inicio.kwargs['json']['size'], 2)
        self.assertIn(
            {'terms': {'codigo_grupo_procedimento': ['0701001']}},
            inicio.kwargs['json']['query']['bool']['must'],
        )

    def test_grava_apenas_dados_mascarados(self):
        self.request.side_effect = self.fila_em_lote([
            fonte(1, cpf_usuario='10000000001'),
        ])

        self.importar()

        registro = RegistroFila.objects.get()
        self.assertEqual(registro.nome_mascarado, 'M**** d* S****')
        self.assertEqual(registro.cns_mascarado, '***********0001')
        self.assertEqual(registro.cpf_mascarado, '')
        self.assertEqual(registro.ano_nascimento, 1990)
        self.assertEqual(registro.sexo, 'F')
        self.assertFalse(Paciente.objects.exists())

    def test_vincula_paciente_existente_por_cns_ou_cpf(self):
        por_cns = Paciente.objects.create(cns='700000000000001')
        por_cpf = Paciente.objects.create(cpf='10000000002')
        self.request.side_effect = self.fila_em_lote([
            fonte(1),
            fonte(2, cns_usuario='700000000000002', cpf_usuario='10000000002'),
            fonte(3, cns_usuario='700000000000003', cpf_usuario=None),
        ])

        self.importar()

        self.assertEqual(
            RegistroFila.objects.get(codigo_solicitacao='1').paciente,
            por_cns,
        )
        self.assertEqual(
            RegistroFila.objects.get(codigo_solicitacao='2').paciente,
            por_cpf,
        )
        self.assertIsNone(RegistroFila.objects.get(codigo_solicitacao='3').paciente)

    def test_campos_opcionais_ausentes_nao_bloqueiam_a_fila(self):
        self.request.side_effect = self.fila_em_lote([
            fonte(
                1,
                no_usuario=None,
                cns_usuario=None,
                dt_nascimento_usuario=None,
                sexo_usuario=None,
                codigo_classificacao_risco=None,
            ),
        ])

        resposta = self.importar()

        self.assertEqual(resposta.status_code, status.HTTP_201_CREATED)
        registro = RegistroFila.objects.get()
        self.assertEqual(registro.nome_mascarado, '')
        self.assertIsNone(registro.ano_nascimento)
        self.assertEqual(registro.sexo, 'N')
        self.assertEqual(registro.prioridade, 3)

    def test_solicitacao_repetida_ocupa_uma_posicao(self):
        self.request.side_effect = self.fila_em_lote([fonte(1), fonte(1), fonte(2)])

        resposta = self.importar()

        self.assertEqual(resposta.status_code, status.HTTP_201_CREATED)
        self.assertEqual(resposta.data['registros_importados'], 2)

    def test_arquiva_publicacao_anterior_e_incrementa_versao(self):
        self.request.side_effect = [
            *self.fila_em_lote([fonte(1)]),
            resposta_busca([fonte(1), fonte(2)]),
            resposta_busca([]),
        ]

        self.importar()
        primeira = self.publicada_atual()
        resposta = self.importar()

        self.assertEqual(resposta.status_code, status.HTTP_201_CREATED)
        self.assertEqual(resposta.data['versao'], primeira.versao + 1)
        self.assertEqual(resposta.data['publicacoes_substituidas'], [primeira.pk])
        primeira.refresh_from_db()
        self.assertEqual(primeira.status, PublicacaoFila.Status.ARQUIVADA)

    def test_fila_identica_nao_gera_nova_publicacao(self):
        self.request.side_effect = [
            *self.fila_em_lote([fonte(1)]),
            resposta_busca([fonte(1)]),
            resposta_busca([]),
        ]

        self.importar()
        resposta = self.importar()

        self.assertEqual(resposta.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(
            resposta.data['detail'],
            ['A fila publicada já está igual à do SISREG.'],
        )
        self.assertEqual(PublicacaoFila.objects.count(), 1)

    def test_fila_pode_voltar_a_um_estado_ja_publicado(self):
        self.request.side_effect = [
            *self.fila_em_lote([fonte(1)]),
            resposta_busca([fonte(1), fonte(2)]),
            resposta_busca([]),
            resposta_busca([fonte(1)]),
            resposta_busca([]),
        ]

        self.importar()
        self.importar()
        resposta = self.importar()

        self.assertEqual(resposta.status_code, status.HTTP_201_CREATED)
        self.assertEqual(self.publicada_atual().versao, 3)

    def assertFilaVigenteIntacta(self, resposta, status_code):
        self.assertEqual(resposta.status_code, status_code)
        publicacao = self.publicada_atual()
        self.assertEqual(publicacao.versao, 1)
        self.assertEqual(PublicacaoFila.objects.count(), 1)
        self.assertEqual(publicacao.registros.count(), 1)

    def test_falha_no_meio_do_scroll_preserva_fila_vigente(self):
        self.request.side_effect = [
            *self.fila_em_lote([fonte(1)]),
            resposta_busca([fonte(1), fonte(2)]),
            resposta_http(500),
        ]

        self.importar()
        resposta = self.importar()

        self.assertFilaVigenteIntacta(resposta, status.HTTP_502_BAD_GATEWAY)

    def test_fila_vazia_preserva_fila_vigente(self):
        self.request.side_effect = [
            *self.fila_em_lote([fonte(1)]),
            resposta_busca([]),
        ]

        self.importar()
        resposta = self.importar()

        self.assertFilaVigenteIntacta(resposta, status.HTTP_400_BAD_REQUEST)

    def test_registro_invalido_preserva_fila_vigente(self):
        for campos in (
            {'data_solicitacao': 'ontem'},
            {'status_solicitacao': 'AGENDAMENTO / CONFIRMADO / EXECUTANTE'},
            {'codigo_solicitacao': None},
        ):
            with self.subTest(campos=campos):
                PublicacaoFila.objects.all().delete()
                cache.clear()
                self.request.side_effect = [
                    *self.fila_em_lote([fonte(1)]),
                    resposta_busca([fonte(2), fonte(3, **campos)]),
                    resposta_busca([]),
                ]

                self.importar()
                resposta = self.importar()

                self.assertFilaVigenteIntacta(
                    resposta,
                    status.HTTP_400_BAD_REQUEST,
                )

    def test_rejeita_fila_acima_do_limite(self):
        self.request.side_effect = self.fila_em_lote(
            [fonte(1), fonte(2)],
            [fonte(3), fonte(4)],
            [fonte(5), fonte(6)],
        )

        resposta = self.importar()

        self.assertEqual(resposta.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertFalse(PublicacaoFila.objects.exists())

    def test_rejeita_especialidade_inativa(self):
        self.especialidade.ativo = False
        self.especialidade.save(update_fields=['ativo'])

        resposta = self.importar()

        self.assertEqual(resposta.status_code, status.HTTP_400_BAD_REQUEST)
        self.request.assert_not_called()

    def test_fila_importada_aparece_na_api_publica(self):
        self.request.side_effect = self.fila_em_lote([fonte(1)])
        self.importar()
        self.client.force_authenticate(None)

        resposta = self.client.get(reverse('fila-registro-list'))

        self.assertEqual(len(resposta.data), 1)
        self.assertEqual(resposta.data[0]['nome_mascarado'], 'M**** d* S****')
        self.assertNotIn('Maria', str(resposta.content))
