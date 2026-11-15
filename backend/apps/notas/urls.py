from django.urls import path, include
from common.routers import OptionalSlashRouter
from .views import NotaViewSet, PrazosTrimestresView, AutorizacaoEdicaoView, PlanoAulaSumarioViewSet, OcorrenciaDisciplinarViewSet

router = OptionalSlashRouter()
router.register(r'planos-sumarios', PlanoAulaSumarioViewSet, basename='notas-planos-sumarios')
router.register(r'ocorrencias', OcorrenciaDisciplinarViewSet, basename='notas-ocorrencias')
router.register(r'', NotaViewSet, basename='notas')

from .views_exames import (
    CalendarioExameDetalheView, CalendarioExamesPdfView, CalendarioExamesView, ExcluidosExamePdfView, ExcluidosExameView,
    FormarJurisView, JurisExamePdfView, JurisExameView,
)

urlpatterns = [
    path('calendario-exames', CalendarioExamesView.as_view(), name='calendario_exames_no_slash'),
    path('calendario-exames/', CalendarioExamesView.as_view(), name='calendario_exames'),
    path('calendario-exames/pdf', CalendarioExamesPdfView.as_view(), name='calendario_exames_pdf_no_slash'),
    path('calendario-exames/pdf/', CalendarioExamesPdfView.as_view(), name='calendario_exames_pdf'),
    path('calendario-exames/<uuid:pk>', CalendarioExameDetalheView.as_view(), name='calendario_exame_det_no_slash'),
    path('calendario-exames/<uuid:pk>/', CalendarioExameDetalheView.as_view(), name='calendario_exame_det'),
    path('juris-exame', JurisExameView.as_view(), name='juris_exame_no_slash'),
    path('juris-exame/', JurisExameView.as_view(), name='juris_exame'),
    path('juris-exame/formar', FormarJurisView.as_view(), name='juris_exame_formar_no_slash'),
    path('juris-exame/formar/', FormarJurisView.as_view(), name='juris_exame_formar'),
    path('juris-exame/pdf', JurisExamePdfView.as_view(), name='juris_exame_pdf_no_slash'),
    path('juris-exame/pdf/', JurisExamePdfView.as_view(), name='juris_exame_pdf'),
    path('juris-exame/excluidos', ExcluidosExameView.as_view(), name='juris_exame_excl_no_slash'),
    path('juris-exame/excluidos/', ExcluidosExameView.as_view(), name='juris_exame_excl'),
    path('juris-exame/excluidos/pdf', ExcluidosExamePdfView.as_view(), name='juris_exame_excl_pdf_no_slash'),
    path('juris-exame/excluidos/pdf/', ExcluidosExamePdfView.as_view(), name='juris_exame_excl_pdf'),
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
