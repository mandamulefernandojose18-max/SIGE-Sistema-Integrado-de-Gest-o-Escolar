from django.urls import path
from rest_framework_simplejwt.views import TokenRefreshView
from .views import LoginView, CurrentUserView, UserStatsView, RedefinirSenhaView

urlpatterns = [
    path('login', LoginView.as_view(), name='auth_login_no_slash'),
    path('login/', LoginView.as_view(), name='auth_login'),
    path('me', CurrentUserView.as_view(), name='auth_me_no_slash'),
    path('me/', CurrentUserView.as_view(), name='auth_me'),
    path('refresh', TokenRefreshView.as_view(), name='auth_refresh_no_slash'),
    path('refresh/', TokenRefreshView.as_view(), name='auth_refresh'),
    path('stats', UserStatsView.as_view(), name='auth_stats_no_slash'),
    path('stats/', UserStatsView.as_view(), name='auth_stats'),
    path('usuarios/<uuid:user_id>/redefinir-senha', RedefinirSenhaView.as_view(), name='auth_redefinir_senha_no_slash'),
    path('usuarios/<uuid:user_id>/redefinir-senha/', RedefinirSenhaView.as_view(), name='auth_redefinir_senha'),
]
