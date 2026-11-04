from django.urls import path, include
from common.routers import OptionalSlashRouter
from .views_transferencias import TransferenciaAnulacaoViewSet, VerificarTransferenciaView
from .views import (
    PresencaAlunoViewSet,
    AlunoViewSet,
    AlunoStatsView,
    AlunoPerfilMeView,
    AlunoMeNotasView,
    AlunoMePagamentosView
)

from .views_me import AlunoMeAnosView, AlunoMeFaltasPdfView

router = OptionalSlashRouter()
router.register(r'presencas', PresencaAlunoViewSet, basename='alunos-presencas')
router.register(r'transferencias', TransferenciaAnulacaoViewSet, basename='alunos-transferencias')
router.register(r'', AlunoViewSet, basename='alunos')

urlpatterns = [
    path('transferencias/verificar/<str:codigo>/', VerificarTransferenciaView.as_view(), name='transferencias_verificar'),
    path('transferencias/verificar/<str:codigo>', VerificarTransferenciaView.as_view(), name='transferencias_verificar_no_slash'),
    path('stats', AlunoStatsView.as_view(), name='alunos_stats_no_slash'),
    path('stats/', AlunoStatsView.as_view(), name='alunos_stats'),
    path('perfil/me', AlunoPerfilMeView.as_view(), name='alunos_perfil_me_no_slash'),
    path('perfil/me/', AlunoPerfilMeView.as_view(), name='alunos_perfil_me'),
    path('me/notas', AlunoMeNotasView.as_view(), name='alunos_me_notas_no_slash'),
    path('me/notas/', AlunoMeNotasView.as_view(), name='alunos_me_notas'),
    path('me/pagamentos', AlunoMePagamentosView.as_view(), name='alunos_me_pagamentos_no_slash'),
    path('me/pagamentos/', AlunoMePagamentosView.as_view(), name='alunos_me_pagamentos'),
    path('me/anos', AlunoMeAnosView.as_view(), name='alunos_me_anos_no_slash'),
    path('me/anos/', AlunoMeAnosView.as_view(), name='alunos_me_anos'),
    path('me/faltas/pdf', AlunoMeFaltasPdfView.as_view(), name='alunos_me_faltas_pdf_no_slash'),
    path('me/faltas/pdf/', AlunoMeFaltasPdfView.as_view(), name='alunos_me_faltas_pdf'),
    path('', include(router.urls)),
]
