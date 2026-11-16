from datetime import date

from django.contrib.auth import get_user_model
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase

from ftc.models import Especialidade, PublicacaoFila, RegistroFila, AuditoriaOperacao


class PB10InativacaoTests(APITestCase):
    def setUp(self):
        self.admin = get_user_model().objects.create_superuser(
            username='admin-teste', 
            password='senha'
        )
        self.cidadao = get_user_model().objects.create_user(
            username='cidadao-teste', 
            password='senha'
        )
        
        self.especialidade = Especialidade.objects.create(
            nome='Pediatria', 
            slug='pediatria', 
            tipo=Especialidade.Tipo.CONSULTA
        )
        
        self.publicacao = PublicacaoFila.objects.create(
            especialidade=self.especialidade, 
            competencia=date(2026, 1, 1),
            arquivo_original='teste.pdf', 
            hash_arquivo='hash123', 
            status=PublicacaoFila.Status.PUBLICADA
        )
        
        self.registro = RegistroFila.objects.create(
            publicacao=self.publicacao, 
            posicao=1, 
            codigo_solicitacao='12345',
            data_solicitacao=date(2026, 1, 1), 
            nome_mascarado='J. S.'
        )
        
        self.url_inativar = reverse('registro-inativar', kwargs={'pk': self.registro.pk})

    def test_admin_pode_inativar_e_gera_auditoria(self):
        self.client.force_authenticate(user=self.admin)
        response = self.client.patch(self.url_inativar, {'motivo': 'Paciente desistiu'})
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        
        self.registro.refresh_from_db()
        self.assertIsNotNone(self.registro.inativado_em)
        
        self.assertEqual(AuditoriaOperacao.objects.count(), 1)
        
        audit = AuditoriaOperacao.objects.first()
        self.assertEqual(audit.acao, AuditoriaOperacao.Acao.INATIVACAO)
        self.assertEqual(audit.motivo, 'Paciente desistiu')

    def test_inativar_sem_motivo_retorna_400(self):
        self.client.force_authenticate(user=self.admin)
        response = self.client.patch(self.url_inativar, {})
        
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_cidadao_nao_pode_inativar(self):
        self.client.force_authenticate(user=self.cidadao)
        response = self.client.patch(self.url_inativar, {'motivo': 'Tentando hackear'})
        
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)