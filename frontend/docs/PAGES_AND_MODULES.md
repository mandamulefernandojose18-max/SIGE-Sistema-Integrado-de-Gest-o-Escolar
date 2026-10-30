# Catálogo de Telas e Módulos — SIGE Frontend (SPA)

> Documento gerado automaticamente via introspecção do `index.html` e `js/app.js`.

**Total de Telas / Visões Detectadas:** 0
**Total de Chamadas a Endpoints:** 81

---

## 1. Módulos e Telas da Interface

| Identificador (ID) | Título da Página | Componentes Detectados | Ações Principais |
| :--- | :--- | :---: | :--- |

---

## 2. Endpoints do Backend Consumidos no Código-Fonte

| Rota da API Backend | Módulo de Destino Estimado |
| :--- | :--- |
| `/api/v1/alunos` | **Alunos** |
| `/api/v1/alunos/${id}` | **Alunos** |
| `/api/v1/alunos/${id}/transferir` | **Alunos** |
| `/api/v1/alunos/me/notas?periodo=${encodeURIComponent(periodo)}` | **Alunos** |
| `/api/v1/alunos/perfil/me` | **Alunos** |
| `/api/v1/alunos/stats` | **Alunos** |
| `/api/v1/alunos?turmaId=${turmaId}` | **Turmas** |
| `/api/v1/auth/minha-senha` | **Autenticação** |
| `/api/v1/auth/stats` | **Autenticação** |
| `/api/v1/auth/usuarios/${userId}/redefinir-senha` | **Autenticação** |
| `/api/v1/certificados` | **Certificados** |
| `/api/v1/configuracoes/anos-lectivos` | **Geral** |
| `/api/v1/dashboard/overview` | **Geral** |
| `/api/v1/disciplinas` | **Geral** |
| `/api/v1/disciplinas/${disciplinaId}` | **Geral** |
| `/api/v1/disciplinas/${disciplinaId}/toggle-exame/` | **Geral** |
| `/api/v1/escola-admin/classes-exames` | **Administração SaaS** |
| `/api/v1/escola-admin/info` | **Administração SaaS** |
| `/api/v1/escola-admin/toggle-notas` | **Notas e Avaliações** |
| `/api/v1/escola-admin/turmas` | **Turmas** |
| `/api/v1/escola-admin/turmas${queryAno}` | **Turmas** |
| `/api/v1/escola-admin/turmas/${tId}/homologar-directores` | **Turmas** |
| `/api/v1/escola-admin/turmas/${tId}/nomear-directores` | **Turmas** |
| `/api/v1/escola-admin/turmas/${turmaId}` | **Turmas** |
| `/api/v1/escola-admin/turmas/${turmaId}/homologar-directores` | **Turmas** |
| `/api/v1/escola-admin/turmas/criar-lote` | **Turmas** |
| `/api/v1/escola-admin/turmas/gerar-e-enturmar-automatico` | **Turmas** |
| `/api/v1/escola-admin/turmas/previa-formacao-automatica?ano_letivo=${anoAtivo}&grau_ano=${classeFiltro}&area=${areaFiltro}` | **Turmas** |
| `/api/v1/escola-admin/turmas/renumerar-turmas` | **Turmas** |
| `/api/v1/escola-admin/usuarios-credenciais` | **Administração SaaS** |
| `/api/v1/impressao/boletim/${alunoId}` | **Alunos** |
| `/api/v1/impressao/certificado/${alunoId}` | **Alunos** |
| `/api/v1/impressao/declaracao/${alunoId}` | **Alunos** |
| `/api/v1/impressao/ficha/${alunoId}` | **Alunos** |
| `/api/v1/impressao/lote/turma/${turmaId}?tipo=${tipo}` | **Turmas** |
| `/api/v1/impressao/recibo/${pagamentoId}` | **Financeiro / Pagamentos** |
| `/api/v1/material-escolar` | **Material Escolar** |
| `/api/v1/material-escolar${query}` | **Material Escolar** |
| `/api/v1/material-escolar/${id}` | **Material Escolar** |
| `/api/v1/material-escolar/classes${paramEscola}` | **Material Escolar** |
| `/api/v1/notas` | **Notas e Avaliações** |
| `/api/v1/notas/autorizacoes` | **Notas e Avaliações** |
| `/api/v1/notas/autorizacoes/${id}` | **Notas e Avaliações** |
| `/api/v1/notas/autorizar-desbloqueio` | **Notas e Avaliações** |
| `/api/v1/notas/prazos-trimestres` | **Notas e Avaliações** |
| `/api/v1/pagamentos` | **Financeiro / Pagamentos** |
| `/api/v1/pagamentos/${id}/liquidar` | **Financeiro / Pagamentos** |
| `/api/v1/pagamentos/gerar-turma` | **Turmas** |
| `/api/v1/pagamentos/stats` | **Financeiro / Pagamentos** |
| `/api/v1/pagamentos?alunoId=${alunoId}` | **Alunos** |
| `/api/v1/pautas/estatisticas-gerais?anoLetivo=${ano}&periodo=${periodo}` | **Pautas e Atas** |
| `/api/v1/pautas/exames/parametros` | **Pautas e Atas** |
| `/api/v1/pautas/exames/parametros/` | **Pautas e Atas** |
| `/api/v1/pautas/exames/professores-autorizados/` | **Professores** |
| `/api/v1/pautas/exames/turma/${turmaId}/salvar/` | **Turmas** |
| `/api/v1/pautas/exames/turma/${turmaId}?anoLetivo=${anoLetivo}` | **Turmas** |
| `/api/v1/pautas/exames/turma/${turmaId}?anoLetivo=${ano}` | **Turmas** |
| `/api/v1/pautas/gerar` | **Pautas e Atas** |
| `/api/v1/pautas/turma/${dtTurmaAtivaId}/completa` | **Turmas** |
| `/api/v1/pautas/turma/${turmaId}/acta?${qParams}` | **Turmas** |
| `/api/v1/pautas/turma/${turmaId}/completa` | **Turmas** |
| `/api/v1/professores` | **Professores** |
| `/api/v1/professores/${profId}` | **Professores** |
| `/api/v1/professores/alocar` | **Professores** |
| `/api/v1/professores/alocar/${a.id}` | **Professores** |
| `/api/v1/professores/alocar/${alocacaoId}` | **Professores** |
| `/api/v1/professores/caderneta/${alocacaoId}/completa` | **Professores** |
| `/api/v1/professores/caderneta/${state.alocacaoAtualId}/completa` | **Professores** |
| `/api/v1/professores/meu-perfil` | **Professores** |
| `/api/v1/professores/minhas-turmas` | **Turmas** |
| `/api/v1/professores/stats` | **Professores** |
| `/api/v1/saas-admin/escolas` | **Administração SaaS** |
| `/api/v1/saas-admin/escolas/${escolaId}` | **Administração SaaS** |
| `/api/v1/saas-admin/escolas/${escolaId}/comprovativo-contrato` | **Administração SaaS** |
| `/api/v1/saas-admin/escolas/${escolaId}/toggle-status` | **Administração SaaS** |
| `/api/v1/saas-admin/metrics` | **Administração SaaS** |
| `/api/v1/saas-admin/minha-escola/comprovativo-contrato` | **Administração SaaS** |
| `/api/v1/saas-admin/planos` | **Administração SaaS** |
| `/api/v1/saas-admin/planos/${planoId}/preco` | **Administração SaaS** |
| `/api/v1/saas-admin/verificar-expiracoes` | **Administração SaaS** |
| `/api/v1/turmas?escola_id=${escolaId}` | **Turmas** |

