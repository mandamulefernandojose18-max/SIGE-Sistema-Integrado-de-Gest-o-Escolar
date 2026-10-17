# 🔌 Catálogo de Endpoints da API RESTful — SIGE (v2.5.0)

> **Especificação RESTful da API Backend**  
> **URL Base em Produção:** `https://sigesaas.duckdns.org/api/v1/`  
> **Swagger UI Interativo:** `https://sigesaas.duckdns.org/api/docs/`  
> **ReDoc:** `https://sigesaas.duckdns.org/api/redoc/`  
> **Autenticação:** HTTP Bearer Token JWT (`Authorization: Bearer <access_token>`)

---

## 1. Padrões de Comunicação e Envelopes JSON

### 1.1. Resposta de Sucesso Padrão
```json
{
  "success": true,
  "data": { ... },
  "message": "Operação realizada com sucesso."
}
```

### 1.2. Resposta de Erro Padronizada
```json
{
  "success": false,
  "error": "Descrição legível da falha",
  "detail": {
    "campo_invalido": ["Mensagem detalhada de validação"]
  }
}
```

### 1.3. Códigos de Status HTTP Utilizados
- `200 OK`: Consulta ou atualização bem-sucedida.
- `201 Created`: Criação de novo recurso (aluno, turma, pagamento, etc.).
- `204 No Content`: Exclusão bem-sucedida sem corpo de resposta.
- `400 Bad Request`: Parâmetros ou corpo da requisição inválidos.
- `401 Unauthorized`: Token JWT ausente, expirado ou inválido.
- `402 Payment Required`: Assinatura da escola expirada ou suspensa.
- `403 Forbidden`: Utilizador sem permissão RBAC para a operação.
- `404 Not Found`: Recurso não localizado para o tenant atual.
- `422 Unprocessable Entity`: Violação de regras pedagógicas do MEC ou integridade de dados.

---

## 2. Catálogo Completo dos Mais de 75 Endpoints

---

### 2.1. Saúde do Sistema e Portal Público

| Método | Endpoint | Permissão | Descrição e Parâmetros |
| :---: | :--- | :---: | :--- |
| `GET` | `/health/` | Pública | Retorna o status de saúde da API (`status: ok`, versão `2.5.0`). |
| `GET` | `/geografia/` | Pública | Retorna as 11 províncias e 161 distritos de Moçambique. |
| `GET` | `/api/v1/public/escolas/` | Pública | Lista escolas com inscrições abertas para auto-inscrição online. |
| `POST`| `/api/v1/public/inscrever-aluno/`| Pública | Realiza a auto-inscrição pública de um estudante e devolve a matrícula e código de acesso. |
| `GET` | `/api/v1/certificados/verificar/<codigo>/` | Pública | Valida a autenticidade de um documento pelo código `CERT-...` lido pelo QR Code. |

---

### 2.2. Autenticação e Gestão de Contas (`apps.accounts`)

| Método | Endpoint | Permissão | Descrição |
| :---: | :--- | :---: | :--- |
| `POST` | `/api/v1/auth/login/` | Pública | Autenticação inteligente (E-mail, Username, `GD`, `DP`, `SECR`, `PR`, `DT`, `DC` ou Aluno). |
| `POST` | `/api/v1/auth/refresh/` | Pública | Renova o Access Token JWT a partir do Refresh Token. |
| `GET` | `/api/v1/auth/me/` | Autenticado | Retorna os dados do utilizador logado e da sua escola (`tenant`). |
| `GET` | `/api/v1/auth/stats/` | Admin Escola | Retorna contagens de utilizadores por perfil na instituição. |
| `POST` | `/api/v1/auth/minha-senha/` | Autenticado | Permite ao utilizador corrente alterar a sua própria palavra-passe. |
| `POST` | `/api/v1/auth/usuarios/<uuid:user_id>/redefinir-senha/` | Admin Escola | Redefine a palavra-passe de um utilizador específico para o padrão inicial. |

---

### 2.3. Painel Master SaaS (`apps.tenants` — SuperAdmin)

