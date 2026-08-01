from django.urls import path

from .views import (
    AdminLogoutView,
    AdminMeView,
    admin_session_login_view,
    csrf_token_view,
    AdminTokenObtainPairView,
    AdminTokenRefreshView,
    AdminUserCreateView,
    EspecialidadeListView,
    FilaOpcoesView,
    RegistroFilaListView,
    PacienteListView,
)

urlpatterns = [
    path('csrf/', csrf_token_view, name='csrf-token'),
    path('admin/users/', AdminUserCreateView.as_view(), name='admin-user-create'),
    path(
        'admin/auth/session/login/',
        admin_session_login_view,
        name='admin-session-login',
    ),
    path('admin/auth/login/', AdminTokenObtainPairView.as_view(), name='admin-login'),
    path(
        'admin/auth/refresh/',
        AdminTokenRefreshView.as_view(),
        name='admin-token-refresh',
    ),
    path('admin/auth/logout/', AdminLogoutView.as_view(), name='admin-logout'),
    path('admin/auth/me/', AdminMeView.as_view(), name='admin-me'),
    path('filas/registros/', RegistroFilaListView.as_view(), name='fila-registro-list'),
    path(
        'filas/especialidades/',
        EspecialidadeListView.as_view(),
        name='fila-especialidade-list',
    ),
    path('filas/opcoes/', FilaOpcoesView.as_view(), name='fila-opcoes'),
    path(
        'pacientes/',
        PacienteListView.as_view(),
        name='pacientes'
    ),
]
