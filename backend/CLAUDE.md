# backend/ — Convenções Django (SIGE)

- Apps em `apps/` (accounts, alunos, notas, pautas, turmas, tenants, ...); utilitários em `common/`; settings em `config/settings/{base,development,production}.py`.
- Em desenvolvimento usar `DJANGO_SETTINGS_MODULE=config.settings.development` (o `manage.py` assume `production` por omissão).
- Todo modelo institucional tem `escola_id`; toda query/viewset filtra pelo tenant (`TenantIsolationMiddleware` ou filtro explícito). Nunca devolver dados de outra escola.
- Notas: 0–20, fórmulas MT1/MT2/MT3, MEC, MFD; centralizar o cálculo, não duplicar em views/serializers.
- Documentos: ReportLab (PDF), python-docx e openpyxl em Times New Roman; notas negativas a vermelho.
- Nova rota/endpoint: serializer + view + `urls.py` + teste em `tests/` + schema OpenAPI (`drf-spectacular`) + `docs/`.
- Migrações: `makemigrations --check` tem de passar; nunca editar migrações já aplicadas em produção.
- Testes: `pytest` (SQLite em memória). Proibido seeds/fixtures com dados fictícios de alunos, notas ou professores.
- Nunca ler nem imprimir `.env`; nunca escrever IPs em código ou docs.