| Método | Endpoint | Permissão | Descrição |
| :---: | :--- | :---: | :--- |
| `GET` | `/api/v1/saas-admin/metrics/` | `SUPERADMIN` | KPIs globais: MRR, ARR, Churn Rate, escolas ativas, alunos e professores. |
| `GET` | `/api/v1/saas-admin/escolas/` | `SUPERADMIN` | Lista todas as escolas cadastradas na plataforma. |
| `POST`| `/api/v1/saas-admin/escolas/` | `SUPERADMIN` | Cadastra nova escola e gera automaticamente as contas diretivas (`GD`, `DP`, `SECR`). |
| `GET` | `/api/v1/saas-admin/escolas/<uuid:pk>/` | `SUPERADMIN` | Detalhes cadastrais e contratuais de uma escola. |
| `PUT` | `/api/v1/saas-admin/escolas/<uuid:pk>/` | `SUPERADMIN` | Atualiza dados e plano de uma instituição. |
| `DELETE`| `/api/v1/saas-admin/escolas/<uuid:pk>/` | `SUPERADMIN` | Elimina definitivamente uma escola e seus registros associados. |
| `POST`| `/api/v1/saas-admin/escolas/<uuid:pk>/toggle-status/` | `SUPERADMIN` | Alterna o status da escola entre `ATIVA` e `SUSPENSA`. |
| `GET` | `/api/v1/saas-admin/escolas/<uuid:pk>/comprovativo-contrato/` | `SUPERADMIN` | Emite o comprovativo formal de assinatura em PDF com termos do plano. |
| `GET` | `/api/v1/saas-admin/planos/` | `SUPERADMIN` | Catálogo de planos de subscrição (`MENSAL`, `TRIMESTRAL`, `SEMESTRAL`, `ANUAL`). |
| `POST`| `/api/v1/saas-admin/planos/<uuid:pk>/preco/` | `SUPERADMIN` | Atualiza o valor em Meticais (`MZN`) de um plano. |
| `POST`| `/api/v1/saas-admin/verificar-expiracoes/` | `SUPERADMIN` | Executa a varredura manual de assinaturas expiradas (rotina diária). |

---

### 2.4. Faturamento e Contratos SaaS (`apps.tenants.saas_views`)

| Método | Endpoint | Permissão | Descrição |
| :---: | :--- | :---: | :--- |
| `GET` | `/api/v1/saas/resumo/` | `SUPERADMIN` | Resumo financeiro do faturamento SaaS e contas a receber. |
| `GET` | `/api/v1/saas/assinaturas/` | `SUPERADMIN` | Lista global de contratos de assinatura de todas as escolas. |
| `GET` | `/api/v1/saas/assinaturas/<uuid:pk>/` | `SUPERADMIN` | Consulta detalhe do contrato da instituição. |
| `POST`| `/api/v1/saas/assinaturas/<uuid:pk>/configurar/` | `SUPERADMIN` | Configura cotas personalizadas de alunos e professores. |
| `GET` | `/api/v1/saas/pagamentos/pendentes/` | `SUPERADMIN` | Lista depósitos e transferências bancárias pendentes de aprovação. |
| `POST`| `/api/v1/saas/pagamentos/<uuid:pk>/confirmar/` | `SUPERADMIN` | Confirma o pagamento da escola e renova a vigência da assinatura. |
| `POST`| `/api/v1/saas/pagamentos/<uuid:pk>/rejeitar/` | `SUPERADMIN` | Rejeita comprovativo inválido de transferência bancária. |
| `POST`| `/api/v1/saas/faturas/<uuid:pk>/prorrogar/` | `SUPERADMIN` | Concede dias de tolerância antes do bloqueio da instituição. |
| `POST`| `/api/v1/saas/instituicoes/<uuid:pk>/suspender-reactivar/` | `SUPERADMIN` | Bloqueio ou desbloqueio manual direto de instituição. |
| `GET` | `/api/v1/saas/minha-assinatura/` | Admin Escola | Permite à escola consultar o status e dias restantes da sua assinatura. |
| `POST`| `/api/v1/saas/registar-pagamento/` | Admin Escola | Envia comprovativo de pagamento de mensalidade para homologação. |
| `GET` | `/api/v1/saas/coordenadas/` | Autenticado | Consulta as contas bancárias e carteiras móveis oficiais (iniciam em branco, sem dados fictícios). |
| `POST`| `/api/v1/saas/coordenadas/` | `SUPERADMIN` | Configura e atualiza contas bancárias (BIM, BCI), carteiras móveis (M-Pesa, e-Mola) e NUIT oficiais. |

