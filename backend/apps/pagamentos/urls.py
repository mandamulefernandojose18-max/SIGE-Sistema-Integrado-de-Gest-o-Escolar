from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import PagamentoViewSet, PagamentoStatsView

router = DefaultRouter()
router.register(r'', PagamentoViewSet, basename='pagamentos')

urlpatterns = [
    path('stats', PagamentoStatsView.as_view(), name='pagamentos_stats_no_slash'),
    path('stats/', PagamentoStatsView.as_view(), name='pagamentos_stats'),
    path('', include(router.urls)),
]
