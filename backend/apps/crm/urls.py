from django.urls import path, include
from common.routers import OptionalSlashRouter
from .views import AtendimentoViewSet, ComunicacaoViewSet, Encarregado360View, AlertasEvasaoView

router = OptionalSlashRouter()
router.register(r'atendimentos', AtendimentoViewSet, basename='crm-atendimentos')
router.register(r'comunicacoes', ComunicacaoViewSet, basename='crm-comunicacoes')

urlpatterns = [
    path('encarregado/<uuid:aluno_id>/', Encarregado360View.as_view(), name='crm_encarregado_360'),
    path('alertas-evasao/', AlertasEvasaoView.as_view(), name='crm_alertas_evasao'),
    path('', include(router.urls)),
]