---

### 2.5. Administração da Escola (`apps.tenants.views`)

| Método | Endpoint | Permissão | Descrição |
| :---: | :--- | :---: | :--- |
| `GET` | `/api/v1/escola-admin/info/` | Autenticado | Consulta os dados cadastrais da instituição, ano letivo ativo e trimestre ativo. |
| `PUT` | `/api/v1/escola-admin/info/` | Admin Escola | Atualiza dados, logótipo Base64, emblema nacional, diretores e prazos de inscrição. |
| `POST`| `/api/v1/escola-admin/toggle-notas/` | `DAP` / Diretor | Ativa ou bloqueia a consulta de notas no Portal do Aluno. |
| `GET` | `/api/v1/escola-admin/usuarios-credenciais/` | Admin / Direção | Cofre de credenciais: sincroniza e lista códigos oficiais e senhas padrão da escola. |
| `GET` | `/api/v1/anos-letivos/` | Autenticado | Lista os anos letivos cadastrados para a escola. |

---

### 2.6. Gestão de Turmas (`apps.turmas`)

| Método | Endpoint | Permissão | Descrição |
| :---: | :--- | :---: | :--- |
| `GET` | `/api/v1/turmas/` | Autenticado | Lista turmas da escola com métricas de ocupação em tempo real. |
| `POST`| `/api/v1/turmas/` | Admin / `DAP` | Cria uma nova turma com capacidade máxima, turno e sala. |
| `GET` | `/api/v1/turmas/<uuid:pk>/` | Autenticado | Consulta detalhes de uma turma específica. |
| `PUT` | `/api/v1/turmas/<uuid:pk>/` | Admin / `DAP` | Atualiza turma, sala, capacidade e directores. |
| `DELETE`| `/api/v1/turmas/<uuid:pk>/` | Admin / `DAP` | Remove turma (bloqueado se houver alunos matriculados). |
| `POST`| `/api/v1/turmas/criar-lote/` | Admin / `DAP` | Criação automática de múltiplas turmas por classe e turno. |
| `POST`| `/api/v1/turmas/distribuir-automaticamente/` | Admin / `DAP` | Distribui alunos sem turma respeitando a capacidade máxima e género. |
| `GET` | `/api/v1/turmas/previa-formacao-automatica/` | Admin / `DAP` | Pré-visualização da distribuição de alunos antes de confirmar. |
| `POST`| `/api/v1/turmas/gerar-e-enturmar-automatico/` | Admin / `DAP` | Cria turmas necessárias e enturma todos os alunos elegíveis de uma só vez. |
| `POST`| `/api/v1/turmas/renumerar-turmas/` | Admin / `DAP` | Padroniza a numeração sequencial das turmas da classe (`Turma 1, 2, 3...`). |
| `POST`| `/api/v1/turmas/<uuid:pk>/nomear-directores/` | `DAP` / Admin | Nomeia um docente para o cargo de Director de Turma ou Director de Classe. |
| `POST`| `/api/v1/turmas/<uuid:pk>/homologar-directores/`| `DIRECTOR_ESCOLA` | Homologa oficialmente os cargos de DT e DC, ativando os códigos `DT...` e `DC...`. |

---

### 2.7. Alunos e Matrículas (`apps.alunos`)

