# 🏫 SIGE — Sistema Integrado de Gestão Escolar (v2.5.0)
### Plataforma SaaS Multi-Tenant Corporativa de Gestão Educacional (MEC — Moçambique)

[![SIGE CI/CD Pipeline](https://github.com/empresa/sige/actions/workflows/ci.yml/badge.svg)](https://github.com/empresa/sige/actions/workflows/ci.yml)
[![Python](https://img.shields.io/badge/Python-3.12-3776AB.svg)](https://www.python.org/)
[![Django](https://img.shields.io/badge/Django-5.1-092E20.svg)](https://www.djangoproject.com/)
[![DRF](https://img.shields.io/badge/DRF-3.15-A30000.svg)](https://www.django-rest-framework.org/)
[![PostgreSQL](https://img.shields.io/badge/PostgreSQL-16-336791.svg)](https://www.postgresql.org/)
[![Docker](https://img.shields.io/badge/Docker-Ready-2496ED.svg)](https://www.docker.com/)

---

## 📖 Visão Geral

O **SIGE (Sistema Integrado de Gestão Escolar)** é uma plataforma corporativa **SaaS Multi-Tenant** projetada para centralizar, padronizar e automatizar integralmente as operações pedagógicas, curriculares, administrativas, financeiras e de certificação digital de instituições de ensino público e privado em **Moçambique**, em estrita conformidade com as normas do **MEC (Ministério da Educação e Desenvolvimento Humano)**.

> 📘 **Central Oficial de Documentação:**  
> Aceda à **[Central de Documentação do SIGE (`docs/README.md`)](docs/README.md)** ou explore diretamente os guias especializados:
> - 📘 **[Documento Mestre do Sistema](docs/DOCUMENTACAO_COMPLETA_DO_SISTEMA.md)**: Panorama unificado de ponta a ponta.
> - 🛡️ **[Arquitetura e Segurança](docs/ARQUITETURA_E_SEGURANCA.md)**: Multi-Tenancy, 6 Pilares de Integridade, RLS e JWT.
> - ⚙️ **[Manual de Módulos e Operação](docs/MANUAL_DE_MODULOS_E_OPERACAO.md)**: Guia operacional passo a passo dos 18 módulos.
> - 🇲🇿 **[Regras Pedagógicas Oficiais MEC](docs/REGRAS_PEDAGOGICAS_MEC.md)**: Matriz curricular, fórmulas de cálculo e aprovação.
> - 🗄️ **[Dicionário de Dados e Modelos](docs/DICIONARIO_DE_DADOS.md)**: Catálogo das 17 tabelas, chaves e constraints.
> - 🔌 **[Catálogo Completo da API REST](docs/REFERENCIA_COMPLETA_API.md)**: Mais de 75 endpoints com métodos e envelopes.
> - 🚀 **[Guia de Implantação e DevOps](docs/GUIA_DE_IMPLANTACAO_E_DEVOPS.md)**: Docker, CI/CD, deploy Cloud e guardrail de US$ 6/mês.

---

## 🎯 Pilares Arquiteturais & Multi-Tenancy

### 1. Isolamento Estrito de Dados (Multi-Tenancy + RLS)
- Cada instituição de ensino opera como um **Tenant** isolado (`escola_id`).
- O contexto da escola é extraído automaticamente do token JWT (`TenantIsolationMiddleware`) ou inspecionado pelo `SUPERADMIN` via cabeçalho `X-Tenant-ID`.
- Validação cruzada em todas as entidades (`validar_integridade_tenant()`) e políticas de **Row-Level Security (RLS)** nativas no PostgreSQL (`backend/supabase_schema_rls.sql`).

### 2. Gestão de Planos, Assinaturas, Suspensão e Reactivação (Automática e Manual)
- Planos de subscrição em Meticais (`MZN`): **Mensal**, **Trimestral**, **Semestral** e **Anual**, com modos de vencimento Automático, Dia Fixo ou Manual, tolerância e corte configuráveis por escola.
- **Suspensão e Reactivação Híbrida (Manual & Automática):** O Super Administrador dispõe de operações manuais imediatas (`Suspender Manualmente` e `Reactivar Manualmente`, com justificação obrigatória de auditoria) e operações automáticas governadas pelo sistema (`Suspensão Automática`, `Reactivação Automática` e `Repor Modo Automático`), complementadas pelo ciclo diário que suspende automaticamente escolas inadimplentes além do corte e reactiva automaticamente instituições regularizadas.
- O middleware `TenantExpirationMiddleware` e a validação de autenticação verificam em tempo real o estado da subscrição e da instituição, mantendo acessíveis apenas o SuperAdmin e as rotas públicas quando uma entidade estiver suspensa.

### 3. Autenticação Inteligente por Código Oficial & 8 Perfis RBAC (+ DT/DC)
- Suporta login por **E-mail**, **Username** ou **Código Oficial de Acesso** gerado automaticamente:
  - **Director da Escola (`DIRECTOR_ESCOLA`):** `GD{CodigoEscola}` *(ex.: `GD0808S0001`)*
  - **Director Adjunto Pedagógico (`DAP`):** `DP{CodigoEscola}` *(ex.: `DP0808S0001`)*
  - **Chefe da Secretaria (`CHEFE_SECRETARIA`):** `SECR{CodigoEscola}` *(ex.: `SECR0808S0001`)*
  - **Professor (`PROFESSOR`):** `PR{CodigoEscola}.{Seq:03d}` *(ex.: `PR0808S0001.001`)*
  - **Director de Turma Homologado (`DT`):** `DT{CodigoEscola}.{Classe}.{Turma}`
  - **Director de Classe Homologado (`DC`):** `DC{CodigoEscola}.{Classe}`
  - **Estudante (`ALUNO`):** `{CodigoEscola}.{Classe}.{Turma}.{Ano}.{Area}`
  - Além dos perfis `SUPERADMIN`, `ADMIN_ESCOLA` e `FINANCEIRO`.

---

## 📁 Módulos e Funcionalidades do Sistema

| # | Módulo | Principais Funcionalidades |
| :-: | :--- | :--- |
| **1** | 🌐 **Portal Público de Auto-Inscrição** | Candidatura e matrícula online de novos alunos por Província/Distrito/Escola, validação de BI/NUIT/Contacto (`+258`), enturmação automática e emissão imediata do Cartão de Matrícula com Código de Acesso. |
| **2** | 🏢 **Painel Master SaaS (`SUPERADMIN`)** | Métricas de MRR, ARR e Churn Rate; criação de escolas com geração automática de contas diretivas; inspeção de escolas sem senha; renovação de contratos e emissão de comprovativo PDF. |
| **3** | 🏫 **Administração da Escola** | Identidade visual (Logótipo Base64 e Emblema da República de Moçambique), Ano Letivo e Trimestre Ativo, titulares de cargos, prazos de inscrição pública e bloqueio/liberação de visualização de notas pelos alunos. |
| **4** | 🏛️ **Gestão de Turmas & Lotação** | Controlo de capacidade máxima (padrão 50 alunos), barras de ocupação, numeração contínua (`Turma 1, 2, 3...`), criação em lote, **Formação/Distribuição Automática de Alunos** e **Homologação de DT/DC** pelo Director da Escola. |
| **5** | 👨‍🎓 **Alunos & Matrículas** | Cadastro biográfico e filiação, geração automática de número de matrícula (`2026001`), transferência interna de turma com migração automática de notas e estatísticas demográficas (retenção, evasão, género). |
| **6** | 👨‍🏫 **Professores & Carreiras MEC** | Carreiras oficiais (`DN4` a `Professor Doutor`), limite de carga horária por classe, cálculo automático de **Horas Normais vs. Horas Extras** e alocação a Turma/Disciplina. |
| **7** | 📚 **Disciplinas & Currículo MEC** | Auto-seed do Plano Curricular Nacional da **7ª à 12ª Classe** (incluindo as 5 secções específicas da 11ª e 12ª: *Ciências com Biologia, Desenho, Geografia* e *Letras com Geografia, História*) e ranking de reprovação. |
| **8** | 📖 **Material Escolar Digital** | Biblioteca digital da **1ª à 12ª Classe** com 34 manuais oficiais pré-carregados e upload de manuais, fichas, guias e livros até 15 MB. |
| **9** | 📝 **Caderneta do Professor** | Grelha com os **3 Trimestres lado a lado** (`1ª ACS`, `2ª ACS`, `3ª ACS`, `MAP`, `MAS`, `AT`, `MT`, `COM`, `Obs`) + `MFD`, estatísticas demográficas no rodapé por coluna (`H`, `M`, `HM`, `%`) e exportação PDF/Excel. |
| **10** | 🔓 **Prazos & Desbloqueio de Notas** | Definição de calendário de abertura/fecho de lançamento por trimestre e concessão de autorizações temporárias de desbloqueio (`PermissaoEdicaoNotas`) pelo DAP/Direção. |
| **11** | 📊 **Pautas Gerais & Actas do Conselho** | Consolidação da **Pauta Geral da Turma** (critério de 0 negativas da 7ª–11ª vs. tolerância de até 2 negativas $\ge 8$ na 12ª Classe) e geração da **Acta Oficial do Conselho de Avaliação** com números por extenso em português. |
| **12** | 📈 **Estatística do Aproveitamento** | Relatório oficial em 4 níveis (*Por Turma*, *Por Classe*, *Geral da Escola* e *Por Disciplina/Docente*) discriminado por género (`H`, `M`, `HM` e `%`), exportável em PDF e Excel. |
| **13** | 📄 **Certificados com QR Code** | Emissão de Certificados de Conclusão, Transferência, Declaração e Matrícula com código único (`CERT-...`), QR Code embutido e página pública de verificação (`/verificar-certificado.html`). |
| **14** | 💰 **Financeiro, Propinas & Planos da Escola (MZN)** | Planos de pagamento próprios da escola (`PlanoPagamentoEscola`), emissão individual ou em lote por turma, liquidação via **M-Pesa**, **e-Mola**, **POS**, **Transferência** ou **Numerário**, recibos numerados (`REC-...`) e isolamento total multi-tenant. |
| **15** | 🖨️ **Central de Impressão & Cofre** | Emissão **Individual** ou **Em Lote para toda a Turma** em **PDF (`ReportLab`)**, **Word (`.docx`)** e **Excel (`.xlsx`)** (Retrato ou Paisagem), com arquivo automático no Cofre de Documentos (`DocumentoSalvo`). |
| **16** | 🔑 **Cofre de Senhas & Auditoria** | Consulta sincronizada de todos os códigos de acesso oficiais e senhas padrão da escola, redefinição de senhas e auditoria completa de acessos (`LogAcesso`). |

---

## 🛠️ Stack Tecnológica

- **Backend**: Python 3.12, Django 5.1.6, Django REST Framework (DRF) 3.15.2, SimpleJWT, `drf-spectacular` (Swagger/OpenAPI).
- **Motores Documentais**: `ReportLab` + `Pillow` + `qrcode` (PDF vetorial), `python-docx` (Word `.docx` em *Times New Roman*), `openpyxl` (Excel `.xlsx` em *Times New Roman*).
- **Banco de Dados**: PostgreSQL 16 (produção / Docker / Supabase com RLS) e SQLite3 (desenvolvimento local rápido).
- **Frontend**: Single-Page Application (SPA) e Progressive Web App (PWA) em HTML5, CSS3, Vanilla JS (ES6+), Bootstrap 5.3.3, Bootstrap Icons e Chart.js 4.4.4.
- **DevOps & Cloud**: Docker, Docker Compose, Nginx Alpine (SSL Let's Encrypt), GitHub Actions CI/CD.

---

## 🚀 Como Executar o Projeto Localmente

### 1. Preparar o Backend (Django)
```powershell
cd backend
python -m venv venv
.\venv\Scripts\activate      # Windows (ou: source venv/bin/activate no Linux/macOS)
pip install -r requirements.txt

# Aplicar migrações e popular dados iniciais de demonstração:
python manage.py migrate
python manage.py seed
```

### 2. Iniciar o Sistema Completo (Backend `:8000` + Frontend `:5173`)
Na raiz do repositório (`d:\SIGE`):
```powershell
npm start
# Ou utilizando o script direto no Windows:
.\scripts\sige.bat
```
- **Aplicação Web (SPA):** `http://localhost:5173`
- **Documentação Swagger da API:** `http://localhost:8000/api/docs/`

---

## 👥 Contas de Demonstração Pré-configuradas (`python manage.py seed`)

| Perfil / Cargo | Identificador (Código Oficial ou E-mail) | Palavra-passe | Instituição / Escopo |
| :--- | :--- | :--- | :--- |
| **SuperAdmin (Master SaaS)** | `mandamulefj.@sige.com` | `Admin@123` | Governação Global SaaS (todas as escolas) |
| **Director da Escola** | `GD0808S0001` *(ou `director@massinga.edu.mz`)* | `Massinga@2026` | Escola Secundária de Massinga (`0808S0001`) |
| **Director Adjunto Pedagógico** | `DP0808S0001` *(ou `dap@massinga.edu.mz`)* | `Massinga@2026` | Escola Secundária de Massinga (`0808S0001`) |
| **Chefe da Secretaria** | `SECR0808S0001` *(ou `secretaria@massinga.edu.mz`)* | `Massinga@2026` | Escola Secundária de Massinga (`0808S0001`) |
| **Admin da Escola** | `admin@massinga.edu.mz` | `Massinga@2026` | Escola Secundária de Massinga (`0808S0001`) |
| **Financeiro** | `financeiro@massinga.edu.mz` | `Massinga@2026` | Escola Secundária de Massinga (`0808S0001`) |
| **Professor** | `PR0808S0001.001` *(ou `carlos.mucavele@massinga.edu.mz`)* | `Prof@2026` | Escola Secundária de Massinga (`0808S0001`) |

---

## 🧪 Execução de Testes Automatizados

```bash
cd backend
pytest -v
```

---

## 📚 Índice de Documentação Técnica do Repositório

- 📘 **[Documentação Completa do Sistema](docs/DOCUMENTACAO_COMPLETA_DO_SISTEMA.md):** Manual exaustivo de todos os módulos, fluxos, fórmulas, tabelas e rotas do SIGE.
- 🛡️ **[Regras de Integridade do Sistema](backend/docs/REGRAS_DE_INTEGRIDADE.md):** Os 6 Pilares de Integridade (Isolamento Multi-Tenant, Domínio MEC, Unicidade, Imutabilidade de Pautas, Finanças e Auditoria).
- 📐 **[Arquitetura do Backend](backend/docs/ARCHITECTURE.md):** Padrões arquiteturais, cadeia de middlewares e RBAC no Django REST Framework.
- 🇲🇿 **[Regras Oficiais do MEC](backend/docs/MEC_RULES.md):** Critérios de aprovação (7ª–11ª vs. 12ª Classe) e fórmulas pedagógicas de Moçambique.
- 🗄️ **[Modelos de Dados do Backend](backend/docs/DATABASE_MODELS.md):** Catálogo de modelos e campos do Django ORM.
- 🖥️ **[Arquitetura do Frontend SPA/PWA](frontend/docs/ARCHITECTURE.md)**, **[Guia de Integração](frontend/docs/INTEGRATION_GUIDE.md)** e **[Catálogo de Páginas e Módulos](frontend/docs/PAGES_AND_MODULES.md)**.
- 🚀 **[Guia de Deploy Automatizado na Cloud/VM](docs/DEPLOY_AUTOMATIZADO.md)**.

---

## 📄 Licença

Este projeto está sob a licença [MIT](LICENSE).
