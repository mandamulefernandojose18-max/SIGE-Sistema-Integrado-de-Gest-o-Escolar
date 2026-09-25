# Catálogo de Telas e Módulos — SIGE Frontend (SPA)

> Documento gerado automaticamente via introspecção do `index.html` e `js/app.js`.

**Total de Telas / Visões Detectadas:** 21
**Total de Chamadas a Endpoints:** 65

---

## 1. Módulos e Telas da Interface

| Identificador (ID) | Título da Página | Componentes Detectados | Ações Principais |
| :--- | :--- | :---: | :--- |
| `view-dashboard` | **0** | Painel / Visual | Carregar / Gerir Logótipo |
| `view-saas` | **0 MZN** | Tabela | Cadastrar Nova Escola, Rodar Verificação de Expiração |
| `view-escola` | **view escola** | Tabela, Formulário | Restaurar Emblema Nacional, Aplicar, Salvar Definições & Logótipo, Nova Turma |
| `view-alunos` | **0** | Tabela | Actualizar, Matricular Aluno, &times; |
| `view-professores` | **0** | Tabela | Alocar a Turma/Disciplina, Cadastrar Docente |
| `view-disciplinas` | **view disciplinas** | Tabela | Nova Disciplina, Todas, 7ª Classe, 8ª Classe, 9ª Classe |
| `view-material-escolar` | **view material escolar** | Painel / Visual | Carregar / Importar Material |
| `view-caderneta` | **view caderneta** | Tabela | Lançar, Excel, PDF |
| `view-pautas` | **view pautas** | Painel / Visual | Pauta Geral da Turma, Acta do Conselho de Avaliação, Consolidar, JSON, Excel (.xlsx) |
| `view-certificados` | **view certificados** | Tabela | Emitir Novo Certificado |
| `view-director-turma` | **view director turma** | Formulário | Configurar Dados da Sessão do Conselho de Avaliação (Presidente, Datas e Horários), Gravar Parâmetros do Conselho |
| `view-estatisticas-aproveitamento` | **0%** | Painel / Visual | Visualizar, Imprimir, Descarregar PDF, Descarregar XLSX |
| `view-pagamentos` | **0 MZN** | Tabela | Gerar em Lote para Turma, Nova Cobrança |
| `view-impressao` | **view impressao** | Painel / Visual | Visualizar, Imprimir, Descarregar PDF (PDFKit), Descarregar Word (DOCX), Descarregar Excel (XLSX) |
| `view-desbloqueio` | **view desbloqueio** | Tabela, Formulário | Guardar Calendário de Prazos, Conceder Autorização de Desbloqueio, Actualizar |
| `view-aluno-perfil` | **view aluno perfil** | Tabela | Sair do Sistema |
| `view-aluno-notas` | **view aluno notas** | Tabela | Sair |
| `view-aluno-pagamentos` | **0 MZN** | Tabela | Actualizar |
| `view-professor-perfil` | **view professor perfil** | Painel / Visual | Actualizar |
| `view-usuarios-senhas` | **view usuarios senhas** | Tabela | Actualizar |
| `view-acessos` | **view acessos** | Tabela | Navegação |

---

## 2. Endpoints do Backend Consumidos no Código-Fonte

| Rota da API Backend | Módulo de Destino Estimado |
| :--- | :--- |
| `/api/v1/alunos` | **Alunos** |
| `/api/v1/alunos/${id}` | **Alunos** |
| `/api/v1/alunos/${id}/transferir` | **Alunos** |
| `/api/v1/alunos/me/notas` | **Alunos** |
| `/api/v1/alunos/me/pagamentos` | **Alunos** |
| `/api/v1/alunos/perfil/me` | **Alunos** |
| `/api/v1/alunos/stats` | **Alunos** |
| `/api/v1/alunos?turmaId=${turmaId}` | **Turmas** |
| `/api/v1/auth/me` | **Autenticação** |
| `/api/v1/auth/stats` | **Autenticação** |
| `/api/v1/auth/usuarios/${userId}/redefinir-senha` | **Autenticação** |
| `/api/v1/certificados` | **Certificados** |
| `/api/v1/dashboard/overview` | **Geral** |
| `/api/v1/disciplinas` | **Geral** |
| `/api/v1/disciplinas/${disciplinaId}` | **Geral** |
| `/api/v1/disciplinas/stats` | **Geral** |
| `/api/v1/escola-admin/administrativos/${userId}` | **Administração SaaS** |
| `/api/v1/escola-admin/info` | **Administração SaaS** |
| `/api/v1/escola-admin/toggle-notas` | **Notas e Avaliações** |
| `/api/v1/escola-admin/turmas` | **Turmas** |
| `/api/v1/escola-admin/turmas/${turmaId}` | **Turmas** |
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
| `/api/v1/material-escolar/classes` | **Material Escolar** |
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
| `/api/v1/pautas/gerar` | **Pautas e Atas** |
| `/api/v1/pautas/turma/${dtTurmaAtivaId}/completa` | **Turmas** |
| `/api/v1/pautas/turma/${turmaId}/acta?${qParams}` | **Turmas** |
| `/api/v1/pautas/turma/${turmaId}/completa` | **Turmas** |
| `/api/v1/professores` | **Professores** |
| `/api/v1/professores/${profId}` | **Professores** |
| `/api/v1/professores/alocar` | **Professores** |
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

---

## 3. Funções Controladoras de Interface Identificadas

Foram detectadas **47** funções essenciais de carregamento e manipulação de estado:

- `carregarDadosGeografia()`
- `carregarEscolasSuperAdminSelect()`
- `carregarDashboardGeral()`
- `renderizarGraficoDashboardFaturamento()`
- `renderizarGraficoDashboardGenero()`
- `carregarPainelSaaS()`
- `carregarEscolaETurmas()`
- `carregarAlunos()`
- `renderizarBotoesClassesAlunos()`
- `renderizarTabelaAlunos()`
- `carregarProfessores()`
- `carregarDisciplinas()`
- `renderizarGraficoReprovacao()`
- `carregarCadernetaDocente()`
- `carregarPautas()`
- `carregarPautaGeral()`
- `carregarActaConselho()`
- `salvarConfigSessaoActa()`
- `carregarCertificados()`
- `carregarPagamentos()`
- `abrirModalReciboPagamento()`
- `carregarVisualizacaoImpressao()`
- `carregarReciboIndividual()`
- `renderizarBoletim()`
- `renderizarDeclaracao()`
- `renderizarCertificado()`
- `renderizarRecibo()`
- `renderizarFichaAluno()`
- `renderizarLoteImpressao()`
- `carregarPrazosTrimestrais()`
- `carregarAutorizacoesDesbloqueio()`
- `carregarAlunoPerfil()`
- `carregarAlunoNotas()`
- `carregarAlunoPagamentos()`
- `carregarLogsAcesso()`
- `abrirModal()`
- `carregarPerfilDocenteIndividual()`
- `abrirCadernetaAlocacao()`
- `carregarCofreUsuarios()`
- `renderizarTabelaCofre()`
- *... e mais 7 funções auxiliares.*
