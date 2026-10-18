from django.urls import path
from .views import (
    api_gateway_stats,
    api_enviar_sms,
    api_historico_sms,
    api_iniciar_pagamento_movel,
    api_transacoes_moveis,
    api_simulador_ussd,
    prompt_gateway_pagina,
    prompt_gateway_descarregar,
    prompt_gateway_api
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

    # Pagamentos Móveis (M-Pesa e e-Mola)
    path('pagamentos-moveis/iniciar', api_iniciar_pagamento_movel, name='api_iniciar_pagamento_movel_sem_barra'),
    path('pagamentos-moveis/iniciar/', api_iniciar_pagamento_movel, name='api_iniciar_pagamento_movel'),
    path('pagamentos-moveis/transacoes', api_transacoes_moveis, name='api_transacoes_moveis_sem_barra'),
    path('pagamentos-moveis/transacoes/', api_transacoes_moveis, name='api_transacoes_moveis'),

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
]
