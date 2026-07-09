from django import forms
from django.contrib.auth.forms import UserCreationForm
from ftc.models import Paciente, Servidor

class PacienteForm(forms.ModelForm):
    class Meta:
        model = Paciente
        fields = ['cns', 'nome', 'cpf', 'ano_nascimento', 'sexo']

class PacienteLoginForm(forms.Form):
    cpf = forms.CharField(max_length = 14, label = "CPF")
    ano_nascimento = forms.IntegerField(label = "Ano de Nascimento") 
    # No caso o modelo final deve ser Data de Nascimento, porém não sei como está modelado no banco e por hora essa diferença não causará
    # nenhum impacto na lógica do login

class ServidorCreationForm(UserCreationForm):
    class Meta:
        model = Servidor
        # Campos que o servidor vai preencher ao se cadastrar
        fields = ['username', 'email', 'cpf', 'carteira_identidade_funcional']