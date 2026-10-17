from django.urls import path
from .views import prompt_gateway_pagina, prompt_gateway_descarregar, prompt_gateway_api

urlpatterns = [
    path('prompt-gateway', prompt_gateway_pagina, name='prompt_gateway_pagina_sem_slash'),
    path('prompt-gateway/', prompt_gateway_pagina, name='prompt_gateway_pagina'),
    path('prompt-gateway/descarregar', prompt_gateway_descarregar, name='prompt_gateway_descarregar_sem_slash'),
    path('prompt-gateway/descarregar/', prompt_gateway_descarregar, name='prompt_gateway_descarregar'),
    path('prompt-gateway/conteudo', prompt_gateway_api, name='prompt_gateway_api_conteudo'),
    path('prompt-gateway/conteudo/', prompt_gateway_api, name='prompt_gateway_api_conteudo_slash'),
]