---

## 3. Funções Controladoras de Interface Identificadas

Foram detectadas **85** funções essenciais de carregamento e manipulação de estado:

- `abrirSeletorDataSeguro()`
- `carregarDadosGeografia()`
- `carregarDadosGlobaisEscola()`
- `renderizarSidebarPorNivel()`
- `carregarAnosLectivos()`
- `renderizarSelectoresAnoLectivo()`
- `carregarEscolasSuperAdminSelect()`
- `carregarPaginaModulo()`
- `carregarScriptModulo()`
- `carregarDashboardGeral()`
- `renderizarGraficoDashboardFaturamento()`
- `renderizarGraficoDashboardGenero()`
- `carregarPainelSaaS()`
- `carregarEscolaETurmas()`
- `carregarTurmas()`
- `renderizarEstatisticasETabelaTurmas()`
- `renderizarTabelaTurmasNoDOM()`
- `abrirAlunosDaTurma()`
- `renderizarGaleriaLogos()`
- `renderizarSeletorTemas()`
- `renderizarGaleriaFundos()`
- `carregarAlunos()`
- `renderizarFiltrosAlunos()`
- `renderizarBotoesClassesAlunos()`
- `renderizarTabelaAlunos()`
- `carregarProfessores()`
- `renderizarBotoesClassesProfessores()`
- `renderizarTabelaProfessores()`
- `carregarDisciplinas()`
- `carregarSelectProfessoresCaderneta()`
- `renderizarBotoesClassesCaderneta()`
- `renderizarBotoesAreasCaderneta()`
- `renderizarBotoesCadernetasDisponiveis()`
- `carregarCadernetaDocente()`
- `carregarNotasAlunoNoModal()`
- `carregarPautas()`
- `carregarPautaGeral()`
- `carregarActaConselho()`
- `salvarConfigSessaoActa()`
- `carregarCertificados()`
- *... e mais 45 funções auxiliares.*
