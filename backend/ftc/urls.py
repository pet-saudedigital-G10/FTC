from django.urls import path

from .views import (
    AtualizacaoFilaView,
    AdminLogoutView,
    AdminMeView,
    AdminTokenObtainPairView,
    AdminTokenRefreshView,
    AdminUserCreateView,
    CidadaoLogoutView,
    CidadaoMeView,
    CidadaoRegistroFilaListView,
    CidadaoTokenObtainPairView,
    CidadaoTokenRefreshView,
    EspecialidadeListView,
    FilaOpcoesView,
    RegistroFilaListView,
    PacienteListView,
    SisregConfiguracaoView,
    SisregFilaView,
    SisregGruposView,
    SisregImportacaoView,
    SisregStatusView,
    SisregTesteConexaoView,
    TransparenciaIndicadoresView,
    TransparenciaPosicaoView,
)

from ftc.views.fila import ConsultaPosicaoFilaAPIView

urlpatterns = [
    path(
        'admin/filas/atualizar/',
        AtualizacaoFilaView.as_view(),
        name='admin-fila-atualizar',
    ),
    path(
        'admin/sisreg/status/',
        SisregStatusView.as_view(),
        name='admin-sisreg-status',
    ),
    path(
        'admin/sisreg/configuracao/',
        SisregConfiguracaoView.as_view(),
        name='admin-sisreg-configuracao',
    ),
    path(
        'admin/sisreg/configuracao/testar/',
        SisregTesteConexaoView.as_view(),
        name='admin-sisreg-testar',
    ),
    path(
        'admin/sisreg/grupos/',
        SisregGruposView.as_view(),
        name='admin-sisreg-grupos',
    ),
    path('admin/sisreg/fila/', SisregFilaView.as_view(), name='admin-sisreg-fila'),
    path(
        'admin/sisreg/importar/',
        SisregImportacaoView.as_view(),
        name='admin-sisreg-importar',
    ),
    path('admin/users/', AdminUserCreateView.as_view(), name='admin-user-create'),
    path('admin/auth/login/', AdminTokenObtainPairView.as_view(), name='admin-login'),
    path(
        'admin/auth/refresh/',
        AdminTokenRefreshView.as_view(),
        name='admin-token-refresh',
    ),
    path('admin/auth/logout/', AdminLogoutView.as_view(), name='admin-logout'),
    path('admin/auth/me/', AdminMeView.as_view(), name='admin-me'),
    path(
        'auth/cidadao/login/',
        CidadaoTokenObtainPairView.as_view(),
        name='cidadao-login',
    ),
    path(
        'auth/cidadao/refresh/',
        CidadaoTokenRefreshView.as_view(),
        name='cidadao-token-refresh',
    ),
    path(
        'auth/cidadao/logout/',
        CidadaoLogoutView.as_view(),
        name='cidadao-logout',
    ),
    path('auth/cidadao/me/', CidadaoMeView.as_view(), name='cidadao-me'),
    path(
        'cidadao/filas/',
        CidadaoRegistroFilaListView.as_view(),
        name='cidadao-filas',
    ),
    path('filas/registros/', RegistroFilaListView.as_view(), name='fila-registro-list'),
    path(
        'filas/especialidades/',
        EspecialidadeListView.as_view(),
        name='fila-especialidade-list',
    ),
    path('filas/opcoes/', FilaOpcoesView.as_view(), name='fila-opcoes'),
    path(
        'filas/posicao/',
        ConsultaPosicaoFilaAPIView.as_view(),
        name='fila-posicao',
    ),
    path(
        'transparencia/indicadores/',
        TransparenciaIndicadoresView.as_view(),
        name='transparencia-indicadores',
    ),
    path(
        'transparencia/posicao/',
        TransparenciaPosicaoView.as_view(),
        name='transparencia-posicao',
    ),
    path(
        'pacientes/',
        PacienteListView.as_view(),
        name='pacientes'
    ),
]
