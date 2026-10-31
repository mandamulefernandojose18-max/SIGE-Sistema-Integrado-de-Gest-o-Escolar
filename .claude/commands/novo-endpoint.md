---
description: Cria um novo endpoint DRF do SIGE (serializer, view, rota, teste e documentação) no padrão do projecto.
---

# Novo endpoint: $ARGUMENTS

1. Identifica a app em `backend/apps/` e lê um endpoint vizinho para copiar o estilo.
2. Cria/actualiza, por esta ordem:
   - modelo (com `escola_id`) e migração, se necessário;
   - serializer (a escola vem do utilizador autenticado, nunca do cliente);
   - view/viewset com `get_queryset` filtrado pelo tenant e permissões por perfil;
   - rota em `urls.py` sob `/api/v1/`;
   - anotações `drf-spectacular` para o Swagger;
   - testes em `backend/tests/` (isolamento entre escolas incluído), sem dados fictícios persistentes.
3. Corre `python manage.py check`, `makemigrations --check` e `pytest` na app.
4. Actualiza `docs/DOCUMENTACAO_COMPLETA_DO_SISTEMA.md` com o endpoint.
5. Invoca o subagente `auditor-tenant` sobre o resultado e corrige o que apontar.
6. Não faças commit nem deploy sem o utilizador pedir (usa `/deploy`).
