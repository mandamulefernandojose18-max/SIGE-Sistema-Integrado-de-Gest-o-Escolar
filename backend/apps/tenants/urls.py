from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import (
    GeografiaView,
    SaaSMetricsView,
    PlanoViewSet,
    EscolaViewSet,
    VerificarExpiracoesView,
    EscolaAdminInfoView,
    ToggleNotasView,
    UsuariosCredenciaisView
)

router = DefaultRouter()
router.register(r'escolas', EscolaViewSet, basename='saas_escola')
router.register(r'planos', PlanoViewSet, basename='saas_plano')

saas_admin_urls = [
    path('metrics', SaaSMetricsView.as_view(), name='saas_metrics_no_slash'),
    path('metrics/', SaaSMetricsView.as_view(), name='saas_metrics'),
    path('verificar-expiracoes', VerificarExpiracoesView.as_view(), name='saas_verificar_expiracoes_no_slash'),
    path('verificar-expiracoes/', VerificarExpiracoesView.as_view(), name='saas_verificar_expiracoes'),
    path('', include(router.urls)),
]

escola_admin_urls = [
    path('info', EscolaAdminInfoView.as_view(), name='escola_admin_info_no_slash'),
    path('info/', EscolaAdminInfoView.as_view(), name='escola_admin_info'),
    path('toggle-notas', ToggleNotasView.as_view(), name='escola_toggle_notas_no_slash'),
    path('toggle-notas/', ToggleNotasView.as_view(), name='escola_toggle_notas'),
    path('usuarios-credenciais', UsuariosCredenciaisView.as_view(), name='escola_usuarios_credenciais_no_slash'),
    path('usuarios-credenciais/', UsuariosCredenciaisView.as_view(), name='escola_usuarios_credenciais'),
]

urlpatterns = [
    path('geografia', GeografiaView.as_view(), name='geografia_no_slash'),
    path('geografia/', GeografiaView.as_view(), name='geografia'),
    path('saas-admin/', include(saas_admin_urls)),
    path('escola-admin/', include(escola_admin_urls)),
]
