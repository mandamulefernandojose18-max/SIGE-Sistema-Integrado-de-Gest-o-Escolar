from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import NotaViewSet, PrazosTrimestresView, AutorizacaoEdicaoView

router = DefaultRouter()
router.register(r'', NotaViewSet, basename='notas')

urlpatterns = [
    path('prazos-trimestres', PrazosTrimestresView.as_view(), name='notas_prazos_no_slash'),
    path('prazos-trimestres/', PrazosTrimestresView.as_view(), name='notas_prazos'),
    path('autorizacoes', AutorizacaoEdicaoView.as_view(), name='notas_autorizacoes_no_slash'),
    path('autorizacoes/', AutorizacaoEdicaoView.as_view(), name='notas_autorizacoes'),
    path('autorizar-desbloqueio', AutorizacaoEdicaoView.as_view(), name='notas_desbloqueio_no_slash'),
    path('autorizar-desbloqueio/', AutorizacaoEdicaoView.as_view(), name='notas_desbloqueio'),
    path('autorizacoes/<uuid:perm_id>', AutorizacaoEdicaoView.as_view(), name='notas_revogar_no_slash'),
    path('autorizacoes/<uuid:perm_id>/', AutorizacaoEdicaoView.as_view(), name='notas_revogar'),
    path('', include(router.urls)),
]
