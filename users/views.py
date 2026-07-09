from django.shortcuts import render, redirect
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.contrib.auth.forms import UserCreationForm, AuthenticationForm
from django.contrib.auth import login, logout
from .forms import PacienteForm, PacienteLoginForm, ServidorCreationForm
from ftc.models import Paciente

# Create your views here.

########## Parte do Paciente

def register_view(request):
    if request.method == "POST":
        form = PacienteForm(request.POST)
        if form.is_valid():
            form.save()
            messages.success(request, "Paciente cadastrado com sucesso!")
            return redirect("/")
    else:
        form = PacienteForm()
    return render(request, "users/paciente_register.html", {"form": form})

def login_view(request):
    if 'paciente_cns' in request.session:
        return redirect("/")
    
    if request.method == "POST":
        form = PacienteLoginForm(request.POST)
        if form.is_valid():
            cpf_digitado = form.cleaned_data['cpf']
            ano_digitado = form.cleaned_data['ano_nascimento']

            paciente = Paciente.objects.filter(cpf = cpf_digitado, ano_nascimento = ano_digitado).first()

            if paciente:
                request.session['paciente_cns'] = paciente.cns
                request.session['paciente_nome'] = paciente.nome
                return redirect("/")
            else:
                messages.error(request, "CPF ou Ano de Nascimento incorretos.")
    else:
        form = PacienteLoginForm()
    return render(request, "users/paciente_login.html", {"form": form})


def logout_view(request):
    if 'paciente_cns' in request.session:
        del request.session['paciente_cns']
        del request.session['paciente_nome']
    return redirect("/")

######### Parte do Servidor

def servidor_register_view(request):

    if request.method == "POST":
        form = ServidorCreationForm(request.POST)
        if form.is_valid():
            usuario = form.save()
            login(request, usuario)
            return redirect("/")
    else:
        form = ServidorCreationForm()
    return render(request, "users/servidor_register.html", {"form": form})

def servidor_login_view(request):
    if request.method == "POST":
        form = AuthenticationForm(data = request.POST)
        if form.is_valid():
            usuario = form.get_user()
            login(request, usuario)
            return redirect("/")
    else:
        form = AuthenticationForm()
    return render(request, "users/servidor_login.html", {"form": form})

def servidor_logout_view(request):
    if request.method == "POST":
        logout(request)
        return redirect("/")