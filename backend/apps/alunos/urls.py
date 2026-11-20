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

from .views_me import AlunoMeCalendarioExamesPdfView, AlunoMeCalendarioExamesView, AlunoMeAnosView, AlunoMeFaltasPdfView, AlunoMeFaltasView, AlunoMeFaltasXlsxView

router = OptionalSlashRouter()
router.register(r'presencas', PresencaAlunoViewSet, basename='alunos-presencas')
router.register(r'transferencias', TransferenciaAnulacaoViewSet, basename='alunos-transferencias')
router.register(r'', AlunoViewSet, basename='alunos')

from .views_estatistica_inicio_ano import (
    EstatisticaInicioAnoTurmaView, EstatisticaInicioAnoClasseView,
    EstatisticaInicioAnoEscolaView, EstatisticaInicioAnoMinhasView,
)

urlpatterns = [
    path('estatistica-inicio-ano/minhas', EstatisticaInicioAnoMinhasView.as_view(), name='est_inicio_ano_minhas'),
    path('estatistica-inicio-ano/turma/<uuid:turma_id>', EstatisticaInicioAnoTurmaView.as_view(), name='est_inicio_ano_turma'),
    path('estatistica-inicio-ano/turma/<uuid:turma_id>/<str:formato>', EstatisticaInicioAnoTurmaView.as_view(), name='est_inicio_ano_turma_fmt'),
    path('estatistica-inicio-ano/classe', EstatisticaInicioAnoClasseView.as_view(), name='est_inicio_ano_classe'),
    path('estatistica-inicio-ano/classe/<str:formato>', EstatisticaInicioAnoClasseView.as_view(), name='est_inicio_ano_classe_fmt'),
    path('estatistica-inicio-ano/escola', EstatisticaInicioAnoEscolaView.as_view(), name='est_inicio_ano_escola'),
    path('estatistica-inicio-ano/escola/<str:formato>', EstatisticaInicioAnoEscolaView.as_view(), name='est_inicio_ano_escola_fmt'),
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
    path('me/calendario-exames', AlunoMeCalendarioExamesView.as_view(), name='alunos_me_cal_exames_no_slash'),
    path('me/calendario-exames/', AlunoMeCalendarioExamesView.as_view(), name='alunos_me_cal_exames'),
    path('me/calendario-exames/pdf', AlunoMeCalendarioExamesPdfView.as_view(), name='alunos_me_cal_exames_pdf_no_slash'),
    path('me/calendario-exames/pdf/', AlunoMeCalendarioExamesPdfView.as_view(), name='alunos_me_cal_exames_pdf'),
    path('me/anos', AlunoMeAnosView.as_view(), name='alunos_me_anos_no_slash'),
    path('me/anos/', AlunoMeAnosView.as_view(), name='alunos_me_anos'),
    path('me/faltas', AlunoMeFaltasView.as_view(), name='alunos_me_faltas_no_slash'),
    path('me/faltas/', AlunoMeFaltasView.as_view(), name='alunos_me_faltas'),
    path('me/faltas/xlsx', AlunoMeFaltasXlsxView.as_view(), name='alunos_me_faltas_xlsx_no_slash'),
    path('me/faltas/xlsx/', AlunoMeFaltasXlsxView.as_view(), name='alunos_me_faltas_xlsx'),
    path('me/faltas/pdf', AlunoMeFaltasPdfView.as_view(), name='alunos_me_faltas_pdf_no_slash'),
    path('me/faltas/pdf/', AlunoMeFaltasPdfView.as_view(), name='alunos_me_faltas_pdf'),
    path('', include(router.urls)),
]
