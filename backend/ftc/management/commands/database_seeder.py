import hashlib
from datetime import date

from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand
from django.db import transaction
from django.utils import timezone

from ftc.models import Especialidade, Paciente, PublicacaoFila, RegistroFila
from ftc.utils.masking import mask_cns, mask_cpf, mask_name


COMPETENCIA_SEED = date(2026, 6, 1)
ADMIN_USERNAME_SEED = 'servidor.saude'
ADMIN_PASSWORD_SEED = 'SenhaForte123!'
CIDADAO_CPF_SEED = '10000000001'
CIDADAO_PASSWORD_SEED = 'SenhaCidadao123!'


class Command(BaseCommand):
    help = 'Popula o banco com dados de exemplo da Fila Transparente Cidada.'

    def add_arguments(self, parser):
        parser.add_argument(
            '--reset-seed',
            action='store_true',
            help='Remove somente registros criados por este seeder antes de recriar.',
        )
        parser.add_argument('--admin-username', default=ADMIN_USERNAME_SEED)
        parser.add_argument('--admin-password', default=ADMIN_PASSWORD_SEED)
        parser.add_argument('--cidadao-cpf', default=CIDADAO_CPF_SEED)
        parser.add_argument('--cidadao-password', default=CIDADAO_PASSWORD_SEED)

    @transaction.atomic
    def handle(self, *args, **options):
        if options['reset_seed']:
            removidos, _ = RegistroFila.objects.filter(
                codigo_solicitacao__startswith='SEED-',
            ).delete()
            self.stdout.write(f'Registros seed removidos: {removidos}')

        importado_por = (
            get_user_model().objects.filter(is_superuser=True).order_by('id').first()
        )

        especialidades = self.criar_especialidades()
        pacientes = self.criar_pacientes()
        admin, cidadao = self.criar_usuarios(pacientes, options)
        publicacoes = {
            slug: self.criar_publicacao(especialidade, importado_por)
            for slug, especialidade in especialidades.items()
        }
        registros = self.criar_registros(publicacoes, pacientes)

        self.stdout.write(self.style.SUCCESS('Seeder executado com sucesso.'))
        self.stdout.write(f'Especialidades disponiveis: {len(especialidades)}')
        self.stdout.write(f'Pacientes de exemplo: {len(pacientes)}')
        self.stdout.write(f'Usuario administrativo: {admin.username}')
        self.stdout.write(f'Usuario cidadao: {cidadao.username}')
        self.stdout.write(f'Publicacoes de exemplo: {len(publicacoes)}')
        self.stdout.write(f'Registros de fila criados/atualizados: {registros}')

    def criar_especialidades(self):
        dados = [
            ('consulta-pediatria', 'Pediatria', Especialidade.Tipo.CONSULTA),
            ('consulta-cardiologia', 'Cardiologia', Especialidade.Tipo.CONSULTA),
            ('consulta-oftalmologia', 'Oftalmologia', Especialidade.Tipo.CONSULTA),
            ('exame-ultrassonografia', 'Ultrassonografia', Especialidade.Tipo.EXAME),
        ]
        especialidades = {}
        for slug, nome, tipo in dados:
            especialidade, _ = Especialidade.objects.update_or_create(
                slug=slug,
                defaults={
                    'nome': nome,
                    'tipo': tipo,
                    'ativo': True,
                },
            )
            especialidades[slug] = especialidade
        return especialidades

    def criar_pacientes(self):
        dados = [
            ('10000000001', '700000000000001', 'Paciente Seed 1'),
            ('10000000002', '700000000000002', 'Paciente Seed 2'),
            ('10000000003', '700000000000003', 'Paciente Seed 3'),
            ('10000000004', '700000000000004', 'Paciente Seed 4'),
            ('10000000005', '700000000000005', 'Paciente Seed 5'),
            ('10000000006', '700000000000006', 'Paciente Seed 6'),
            ('10000000007', '700000000000007', 'Paciente Seed 7'),
            ('10000000008', '700000000000008', 'Paciente Seed 8'),
            ('10000000009', '700000000000009', 'Paciente Seed 9'),
            ('10000000010', '700000000000010', 'Paciente Seed 10'),
            ('10000000011', '700000000000011', 'Paciente Seed 11'),
            ('10000000012', '700000000000012', 'Paciente Seed 12'),
            ('10000000013', '700000000000013', 'Paciente Seed 13'),
        ]
        pacientes = []
        for cpf, cns, nome in dados:
            paciente, _ = Paciente.objects.update_or_create(
                cpf=cpf,
                defaults={
                    'cns': cns,
                    'nome_completo': nome,
                    'sexo': Paciente.Sexo.NAO_INFORMADO,
                },
            )
            pacientes.append(paciente)
        return pacientes

    def criar_usuarios(self, pacientes, options):
        User = get_user_model()

        admin, _ = User.objects.get_or_create(
            username=options['admin_username'],
        )
        admin.is_active = True
        admin.is_staff = True
        admin.set_password(options['admin_password'])
        admin.save(update_fields=['is_active', 'is_staff', 'password'])

        paciente_por_cpf = {paciente.cpf: paciente for paciente in pacientes}
        cpf_cidadao = options['cidadao_cpf']
        if cpf_cidadao not in paciente_por_cpf:
            self.stderr.write(
                self.style.WARNING(
                    f'O CPF {cpf_cidadao} nao pertence aos pacientes do seeder; '
                    f'usando {CIDADAO_CPF_SEED}.'
                )
            )
            cpf_cidadao = CIDADAO_CPF_SEED

        cidadao, _ = User.objects.get_or_create(username=cpf_cidadao)
        cidadao.is_active = True
        cidadao.is_staff = False
        cidadao.is_superuser = False
        cidadao.set_password(options['cidadao_password'])
        cidadao.save(
            update_fields=['is_active', 'is_staff', 'is_superuser', 'password'],
        )

        return admin, cidadao

    def criar_publicacao(self, especialidade, importado_por):
        hash_arquivo = hashlib.sha256(
            f'ftc-seed:{especialidade.slug}:{COMPETENCIA_SEED:%Y-%m}'.encode()
        ).hexdigest()
        publicacao, _ = PublicacaoFila.objects.update_or_create(
            especialidade=especialidade,
            competencia=COMPETENCIA_SEED,
            versao=1,
            defaults={
                'arquivo_original': f'filas/seed/{especialidade.slug}.csv',
                'hash_arquivo': hash_arquivo,
                'status': PublicacaoFila.Status.PUBLICADA,
                'publicada_em': timezone.now(),
                'importado_por': importado_por,
                'observacao': 'Dados de exemplo criados pelo database_seeder.',
            },
        )
        return publicacao

    def criar_registros(self, publicacoes, pacientes):
        dados = [
            (
                'consulta-pediatria',
                'SEED-PED-001',
                9001,
                RegistroFila.Prioridade.NIVEL_1,
                RegistroFila.Tipo.SOLICITADAS,
                RegistroFila.Situacao.SOLICITADO,
            ),
            (
                'consulta-pediatria',
                'SEED-PED-002',
                9002,
                RegistroFila.Prioridade.NIVEL_2,
                RegistroFila.Tipo.PENDENTES,
                RegistroFila.Situacao.AGUARDANDO_REGULACAO,
            ),
            (
                'consulta-pediatria',
                'SEED-PED-003',
                9003,
                RegistroFila.Prioridade.NIVEL_3,
                RegistroFila.Tipo.BAIXADAS,
                RegistroFila.Situacao.AGENDADO,
            ),
            (
                'consulta-cardiologia',
                'SEED-CAR-001',
                9001,
                RegistroFila.Prioridade.NIVEL_1,
                RegistroFila.Tipo.SOLICITADAS,
                RegistroFila.Situacao.DEVOLVIDO,
            ),
            (
                'consulta-cardiologia',
                'SEED-CAR-002',
                9002,
                RegistroFila.Prioridade.NIVEL_2,
                RegistroFila.Tipo.PENDENTES,
                RegistroFila.Situacao.PENDENTE,
            ),
            (
                'consulta-cardiologia',
                'SEED-CAR-003',
                9003,
                RegistroFila.Prioridade.NIVEL_3,
                RegistroFila.Tipo.BAIXADAS,
                RegistroFila.Situacao.REENVIADO,
            ),
            (
                'consulta-oftalmologia',
                'SEED-OFT-001',
                9001,
                RegistroFila.Prioridade.NIVEL_1,
                RegistroFila.Tipo.SOLICITADAS,
                RegistroFila.Situacao.NEGADO,
            ),
            (
                'consulta-oftalmologia',
                'SEED-OFT-002',
                9002,
                RegistroFila.Prioridade.NIVEL_2,
                RegistroFila.Tipo.PENDENTES,
                RegistroFila.Situacao.CANCELADO,
            ),
            (
                'consulta-oftalmologia',
                'SEED-OFT-003',
                9003,
                RegistroFila.Prioridade.NIVEL_3,
                RegistroFila.Tipo.BAIXADAS,
                RegistroFila.Situacao.BAIXADO_INTERNADO_CRL,
            ),
            (
                'exame-ultrassonografia',
                'SEED-USG-001',
                9001,
                RegistroFila.Prioridade.NIVEL_1,
                RegistroFila.Tipo.SOLICITADAS,
                RegistroFila.Situacao.AGUARDANDO_TRANSPORTE,
            ),
            (
                'exame-ultrassonografia',
                'SEED-USG-002',
                9002,
                RegistroFila.Prioridade.NIVEL_2,
                RegistroFila.Tipo.PENDENTES,
                RegistroFila.Situacao.SOLICITADO_CRL,
            ),
            (
                'exame-ultrassonografia',
                'SEED-USG-003',
                9003,
                RegistroFila.Prioridade.NIVEL_3,
                RegistroFila.Tipo.BAIXADAS,
                RegistroFila.Situacao.NEGADO_CRL,
            ),
            (
                'exame-ultrassonografia',
                'SEED-USG-004',
                9004,
                RegistroFila.Prioridade.NIVEL_2,
                RegistroFila.Tipo.PENDENTES,
                RegistroFila.Situacao.AGUARDANDO_LEITO,
            ),
        ]

        total = 0
        for indice, item in enumerate(dados):
            slug, codigo, posicao, prioridade, tipo, situacao = item
            paciente = pacientes[indice % len(pacientes)]
            RegistroFila.objects.update_or_create(
                publicacao=publicacoes[slug],
                codigo_solicitacao=codigo,
                defaults={
                    'paciente': paciente,
                    'data_solicitacao': date(2026, 5, (indice % 20) + 1),
                    'nome_mascarado': mask_name(paciente.nome_completo),
                    'ano_nascimento': 1980 + indice,
                    'cpf_mascarado': mask_cpf(paciente.cpf),
                    'cns_mascarado': mask_cns(paciente.cns),
                    'sexo': Paciente.Sexo.NAO_INFORMADO,
                    'posicao': posicao,
                    'prioridade': prioridade,
                    'tipo': tipo,
                    'situacao': situacao,
                },
            )
            total += 1
        return total