| Método | Endpoint | Permissão | Descrição |
| :---: | :--- | :---: | :--- |
| `GET` | `/api/v1/alunos/` | Autenticado | Lista alunos matriculados com filtros por turma, classe, área e status. |
| `POST`| `/api/v1/alunos/` | Secretaria / Admin | Matricula um novo aluno, gera o número sequencial e cria o utilizador `ALUNO`. |
| `GET` | `/api/v1/alunos/stats/` | Autenticado | Estatísticas demográficas: retenção, evasão e proporção de género (H vs M). |
| `GET` | `/api/v1/alunos/<uuid:pk>/` | Autenticado | Ficha biográfica e dados escolares completos do aluno. |
| `PUT` | `/api/v1/alunos/<uuid:pk>/` | Secretaria / Admin | Atualiza dados biográficos, filiação e contactos. |
| `DELETE`| `/api/v1/alunos/<uuid:pk>/` | Secretaria / Admin | Exclusão de registo de aluno. |
| `POST`| `/api/v1/alunos/<uuid:pk>/transferir/` | Secretaria / `DAP` | Transfere o aluno para outra turma e migra automaticamente todas as suas notas. |
| `GET` | `/api/v1/alunos/perfil/me/` | `ALUNO` | Perfil do aluno autenticado no Portal do Aluno. |
| `GET` | `/api/v1/alunos/me/notas/` | `ALUNO` | Boletim de notas do aluno logado (respeita bloqueio temporário do DAP). |
| `GET` | `/api/v1/alunos/me/pagamentos/`| `ALUNO` | Consulta de mensalidades pagas e pendentes do aluno logado. |

---

### 2.8. Professores e Alocações Docentes (`apps.professores`)

| Método | Endpoint | Permissão | Descrição |
| :---: | :--- | :---: | :--- |
| `GET` | `/api/v1/professores/` | Autenticado | Lista docentes com soma automática de Horas Normais vs. Horas Extras. |
| `POST`| `/api/v1/professores/` | Admin / `DAP` | Cadastra novo docente com carreira oficial do MEC (`DN4` a `Doutor`). |
| `GET` | `/api/v1/professores/stats/` | Autenticado | Indicadores do corpo docente: total de professores e distribuição por carreira. |
| `GET` | `/api/v1/professores/meu-perfil/`| `PROFESSOR` | Perfil e dados funcionais do professor logado. |
| `GET` | `/api/v1/professores/minhas-turmas/` | `PROFESSOR` | Lista as turmas e disciplinas sob responsabilidade do docente logado. |
| `POST`| `/api/v1/professores/alocar/` | `DAP` / Admin | Aloca `Professor + Disciplina + Turma`, inicializando pautas dos 3 trimestres. |
| `DELETE`| `/api/v1/professores/alocar/<uuid:alocacao_id>/` | `DAP` / Admin | Remove uma alocação docente existente. |
| `GET` | `/api/v1/professores/caderneta/<uuid:alocacao_id>/completa/` | Pedagógico | Dados da caderneta com os 3 trimestres, MFD e estatísticas por coluna. |
| `GET` | `/api/v1/professores/caderneta/<uuid:alocacao_id>/pdf/` | Pedagógico | Download do Mapa Oficial da Caderneta em formato PDF (Landscape). |
| `GET` | `/api/v1/professores/caderneta/<uuid:alocacao_id>/xlsx/`| Pedagógico | Download da Caderneta Oficial em planilha eletrónica Excel (`.xlsx`). |
| `GET` | `/api/v1/professores/caderneta/<uuid:alocacao_id>/docx/`| Pedagógico | Download da Caderneta em documento Word editável (`.docx`). |

---

### 2.9. Disciplinas e Matriz Curricular (`apps.disciplinas`)

| Método | Endpoint | Permissão | Descrição |
| :---: | :--- | :---: | :--- |
| `GET` | `/api/v1/disciplinas/` | Autenticado | Lista a matriz de disciplinas (com auto-seed automático do MEC se vazio). |
| `POST`| `/api/v1/disciplinas/` | `DAP` / Admin | Cadastra disciplina individual na matriz curricular. |
| `GET` | `/api/v1/disciplinas/stats/` | Autenticado | Resumo quantitativo de disciplinas ativas e médias de carga horária. |
| `GET` | `/api/v1/disciplinas/ranking-reprovacao/` | Autenticado | Ranking percentual das disciplinas com maior índice de negativas. |

---

### 2.10. Notas e Avaliações Pedagógicas (`apps.notas`)

