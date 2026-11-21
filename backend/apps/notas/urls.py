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

from .views_correcao import (
    CorrecaoAlunoView, CorrecaoImagemFicheiroView, CorrecaoImagemUploadView, FolhasCorrigidasPdfView, LancarCorrecoesView, ListaNotasAvaliacaoView,
    ProvaFisicaDetalheView, ProvasFisicasView,
)

from .views_omr import (
    ConfirmarOmrView, FolhasPendentesView, GabaritoImportarView, GabaritosGuardadosView, LeituraOmrView,
)

urlpatterns = [
    path('provas-fisicas/gabarito/importar', GabaritoImportarView.as_view(), name='provas_fisicas_gab_no_slash'),
    path('provas-fisicas/gabarito/importar/', GabaritoImportarView.as_view(), name='provas_fisicas_gab'),
    path('provas-fisicas/<uuid:pk>/correcoes/<uuid:aluno_id>/confirmar-omr', ConfirmarOmrView.as_view(), name='provas_fisicas_confirmar_omr_no_slash'),
    path('provas-fisicas/<uuid:pk>/correcoes/<uuid:aluno_id>/confirmar-omr/', ConfirmarOmrView.as_view(), name='provas_fisicas_confirmar_omr'),
    path('provas-fisicas/<uuid:pk>/folhas-pendentes/', FolhasPendentesView.as_view(), name='folhas_pendentes'),
    path('provas-fisicas/<uuid:pk>/folhas-pendentes/<uuid:fid>/', FolhasPendentesView.as_view(), name='folhas_pendentes_detalhe'),
    path('provas-fisicas/<uuid:pk>/folhas-pendentes/<uuid:fid>/imagem/', FolhasPendentesView.as_view(), name='folhas_pendentes_imagem'),
    path('provas-fisicas/gabaritos-guardados', GabaritosGuardadosView.as_view(), name='gabaritos_guardados_no_slash'),
    path('provas-fisicas/gabaritos-guardados/', GabaritosGuardadosView.as_view(), name='gabaritos_guardados'),
    path('provas-fisicas/gabaritos-guardados/<uuid:pk>/', GabaritosGuardadosView.as_view(), name='gabaritos_guardados_detalhe'),
    path('provas-fisicas/<uuid:pk>/lista-notas', ListaNotasAvaliacaoView.as_view(), name='provas_fisicas_lista_no_slash'),
    path('provas-fisicas/<uuid:pk>/lista-notas/', ListaNotasAvaliacaoView.as_view(), name='provas_fisicas_lista'),
    path('provas-fisicas/<uuid:pk>/folhas-corrigidas', FolhasCorrigidasPdfView.as_view(), name='provas_fisicas_pdf_no_slash'),
    path('provas-fisicas/<uuid:pk>/folhas-corrigidas/', FolhasCorrigidasPdfView.as_view(), name='provas_fisicas_pdf'),
    path('provas-fisicas/<uuid:pk>/leitura-omr', LeituraOmrView.as_view(), name='provas_fisicas_omr_no_slash'),
    path('provas-fisicas/<uuid:pk>/leitura-omr/', LeituraOmrView.as_view(), name='provas_fisicas_omr'),
    path('provas-fisicas', ProvasFisicasView.as_view(), name='provas_fisicas_no_slash'),
    path('provas-fisicas/', ProvasFisicasView.as_view(), name='provas_fisicas'),
    path('provas-fisicas/imagens/<uuid:img_id>', CorrecaoImagemFicheiroView.as_view(), name='provas_fisicas_img_no_slash'),
    path('provas-fisicas/imagens/<uuid:img_id>/', CorrecaoImagemFicheiroView.as_view(), name='provas_fisicas_img'),
    path('provas-fisicas/<uuid:pk>', ProvaFisicaDetalheView.as_view(), name='provas_fisicas_det_no_slash'),
    path('provas-fisicas/<uuid:pk>/', ProvaFisicaDetalheView.as_view(), name='provas_fisicas_det'),
    path('provas-fisicas/<uuid:pk>/lancar', LancarCorrecoesView.as_view(), name='provas_fisicas_lancar_no_slash'),
    path('provas-fisicas/<uuid:pk>/lancar/', LancarCorrecoesView.as_view(), name='provas_fisicas_lancar'),
    path('provas-fisicas/<uuid:pk>/correcoes/<uuid:aluno_id>', CorrecaoAlunoView.as_view(), name='provas_fisicas_corr_no_slash'),
    path('provas-fisicas/<uuid:pk>/correcoes/<uuid:aluno_id>/', CorrecaoAlunoView.as_view(), name='provas_fisicas_corr'),
    path('provas-fisicas/<uuid:pk>/correcoes/<uuid:aluno_id>/imagens', CorrecaoImagemUploadView.as_view(), name='provas_fisicas_up_no_slash'),
    path('provas-fisicas/<uuid:pk>/correcoes/<uuid:aluno_id>/imagens/', CorrecaoImagemUploadView.as_view(), name='provas_fisicas_up'),
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
