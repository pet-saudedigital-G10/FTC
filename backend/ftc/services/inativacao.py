from django.db import transaction
from django.utils import timezone
from ftc.models import RegistroFila, AuditoriaOperacao

@transaction.atomic
def inativar_registro(*, registro_id, usuario, motivo):
    registro = RegistroFila.objects.select_for_update().get(pk=registro_id)
    
    if registro.inativado_em:
        raise ValueError('Registro já está inativado.')

    registro.inativado_em = timezone.now()
    registro.inativado_por = usuario
    registro.motivo_inativacao = motivo
    registro.save(update_fields=['inativado_em', 'inativado_por', 'motivo_inativacao'])

    AuditoriaOperacao.objects.create(
        usuario=usuario,
        acao=AuditoriaOperacao.Acao.INATIVACAO,
        alvo_tipo='RegistroFila',
        alvo_id=registro.id,
        codigo_solicitacao=registro.codigo_solicitacao,
        motivo=motivo
    )
    return registro

@transaction.atomic
def reativar_registro(*, registro_id, usuario, motivo):
    registro = RegistroFila.objects.select_for_update().get(pk=registro_id)
    
    if not registro.inativado_em:
        raise ValueError('Registro já está ativo.')

    registro.inativado_em = None
    registro.inativado_por = None
    registro.motivo_inativacao = ''
    registro.save(update_fields=['inativado_em', 'inativado_por', 'motivo_inativacao'])

    AuditoriaOperacao.objects.create(
        usuario=usuario,
        acao=AuditoriaOperacao.Acao.REATIVACAO,
        alvo_tipo='RegistroFila',
        alvo_id=registro.id,
        codigo_solicitacao=registro.codigo_solicitacao,
        motivo=motivo
    )
    return registro