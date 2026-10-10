from django.urls import path, include
from common.routers import OptionalSlashRouter
from .views import (
    ProfessorViewSet,
    AlocarProfessorView,
    ProfessorStatsView,
    MinhasTurmasView,
    MeuPerfilView,
    CadernetaCompletaView,
    CadernetaPDFView,
    CadernetaXLSXView,
    CadernetaDOCXView,
)

router = OptionalSlashRouter()
router.register(r'', ProfessorViewSet, basename='professores')

urlpatterns = [
    path('stats', ProfessorStatsView.as_view(), name='professores_stats_no_slash'),
    path('stats/', ProfessorStatsView.as_view(), name='professores_stats'),
    path('minhas-turmas', MinhasTurmasView.as_view(), name='professores_minhas_turmas_no_slash'),
    path('minhas-turmas/', MinhasTurmasView.as_view(), name='professores_minhas_turmas'),
    path('meu-perfil', MeuPerfilView.as_view(), name='professores_meu_perfil_no_slash'),
    path('meu-perfil/', MeuPerfilView.as_view(), name='professores_meu_perfil'),
    path('alocar', AlocarProfessorView.as_view(), name='professores_alocar_no_slash'),
    path('alocar/', AlocarProfessorView.as_view(), name='professores_alocar'),
    path('alocar/<uuid:alocacao_id>', AlocarProfessorView.as_view(), name='professores_dealocar_no_slash'),
    path('alocar/<uuid:alocacao_id>/', AlocarProfessorView.as_view(), name='professores_dealocar'),
    path('caderneta/<uuid:alocacao_id>/completa', CadernetaCompletaView.as_view(), name='caderneta_completa_no_slash'),
    path('caderneta/<uuid:alocacao_id>/completa/', CadernetaCompletaView.as_view(), name='caderneta_completa'),
    path('caderneta/<uuid:alocacao_id>/pdf', CadernetaPDFView.as_view(), name='caderneta_pdf_no_slash'),
    path('caderneta/<uuid:alocacao_id>/pdf/', CadernetaPDFView.as_view(), name='caderneta_pdf'),
    path('caderneta/<uuid:alocacao_id>/xlsx', CadernetaXLSXView.as_view(), name='caderneta_xlsx_no_slash'),
    path('caderneta/<uuid:alocacao_id>/xlsx/', CadernetaXLSXView.as_view(), name='caderneta_xlsx'),
    path('caderneta/<uuid:alocacao_id>/docx', CadernetaDOCXView.as_view(), name='caderneta_docx_no_slash'),
    path('caderneta/<uuid:alocacao_id>/docx/', CadernetaDOCXView.as_view(), name='caderneta_docx'),
    path('', include(router.urls)),
]

