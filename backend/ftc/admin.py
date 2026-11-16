from django.contrib import admin
from django.utils import timezone

from .models import Especialidade, Paciente, PublicacaoFila, RegistroFila, AuditoriaOperacao


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
    
    def get_queryset(self, request):
        return Especialidade.all_objects.all()

    actions = ['inativar_especialidades', 'reativar_especialidades']

    @admin.action(description='Inativar especialidades selecionadas')
    def inativar_especialidades(self, request, queryset):
        atualizados = queryset.update(ativo=False)
        self.message_user(request, f'{atualizados} especialidades inativadas.')

    @admin.action(description='Reativar especialidades selecionadas')
    def reativar_especialidades(self, request, queryset):
        atualizados = queryset.update(ativo=True)
        self.message_user(request, f'{atualizados} especialidades reativadas.')


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
        'inativado_em',
    )
    search_fields = ('especialidade__nome', 'hash_arquivo')
    list_filter = ('status', 'especialidade__tipo', 'competencia', 'inativado_em')
    autocomplete_fields = ('especialidade', 'importado_por')
    
    readonly_fields = ('importado_em', 'inativado_em', 'inativado_por', 'motivo_inativacao')

    def has_delete_permission(self, request, obj=None):
        return False

    actions = ['inativar_publicacoes']

    @admin.action(description='Inativar publicações selecionadas')
    def inativar_publicacoes(self, request, queryset):
        filtro = list(queryset.filter(inativado_em__isnull=True))
        
        if not filtro:
            self.message_user(request, 'Nenhuma publicação ativa selecionada.')
            return

        ids = [pub.id for pub in filtro]
        PublicacaoFila.objects.filter(id__in=ids).update(
            inativado_em=timezone.now(),
            inativado_por=request.user,
            motivo_inativacao='Inativação em massa via painel Admin.'
        )

        auditorias = [
            AuditoriaOperacao(
                usuario=request.user,
                acao=AuditoriaOperacao.Acao.INATIVACAO,
                alvo_tipo='PublicacaoFila',
                alvo_id=pub.id,
                motivo='Inativação em massa via painel Admin.'
            ) for pub in filtro
        ]
        AuditoriaOperacao.objects.bulk_create(auditorias)
        
        self.message_user(request, f'{len(filtro)} publicações inativadas.')

@admin.register(RegistroFila)
class RegistroFilaAdmin(admin.ModelAdmin):
    list_display = (
        'id',
        'publicacao',
        'posicao',
        'prioridade',
        'tipo',
        'situacao',
        'codigo_solicitacao',
        'nome_mascarado',
        'data_solicitacao',
        'inativado_em',
    )
    search_fields = (
        'codigo_solicitacao',
        'nome_mascarado',
        'cpf_mascarado',
        'cns_mascarado',
    )
    list_filter = (
        'publicacao__especialidade',
        'publicacao__especialidade__tipo',
        'prioridade',
        'tipo',
        'situacao',
        'sexo',
        'inativado_em', # Novo filtro
    )
    autocomplete_fields = ('publicacao', 'paciente')
    
    readonly_fields = ('inativado_em', 'inativado_por', 'motivo_inativacao')

    def has_delete_permission(self, request, obj=None):
        return False

    actions = ['inativar_registros', 'reativar_registros']

    @admin.action(description='Inativar registros selecionados')
    def inativar_registros(self, request, queryset):
        filtro = list(queryset.filter(inativado_em__isnull=True))
        
        if not filtro:
            self.message_user(request, 'Nenhum registro ativo selecionado.')
            return

        ids = [reg.id for reg in filtro]
        RegistroFila.objects.filter(id__in=ids).update(
            inativado_em=timezone.now(),
            inativado_por=request.user,
            motivo_inativacao='Inativação em massa via painel Admin.'
        )
        
        auditorias = [
            AuditoriaOperacao(
                usuario=request.user,
                acao=AuditoriaOperacao.Acao.INATIVACAO,
                alvo_tipo='RegistroFila',
                alvo_id=reg.id,
                codigo_solicitacao=reg.codigo_solicitacao,
                motivo='Inativação em massa via painel Admin.'
            ) for reg in filtro
        ]
        AuditoriaOperacao.objects.bulk_create(auditorias)
        
        self.message_user(request, f'{len(filtro)} registros inativados.')

    @admin.action(description='Reativar registros selecionados')
    def reativar_registros(self, request, queryset):
        filtro = list(queryset.filter(inativado_em__isnull=False))
        
        if not filtro:
            self.message_user(request, 'Nenhum registro inativo selecionado.')
            return

        ids = [reg.id for reg in filtro]
        RegistroFila.objects.filter(id__in=ids).update(
            inativado_em=None,
            inativado_por=None,
            motivo_inativacao=''
        )
        
        auditorias = [
            AuditoriaOperacao(
                usuario=request.user,
                acao=AuditoriaOperacao.Acao.REATIVACAO,
                alvo_tipo='RegistroFila',
                alvo_id=reg.id,
                codigo_solicitacao=reg.codigo_solicitacao,
                motivo='Reativação em massa via painel Admin.'
            ) for reg in filtro
        ]
        AuditoriaOperacao.objects.bulk_create(auditorias)

        self.message_user(request, f'{len(filtro)} registros reativados.')


@admin.register(AuditoriaOperacao)
class AuditoriaOperacaoAdmin(admin.ModelAdmin):
    list_display = (
        'id',
        'criado_em',
        'usuario',
        'acao',
        'alvo_tipo',
        'alvo_id',
        'codigo_solicitacao',
        'motivo',
    )
    list_filter = ('acao', 'alvo_tipo', 'criado_em')
    search_fields = ('motivo', 'codigo_solicitacao', 'usuario__username')
    
    # A tabela de auditoria é IMUTÁVEL. Ninguém pode adicionar, editar ou apagar.
    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return False