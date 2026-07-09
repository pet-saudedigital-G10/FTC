# Em users/urls.py
from django.urls import path
from users import views

app_name = 'users'

urlpatterns = [
    # Rotas do Paciente
    path('paciente/login/', views.login_view, name="login_paciente"),
    path('paciente/cadastro/', views.register_view, name="cadastro_paciente"), 
    path('paciente/logout/', views.logout_view, name="logout_paciente"), # Nome corrigido
    
    # Rotas do Servidor
    path('servidor/login/', views.servidor_login_view, name="login_servidor"),
    path('servidor/cadastro/', views.servidor_register_view, name="cadastro_servidor"),
    path('servidor/logout/', views.servidor_logout_view, name="logout_servidor"),
]