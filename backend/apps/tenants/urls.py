from django.urls import path, re_path, include
from common.routers import OptionalSlashRouter
from .views import (
    GeografiaView,
    SaaSMetricsView,
    PlanoViewSet,
    EscolaViewSet,
    VerificarExpiracoesView,
    EscolaAdminInfoView,
    ToggleNotasView,
    UsuariosCredenciaisView,
    MinhaEscolaComprovativoView,
    AnoLectivoViewSet,
    ClassesExamesConfigView
)

from .saas_views import (
    SaasResumoView,
    SaasAssinaturasListView,
    SaasAssinaturaDetalheView,
    SaasPagamentosPendentesView,
    SaasConfirmarPagamentoView,
    SaasRejeitarPagamentoView,
    SaasProrrogarDataLimiteView,
    SaasSuspenderReactivarManualView,
    SaasRotinaDiariaManualView,
    MinhaAssinaturaView,
    MinhaAssinaturaConfigurarView,
    RegistarPagamentoInstituicaoView,
    SaasCoordenadasPagamentoView,
    SaasCalcularAdiantamentoView,
    SaasPlanosDisponiveisView
)

router = OptionalSlashRouter()
router.register(r'escolas', EscolaViewSet, basename='saas_escola')
router.register(r'planos', PlanoViewSet, basename='saas_plano')
router.register(r'anos-letivos', AnoLectivoViewSet, basename='saas_ano_letivo')

escola_router = OptionalSlashRouter()
escola_router.register(r'anos-letivos', AnoLectivoViewSet, basename='escola_ano_letivo')

saas_admin_urls = [
    path('metrics', SaaSMetricsView.as_view(), name='saas_metrics_no_slash'),
    path('metrics/', SaaSMetricsView.as_view(), name='saas_metrics'),
    path('verificar-expiracoes', VerificarExpiracoesView.as_view(), name='saas_verificar_expiracoes_no_slash'),
    path('verificar-expiracoes/', VerificarExpiracoesView.as_view(), name='saas_verificar_expiracoes'),
    path('minha-escola/comprovativo-contrato', MinhaEscolaComprovativoView.as_view(), name='saas_minha_escola_comprovativo_no_slash'),
    path('minha-escola/comprovativo-contrato/', MinhaEscolaComprovativoView.as_view(), name='saas_minha_escola_comprovativo'),
    path('', include(router.urls)),
]

escola_admin_urls = [
    path('info', EscolaAdminInfoView.as_view(), name='escola_admin_info_no_slash'),
    path('info/', EscolaAdminInfoView.as_view(), name='escola_admin_info'),
    path('toggle-notas', ToggleNotasView.as_view(), name='escola_toggle_notas_no_slash'),
    path('toggle-notas/', ToggleNotasView.as_view(), name='escola_toggle_notas'),
    path('usuarios-credenciais', UsuariosCredenciaisView.as_view(), name='escola_usuarios_credenciais_no_slash'),
    path('usuarios-credenciais/', UsuariosCredenciaisView.as_view(), name='escola_usuarios_credenciais'),
    path('classes-exames', ClassesExamesConfigView.as_view(), name='escola_classes_exames_no_slash'),
    path('classes-exames/', ClassesExamesConfigView.as_view(), name='escola_classes_exames'),
    path('', include(escola_router.urls)),
]

