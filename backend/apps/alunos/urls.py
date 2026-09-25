from django.urls import path, include
from common.routers import OptionalSlashRouter
from .views import (
    AlunoViewSet,
    AlunoStatsView,
    AlunoPerfilMeView,
    AlunoMeNotasView,
    AlunoMePagamentosView
)

router = OptionalSlashRouter()
router.register(r'', AlunoViewSet, basename='alunos')

urlpatterns = [
    path('stats', AlunoStatsView.as_view(), name='alunos_stats_no_slash'),
    path('stats/', AlunoStatsView.as_view(), name='alunos_stats'),
    path('perfil/me', AlunoPerfilMeView.as_view(), name='alunos_perfil_me_no_slash'),
    path('perfil/me/', AlunoPerfilMeView.as_view(), name='alunos_perfil_me'),
    path('me/notas', AlunoMeNotasView.as_view(), name='alunos_me_notas_no_slash'),
    path('me/notas/', AlunoMeNotasView.as_view(), name='alunos_me_notas'),
    path('me/pagamentos', AlunoMePagamentosView.as_view(), name='alunos_me_pagamentos_no_slash'),
    path('me/pagamentos/', AlunoMePagamentosView.as_view(), name='alunos_me_pagamentos'),
    path('', include(router.urls)),
]
