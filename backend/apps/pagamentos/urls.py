from django.urls import path, include
from common.routers import OptionalSlashRouter
from .views import PagamentoViewSet, PagamentoStatsView, PlanoPagamentoEscolaViewSet, TransacaoFinanceiraViewSet, FolhaSalarioViewSet, ItemPatrimonioViewSet

router = OptionalSlashRouter()
router.register(r'planos-escola', PlanoPagamentoEscolaViewSet, basename='planos_escola')
router.register(r'transacoes', TransacaoFinanceiraViewSet, basename='pagamentos-transacoes')
router.register(r'folha-salarios', FolhaSalarioViewSet, basename='pagamentos-folhasalarios')
router.register(r'patrimonio', ItemPatrimonioViewSet, basename='pagamentos-patrimonio')
router.register(r'', PagamentoViewSet, basename='pagamentos')

urlpatterns = [
    path('stats', PagamentoStatsView.as_view(), name='pagamentos_stats_no_slash'),
    path('stats/', PagamentoStatsView.as_view(), name='pagamentos_stats'),
    path('', include(router.urls)),
]
