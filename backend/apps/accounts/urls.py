from django.urls import path
from rest_framework_simplejwt.views import TokenRefreshView
from .views import (
    LoginView,
    LogoutView,
    CurrentUserView,
    UserStatsView,
    RedefinirSenhaView,
    AlterarMinhaSenhaView,
    AuditoriaListView,
)
from .views_2fa import (
    Estado2FAView,
    Configurar2FAView,
    Activar2FAView,
    Desativar2FAView,
    Repor2FAView,
)

urlpatterns = [
    path('login', LoginView.as_view(), name='auth_login_no_slash'),
    path('login/', LoginView.as_view(), name='auth_login'),
    path('logout', LogoutView.as_view(), name='auth_logout_no_slash'),
    path('logout/', LogoutView.as_view(), name='auth_logout'),
    path('me', CurrentUserView.as_view(), name='auth_me_no_slash'),
    path('me/', CurrentUserView.as_view(), name='auth_me'),
    path('refresh', TokenRefreshView.as_view(), name='auth_refresh_no_slash'),
    path('refresh/', TokenRefreshView.as_view(), name='auth_refresh'),
    path('stats', UserStatsView.as_view(), name='auth_stats_no_slash'),
    path('stats/', UserStatsView.as_view(), name='auth_stats'),
    path('minha-senha', AlterarMinhaSenhaView.as_view(), name='auth_minha_senha_no_slash'),
    path('minha-senha/', AlterarMinhaSenhaView.as_view(), name='auth_minha_senha'),
    path('usuarios/<uuid:user_id>/redefinir-senha', RedefinirSenhaView.as_view(), name='auth_redefinir_senha_no_slash'),
    path('usuarios/<uuid:user_id>/redefinir-senha/', RedefinirSenhaView.as_view(), name='auth_redefinir_senha'),
    path('2fa/estado/', Estado2FAView.as_view(), name='auth_2fa_estado'),
    path('2fa/configurar/', Configurar2FAView.as_view(), name='auth_2fa_configurar'),
    path('2fa/activar/', Activar2FAView.as_view(), name='auth_2fa_activar'),
    path('2fa/desactivar/', Desativar2FAView.as_view(), name='auth_2fa_desactivar'),
    path('usuarios/<uuid:user_id>/2fa/repor/', Repor2FAView.as_view(), name='auth_2fa_repor'),
    path('auditoria', AuditoriaListView.as_view(), name='auth_auditoria_no_slash'),
    path('auditoria/', AuditoriaListView.as_view(), name='auth_auditoria'),
]