saas_pagamentos_urls = [
    path('resumo', SaasResumoView.as_view(), name='saas_resumo_no_slash'),
    path('resumo/', SaasResumoView.as_view(), name='saas_resumo'),
    path('assinaturas', SaasAssinaturasListView.as_view(), name='saas_assinaturas_list_no_slash'),
    path('assinaturas/', SaasAssinaturasListView.as_view(), name='saas_assinaturas_list'),
    path('assinaturas/<uuid:pk>', SaasAssinaturaDetalheView.as_view(), name='saas_assinatura_detalhe_no_slash'),
    path('assinaturas/<uuid:pk>/', SaasAssinaturaDetalheView.as_view(), name='saas_assinatura_detalhe'),
    path('assinaturas/<uuid:pk>/configurar', SaasAssinaturaDetalheView.as_view(), name='saas_assinatura_config_no_slash'),
    path('assinaturas/<uuid:pk>/configurar/', SaasAssinaturaDetalheView.as_view(), name='saas_assinatura_config'),
    path('pagamentos/pendentes', SaasPagamentosPendentesView.as_view(), name='saas_pagamentos_pendentes_no_slash'),
    path('pagamentos/pendentes/', SaasPagamentosPendentesView.as_view(), name='saas_pagamentos_pendentes'),
    path('pagamentos/<uuid:pk>/confirmar', SaasConfirmarPagamentoView.as_view(), name='saas_pagamento_confirmar_no_slash'),
    path('pagamentos/<uuid:pk>/confirmar/', SaasConfirmarPagamentoView.as_view(), name='saas_pagamento_confirmar'),
    path('pagamentos/<uuid:pk>/rejeitar', SaasRejeitarPagamentoView.as_view(), name='saas_pagamento_rejeitar_no_slash'),
    path('pagamentos/<uuid:pk>/rejeitar/', SaasRejeitarPagamentoView.as_view(), name='saas_pagamento_rejeitar'),
    path('faturas/<uuid:pk>/prorrogar', SaasProrrogarDataLimiteView.as_view(), name='saas_fatura_prorrogar_no_slash'),
    path('faturas/<uuid:pk>/prorrogar/', SaasProrrogarDataLimiteView.as_view(), name='saas_fatura_prorrogar'),
    path('instituicoes/<uuid:pk>/suspender-reactivar', SaasSuspenderReactivarManualView.as_view(), name='saas_suspender_reactivar_no_slash'),
    path('instituicoes/<uuid:pk>/suspender-reactivar/', SaasSuspenderReactivarManualView.as_view(), name='saas_suspender_reactivar'),
    path('rotina-diaria', SaasRotinaDiariaManualView.as_view(), name='saas_rotina_diaria_no_slash'),
    path('rotina-diaria/', SaasRotinaDiariaManualView.as_view(), name='saas_rotina_diaria'),
    path('minha-assinatura', MinhaAssinaturaView.as_view(), name='saas_minha_assinatura_no_slash'),
    path('minha-assinatura/', MinhaAssinaturaView.as_view(), name='saas_minha_assinatura'),
    path('minha-assinatura/configurar', MinhaAssinaturaConfigurarView.as_view(), name='saas_minha_assinatura_config_no_slash'),
    path('minha-assinatura/configurar/', MinhaAssinaturaConfigurarView.as_view(), name='saas_minha_assinatura_config'),
    path('calcular-adiantamento', SaasCalcularAdiantamentoView.as_view(), name='saas_calcular_adiantamento_no_slash'),
    path('calcular-adiantamento/', SaasCalcularAdiantamentoView.as_view(), name='saas_calcular_adiantamento'),
    path('planos-disponiveis', SaasPlanosDisponiveisView.as_view(), name='saas_planos_disponiveis_no_slash'),
    path('planos-disponiveis/', SaasPlanosDisponiveisView.as_view(), name='saas_planos_disponiveis'),
    path('registar-pagamento', RegistarPagamentoInstituicaoView.as_view(), name='saas_registar_pagamento_no_slash'),
    path('registar-pagamento/', RegistarPagamentoInstituicaoView.as_view(), name='saas_registar_pagamento'),
    path('coordenadas', SaasCoordenadasPagamentoView.as_view(), name='saas_coordenadas_no_slash'),
    path('coordenadas/', SaasCoordenadasPagamentoView.as_view(), name='saas_coordenadas'),
]

urlpatterns = [
    path('geografia', GeografiaView.as_view(), name='geografia_no_slash'),
    path('geografia/', GeografiaView.as_view(), name='geografia'),
    re_path(r'^saas-admin/?', include(saas_admin_urls)),
    re_path(r'^escola-admin/?', include(escola_admin_urls)),
    re_path(r'^saas/?', include(saas_pagamentos_urls)),
    path('', include(router.urls)),
]


