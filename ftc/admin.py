from django.contrib import admin

# Register your models here.

from .models import Paciente, Especialidades, Solicitacoes

# Registra os modelos para aparecerem no painel administrativo [cite: 22, 23]
admin.site.register(Paciente)
admin.site.register(Especialidades)
admin.site.register(Solicitacoes)