| Método | Endpoint | Permissão | Descrição |
| :---: | :--- | :---: | :--- |
| `GET` | `/api/v1/notas/` | Pedagógico | Lista notas com filtros por turma, disciplina e período. |
| `POST`| `/api/v1/notas/` | `PROFESSOR` / `DAP` | Lança ou edita notas (`1ª ACS`, `2ª ACS`, `3ª ACS`, `MAP`, `MAS`, `AT`, faltas). |
| `GET` | `/api/v1/notas/prazos-trimestres/` | Autenticado | Consulta as datas de abertura e encerramento de lançamento por trimestre. |
| `POST`| `/api/v1/notas/prazos-trimestres/` | `DAP` / Diretor | Define o calendário de abertura e fecho de lançamento de notas. |
| `GET` | `/api/v1/notas/autorizacoes/` | `DAP` / Diretor | Lista autorizações temporárias ativas de desbloqueio de notas. |
| `POST`| `/api/v1/notas/autorizar-desbloqueio/` | `DAP` / Diretor | Concede autorização temporária de edição de notas fora do prazo ou com pauta fechada. |
| `DELETE`| `/api/v1/notas/autorizacoes/<uuid:perm_id>/` | `DAP` / Diretor | Revoga antecipadamente uma autorização de desbloqueio. |

---

### 2.11. Pautas e Actas do Conselho de Avaliação (`apps.pautas`)

| Método | Endpoint | Permissão | Descrição |
| :---: | :--- | :---: | :--- |
| `POST`| `/api/v1/pautas/gerar/` | `DAP` / `DT` | Consolida as notas de todas as disciplinas e gera a pauta da turma. |
| `GET` | `/api/v1/pautas/turma/<uuid:turma_id>/completa/` | Pedagógico | Retorna a Pauta Geral consolidada com quadro estatístico do MEC. |
| `GET` | `/api/v1/pautas/turma/<uuid:turma_id>/pdf/` | Pedagógico | Download da Pauta Geral Oficial da Turma em PDF (A4 Paisagem). |
| `GET` | `/api/v1/pautas/turma/<uuid:turma_id>/xlsx/`| Pedagógico | Download da Pauta Geral em planilha eletrónica Excel (`.xlsx`). |
| `GET` | `/api/v1/pautas/turma/<uuid:turma_id>/docx/`| Pedagógico | Download da Pauta Geral em documento Word (`.docx`). |
| `GET` | `/api/v1/pautas/turma/<uuid:turma_id>/acta/`| Pedagógico | Retorna dados da Acta do Conselho de Avaliação da turma. |
| `GET` | `/api/v1/pautas/turma/<uuid:turma_id>/acta-pdf/` | Pedagógico | Download da Acta Oficial do Conselho em PDF (com números por extenso). |
| `GET` | `/api/v1/pautas/turma/<uuid:turma_id>/acta-docx/`| Pedagógico | Download da Acta Oficial em formato Word editável (`.docx`). |
| `GET` | `/api/v1/pautas/turma/<uuid:turma_id>/acta-xlsx/`| Pedagógico | Download da Acta Oficial em formato Excel (`.xlsx`). |
| `GET` | `/api/v1/pautas/estatisticas-gerais/` | Autenticado | Mapa estatístico comparativo de aproveitamento de todas as turmas. |
| `GET` | `/api/v1/pautas/estatisticas-gerais/xlsx/` | Autenticado | Exportação do mapa estatístico geral em Excel (`.xlsx`). |

---

### 2.12. Biblioteca Digital de Material Escolar (`apps.material_escolar`)

| Método | Endpoint | Permissão | Descrição |
| :---: | :--- | :---: | :--- |
| `GET` | `/api/v1/material-escolar/` | Autenticado | Lista materiais escolares (1ª à 12ª classe) com filtros por tipo e classe. |
| `POST`| `/api/v1/material-escolar/` | `PROFESSOR` / Admin | Publica novo material didático (manual, ficha, guia) até 15 MB. |
| `GET` | `/api/v1/material-escolar/<uuid:pk>/` | Autenticado | Detalhes e download binário direto do material escolar. |
| `DELETE`| `/api/v1/material-escolar/<uuid:pk>/`| `PROFESSOR` / Admin | Remove publicação de material didático. |
| `GET` | `/api/v1/material-escolar/classes/` | Autenticado | Lista classes que possuem materiais pedagógicos disponíveis. |

---

### 2.13. Gestão Financeira, Propinas e Planos Escolares (`apps.pagamentos`)

