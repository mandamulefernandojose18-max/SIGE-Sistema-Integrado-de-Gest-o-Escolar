# 🔌 Catálogo de Endpoints da API RESTful — SIGE Backend

> **Documento Oficial de Endpoints da API**  
> **Versão:** 2.5.0  
> **Consulte o documento completo e detalhado em:** `docs/REFERENCIA_COMPLETA_API.md`  
> **Documentação Swagger UI Interativa:** `https://sigesaas.duckdns.org/api/docs/`  
> **Documentação Técnica ReDoc:** `https://sigesaas.duckdns.org/api/redoc/`  

---

## 📌 Resumo dos Grupos de Rotas da API (`/api/v1/`)

1. **Saúde e Portal Público:**
   - `GET /health/`: Verificação de saúde da API (`status: ok`, versão `2.5.0`).
   - `GET /api/v1/public/escolas/`: Escolas com inscrições abertas.
   - `POST /api/v1/public/inscrever-aluno/`: Auto-inscrição de alunos sem login.
   - `GET /api/v1/certificados/verificar/<codigo>/`: Validador público de QR Code.

2. **Autenticação e Perfis (`apps.accounts`):**
   - `POST /api/v1/auth/login/`: Login inteligente (e-mail, username, códigos oficiais `GD`, `DP`, `SECR`, `PR`, `DT`, `DC`, Aluno).
   - `POST /api/v1/auth/refresh/`: Renovação de token JWT.
   - `GET /api/v1/auth/me/`: Dados do usuário e escola conectada.
   - `POST /api/v1/auth/minha-senha/`: Troca de senha pelo próprio usuário.
   - `POST /api/v1/auth/usuarios/<id>/redefinir-senha/`: Redefinição de senha de terceiros.

3. **Administração Master SaaS (`apps.tenants`):**
   - `GET /api/v1/saas-admin/metrics/`: Métricas de MRR, ARR, Churn e volumetria.
   - `GET /api/v1/saas-admin/escolas/`: Gestão e cadastro de escolas.
   - `POST /api/v1/saas-admin/escolas/<id>/toggle-status/`: Ativação/suspensão de escolas.
   - `GET /api/v1/saas-admin/planos/`: Catálogo de planos SaaS.
   - `POST /api/v1/saas-admin/verificar-expiracoes/`: Varredura de assinaturas vencidas.

4. **Administração da Escola e Turmas (`apps.turmas`):**
   - `GET/PUT /api/v1/escola-admin/info/`: Parametrização escolar e logótipo Base64.
   - `POST /api/v1/escola-admin/toggle-notas/`: Bloqueio de visualização de notas pelos alunos.
   - `GET/POST /api/v1/turmas/`: CRUD de turmas e ocupação em tempo real.
   - `POST /api/v1/turmas/criar-lote/`: Criação de turmas em massa.
   - `POST /api/v1/turmas/distribuir-automaticamente/`: Formação automática de turmas.
   - `POST /api/v1/turmas/renumerar-turmas/`: Padronização de nomes das turmas.
   - `POST /api/v1/turmas/<id>/homologar-directores/`: Homologação de cargos DT e DC.

5. **Alunos, Professores e Disciplinas:**
   - `GET/POST /api/v1/alunos/`: Matrículas, biografia e estatísticas demográficas.
   - `POST /api/v1/alunos/<id>/transferir/`: Transferência com migração automática de notas.
   - `GET/POST /api/v1/professores/`: Gestão docente, horas normais vs. extras.
   - `POST /api/v1/professores/alocar/`: Alocação docente a turma/disciplina.
   - `GET /api/v1/professores/caderneta/<alocacao_id>/completa/`: Caderneta com os 3 trimestres.
   - `GET/POST /api/v1/disciplinas/`: Currículo e ranking de reprovação.

6. **Notas, Pautas e Actas de Conselho:**
   - `GET/POST /api/v1/notas/`: Lançamento individual e em lote com validação MEC.
   - `GET/POST /api/v1/notas/prazos-trimestres/`: Calendário de notas.
   - `POST /api/v1/notas/autorizar-desbloqueio/`: Autorizações temporárias de edição.
   - `POST /api/v1/pautas/gerar/`: Consolidação de pautas de turma.
   - `GET /api/v1/pautas/turma/<id>/completa/`: Pauta geral com quadro do MEC.
   - `GET /api/v1/pautas/turma/<id>/acta/`: Acta oficial com valores por extenso.

7. **Financeiro, Material Escolar, Certificados e Impressão:**
   - `GET/POST /api/v1/pagamentos/`: Cobrança em lote por turma e quitação multicanal.
   - `GET/POST /api/v1/material-escolar/`: Biblioteca didática até 15 MB.
   - `GET/POST /api/v1/certificados/`: Emissão de certificados com QR Code.
   - `GET /api/v1/documentos/<tipo>/<id>/(pdf|docx|xlsx)`: Emissão em PDF, Word e Excel.
   - `GET /api/v1/documentos/lote/turma/<id>/(pdf|docx|xlsx)`: Emissão em lote para a turma inteira.