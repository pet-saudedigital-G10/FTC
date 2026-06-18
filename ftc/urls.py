from django.urls import path

from .views import (
    AdminLogoutView,
    AdminMeView,
    AdminTokenObtainPairView,
    AdminTokenRefreshView,
    AdminUserCreateView,
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
    path(
        'pacientes/',
        PacienteListView.as_view(),
        name='pacientes'
    ),
]