| Método | Endpoint | Permissão | Descrição |
| :---: | :--- | :---: | :--- |
| `GET` | `/api/v1/pagamentos/planos-escola/` | Financeiro / Admin / Secr | Lista planos de pagamento e propinas criados pela instituição logada. |
| `POST`| `/api/v1/pagamentos/planos-escola/` | Financeiro / Admin / Secr | Cria novo plano de pagamento/propina da escola com valor em MZN, periodicidade e vencimento. |
| `GET` | `/api/v1/pagamentos/planos-escola/<uuid:pk>/` | Financeiro / Admin / Secr | Detalhes de um plano de pagamento da escola. |
| `PATCH`| `/api/v1/pagamentos/planos-escola/<uuid:pk>/` | Financeiro / Admin / Secr | Atualiza dados ou ativa/desativa plano de propina da instituição. |
| `DELETE`| `/api/v1/pagamentos/planos-escola/<uuid:pk>/` | Financeiro / Admin / Secr | Desativação lógica segura do plano escolar (preserva histórico financeiro). |
| `GET` | `/api/v1/pagamentos/` | Financeiro / Aluno | Lista mensalidades e faturas com filtros por aluno, turma e status. |
| `POST`| `/api/v1/pagamentos/` | Financeiro | Cria cobrança individual para um aluno (opcionalmente vinculada a um plano escolar). |
| `GET` | `/api/v1/pagamentos/stats/` | Financeiro / Admin | KPIs de receita: Total Recebido, Pendente, Atrasado e taxa de adimplência. |
| `POST`| `/api/v1/pagamentos/<uuid:pk>/liquidar/` | Financeiro / Secr | Quita propina (M-Pesa, e-Mola, POS, Banco) e emite recibo `REC-...`. |
| `POST`| `/api/v1/pagamentos/gerar-turma/` | Financeiro | Gera cobranças de um mês para toda a turma, permitindo vincular plano escolar. |


---

### 2.14. Emissão de Certificados Digitais (`apps.certificados`)

| Método | Endpoint | Permissão | Descrição |
| :---: | :--- | :---: | :--- |
| `GET` | `/api/v1/certificados/` | Secretaria / Admin | Lista certificados emitidos pela escola com código `CERT-...`. |
| `POST`| `/api/v1/certificados/` | Secretaria / Diretor | Emite novo certificado oficial (`CONCLUSAO`, `TRANSFERENCIA`, `DECLARACAO`). |
| `GET` | `/api/v1/certificados/<uuid:pk>/` | Autenticado | Consulta detalhada do certificado e chave pública do QR Code. |

---

### 2.15. Central de Impressão e Cofre de Arquivos (`apps.documentos`)

| Método | Endpoint | Permissão | Formatos Suportados |
| :---: | :--- | :---: | :---: |
| `GET` | `/api/v1/documentos/boletim/<uuid:aluno_id>/(pdf\|docx\|xlsx)` | Autenticado | Boletim Individual de Notas |
| `GET` | `/api/v1/documentos/declaracao/<uuid:aluno_id>/(pdf\|docx\|xlsx)` | Autenticado | Declaração Escolar com Notas |
| `GET` | `/api/v1/documentos/certificado/<uuid:aluno_id>/(pdf\|docx\|xlsx)` | Autenticado | Certificado com QR Code |
| `GET` | `/api/v1/documentos/recibo/<uuid:pagamento_id>/(pdf\|docx)` | Financeiro | Recibo Oficial de Quitação |
| `GET` | `/api/v1/documentos/ficha/<uuid:aluno_id>/(pdf\|docx)` | Secretaria | Ficha Biográfica do Estudante |
| `GET` | `/api/v1/documentos/lote/turma/<uuid:turma_id>/(pdf\|docx\|xlsx)` | Pedagógico | Emissão em lote para toda a turma |

---

### 2.16. Dashboard Executivo (`apps.dashboard`)

| Método | Endpoint | Permissão | Descrição |
| :---: | :--- | :---: | :--- |
| `GET` | `/api/v1/dashboard/overview/` | Autenticado | Indicadores resumidos do dashboard e dias restantes da assinatura da escola. |
