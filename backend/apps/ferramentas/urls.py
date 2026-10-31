from django.urls import path
from .views import (
    api_gateway_stats,
    api_enviar_sms,
    api_historico_sms,
    api_enviar_whatsapp,
    api_historico_whatsapp,
    api_iniciar_pagamento_movel,
    api_transacoes_moveis,
    api_liquidar_pagamento_manual,
    api_reconciliacao_sms_webhook,
    api_reconciliacoes_lista,
    api_reconciliacao_associar,
    api_configuracao_gateway,
    api_simulador_ussd,
    prompt_gateway_pagina,
    prompt_gateway_descarregar,
    prompt_gateway_api,
    api_provas_anti_ia_codificar,
    api_provas_anti_ia_listar,
    api_provas_anti_ia_detalhe,
    api_provas_anti_ia_descarregar_pdf,
    api_provas_anti_ia_simular_ia,
    api_provas_anti_ia_verificar,
    api_provas_anti_ia_alertas,
    api_provas_anti_ia_definicoes,
    api_provas_anti_ia_definicoes_previa,
)

urlpatterns = [
    # Métricas e Painel de Operação
    path('stats', api_gateway_stats, name='api_gateway_stats_sem_barra'),
    path('stats/', api_gateway_stats, name='api_gateway_stats'),

    # SMS: Envio e Histórico
    path('sms/enviar', api_enviar_sms, name='api_enviar_sms_sem_barra'),
    path('sms/enviar/', api_enviar_sms, name='api_enviar_sms'),
    path('sms/historico', api_historico_sms, name='api_historico_sms_sem_barra'),
    path('sms/historico/', api_historico_sms, name='api_historico_sms'),

    # WhatsApp: Envio e Histórico
    path('whatsapp/enviar', api_enviar_whatsapp, name='api_enviar_whatsapp_sem_barra'),
    path('whatsapp/enviar/', api_enviar_whatsapp, name='api_enviar_whatsapp'),
    path('whatsapp/historico', api_historico_whatsapp, name='api_historico_whatsapp_sem_barra'),
    path('whatsapp/historico/', api_historico_whatsapp, name='api_historico_whatsapp'),

    # Pagamentos Móveis (M-Pesa e e-Mola STK Push)
    path('pagamentos-moveis/iniciar', api_iniciar_pagamento_movel, name='api_iniciar_pagamento_movel_sem_barra'),
    path('pagamentos-moveis/iniciar/', api_iniciar_pagamento_movel, name='api_iniciar_pagamento_movel'),
    path('pagamentos-moveis/transacoes', api_transacoes_moveis, name='api_transacoes_moveis_sem_barra'),
    path('pagamentos-moveis/transacoes/', api_transacoes_moveis, name='api_transacoes_moveis'),

    # Pagamento Manual de Propinas (Comprovativo M-Pesa / Banco)
    path('pagamentos/liquidar-manual', api_liquidar_pagamento_manual, name='api_liquidar_pagamento_manual_sem_barra'),
    path('pagamentos/liquidar-manual/', api_liquidar_pagamento_manual, name='api_liquidar_pagamento_manual'),

    # Reconciliação Automática por SMS M-Pesa / e-Mola (Custo Zero)
    path('reconciliacao/sms-webhook', api_reconciliacao_sms_webhook, name='api_reconciliacao_sms_webhook_sem_barra'),
    path('reconciliacao/sms-webhook/', api_reconciliacao_sms_webhook, name='api_reconciliacao_sms_webhook'),
    path('reconciliacao/lista', api_reconciliacoes_lista, name='api_reconciliacoes_lista_sem_barra'),
    path('reconciliacao/lista/', api_reconciliacoes_lista, name='api_reconciliacoes_lista'),
    path('reconciliacao/associar', api_reconciliacao_associar, name='api_reconciliacao_associar_sem_barra'),
    path('reconciliacao/associar/', api_reconciliacao_associar, name='api_reconciliacao_associar'),

    # Configurações do Gateway (Android SIM, WhatsApp, M-Pesa)
    path('configuracao', api_configuracao_gateway, name='api_configuracao_gateway_sem_barra'),
    path('configuracao/', api_configuracao_gateway, name='api_configuracao_gateway'),

    # Simulador USSD
    path('ussd/simular', api_simulador_ussd, name='api_simulador_ussd_sem_barra'),
    path('ussd/simular/', api_simulador_ussd, name='api_simulador_ussd'),

    # Rotas de Compatibilidade: Página Web, Download e Prompt
    path('prompt-gateway', prompt_gateway_pagina, name='prompt_gateway_pagina_sem_slash'),
    path('prompt-gateway/', prompt_gateway_pagina, name='prompt_gateway_pagina'),
    path('prompt-gateway/descarregar', prompt_gateway_descarregar, name='prompt_gateway_descarregar_sem_slash'),
    path('prompt-gateway/descarregar/', prompt_gateway_descarregar, name='prompt_gateway_descarregar'),
    path('prompt-gateway/conteudo', prompt_gateway_api, name='prompt_gateway_api_conteudo'),
    path('prompt-gateway/conteudo/', prompt_gateway_api, name='prompt_gateway_api_conteudo_slash'),

    # =================================================================
    # BLINDAGEM ANTI-IA DE PROVAS E AVALIAÇÕES (QR Code + Barcode)
    # =================================================================
    path('provas-anti-ia/codificar', api_provas_anti_ia_codificar, name='api_provas_anti_ia_codificar_sem_barra'),
    path('provas-anti-ia/codificar/', api_provas_anti_ia_codificar, name='api_provas_anti_ia_codificar'),
    path('provas-anti-ia/alertas/', api_provas_anti_ia_alertas, name='api_provas_anti_ia_alertas'),
    path('provas-anti-ia/definicoes/', api_provas_anti_ia_definicoes, name='api_provas_anti_ia_definicoes'),
    path('provas-anti-ia/definicoes/previa/', api_provas_anti_ia_definicoes_previa, name='api_provas_anti_ia_definicoes_previa'),
    path('provas-anti-ia/lista', api_provas_anti_ia_listar, name='api_provas_anti_ia_listar_sem_barra'),
    path('provas-anti-ia/lista/', api_provas_anti_ia_listar, name='api_provas_anti_ia_listar'),
    path('provas-anti-ia/<str:prova_id>/detalhe', api_provas_anti_ia_detalhe, name='api_provas_anti_ia_detalhe_sem_barra'),
    path('provas-anti-ia/<str:prova_id>/detalhe/', api_provas_anti_ia_detalhe, name='api_provas_anti_ia_detalhe'),
    path('provas-anti-ia/<str:prova_id>/descarregar-pdf', api_provas_anti_ia_descarregar_pdf, name='api_provas_anti_ia_descarregar_pdf_sem_barra'),
    path('provas-anti-ia/<str:prova_id>/descarregar-pdf/', api_provas_anti_ia_descarregar_pdf, name='api_provas_anti_ia_descarregar_pdf'),
    path('provas-anti-ia/<str:prova_id>/simular-ia', api_provas_anti_ia_simular_ia, name='api_provas_anti_ia_simular_ia_sem_barra'),
    path('provas-anti-ia/<str:prova_id>/simular-ia/', api_provas_anti_ia_simular_ia, name='api_provas_anti_ia_simular_ia'),
    path('provas-anti-ia/verificar/<str:codigo_autenticidade>', api_provas_anti_ia_verificar, name='api_provas_anti_ia_verificar_sem_barra'),
    path('provas-anti-ia/verificar/<str:codigo_autenticidade>/', api_provas_anti_ia_verificar, name='api_provas_anti_ia_verificar'),
]
