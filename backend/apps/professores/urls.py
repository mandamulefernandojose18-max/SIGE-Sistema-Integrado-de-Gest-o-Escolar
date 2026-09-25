from django.urls import path, include
from common.routers import OptionalSlashRouter
from .views import (
    ProfessorViewSet,
    AlocarProfessorView,
    ProfessorStatsView,
    MinhasTurmasView,
    MeuPerfilView,
    CadernetaCompletaView
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
    path('', include(router.urls)),
]
