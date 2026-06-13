from django.contrib import admin

from .models import Especialidade, Paciente, PublicacaoFila, RegistroFila


@admin.register(Paciente)
class PacienteAdmin(admin.ModelAdmin):
    list_display = (
        'id',
        'nome_completo',
        'cpf',
        'cns',
        'data_nascimento',
        'sexo',
    )
    search_fields = ('nome_completo', 'cpf', 'cns')
    list_filter = ('sexo',)


@admin.register(Especialidade)
class EspecialidadeAdmin(admin.ModelAdmin):
    list_display = ('id', 'nome', 'tipo', 'ativo')
    search_fields = ('nome', 'slug')
    list_filter = ('tipo', 'ativo')
    prepopulated_fields = {'slug': ('nome',)}


@admin.register(PublicacaoFila)
class PublicacaoFilaAdmin(admin.ModelAdmin):
    list_display = (
        'id',
        'especialidade',
        'competencia',
        'versao',
        'status',
        'importado_em',
        'publicada_em',
    )
    search_fields = ('especialidade__nome', 'hash_arquivo')
    list_filter = ('status', 'especialidade__tipo', 'competencia')
    autocomplete_fields = ('especialidade', 'importado_por')
    readonly_fields = ('importado_em',)


@admin.register(RegistroFila)
class RegistroFilaAdmin(admin.ModelAdmin):
    list_display = (
        'id',
        'publicacao',
        'posicao',
        'codigo_solicitacao',
        'nome_mascarado',
        'data_solicitacao',
    )
    search_fields = (
        'codigo_solicitacao',
        'nome_mascarado',
        'cpf_mascarado',
        'cns_mascarado',
    )
    list_filter = ('publicacao__especialidade', 'sexo')
    autocomplete_fields = ('publicacao', 'paciente')
