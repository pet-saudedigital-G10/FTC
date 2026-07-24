from django.urls import path

from .views import (
    AdminLogoutView,
    AdminMeView,
    AdminTokenObtainPairView,
    AdminTokenRefreshView,
    AdminUserCreateView,
    EspecialidadeListView,
    FilaOpcoesView,
    RegistroFilaListView,
    PacienteListView,
)

urlpatterns = [
    path('admin/users/', AdminUserCreateView.as_view(), name='admin-user-create'),
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
