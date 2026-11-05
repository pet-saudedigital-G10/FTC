import logging

from cryptography.fernet import InvalidToken
from django.conf import settings
from django.db import models

from ftc.utils.criptografia import cifrar, decifrar


logger = logging.getLogger(__name__)


class ConfiguracaoSisreg(models.Model):
    """Configuracao unica da integracao, mantida pela area administrativa."""

    class Ambiente(models.TextChoices):
        HOMOLOGACAO = 'homologacao', 'Homologação'
        PRODUCAO = 'producao', 'Produção'

    habilitado = models.BooleanField(default=False)
    ambiente = models.CharField(
        max_length=15,
        choices=Ambiente.choices,
        default=Ambiente.HOMOLOGACAO,
    )
    client_id = models.CharField(max_length=7, blank=True)
    client_secret_cifrado = models.TextField(blank=True, editable=False)
    indice = models.CharField(max_length=120, blank=True)
    centrais_reguladoras = models.JSONField(default=list, blank=True)
    atualizado_em = models.DateTimeField(auto_now=True)
    atualizado_por = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='+',
    )

    class Meta:
        db_table = 'configuracao_sisreg'
        verbose_name = 'Configuracao do SISREG'
        verbose_name_plural = 'Configuracao do SISREG'

    def __str__(self):
        return f'SISREG - {self.get_ambiente_display()}'

    def save(self, *args, **kwargs):
        self.pk = 1
        super().save(*args, **kwargs)

    @classmethod
    def carregar(cls):
        return cls.objects.filter(pk=1).first() or cls(pk=1)

    @property
    def client_secret(self):
        if not self.client_secret_cifrado:
            return ''
        try:
            return decifrar(self.client_secret_cifrado)
        except InvalidToken:
            # Ocorre quando a SECRET_KEY muda: a credencial deve ser informada
            # novamente pela tela de configuracao.
            logger.warning('Nao foi possivel decifrar a credencial do SISREG.')
            return ''

    @client_secret.setter
    def client_secret(self, valor):
        self.client_secret_cifrado = cifrar(valor)

    @property
    def client_secret_configurado(self):
        return bool(self.client_secret)
