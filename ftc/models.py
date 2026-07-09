from django.db import models
from django.contrib.auth.models import AbstractUser

# Create your models here.

class Paciente(models.Model):
    SEXO = [
        ('M', 'MASCULINO'),
        ('F', 'FEMININO'),
    ]

    cns = models.CharField(max_length=15, primary_key=True, verbose_name="Cartão Nacional de Saúde (CNS)")
    nome = models.CharField(max_length=255, verbose_name="Nome")
    ano_nascimento = models.PositiveIntegerField(verbose_name="Ano de Nascimento")
    sexo = models.CharField(max_length=1, choices=SEXO, verbose_name="Sexo")
    cpf = models.CharField(max_length=14, unique=True, verbose_name="CPF", blank=True, null=True)

    class Meta:
        # Força o nome da tabela no banco de dados para ser exatamente 'pacientes'
        db_table = 'pacientes'
        verbose_name = "Paciente"
        verbose_name_plural = "Pacientes"
        ordering = ['nome']

    def __str__(self):
        return f"{self.nome} - CNS: {self.cns}"
    
class Especialidades(models.Model):
    id_especialidade = models.PositiveIntegerField(primary_key=True, verbose_name="ID da Especilidade")
    nome_especialidade = models.CharField(max_length=255, verbose_name="Nome da Especialidade")

    class Meta:
        # Força o nome da tabela no banco de dados para ser exatamente 'pacientes'
        db_table = 'Especialidades'
        verbose_name = "especialidade"
        verbose_name_plural = "especialidades"

    def __str__(self):
        return f"{self.id_especialidade} - Especialidade: {self.nome_especialidade}"

class Solicitacoes(models.Model):
    cod_solicitacao = models.PositiveBigIntegerField(verbose_name="Código de solicitação")
    paciente = models.ForeignKey(Paciente, on_delete=models.CASCADE, db_column='cns_paciente', to_field='cns')
    especialidade = models.ForeignKey(Especialidades, on_delete=models.PROTECT, db_column='id_especialidade')

    data_solicitacao = models.DateField(auto_now_add=True, verbose_name="Data da solicitação")

    def __str__(self):
        return f"Solicitação {self.cod_solicitacao}: Paciente {self.paciente.nome} - Especialidade {self.especialidade.nome_especialidade}"
    
class Servidor(AbstractUser):
    cpf = models.CharField(max_length=14, unique=True, verbose_name="CPF")
    carteira_identidade_funcional = models.CharField(max_length=14, unique=True, verbose_name="Identidade Funcional")

    def __str__(self):
        return f"{self.username} - Funcional: {self.carteira_identidade_funcional}"
