from django.urls import path, include
from common.routers import OptionalSlashRouter
from .views import PagamentoViewSet, PagamentoStatsView, PlanoPagamentoEscolaViewSet

router = OptionalSlashRouter()
router.register(r'planos-escola', PlanoPagamentoEscolaViewSet, basename='planos_escola')
router.register(r'', PagamentoViewSet, basename='pagamentos')

urlpatterns = [
    path('stats', PagamentoStatsView.as_view(), name='pagamentos_stats_no_slash'),
    path('stats/', PagamentoStatsView.as_view(), name='pagamentos_stats'),
    path('', include(router.urls)),
]
