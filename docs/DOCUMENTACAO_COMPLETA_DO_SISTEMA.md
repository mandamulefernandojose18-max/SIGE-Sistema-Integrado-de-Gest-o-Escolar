# 📘 Documentação Completa do Sistema — SIGE (v2.5.0)
### Sistema Integrado de Gestão Escolar — Plataforma SaaS Multi-Tenant (MEC — Moçambique)

> **Documento Mestre de Arquitetura, Regras de Negócio, Módulos Funcionais, API e Infraestrutura**  
> **Versão do Sistema:** `2.5.0`  
> **Conformidade Normativa:** Ministério da Educação e Desenvolvimento Humano da República de Moçambique (MEC)  
> **Arquitetura:** Backend Django 5.1 + Django REST Framework (Python 3.12) | Frontend SPA/PWA Vanilla JS + Bootstrap 5 | PostgreSQL 16 (RLS) / SQLite3

### 🧭 Guias Especializados Complementares
Para consulta aprofundada por domínio técnico ou operacional:
- 🗺️ **[Central de Documentação](README.md)** — Mapa geral e diretrizes do sistema.
- 🛡️ **[Arquitetura e Segurança](ARQUITETURA_E_SEGURANCA.md)** — Multi-Tenancy, RLS, 6 Pilares de Integridade e JWT.
- ⚙️ **[Manual de Módulos e Operação](MANUAL_DE_MODULOS_E_OPERACAO.md)** — Guia passo a passo dos 18 módulos funcionais.
- 🇲🇿 **[Regras Pedagógicas Oficiais MEC](REGRAS_PEDAGOGICAS_MEC.md)** — Matriz curricular, fórmulas de cálculo e aprovação.
- 🗄️ **[Dicionário de Dados e Modelos](DICIONARIO_DE_DADOS.md)** — Especificação relacional das 17 tabelas e constraints.
- 🔌 **[Catálogo Completo da API REST](REFERENCIA_COMPLETA_API.md)** — Documentação de todos os endpoints RESTful.
- 🚀 **[Guia de Implantação e DevOps](GUIA_DE_IMPLANTACAO_E_DEVOPS.md)** — Docker, CI/CD, deploy na Cloud e guardrail de US$ 6/mês.

---

## 📑 Índice Geral

1. [Visão Geral do Sistema](#1-visão-geral-do-sistema)
2. [Arquitetura Técnica e Stack Tecnológica](#2-arquitetura-técnica-e-stack-tecnológica)
3. [Arquitetura Multi-Tenant, Assinaturas SaaS e Isolamento de Dados](#3-arquitetura-multi-tenant-assinaturas-saas-e-isolamento-de-dados)
4. [Autenticação Inteligente, Perfis de Acesso (RBAC) e Códigos Oficiais](#4-autenticação-inteligente-perfis-de-acesso-rbac-e-códigos-oficiais)
5. [Regras Pedagógicas e Curriculares Oficiais do MEC](#5-regras-pedagógicas-e-curriculares-oficiais-do-minedh)
6. [O Que Faz Cada Módulo do Sistema (19 Módulos e Fluxos Operacionais)](#6-o-que-faz-cada-módulo-do-sistema-19-módulos-e-fluxos-operacionais)
7. [Motor de Geração Documental (PDF, Word DOCX, Excel XLSX) e Cofre de Documentos](#7-motor-de-geração-documental-pdf-word-docx-excel-xlsx-e-cofre-de-documentos)
8. [Modelo de Dados Completo (17 Tabelas e Restrições de Integridade)](#8-modelo-de-dados-completo-17-tabelas-e-restrições-de-integridade)
9. [Catálogo Completo de Endpoints da API REST (`/api/v1/`)](#9-catálogo-completo-de-endpoints-da-api-rest-apiv1)
10. [Segurança, Defesa em Profundidade e Auditoria](#10-segurança-defesa-em-profundidade-e-auditoria)
11. [Execução Local, Docker, CI/CD e Deploy na Cloud](#11-execução-local-docker-cicd-e-deploy-na-cloud)

---

## 1. Visão Geral do Sistema

O **SIGE (Sistema Integrado de Gestão Escolar)** é uma plataforma corporativa **SaaS (Software as a Service) Multi-Tenant** concebida para digitalizar, padronizar e automatizar todas as operações académicas, pedagógicas, administrativas, financeiras e de certificação digital de instituições de ensino público e privado em **Moçambique**.

### Principais Capacidades do Sistema:
- **Gestão Multi-Escolar Isolada (Multi-Tenancy):** Múltiplas escolas operam na mesma infraestrutura em nuvem com isolamento absoluto de dados (`escola_id`), planos de subscrição em Meticais (`MZN`) e controlo automático de validade contratual.
- **Conformidade Integral com o MEC:** Implementa nativamente o Plano Curricular Nacional (7ª à 12ª Classe, incluindo todas as secções/áreas do 2º Ciclo), fórmulas oficiais de cálculo de médias (`MAC`, `MT`, `MFD`), regras distintas de transição/aprovação para 7ª–11ª Classe e 12ª Classe, escala qualitativa (`E`, `MB`, `B`, `S`, `NS`) e anotações regulamentares (`D`, `T`, `VT`, `F`, `AM`, `PPF`, `PDF`).
- **Geração Automática de Códigos Oficiais de Acesso:** Cada ator institucional (Director da Escola, DAP, Chefe da Secretaria, Director de Turma, Director de Classe, Professor e Estudante) recebe um código único estruturado segundo a codificação da escola, classe, turma, ano e área.
- **Portal Público de Auto-Inscrição Online:** Permite que candidatos e encarregados realizem a inscrição/matrícula diretamente pela internet nas escolas com vagas abertas, gerando imediatamente o número de matrícula e as credenciais de acesso do estudante.
- **Emissão Oficial Multiformato (PDF, Word `.docx`, Excel `.xlsx`) em Retrato/Paisagem:** Geração individual e em lote de Boletins, Declarações, Certificados com QR Code, Recibos, Fichas Biográficas, Cadernetas do Professor, Pautas Gerais da Turma, Actas do Conselho de Avaliação (com números por extenso) e Mapas Estatísticos do Aproveitamento Pedagógico.

---

## 2. Arquitetura Técnica e Stack Tecnológica

O sistema adota uma arquitetura **desacoplada em duas camadas principais** (API Backend RESTful + Cliente Frontend SPA/PWA), comunicando exclusivamente via JSON sobre HTTP/HTTPS com autenticação Bearer JWT.

```mermaid
flowchart TD
    subgraph Clientes ["Camada de Cliente (Web / Mobile PWA)"]
        LoginPublic["Portal Público (Login, Auto-Inscrição, Verificador QR)"]
        SPA["SPA SIGE (frontend/index.html + js/app.js - 18 Vistas)"]
        SW["Service Worker PWA (Cache & Instalação Offline)"]
    end

    subgraph Proxy ["Servidor Web / Reverse Proxy"]
        Nginx["Nginx (SSL Let's Encrypt :443 / Proxy /api/ -> :8000)"]
    end

    subgraph Backend ["Backend API (Django 5.1 + DRF - Porta 8000)"]
        MW1["CorsMiddleware & SecurityMiddleware"]
        MW2["TenantIsolationMiddleware (Extrai JWT e isola escola_id)"]
        MW3["TenantExpirationMiddleware (Bloqueio HTTP 402 se Expirado)"]
        RBAC["Permissões RBAC (8 Perfis + DT/DC Homologados)"]
        Apps["13 Aplicações de Domínio (apps/*)"]
        DocEngine["Motores Documentais: ReportLab (PDF), python-docx (Word), openpyxl (Excel)"]
    end

    subgraph Persistencia ["Camada de Dados"]
        DB[("PostgreSQL 16 (Produção + RLS) / SQLite3 (Dev)")]
    end

    LoginPublic --> Nginx
    SPA --> Nginx
    SW -.-> SPA
    Nginx --> MW1 --> MW2 --> MW3 --> RBAC --> Apps
    Apps --> DocEngine
    Apps --> DB
    DocEngine --> DB
```

### Stack Tecnológica Completa

| Camada | Tecnologias Utilizadas | Função no Sistema |
| :--- | :--- | :--- |
| **Backend Core** | Python 3.12, Django 5.1.6, Django REST Framework 3.15.2 | API RESTful, regras de negócio, ORM, validações e comandos CLI |
| **Autenticação & Segurança** | `djangorestframework-simplejwt` 5.4, `django-cors-headers` | Emissão/rotação de tokens JWT Bearer, claims customizadas e proteção CORS |
| **Documentação da API** | `drf-spectacular` 0.28 (OpenAPI 3.0) | Geração automática do esquema Swagger UI (`/api/docs/`) e ReDoc (`/api/redoc/`) |
| **Motor PDF** | `reportlab` 4.2.5, `Pillow` 11.1.0, `qrcode[pil]` 8.0 | Desenho vetorial nativo de pautas, actas, boletins, recibos e certificados com QR Code |
| **Motor Word (`.docx`)** | `python-docx` 1.1.2 | Geração de documentos editáveis rigorosamente formatados em *Times New Roman* |
| **Motor Excel (`.xlsx`)** | `openpyxl` 3.1.5 | Geração de grelhas eletrónicas de cadernetas, pautas e estatísticas em *Times New Roman* |
| **Servidor de Aplicação** | `gunicorn` 23.0 (Linux/Docker), `waitress` (Windows), `whitenoise` 6.9 | Execução WSGI multi-worker em produção e entrega otimizada de ficheiros estáticos |
| **Frontend SPA / PWA** | HTML5, CSS3, Vanilla JavaScript (ES6+), Bootstrap 5.3.3, Chart.js 4.4.4 | Interface reativa de página única, gráficos analíticos em tempo real e suporte PWA instalável |
| **Base de Dados** | PostgreSQL 16 (`psycopg` 3.2.4) / Supabase RLS / SQLite3 | Persistência relacional transacional com *CheckConstraints*, *UniqueConstraints* e *Row-Level Security* |
| **DevOps & Infraestrutura** | Docker, Docker Compose, Nginx Alpine, GitHub Actions | Contentorização, proxy reverso HTTPS, integração contínua (Pytest) e deploy automatizado via SSH |

---

## 3. Arquitetura Multi-Tenant, Assinaturas SaaS e Isolamento de Dados

### 3.1 Isolamento Estrito por Escola (`Tenant`)
1. **Particionamento Lógico Obrigatório:** Todas as entidades operacionais contêm a chave estrangeira `escola_id` apontando para `tenants.Escola`.
2. **Injeção Automática no Middleware (`common/middleware/tenant.py`):**
   - O `TenantIsolationMiddleware` decodifica o token JWT em cada requisição e define `request.escola_id` e `request.escola`.
   - Utilizadores comuns ficam estritamente confinados ao `escola_id` gravado no seu token JWT, ignorando qualquer parâmetro externo.
   - O perfil `SUPERADMIN` pode inspecionar e gerir qualquer instituição enviando o cabeçalho HTTP `X-Tenant-ID: <uuid>` ou `?escola_id=<uuid>`, permitindo suporte técnico e auditoria sem necessidade de conhecer as senhas locais da escola.
3. **Prevenção de Relacionamento Cruzado (`common/integrity/tenant_checks.py`):**
   - Antes de gravar qualquer entidade relacional (ex.: associar um `Aluno` a uma `Turma`, lançar uma `Nota` para `Aluno + Disciplina + Turma`, ou criar uma `AlocacaoDocente`), a função `validar_integridade_tenant()` verifica se todos os objetos pertencem exatamente à mesma escola. Qualquer discrepância levanta `CrossTenantViolation`.
4. **Row-Level Security (RLS) no PostgreSQL (`backend/supabase_schema_rls.sql`):**
   - Em ambientes PostgreSQL/Supabase, políticas nativas de RLS garantem ao nível do motor SQL que nenhuma query possa ler ou alterar linhas cujo `escola_id` difira de `auth.user_escola_id()`, exceto quando `auth.is_superadmin()` é verdadeiro.

### 3.2 Planos de Subscrição SaaS vs. Planos de Pagamento Próprios da Escola (Isolamento B2B vs. B2C)
O sistema aplica uma distinção arquitetural e de negócio estrita e inquebrável entre pagamentos da plataforma SaaS e cobranças de propinas escolares:

1. **Planos de Subscrição SaaS B2B (`tenants.Plano` & `tenants.SaasPlano`):**
   - **Exclusividade Super Admin:** Geridos e aplicados unicamente pelo Super Administrador da plataforma para governar as instituições escolares (licenciamento, quotas e contratos SaaS).
   - **Isolamento Total:** As definições e valores dos planos SaaS **jamais refletem para os utilizadores finais das escolas** (alunos, encarregados, professores). O endpoint `/api/v1/planos/` é protegido por `[IsAuthenticated, IsSuperAdmin]`, retornando `HTTP 403 Forbidden` a qualquer utilizador de escola comum.
   - **Vigências Disponíveis:** `MENSAL` (30 dias — padrão 2.500,00 MZN), `TRIMESTRAL` (90 dias), `SEMESTRAL` (180 dias) e `ANUAL` (365 dias), com limites contratados de `max_alunos` e `max_professores`.
   - **Verificação em Tempo Real (`common/middleware/tenant_expiration.py`):** Interceta todas as requisições privadas. Se a data atual ultrapassar `assinatura.data_fim`, retorna **HTTP 402 (Payment Required)**. Rotas isentas: `/health/`, `/api/v1/auth/*`, `/api/v1/saas-admin/*` e `/api/v1/public/*`.

2. **Planos de Pagamento e Propinas Próprios da Escola B2C (`pagamentos.PlanoPagamentoEscola`):**
   - **Autonomia da Instituição:** Cada escola cria, configura e gere a sua própria tabela de propinas, taxas de matrícula e emolumentos a aplicar aos seus respetivos alunos.
   - **Isolamento Absoluto entre Instituições:** O que uma instituição cria e gere no seu sistema vigora estrita e exclusivamente dentro do seu perímetro (`escola_id`), sem interferir, comprometer ou refletir em nenhuma outra escola da rede.

### 3.3 Isolamento Estrito de Identidade Visual, Temas de Cores, Logótipos e Definições Institucionais
A identidade visual, paleta cromática, marcas d'água e configurações operacionais de cada escola são 100% independentes e isoladas:

1. **Camada de Dados Relacional (`tenants.Escola`):**
   - Cada escola armazena em colunas dedicadas o seu `tema_codigo`, `tema_cor_primaria`, `tema_cor_hover`, `tema_cor_sidebar`, `tema_cor_sidebar_ativa`, `imagem_fundo_url`, `imagem_fundo_modo`, `imagem_fundo_opacidade`, `galeria_fundos` e `galeria_logos`.
   - Apenas ficheiros e itens de upload próprios da escola (`tipo: 'UPLOAD'`) são persistidos nos campos JSON, enquanto opções padrão de sistema (Emblema Nacional, Marca SIGE, Sem Imagem) são providas dinamicamente pelo motor do sistema.
   - As alterações realizadas nas **Definições da Escola** e logótipos vigoram exclusivamente na instituição ativa e jamais contaminam outras escolas.

2. **Isolamento no Frontend e Armazenamento Local (`localStorage`):**
   - Chaves de galeria e cache visual no browser utilizam estritamente o identificador da instituição (`sige_galeria_fundos_<id>`, `sige_galeria_logos_<id>`, `sige_tema_escola_<id>`).
   - Não são permitidos nem utilizados fallbacks globais ou genéricos (`default`). Qualquer resquício legado é imediatamente removido.
   - Seleção em tempo real: ao utilizar o espectro de cores (paleta rápida, slider contínuo de 0° a 360° ou seletor nativo), o sistema recalcula harmonicamente a paleta completa e sincroniza os cartões de temas pré-configurados. Quando uma cor customizada é escolhida, o cartão "Personalizado" é destacado como ativo, desmarcando os presets pré-definidos.
   - Na secção de Imagem de Fundo & Marca de Água, o cartão "Sem Imagem (Liso)" é ativo exclusivamente quando o modo for "Sem Imagem de Fundo", permanecendo em rigorosa harmonia com a pré-visualização superior.

3. **Separação Visual Entre Escolas e o Super Admin (SaaS Master):**
   - O painel Master SaaS do Super Administrador opera sempre sob a identidade institucional oficial do SIGE (`img/logo-sige.png`, cor azul `#1e3a8a`, sem marcas d'água de escolas).
   - Ao inspecionar uma escola, o Super Admin carrega isoladamente a identidade daquela instituição para efeitos de auditoria e suporte. Ao sair do modo de inspeção ou retornar à visão SaaS (`#view-saas`), o sistema executa a reposição imediata de estilos e marcas d'água (`restaurarPadraoTemaEFundo()`), garantindo isolamento total.

---

## 4. Autenticação Inteligente, Perfis de Acesso (RBAC) e Códigos Oficiais

### 4.1 Os 8 Perfis Nativos + 2 Cargos Homologáveis
O SIGE implementa Controlo de Acesso Baseado em Papéis (`RBAC`) com 8 perfis nativos no modelo `Usuario` e 2 cargos pedagógicos atribuíveis a docentes:

| Perfil / Código Role | Designação Institucional | Formato do Código Oficial de Acesso | Escopo de Atuação Principal |
| :--- | :--- | :--- | :--- |
| `SUPERADMIN` | Administrador Master SaaS | E-mail / Username Master | Governação global de todas as escolas, planos, contratos, métricas MRR/ARR/Churn e inspeção multi-tenant. |
| `ADMIN_ESCOLA` | Administrador da Instituição | E-mail Institucional | Gestão completa da escola, configurações gerais, utilizadores e todos os módulos locais. |
| `DIRECTOR_ESCOLA` | Director da Escola | `GD{CodigoEscola}` *(ex: `GD0808S0001`)* | Órgão executivo máximo da escola; homologa cargos de Director de Turma (`DT`) e Director de Classe (`DC`), fecha pautas e supervisiona toda a instituição. |
| `DAP` | Director Adjunto Pedagógico | `DP{CodigoEscola}` *(ex: `DP0808S0001`)* | Gestão pedagógica: turmas, horários/alocações, disciplinas, cadernetas, pautas, estatísticas, prazos trimestrais, desbloqueio de notas e controlo de visibilidade de notas dos alunos. |
| `CHEFE_SECRETARIA` | Chefe da Secretaria Escolar | `SECR{CodigoEscola}` *(ex: `SECR0808S0001`)* | Matrículas, transferências, arquivo de alunos, emissão de certificados, declarações, boletins, recibos e cobrança de propinas. |
| `FINANCEIRO` | Gestor Financeiro / Tesouraria | E-mail / Username Financeiro | Emissão de mensalidades/propinas em lote, liquidação de pagamentos (M-Pesa, e-Mola, POS, etc.), recibos e controlo de inadimplência. |
| `PROFESSOR` | Docente | `PR{CodigoEscola}.{Seq:03d}` *(ex: `PR0808S0001.001`)* | Lançamento de avaliações (`ACS`, `MAP`, `AT`) e faltas nas cadernetas das suas disciplinas/turmas alocadas e publicação de material escolar. |
| `DT` *(Cargo Docente)* | Director de Turma Homologado | `DT{CodigoEscola}.{Classe}.{Turma}` *(ex: `DT0808S0001.10.01`)* | Atribuído a um Professor e **homologado pelo Director da Escola**: gere a sua turma específica, configura os parâmetros da Sessão do Conselho de Avaliação e emite a Pauta Geral e a Acta do Conselho da turma. |
| `DC` *(Cargo Docente)* | Director de Classe Homologado | `DC{CodigoEscola}.{Classe}` *(ex: `DC0808S0001.10`)* | Atribuído a um Professor e **homologado pelo Director da Escola**: coordena pedagogicamente todas as turmas de uma determinada classe. |
| `ALUNO` | Estudante / Encarregado | `{CodigoEscola}.{Classe}.{Turma}.{Ano}.{Area}` | Acesso exclusivo ao Portal Privado do Aluno: consulta os seus dados biográficos, boletim de notas (quando liberado pelo DAP), estado de propinas e biblioteca de material escolar da sua classe. |

### 4.2 Motor de Login Inteligente (`LoginSerializer`)
No ecrã de login (`POST /api/v1/auth/login`), o campo de identificação aceita indistintamente:
1. **Endereço de E-mail** (ex.: `director@massinga.edu.mz`);
2. **Nome de Utilizador (`username`)**;
3. **Código Oficial de Acesso Permanente** (`GD...`, `DP...`, `SECR...`, `PR...`, ou código estruturado do aluno);
4. **Código de Função Homologada (`DT...` ou `DC...`)**: O sistema localiza a turma correspondente, verifica se o cargo foi formalmente **HOMOLOGADO** pelo Director da Escola (`dt_status_homologacao == 'HOMOLOGADO'` ou `dc_status_homologacao == 'HOMOLOGADO'`) e autentica o docente titular com o contexto do cargo diretivo.

---

## 5. Regras Pedagógicas e Curriculares Oficiais do MEC

Toda a lógica pedagógica encontra-se centralizada em `backend/common/utils/avaliacoes_mocambique.py` e `backend/apps/pautas/services.py`, garantindo rigor normativo em todos os ecrãs e documentos impressos.

### 5.1 Geografia Oficial de Moçambique (`geografia_mocambique.py`)
O sistema inclui a base oficial das **11 Províncias** (*Niassa, Cabo Delgado, Nampula, Zambézia, Tete, Manica, Sofala, Inhambane, Gaza, Maputo Província e Maputo Cidade*) e todos os respetivos **161 Distritos**, utilizada no registo de escolas, naturalidade/residência de alunos e professores, e no Portal Público de Inscrições.

### 5.2 Plano Curricular Nacional do Ensino Secundário Geral (7ª à 12ª Classe)
Quando uma escola acede ao módulo de disciplinas ou é criada no sistema, o SIGE semeia automaticamente (`auto-seed`) a matriz oficial do MEC:

- **1º Ciclo — 7ª, 8ª e 9ª Classes (Tronco Comum — 11 Disciplinas):**
  1. Língua Portuguesa (`5h`)
  2. Matemática (`5h`)
  3. Língua Inglesa (`3h`)
  4. Física (`3h`)
  5. Química (`3h`)
  6. Biologia (`3h`)
  7. Geografia (`3h`)
  8. História (`3h`)
  9. Educação Visual (`2h`)
  10. Educação Física (`2h`)
  11. Agropecuária (`2h`)
- **2º Ciclo — 10ª Classe (Tronco Comum — 12 Disciplinas):**
  - Língua Portuguesa (`5h`), Matemática (`5h`), Língua Inglesa (`3h`), Física (`3h`), Química (`3h`), Biologia (`3h`), Geografia (`3h`), História (`3h`), Introdução à Filosofia (`2h`), Educação Física (`2h`), Agropecuária (`2h`) e Tecnologias de Informação e Comunicação — TIC's (`2h`).
- **2º Ciclo — 11ª e 12ª Classes (Organizadas em 5 Secções / Áreas Curriculares Específicas):**
  1. **Ciências com Biologia (`CB` — 9 disciplinas):** Língua Portuguesa, Língua Inglesa, Introdução à Filosofia, Educação Física, Matemática, Biologia, Química, Física, TIC's.
  2. **Ciências com Desenho (`CD` — 9 disciplinas):** Língua Portuguesa, Língua Inglesa, Introdução à Filosofia, Educação Física, Matemática, Física, Desenho e Geometria Descritiva (`DGD`), Química, TIC's.
  3. **Ciências com Geografia (`CG` — 10 disciplinas):** Língua Portuguesa, Língua Inglesa, Introdução à Filosofia, Educação Física, Matemática, Geografia, Física, Química, Agropecuária, TIC's.
  4. **Letras com Geografia (`LG` — 9 disciplinas):** Língua Portuguesa, Língua Inglesa, Língua Francesa, Introdução à Filosofia, História, Geografia, Matemática Aplicada, Educação Física, TIC's.
  5. **Letras com História (`LH` — 9 disciplinas):** Língua Portuguesa, Língua Inglesa, Língua Francesa, Introdução à Filosofia, História, Geografia, Introdução à Literatura, Educação Física, TIC's.

> **Isolamento Estrito de Secção/Área:** Nas pautas, boletins, actas e cadernetas da 11ª e 12ª Classe, o motor curricular (`obter_disciplinas_plano_curricular` e `CURRICULO_REGRAS_AREAS`) filtra estritamente as disciplinas que pertencem à secção/área da turma, impedindo que disciplinas de *Letras* apareçam em turmas de *Ciências* e vice-versa.

### 5.3 Fórmulas de Cálculo de Notas Trimestrais e Anuais (Escala 0 a 20)
Em cada trimestre (`1_TRIMESTRE`, `2_TRIMESTRE`, `3_TRIMESTRE`), cada disciplina dispõe dos seguintes elementos de avaliação:
- `teste1` (**1ª ACS** — 1ª Avaliação Contínua e Sistemática)
- `teste2` (**2ª ACS** — 2ª Avaliação Contínua e Sistemática)
- `teste3` (**3ª ACS** — 3ª Avaliação Contínua e Sistemática, opcional)
- `teste4` (**MAP** — Média de Avaliações Práticas, opcional)
- `trabalho` (**MAS** — Média de Avaliações Sistemáticas / Trabalhos, opcional)
- `avaliacao_trimestral` (**AT** — Avaliação Trimestral /ACP)

#### Regras de Cálculo (`calcular_media_trimestral`):
1. **Condição de Validade da Média Trimestral (`MT`):**
   - A `MT` **só é formada e exibida** quando o aluno possui obrigatoriamente pelo menos **duas ACS (`1ª ACS` e `2ª ACS`) e a `AT`** lançadas. Caso contrário, a situação permanece como `Pendente` (`mt = None`).
2. **Média das Avaliações Contínuas (`MAC`):**
   $$MAC = \text{round}\left(\frac{\sum \text{Avaliações Contínuas Válidas}}{N}, 1\right)$$
   *(Nota técnica: campos opcionais como `3ª ACS`, `MAP` e `MAS` com valor `0` não lançado explicitamente não diluem a média das avaliações positivas já realizadas).*
3. **Média Trimestral (`MT`):**
   $$MT = \text{round}\left(\frac{2 \times MAC + AT}{3}\right)$$
   O resultado é arredondado para o **número inteiro mais próximo** na escala de `0` a `20` valores.
4. **Média Final da Disciplina (`MFD` — Anual):**
   $$MFD = \text{round}\left(\frac{MT_1 + MT_2 + MT_3}{3}\right)$$

### 5.4 Escala Qualitativa de Comportamento e Anotações Regulamentares

| Intervalo da Média (`MT` / `MFD`) | Sigla Oficial | Classificação Qualitativa | Representação Visual |
| :---: | :---: | :--- | :---: |
| $18,5 \le \text{Nota} \le 20,0$ | **E** | Excelente | Azul / Preto |
| $16,5 \le \text{Nota} < 18,5$ | **MB** | Muito Bom | Azul / Preto |
| $13,5 \le \text{Nota} < 16,5$ | **B** | Bom | Preto |
| $9,5 \le \text{Nota} < 13,5$ | **S** | Suficiente (Positiva) | Preto |
| $0,0 \le \text{Nota} < 9,5$ | **NS** | Não Suficiente (Negativa) | **Vermelho** |

**Códigos Oficiais de Situação/Anotação (`anotacao`):**
- `D`: Dispensado / Desistente
- `T`: Transferido
- `VT`: Veio Transferido
- `F`: Falecido
- `AM`: Anulação de Matrícula / Atestado Médico
- `PPF`: Perdeu por Faltas
- `PDF`: Perdeu por Disciplina / Pendente de Documentos

### 5.5 Critérios Oficiais de Aprovação e Transição na Pauta Geral (`avaliar_aprovacao_pauta`)
- **Regra Geral (7ª, 8ª, 9ª, 10ª e 11ª Classes) — Princípio dos 100% de Positivas:**
  - O aluno **SÓ APROVA** se obtiver nota final positiva ($\ge 10$ valores / $\ge 9,5$) em **TODAS as disciplinas** do seu plano curricular (**zero negativas**) e Média Geral $\ge 9,5$.
  - Basta **1 nota negativa** para o aluno ficar **Reprovado**.
- **Regra Especial da 12ª Classe:**
  - O aluno **APROVA** se cumprir cumulativamente os 3 requisitos:
    1. **Média Geral Anual $\ge 9,5$ valores** ($\ge 10$ arredondado);
    2. **Máximo de 2 disciplinas com nota negativa**;
    3. **Nenhuma nota negativa inferior a 8 valores** (se o aluno tiver qualquer disciplina com nota $\le 7$ valores, fica automaticamente **Reprovado**, independentemente da média geral).

---

## 6. O Que Faz Cada Módulo do Sistema (19 Módulos e Fluxos Operacionais)

### Módulo 1: Portal Público de Auto-Inscrição de Alunos (`#modalInscricaoPublica`)
Acessível diretamente a partir do ecrã inicial de Login, sem necessidade de autenticação prévia:
1. **Seleção Geográfica e Institucional:** O candidato filtra por Província e Distrito e escolhe uma escola que esteja com `inscricoes_abertas = True` e dentro do período válido (`inscricoes_inicio` a `inscricoes_fim`).
2. **Escolha Académica:** Seleciona a Classe pretendida (7ª à 12ª Classe), a Secção/Área (no caso da 11ª ou 12ª Classe) e o Turno preferencial (`MANHA`, `TARDE`, `NOITE`).
3. **Validação Rigorosa de Dados Biográficos:**
   - Nome completo, apelido, género e data de nascimento (valida idade compatível entre 10 e 25 anos).
   - Documento de identificação (`BI`, `Passaporte`, `DIRE`, `Cédula`, `Certidão`) com validação de formato do BI moçambicano (12 dígitos + 1 letra maiúscula).
   - `NUIT` opcional validado exatamente com 9 dígitos numéricos.
   - Filiação (Nome do Pai e da Mãe), Nome do Encarregado de Educação e Contacto telefónico moçambicano (`+258 82/83/84/85/86/87...`).
4. **Enturmação e Credenciais Instantâneas:**
   - O sistema procura automaticamente uma turma disponível daquela classe/secção que ainda tenha vagas livres (`ocupacao < capacidade_maxima`), gera o número de matrícula sequencial (`{ano}{seq:03d}`), cria a conta `Usuario(role='ALUNO')` com a senha definida pelo candidato e exibe no ecrã o **Cartão Oficial de Confirmação de Matrícula** contendo o **Código de Acesso do Estudante**.

### Módulo 2: Painel Master SaaS (`#view-saas` — Exclusivo `SUPERADMIN`)
- **KPIs Financeiros e Operacionais do SaaS:** Calcula em tempo real o **MRR** (*Monthly Recurring Revenue*), **ARR** (*Annual Recurring Revenue*), **Taxa de Churn (%)**, total de escolas ativas vs. expiradas/suspensas e volume global de alunos e professores na plataforma.
- **Gestão Completa do Ciclo de Vida das Escolas:**
  - Cadastro de novas escolas com geração automática do **Código Oficial da Escola** (formato `0101S0001` baseado no código da província e distrito), criação imediata da `AssinaturaEscola` e provisão automática das 4 contas diretivas (`ADMIN_ESCOLA`, `DIRECTOR_ESCOLA`, `DAP`, `CHEFE_SECRETARIA`).
  - **Inspeção Direta ("Botão Entrar"):** O SuperAdmin entra no painel de qualquer escola com um clique sem precisar de senha.
  - **Controlo Contratual:** Renovação de assinatura por $N$ dias, alteração de plano, suspensão/ativação manual (`toggle-status`), emissão de **Comprovativo/Contrato Oficial de Subscrição em PDF** e eliminação definitiva de escolas de teste.
- **Gestão de Planos Comerciais:** Criação e atualização de preços (MZN), duração em dias e limites de alunos/professores de cada plano.

### Módulo 3: Administração Institucional da Escola (`#view-escola`)
- **Configuração de Identidade e Parâmetros Letivos:**
  - Atualização do nome da escola, NUIT, endereço, província, distrito, telefone, e-mail, **Ano Letivo Ativo** (ex.: `2026`) e **Trimestre Ativo** (`1_TRIMESTRE`, `2_TRIMESTRE`, `3_TRIMESTRE`).
  - **Identidade Visual nos Documentos:** Opção de exibir o **Emblema Oficial da República de Moçambique** no cabeçalho das pautas/boletins e upload direto do **Logótipo da Escola** (convertido e persistido em `logo_base64` para funcionar offline e em PDFs gerados no servidor).
  - **Personalização Visual da Instituição (Tema de Cores e Imagem de Fundo/Marca de Água):**
    - **Catálogo de 8 Temas de Cores e Paleta Personalizada:** Cada instituição pode selecionar o seu esquema cromático institucional através de 8 temas pré-configurados (*Azul Clássico SIGE*, *Índigo Save*, *Verde Esmeralda*, *Bordeaux Rubi*, *Âmbar Dourado*, *Grafite Safira*, *Púrpura Real* e *Petróleo Ciano*) ou escolher o modo **Personalizado**, configurando diretamente a cor primária (`tema_cor_primaria`), cor de hover (`tema_cor_hover`), fundo da barra lateral (`tema_cor_sidebar`) e cor do menu ativo (`tema_cor_sidebar_ativa`).
    - **Papel de Parede, Imagem de Fundo e Marca de Água:** Permite carregar ficheiro de imagem local (PNG, JPG, WebP convertido para `imagem_fundo_base64`) ou indicar um link direto (`imagem_fundo_url`), com galeria dinâmica de fundos (`galeria_fundos`), ajuste fino de opacidade (5% a 50%) e 4 modos de exibição:
      - *Marca de Água Central Sutil:* Exibição discreta e translúcida centralizada na área de trabalho sem atrapalhar a leitura de tabelas e pautas;
      - *Papel de Parede Total (Wallpaper):* Cobertura completa de fundo da aplicação;
      - *Padrão Textura Suave:* Repetição contínua em padrão visual;
      - *Sem Imagem de Fundo:* Fundo monocromático e limpo usando apenas as cores do tema.
    - **Aplicação e Persistência Dinâmica:** As variáveis CSS (`--primary-color`, `--primary-hover`, `--sidebar-bg`, `--sidebar-active`, `--marca-dagua-url`, `--marca-dagua-opacity`) são injetadas no `:root` no arranque da sessão, ao inspecionar tenants no painel SuperAdmin e com atualização em tempo real (*Live Preview*) no formulário de administração da escola.
    - **Isolamento Multi-Tenant Estrito de Identidade Visual:** A personalização cromática, de logotipo e imagem de fundo por uma escola é encapsulada na linha da respetiva entidade (`tenants.Escola`) e **NÃO vaza nem influencia nenhuma outra instituição**. A tela pública de login e a visão Master SaaS do SuperAdmin mantêm permanentemente o padrão institucional neutro do SIGE (*Azul Clássico* `#1e3a8a`), ocorrendo limpeza e reposição imediata (`restaurarPadraoTemaEFundo()`) ao deslogar ou alternar de tenant, com cache em `localStorage` estritamente escopada pelo UUID da instituição (`sige_tema_escola_{id}`).
  - **Titulares dos Órgãos Diretivos:** Registo do nome e carreira do Director da Escola, nome do DAP e nome do Chefe da Secretaria (impressos automaticamente nas linhas de assinatura de todos os documentos oficiais).
  - **Controlo do Período de Inscrições Públicas:** Botão para abrir/fechar as inscrições online e definir as datas de início e encerramento.
  - **Controlo de Visibilidade de Notas (`permitir_visualizacao_notas`):** Permite ao DAP ou Director bloquear temporariamente a visualização de notas no Portal do Aluno durante períodos de conselho de notas ou manutenção de pautas.

### Módulo 4: Gestão de Turmas, Capacidade Máxima e Homologação de Cargos (`#view-turmas` e `#view-escola`)
- **Controlo de Lotação em Tempo Real:**
  - Cada turma possui `capacidade_maxima` configurável (padrão: **50 alunos**, validado até 200).
  - O sistema calcula em tempo real `ocupacao_atual`, `vagas_livres`, `percentual_ocupacao` e exibe barras visuais de progresso (**Verde** $< 80\%$, **Amarelo** $\ge 80\%$, **Vermelho** $100\%$ Lotada).
- **Numeração Sequencial Contínua por Classe:**
  - As turmas de uma mesma classe seguem numeração única contínua (`Turma 1`, `Turma 2`, `Turma 3`...), independentemente do turno ou secção, evitando duplicidades. Inclui utilitário de **Correção Automática de Numeração**.
- **Geração de Turmas em Lote (`/turmas/lote`):**
  - Cria múltiplas turmas de uma só vez para uma Classe, Área e Turno, atribuindo salas e capacidade máxima automaticamente.
- **Formação e Distribuição Automática de Alunos (`/turmas/distribuir-alunos`):**
  - Distribui automaticamente os alunos sem turma (ou redistribui alunos de uma classe/área) pelas turmas disponíveis, respeitando rigorosamente o limite de vagas e aplicando o critério pedagógico escolhido: **Ordem Alfabética**, **Equilíbrio de Género (M/F)** ou **Faixa Etária**.
- **Atribuição e Homologação de Director de Turma (`DT`) e Director de Classe (`DC`):**
  - O DAP/Admin propõe o professor para `director_turma` ou `director_classe` (estado inicial `PENDENTE`).
  - O **Director da Escola** executa a **Homologação Oficial** (`/turmas/<id>/homologar-cargo`), o que gera imediatamente os códigos de acesso `DT{cod_escola}.{classe}.{turma}` e `DC{cod_escola}.{classe}` no Cofre de Senhas.

### Módulo 5: Gestão de Alunos e Matrículas (`#view-alunos`)
- **Cadastro e Ficha Biográfica Completa:** Registo demográfico completo, documento de identificação, NUIT, filiação, contactos de emergência e vinculação à classe, secção/área e turma.
- **Geração Automática de Matrícula:** Código sequencial anual (`2026001`, `2026002`...) e criação automática da conta de acesso do estudante.
- **Transferência Interna de Turma (`/alunos/<id>/transferir`):**
  - Verifica se a turma de destino pertence à mesma escola e possui vagas disponíveis.
  - Transfere o aluno e **migra automaticamente todas as suas notas do ano letivo corrente** para a nova turma, preservando o histórico académico sem perda de avaliações.
- **Estatísticas Demográficas em Tempo Real (`/alunos/stats`):** Total de alunos ativos, inativos, transferidos e evadidos, taxas de retenção e evasão escolar e proporção de género (`Masculino` vs. `Feminino`).

### Módulo 6: Corpo Docente, Carreiras MEC, Carga Horária e Alocações (`#view-professores`)
- **Enquadramento nas Carreiras Oficiais do MEC:**
  - Suporta as categorias docentes de Moçambique: `Docente N4 (DN4)`, `Docente N3 (DN3)`, `Docente N2 (DN2)`, `Docente N1 (DN1)`, `Especialista de Educação`, `Mestre` e `Professor Doutor`.
- **Cálculo Automático de Horas Normais vs. Horas Extras:**
  - Cada professor possui uma carga horária base (`carga_horaria_semanal`, padrão 24h) e limites configuráveis por classe (`carga_maxima_por_classe`).
  - À medida que o professor é alocado a turmas e disciplinas, o sistema soma a carga horária semanal de cada disciplina e separa automaticamente quantas horas são **Horas Normais** e quantas constituem **Horas Extras** em cada classe.
- **Alocação Docente (`AlocacaoDocente`):**
  - Vincula `Professor + Disciplina + Turma`.
  - Ao alocar o professor, o sistema **inicializa automaticamente as Pautas/Cadernetas dos 3 Trimestres** para aquela turma, deixando-as prontas para o lançamento de notas.

### Módulo 7: Disciplinas e Plano Curricular (`#view-disciplinas`)
- Gestão do catálogo de disciplinas por Classe (7ª à 12ª) e Secção/Área de Estudo, com códigos canónicos (`LP-10`, `MAT-12CB`, `DGD-11CD`, etc.) e carga horária semanal.
- Botão para **Sincronizar Currículo Nacional MEC** (`seed-curriculo`) a qualquer momento.
- **Gráfico de Ranking de Reprovação (`/disciplinas/ranking-reprovacao`):** Calcula e exibe em gráfico Chart.js as disciplinas com maior índice percentual de notas negativas na escola.

### Módulo 8: Biblioteca Digital de Material Escolar (`#view-material-escolar`)
- Acervo pedagógico organizado da **1ª à 12ª Classe**, acessível a professores, alunos e direção.
- **Auto-Seed Inicial:** Inclui 34 manuais e livros escolares oficiais do Sistema Nacional de Educação pré-catalogados.
- **Upload Local até 15 MB ou Link Externo:** Permite a professores e administradores publicar ficheiros em PDF, Word (`.docx`), Excel (`.xlsx`), PowerPoint (`.pptx`), EPUB, ZIP ou imagens, classificados como `MANUAL`, `FICHA`, `LIVRO`, `EXERCICIOS`, `GUIA` ou `APOSTILA`, com download binário direto (`/material-escolar/<id>/download`).

### Módulo 9: Caderneta Electrónica do Professor (`#view-caderneta`)
- **Navegação Hierárquica:** Seleção encadeada de `Classe` $\to$ `Secção/Área` $\to$ `Turma e Disciplina` $\to$ `Trimestre`.
- **Visão Integrada dos 3 Trimestres + MFD:**
  - Exibe todos os alunos da turma por ordem alfabética com as colunas oficiais do 1º, 2º e 3º Trimestres (`1ª ACS`, `2ª ACS`, `3ª ACS`, `MAP`, `MAS`, `AT`, `MT`, `COM`, `Obs`) e a **Média Final da Disciplina (`MFD`)** + Situação Anual.
- **Rodapé Estatístico Demográfico Automático por Coluna:**
  - Para **cada coluna de avaliação** (`teste1` a `media_final` nos 3 trimestres), o backend (`GET /api/v1/notas/caderneta`) calcula e exibe no rodapé da grelha:
    - **Avaliados** (`H`, `M`, `HM`)
    - **Positivos ($\ge 10$)** (`H`, `M`, `HM` e `% Positivos`)
    - **Negativos ($< 10$)** (`H`, `M`, `HM` e `% Negativos`)
- **Lançamento Individual e em Lote:**
  - Permite lançar ou editar notas e faltas de toda a turma com cálculo instantâneo de `MAC`, `MT`, `Comportamento` e `Resultado`.
- **Exportação Direta da Caderneta:** Botões para descarregar o **Mapa Oficial de Registo de Avaliações** em **Excel (`.xlsx`)**, **PDF (`.pdf`)** ou imprimir diretamente em formato **A4 Horizontal (Landscape)**.

### Módulo 10: Calendário de Notas e Desbloqueio de Trimestre (`#view-desbloqueio`)
- **Prazos Trimestrais (`GET/POST /api/v1/notas/prazos-trimestrais`):**
  - O DAP/Direção define as datas oficiais de abertura (`data_inicio`) e encerramento (`data_fim`) para o lançamento de notas do 1º, 2º e 3º Trimestres.
  - Fora da janela temporal ativa (ou quando a pauta já foi fechada), os professores ficam impedidos de alterar notas.
- **Autorização Excecional de Desbloqueio (`PermissaoEdicaoNotas`):**
  - Quando um professor atrasa o lançamento por motivo justificado ou precisa retificar uma nota após o fecho do prazo/pauta, o DAP ou Director concede uma **Autorização de Edição Temporária** especificando a Turma, a Disciplina (ou todas), o Trimestre, o Professor (ou todos da turma) e o motivo formal, podendo revogá-la a qualquer instante.

### Módulo 11: Pautas Gerais da Turma e Actas do Conselho de Avaliação (`#view-pautas` e `#view-director-turma`)
- **Sub-aba 1 — Pauta Geral Oficial da Turma:**
  - Consolida num único mapa todas as disciplinas oficiais da secção/área da turma, apresentando para cada aluno as médias do `1ºT`, `2ºT`, `3ºT` e `MFD` em cada disciplina, Faltas acumuladas, Média Geral Global, Comportamento e Observação Final (`Aprovado`, `Reprovado`, `Transferido`, `Desistente`, etc.).
  - Inclui o **Quadro Estatístico Oficial da Pauta** com apuramento de Matriculados, Avaliados, Positivos (`%`) e Negativos (`%`) discriminados por `H`, `M` e `HM` para os 3 trimestres e final anual.
- **Sub-aba 2 — Acta Oficial do Conselho de Avaliação:**
  - Gera automaticamente o documento formal da reunião do Conselho de Turma segundo o modelo do MEC:
    - Cabeçalho com Emblema da República, Governo da Província, Direção Distrital e Nome da Escola.
    - Narrativa oficial com **conversão automática de números e percentagens por extenso em português** (ex.: *"vinte e cinco alunos, correspondente a oitenta e três vírgula três por cento..."*).
    - Tabela demográfica consolidada (`H`, `M`, `HM`, `%`) de Matriculados, Desistentes, Transferidos, Avaliados, Em Situação Positiva e Em Situação Negativa.
    - Linhas de assinatura para o Presidente do Conselho, Secretário (Director de Turma) e Homologação do Director da Escola.
- **Painel Exclusivo do Director de Turma (`#view-director-turma`):**
  - Permite ao Director de Turma configurar e guardar os **Parâmetros da Sessão do Conselho de Avaliação** (Nome do Presidente, Data da Realização, Hora de Início e Hora de Término para o Iº, IIº e IIIº Trimestres), que são imediatamente refletidos na Acta Oficial em ecrã, PDF e Word.

### Módulo 12: Estatística Oficial do Aproveitamento Pedagógico Escolar (`#view-estatisticas-aproveitamento`)
Motor analítico completo (`GET /api/v1/dashboard/estatisticas-aproveitamento`) estruturado em **4 níveis de agregação** (todos discriminados por Género `H`, `M`, `HM` e `%`):
1. **Resumo Global da Escola (`geral_escola`):** Total de turmas, matriculados, avaliados, aprovados (`%`), reprovados (`%`), sem notas e média global da escola.
2. **Estatística Agregada por Classe (`por_classe`):** Comparativo de aproveitamento da 7ª à 12ª Classe.
3. **Estatística Detalhada por Turma (`por_turma`):** Desempenho de cada turma com indicação do turno, área e Director de Turma.
4. **Estatística por Disciplina e Docente (`por_disciplina`):** Taxa de positivas, negativas e média de cada disciplina em cada turma, identificando o professor titular.
- **Exportação Oficial:** Download direto do relatório completo em **PDF** e **Excel (`.xlsx`)**.

### Módulo 13: Emissão de Certificados Digitais com QR Code e Verificação Pública (`#view-certificados`)
- Emite 4 tipologias de documentos certificados:
  - `CONCLUSAO` (Certificado de Conclusão de Ciclo/Classe)
  - `TRANSFERENCIA` (Guia/Certificado de Transferência Escolar)
  - `DECLARACAO` (Declaração Oficial com Notas)
  - `MATRICULA` (Comprovativo Oficial de Matrícula)
- Cada emissão gera um **Código de Autenticidade Único** (`CERT-XXXXXXXXXX`) e um **QR Code criptográfico** que aponta para:
  `https://<dominio>/verificar-certificado.html?codigo=CERT-XXXXXXXXXX`
- Qualquer entidade externa (outra escola, universidade, empregador ou ministério) pode ler o QR Code com a câmara do telemóvel e validar a autenticidade pública do documento em tempo real sem precisar de login.

### Módulo 14: Gestão Financeira, Propinas e Tesouraria (`#view-pagamentos`)
O módulo financeiro do SIGE implementa a gestão completa da tesouraria da instituição, operando com total autonomia em relação aos planos de assinatura da plataforma:
- **Separação Rígida SaaS vs. Escola:**
  - O catálogo de assinaturas do Super Admin (`SaasPlano`) é restrito à governança B2B entre a plataforma e as escolas.
  - Cada escola cria e mantém a sua própria tabela de propinas e emolumentos (`PlanoPagamentoEscola`), que se aplica estritamente aos seus próprios alunos. Nenhuma instituição tem visibilidade sobre os planos ou dados financeiros de outra.
- **Estrutura dos Planos Próprios da Escola (`PlanoPagamentoEscola` / `/api/v1/pagamentos/planos-escola/`):**
  - **Parâmetros Parametrizáveis:** Nome do plano (ex: *Propina Geral 10ª Classe*, *Taxa de Matrícula*), Valor em Meticais (`MZN`), Periodicidade (`MENSAL`, `TRIMESTRAL`, `SEMESTRAL`, `ANUAL`, `UNICA`), Dia de Vencimento Padrão (1 a 31), Multa por Atraso (%) e Descrição.
  - **Controlo de Ciclo de Vida:** Criação, edição e ativação/desativação de planos com contagem de faturas associadas. Planos desativados são preservados para histórico contábil sem permitir novas vinculações.
  - **Permissões de Acesso:** Apenas perfis autorizados da instituição (`ADMIN_ESCOLA`, `DIRECTOR_ESCOLA`, `CHEFE_SECRETARIA`, `FINANCEIRO`) podem criar ou alterar planos de pagamento escolares.
- **Interface em Abas Duplas (`frontend/pages/painel-escola/pagamentos.html` e `painel-financeiro/pagamentos.html`):**
  - **Aba 1 (Cobranças & Mensalidades aos Alunos):** Gestão operacional de faturas, filtros por turma, aluno, mês de referência e estado, liquidação com emissão imediata de recibo e emissão individual/em lote.
  - **Aba 2 (Planos & Tabela de Propinas da Escola):** Tabela de emolumentos e propinas vigentes na instituição, com badges de periodicidade, dia de vencimento, percentual de multa e ações de edição/estado.
- **Emissão Individual e Geração em Lote por Turma (`/pagamentos/gerar-turma`):**
  - Permite selecionar um plano de pagamento escolar existente para preenchimento automático inteligente do valor, descrição e dia de vencimento, ou introduzir valores customizados.
  - Gera simultaneamente cobranças para todos os estudantes ativos da turma no mês de referência selecionado (Janeiro a Dezembro), prevenindo duplicidade de faturas.
- **Validação de Integridade Multi-Tenant (`validar_integridade_tenant`):**
  - O sistema impede em nível de modelo (`clean()`) e API que uma cobrança vincule um plano de pagamento ou aluno pertencente a outra escola.
- **Deteção Automática de Atrasos:** Cobranças `PENDENTE` cuja `data_vencimento` já passou são automaticamente classificadas como `ATRASADO`.
- **Liquidação Multicanal e Pagamento de Saldo com Carteira Móvel (`/pagamentos/<id>/liquidar` e `/alunos/me/pagamentos/`):**
  - Permite liquidar o saldo devedor através dos métodos oficiais de Moçambique: **Carteira Móvel M-Pesa (`MPESA`)**, **Carteira Móvel e-Mola (`EMOLA`)**, **POS / Cartão (`POS`)**, **Transferência Bancária (`TRANSFERENCIA`)** ou **Numerário (`NUMERARIO`)**.
  - Suporta o registo do número de telefone móvel (`+258 84/85` ou `+258 86/87`) e do código/referência da transacção móvel para conciliação imediata.
  - Acesso direto e responsivo tanto para a gestão escolar/secretaria como para o próprio aluno no **Espaço do Aluno**, com botão dedicado *"Pagar com Carteira Móvel"*.
  - Gera automaticamente o número de recibo sequencial único (`REC-2026-00001`) pronto para impressão ou download em PDF/Word/Excel.
- **KPIs Financeiros (`/pagamentos/stats`):** Total Recebido (MZN), Total Pendente (MZN), Total em Atraso (MZN), Taxa de Adimplência (%), Taxa de Inadimplência (%) e histórico mensal de faturação dos 12 meses do ano.

### Módulo 15: Central de Impressão Individual e em Lote (`#view-impressao`)
Centro unificado para emissão, pré-visualização em folha A4 e descarregamento de todos os documentos escolares:
- **7 Tipologias Documentais na Central:**
  1. **Boletim Individual de Aproveitamento (`BOLETIM`)**
  2. **Declaração de Matrícula / Frequência / Notas (`DECLARACAO`)**
  3. **Certificado Oficial com QR Code (`CERTIFICADO`)**
  4. **Recibo Oficial de Pagamento (`RECIBO`)**
  5. **Ficha Biográfica / Cadastro do Aluno (`FICHA`)**
  6. **Pauta Geral Oficial da Turma (`PAUTA_TURMA`)**
  7. **Acta Oficial do Conselho de Avaliação (`ACTA_CONSELHO`)**
- **Modo Individual vs. Modo Lote por Turma:**
  - O operador pode selecionar **um Aluno específico** ou escolher **"Todos os Alunos da Turma (Emissão em Lote)"**, gerando num único ficheiro multi-página todos os boletins, declarações, certificados, recibos ou fichas da turma inteira.
- **Escolha de Orientação e Formato:**
  - Permite alternar entre orientação **Automática**, **Vertical (Retrato / Portrait)** ou **Horizontal (Paisagem / Landscape)** e exportar em **PDF (`.pdf`)**, **Word (`.docx`)** ou **Excel (`.xlsx`)**.

### Módulo 16: Portal Privado do Aluno (`#view-aluno-perfil`, `#view-aluno-notas`, `#view-aluno-pagamentos`)
Quando um estudante acede com o seu Código Oficial de Estudante:
- A barra lateral exibe apenas as vistas permitidas ao perfil `ALUNO`:
  1. **O Meu Perfil (`#view-aluno-perfil`):** Dados pessoais, número de matrícula, código de acesso, turma, sala, turno e filiação.
  2. **As Minhas Notas (`#view-aluno-notas`):** Grelha das suas disciplinas com notas de `1ª ACS`, `2ª ACS`, `3ª ACS`, `MAP`, `MAS`, `AT`, `MT` e `Comportamento` por trimestre (respeitando o bloqueio temporário do DAP caso `permitir_visualizacao_notas = False`).
  3. **Material Escolar (`#view-material-escolar`):** Download gratuito de manuais, fichas e livros da sua classe.
  4. **As Minhas Propinas (`#view-aluno-pagamentos`):** Consulta de mensalidades pagas, pendentes e recibos emitidos.

### Módulo 17: Cofre Restrito de Credenciais e Gestão de Senhas (`#view-usuarios-senhas`)
Acessível apenas a Administradores, Director da Escola, DAP e Chefe de Secretaria:
- **Sincronização Inteligente (`/auth/usuarios-cofre`):** Ao abrir o cofre, o backend verifica e cria automaticamente quaisquer contas de utilizador em falta para os órgãos diretivos (`GD`, `DP`, `SECR`), professores (`PR`), directores de turma/classe homologados (`DT`, `DC`) e alunos matriculados.
- Exibe a tabela completa com Nome, Perfil/Cargo, **Código Oficial de Acesso**, E-mail, **Senha Padrão / Inicial** e Estado (`Ativo`/`Inativo`).
- Permite filtrar por perfil, copiar o código de acesso com um clique, **redefinir a palavra-passe** de qualquer utilizador e ativar/bloquear contas.

### Módulo 18: Auditoria e Registo de Acessos (`#view-acessos`)
- Exibe o registo cronológico (`LogAcesso`) de todas as autenticações bem-sucedidas (`LOGIN_SUCESSO`), tentativas falhadas (`LOGIN_FALHA`) e bloqueios por expiração de assinatura (`ACESSO_BLOQUEADO_EXPIRADO`), detalhando Utilizador, Perfil, Navegador/Dispositivo (`user_agent`) e Data/Hora exata.

### Módulo 19: Assinatura do Sistema e Pagamentos SaaS da Escola (`#view-assinatura-escola`)
- **Painel Financeiro Institucional:**
  - **Estado da Subscrição:** Acompanhamento dinâmico (`Activa`, `Fatura Aberta`, `Em Atraso`, `Restrita` ou `Suspensa`) com badges e banner de avisos de tolerância.
  - **Plano Contratado:** Identificação institucional como **Plano Básico** com indicação da periodicidade (`Mensal`) e valor contratado em Meticais (`MZN`).
  - **Faturação & Submissão de Comprovativos:** Visualização das faturas emitidas e modal de registo de pagamentos com upload de talão/comprovativo bancário.
  - **Coordenadas Oficiais em Moçambique (Sem Dados Fictícios):** Carteiras móveis M-Pesa (Vodacom 84) e e-Mola (Movitel 86), além de contas e NIB no Millennium BIM e BCI com dados dinâmicos configuráveis pelo Super Administrador (iniciando estritamente em branco para evitar números simulados ou falsos).

### Módulo 20: Ferramentas & Integrações — Prompt do Gateway (`#view-prompt-gateway` / `/ferramentas/prompt-gateway`)
- **Acesso Restrito:** Exclusivo para perfis diretivos e de administração (`SUPERADMIN`, `ADMIN_ESCOLA`, `DIRECTOR_ESCOLA`, `DAP`, `CHEFE_SECRETARIA`).
- **Página de Prompt com Layout Completo:** Rota `/ferramentas/prompt-gateway` servida com o layout, sidebar, cabeçalho e variáveis de estilo do sistema, com cabeçalhos anti-indexação (`X-Robots-Tag: noindex`, `<meta name="robots" content="noindex">`) e `Cache-Control: no-store`.
- **Leitura em Cache e Sincronização Dinâmica:** Carregamento do ficheiro `conteudo/prompt-gateway.txt` (UTF-8) em memória com recarregamento em tempo real via `fs.watch`.
- **Cópia Acessível e Descarregamento Direto:** Botão "Copiar prompt" via `navigator.clipboard` (com fallback de selecção `Range` + `execCommand`) e região acessível `aria-live="polite"` de confirmação (~2,5 s), acompanhado do botão "Descarregar .txt" com download via `/ferramentas/prompt-gateway/descarregar`.
- **Segurança Anti-XSS e CSP:** Escape integral e sanitização automática de caracteres especiais (`<`, `>`, `&`) e execução via ficheiro estático próprio (`/js/prompt-gateway.js`), sem scripts inline.

---

## 7. Motor de Geração Documental (PDF, Word DOCX, Excel XLSX) e Cofre de Documentos

Implementado em `backend/apps/documentos/views.py`, o motor documental do SIGE garante que todos os ficheiros gerados pelo servidor sigam rigorosamente os padrões formais do ensino moçambicano:

1. **Cabeçalho Institucional Oficial:**
   - Inclui o **Emblema da República de Moçambique** (`frontend/img/emblema-mocambique.png`), os dizeres *"REPÚBLICA DE MOÇAMBIQUE"*, *"GOVERNO DA PROVÍNCIA DE ..."*, *"DIRECÇÃO DISTRITAL DE EDUCAÇÃO DE ..."*, o **Nome Oficial da Escola** e o **Logótipo da Escola** (se configurado).
2. **Três Formatos Nativos no Servidor:**
   - **PDF (`ReportLab`):** Desenho vetorial de alta precisão com tabelas paginadas, cores regulamentares (notas negativas `< 10` e `NS` destacadas a vermelho) e QR Codes gerados em memória via `qrcode` + `Pillow`.
   - **Word `.docx` (`python-docx`):** Documentos editáveis com tipografia integralmente configurada em **Times New Roman**, tabelas com bordas visíveis, cabeçalhos institucionais e blocos de assinatura.
   - **Excel `.xlsx` (`openpyxl`):** Folhas de cálculo formatadas em **Times New Roman**, células mescladas no cabeçalho oficial, ajuste automático de largura de colunas, bordas finas e configuração de página pronta para impressão A4.
3. **Cofre Persistente de Documentos na Base de Dados (`DocumentoSalvo`):**
   - Cada vez que um PDF, DOCX ou XLSX é gerado (individualmente ou em lote), a função `_persistir_documento_bd()` armazena automaticamente uma cópia binária codificada em Base64 na tabela `sige_documentos_salvos` (mantendo os últimos 200 documentos por escola para otimização de espaço) e grava um registo de auditoria em `sige_logs_impressao`.
   - Através dos endpoints `/api/v1/documentos/salvos` e `/api/v1/documentos/salvos/<doc_id>/download`, a escola pode consultar o histórico de documentos emitidos e voltar a descarregar qualquer ficheiro exatamente como foi emitido.

---

## 8. Modelo de Dados Completo (17 Tabelas e Restrições de Integridade)

Todas as tabelas utilizam chaves primárias `UUID v4`, prefixo `sige_` no banco de dados e validação automática `full_clean()` antes de cada `save()`.

```mermaid
erDiagram
    PLANO ||--o{ ESCOLA : "define limites"
    PLANO ||--o{ ASSINATURA_ESCOLA : "subscreve"
    ESCOLA ||--o{ ASSINATURA_ESCOLA : "possui"
    ESCOLA ||--o{ USUARIO : "pertence"
    ESCOLA ||--o{ LOG_ACESSO : "audita"
    ESCOLA ||--o{ TURMA : "organiza"
    ESCOLA ||--o{ ALUNO : "matricula"
    ESCOLA ||--o{ PROFESSOR : "contrata"
    ESCOLA ||--o{ DISCIPLINA : "leciona"
    ESCOLA ||--o{ NOTA : "regista"
    ESCOLA ||--o{ PAUTA : "consolida"
    ESCOLA ||--o{ PAGAMENTO : "fatura"
    ESCOLA ||--o{ CERTIFICADO : "emite"
    ESCOLA ||--o{ MATERIAL_ESCOLAR : "publica"
    ESCOLA ||--o{ DOCUMENTO_SALVO : "arquiva"

    TURMA ||--o{ ALUNO : "enturma"
    PROFESSOR ||--o{ TURMA : "director_turma / director_classe"
    PROFESSOR ||--o{ ALOCACAO_DOCENTE : "leciona em"
    DISCIPLINA ||--o{ ALOCACAO_DOCENTE : "alocada a"
    TURMA ||--o{ ALOCACAO_DOCENTE : "recebe"

    ALUNO ||--o{ NOTA : "obtém"
    DISCIPLINA ||--o{ NOTA : "avalia"
    TURMA ||--o{ NOTA : "contexto"
    TURMA ||--o{ PAUTA : "gera"
    TURMA ||--o{ PERMISSAO_EDICAO_NOTAS : "desbloqueia"
    ALUNO ||--o{ PAGAMENTO : "paga"
    ALUNO ||--o{ CERTIFICADO : "titular"
```

### Resumo das 17 Tabelas do Sistema (`sige_*`)

| # | Tabela SQL (`db_table`) | Modelo Django (`app.Model`) | Descrição e Restrições Principais (`Constraints`) |
| :-: | :--- | :--- | :--- |
| **1** | `sige_usuarios` | `accounts.Usuario` | Contas de utilizador (8 roles), `email` único, `codigo_acesso` indexado, FK `escola`. |
| **2** | `sige_logs_acesso` | `accounts.LogAcesso` | Registo de auditoria de logins, falhas e bloqueios (`ip`, `user_agent`, `tipo`). |
| **3** | `sige_planos` | `tenants.Plano` | Catálogo de planos SaaS (`MENSAL`, `TRIMESTRAL`, `SEMESTRAL`, `ANUAL`), preço em MZN e cotas `max_alunos`/`max_professores`. |
| **4** | `sige_escolas` | `tenants.Escola` | Registo institucional do Tenant, `codigo_escola`, `nif_cnpj` único, `ano_letivo_ativo`, `trimestre_ativo`, `logo_base64`, `inscricoes_abertas`, `permitir_visualizacao_notas`. |
| **5** | `sige_assinaturas_escolas` | `tenants.AssinaturaEscola` | Contratos de subscrição da escola (`data_inicio`, `data_fim`, `valor`, `status`, `metodo_pagamento`). Check: `data_fim > data_inicio`. |
| **6** | `sige_alunos` | `alunos.Aluno` | Cadastro biográfico e académico do estudante, `matricula` única global, FK `turma`, `classe`, `area`, `status`. |
| **7** | `sige_professores` | `professores.Professor` | Cadastro docente, `carreira` MEC, `carga_horaria_semanal` (1–60h), `carga_maxima_por_classe` (JSON). Unique: `(escola, email)`. |
| **8** | `sige_professor_disciplina_turma` | `professores.AlocacaoDocente` | Associação entre Professor, Disciplina e Turma. Unique: `(escola, professor, disciplina, turma)`. |
| **9** | `sige_turmas` | `turmas.Turma` | Turmas por `grau_ano` (Classe), `area` (Secção), `turno`, `sala`, `capacidade_maxima`, FKs `director_turma` e `director_classe`. Unique: `(escola, grau_ano, nome, ano_letivo)`. |
| **10** | `sige_disciplinas` | `disciplinas.Disciplina` | Matriz curricular por `classe` e `area`, `codigo`, `carga_horaria`. Unique: `(escola, codigo, ano_letivo)`. |
| **11** | `sige_notas` | `notas.Nota` | Avaliações trimestrais (`teste1`..`teste4`, `trabalho`, `avaliacao_trimestral`, `media_final`, `faltas`, `comportamento`, `anotacao`, `resultado`). Unique: `(aluno, disciplina, turma, periodo)`. Check: `0 <= media_final <= 20` e `faltas >= 0`. |
| **12** | `sige_permissoes_edicao_notas` | `notas.PermissaoEdicaoNotas` | Autorizações temporárias de desbloqueio de lançamento de notas concedidas pelo DAP/Direção. |
| **13** | `sige_pautas` | `pautas.Pauta` | Estado de consolidação da pauta por turma e período (`ABERTA`, `EM_CONSOLIDACAO`, `FECHADA`). Unique: `(escola, turma, ano_letivo, periodo)`. |
| **14** | `sige_material_escolar` | `material_escolar.MaterialEscolar` | Biblioteca digital de ficheiros (`conteudo_base64` ou `arquivo_url`) da 1ª à 12ª Classe. |
| **15** | `sige_logs_impressao` | `documentos.LogImpressao` | Auditoria de documentos emitidos e armazenamento JSON de configurações de conselho de turma, homologações DT/DC e prazos trimestrais. |
| **16** | `sige_documentos_salvos` | `documentos.DocumentoSalvo` | Cofre persistente de ficheiros PDF, DOCX e XLSX gerados pelo sistema (`conteudo_base64`, `mime_type`, `tamanho_bytes`). |
| **17** | `sige_pagamentos` / `sige_certificados` | `pagamentos.Pagamento` & `certificados.Certificado` | `sige_pagamentos`: Mensalidades/propinas em MZN e recibos `REC-...` (Checks: `valor > 0`, `valor_pago >= 0`).<br>`sige_certificados`: Certificados oficiais com `codigo_autenticidade` único (`CERT-...`) e `qrcode_data`. |

---

## 9. Catálogo Completo de Endpoints da API REST (`/api/v1/`)

Todas as respostas seguem o envelope JSON padronizado por `common/responses/api_response.py` e `common/exceptions/handler.py`.

### 9.1 Saúde, Esquema OpenAPI e Portal Público
| Método | Endpoint | Permissão | Descrição |
| :---: | :--- | :---: | :--- |
| `GET` | `/health/` | Pública | Verifica o estado de saúde da API (`status: ok`, versão `2.5.0`). |
| `GET` | `/api/docs/` e `/api/redoc/` | Pública | Interfaces interativas Swagger UI e ReDoc (esquema em `/api/schema/`). |
| `GET` | `/api/v1/public/escolas` | Pública | Lista escolas ativas com inscrições públicas abertas dentro do prazo. |
| `POST` | `/api/v1/public/inscrever-aluno` | Pública | Realiza a auto-inscrição pública de um novo estudante e devolve matrícula e código de acesso. |
| `GET` | `/api/v1/public/verificar-certificado/<codigo>` | Pública | Valida um certificado pelo código `CERT-...` (QR Code) e devolve os dados oficiais. |

### 9.2 Autenticação, Geografia, Cofre de Senhas e Auditoria (`apps.accounts`)
| Método | Endpoint | Permissão | Descrição |
| :---: | :--- | :---: | :--- |
| `POST` | `/api/v1/auth/login` | Pública | Autentica por e-mail, username ou código oficial (`GD`, `DP`, `SECR`, `DT`, `DC`, `PR`, Aluno). |
| `POST` | `/api/v1/auth/refresh` | Pública | Renova o Access Token JWT a partir do Refresh Token. |
| `GET` | `/api/v1/auth/me` | Autenticado | Retorna os dados do utilizador logado e os dados completos da sua `Escola` (`tenant`). |
| `GET` | `/api/v1/auth/geografia` | Pública | Retorna as 11 províncias e 161 distritos oficiais de Moçambique. |
| `GET` | `/api/v1/auth/logs-acesso` | Admin Escola | Lista o histórico de acessos, falhas de login e bloqueios da escola. |
| `GET` | `/api/v1/auth/usuarios-cofre` | Admin / Direção / Secretaria | Sincroniza e lista todas as contas da escola com códigos de acesso oficiais e senhas padrão. |
| `POST/PATCH` | `/api/v1/auth/usuarios-cofre/<pk>/redefinir-senha` | Admin / Direção / Secretaria | Redefine a senha de um utilizador e ativa/desativa a sua conta. |

### 9.3 Administração Master SaaS (`apps.tenants` — `/api/v1/saas-admin/`)
| Método | Endpoint | Permissão | Descrição |
| :---: | :--- | :---: | :--- |
| `GET` | `/api/v1/saas-admin/metrics` | `SUPERADMIN` | Retorna MRR, ARR, Churn Rate, contagens de escolas, alunos, professores e dados para gráficos. |
| `GET/POST` | `/api/v1/saas-admin/planos` | `SUPERADMIN` | Lista ou cria novos planos de subscrição SaaS. |
| `PUT/PATCH` | `/api/v1/saas-admin/planos/<pk>` | `SUPERADMIN` | Atualiza preço, duração ou limites de um plano. |
| `GET/POST` | `/api/v1/saas-admin/escolas` | `SUPERADMIN` | Lista todas as escolas ou regista uma nova instituição com geração automática de contas diretivas. |
| `GET/PUT/PATCH/DELETE` | `/api/v1/saas-admin/escolas/<pk>` | `SUPERADMIN` | Consulta, edita contrato/dados ou elimina definitivamente uma escola. |
| `PATCH` | `/api/v1/saas-admin/escolas/<pk>/toggle-status` | `SUPERADMIN` | Alterna o estado de uma escola entre `ATIVA` e `SUSPENSA` (ou `/status`). |
| `POST` | `/api/v1/saas-admin/escolas/<pk>/renovar` | `SUPERADMIN` | Renova a assinatura da escola adicionando dias de vigência e reativando o acesso. |
| `POST` | `/api/v1/saas-admin/cron/verificar-expiracoes` | `SUPERADMIN` | Executa varredura imediata de todas as assinaturas vencidas e marca-as como `EXPIRADA`. |
| `GET` | `/api/v1/saas/resumo` | `SUPERADMIN` | Resumo financeiro do faturamento SaaS e contas a receber. |
| `GET` | `/api/v1/saas/assinaturas` | `SUPERADMIN` | Lista global de contratos de assinatura de todas as escolas. |
| `GET/POST` | `/api/v1/saas/assinaturas/<pk>/configurar` | `SUPERADMIN` | Configura cotas personalizadas de alunos e professores para a escola. |
| `GET` | `/api/v1/saas/pagamentos/pendentes` | `SUPERADMIN` | Lista transferências bancárias pendentes de aprovação pelo SuperAdmin. |
| `POST` | `/api/v1/saas/pagamentos/<pk>/confirmar` | `SUPERADMIN` | Confirma o pagamento da escola e renova a vigência da assinatura. |
| `POST` | `/api/v1/saas/pagamentos/<pk>/rejeitar` | `SUPERADMIN` | Rejeita comprovativo bancário inválido. |
| `POST` | `/api/v1/saas/faturas/<pk>/prorrogar` | `SUPERADMIN` | Concede tolerância de dias antes do bloqueio da instituição. |
| `POST` | `/api/v1/saas/instituicoes/<pk>/suspender-reactivar` | `SUPERADMIN` | Gestão de Acesso: Suspensão e Reactivação Manuais (com justificação de auditoria) e Operações Automáticas ('auto_suspender', 'auto_reactivar', 'auto_avaliar' com base nas regras de tolerância e corte). |
| `POST` | `/api/v1/saas/rotina-diaria` | `SUPERADMIN` | Executa o ciclo diário de faturação, aplicação de multas por atraso e suspensão/reactivação automáticas de instituições. |
| `GET` | `/api/v1/saas/minha-assinatura` | Admin Escola | Permite à escola consultar o status e dias restantes da sua assinatura. |
| `POST` | `/api/v1/saas/registar-pagamento` | Admin Escola | Envia comprovativo de pagamento de subscrição para homologação. |
| `GET` | `/api/v1/saas/coordenadas` | Autenticado | Consulta as contas bancárias e carteiras móveis oficiais (iniciam em branco, sem dados fictícios). |
| `POST` | `/api/v1/saas/coordenadas` | `SUPERADMIN` | Configura e atualiza contas bancárias (BIM, BCI), carteiras móveis (M-Pesa, e-Mola) e NUIT oficiais. |

### 9.4 Administração da Escola e Gestão de Turmas (`/api/v1/escola-admin/` e `/api/v1/turmas`)
| Método | Endpoint | Permissão | Descrição |
| :---: | :--- | :---: | :--- |
| `GET/PUT/PATCH` | `/api/v1/escola-admin/info` | Autenticado / Admin | Consulta ou atualiza dados da escola, logótipo Base64, emblema, ano letivo, trimestre e inscrições. |
| `POST/PATCH` | `/api/v1/escola-admin/toggle-visualizacao-notas` | `DAP` / Direção | Ativa ou bloqueia a visualização de notas no Portal do Aluno. |
| `GET/POST` | `/api/v1/escola-admin/usuarios` | Admin Escola | Lista ou cria utilizadores administrativos da escola. |
| `GET/POST` | `/api/v1/escola-admin/turmas` (ou `/api/v1/turmas`) | Autenticado / Admin | Lista turmas com métricas de lotação ou cria nova turma individual. |
| `GET/PUT/PATCH/DELETE` | `/api/v1/escola-admin/turmas/<pk>` | Admin / Pedagógico | Consulta, atualiza (sala, turno, capacidade, DT, DC) ou elimina uma turma. |
| `POST` | `/api/v1/escola-admin/turmas/lote` | Admin / `DAP` | Cria múltiplas turmas em lote com numeração sequencial automática. |
| `POST` | `/api/v1/escola-admin/turmas/distribuir-alunos` | Admin / `DAP` | Executa a formação/distribuição automática de alunos pelas turmas respeitando a capacidade máxima. |
| `POST` | `/api/v1/escola-admin/turmas/corrigir-numeracao` | Admin / `DAP` | Corrige e padroniza a numeração sequencial (`Turma 1, 2, 3...`) dentro de cada classe. |
| `POST` | `/api/v1/escola-admin/turmas/<pk>/homologar-cargo` | `DIRECTOR_ESCOLA` / Admin | Homologa ou revoga o cargo de Director de Turma (`DT`) ou Director de Classe (`DC`). |
| `GET/POST` | `/api/v1/escola-admin/turmas/<pk>/parametros-conselho` | `DT` / `DAP` / Direção | Consulta ou guarda Presidente, Data e Horas da Sessão do Conselho de Avaliação dos 3 Trimestres. |

### 9.5 Alunos, Professores e Disciplinas
| Método | Endpoint | Permissão | Descrição |
| :---: | :--- | :---: | :--- |
| `GET/POST` | `/api/v1/alunos` | Autenticado / Secretaria | Lista alunos (com filtros por turma, classe, área, status) ou matricula novo aluno. |
| `GET` | `/api/v1/alunos/stats` | Autenticado | Estatísticas de retenção, evasão, status e género dos alunos. |
| `GET/PUT/PATCH/DELETE` | `/api/v1/alunos/<pk>` | Secretaria / Admin | Consulta, edita dados biográficos ou remove registo de aluno. |
| `POST/PATCH` | `/api/v1/alunos/<pk>/transferir` | Secretaria / `DAP` / Admin | Transfere o aluno para outra turma e migra as suas notas do ano letivo. |
| `GET/POST` | `/api/v1/professores` | Autenticado / Admin | Lista docentes (com cálculo de horas normais vs. extras) ou cadastra novo professor. |
| `GET/PUT/PATCH/DELETE` | `/api/v1/professores/<pk>` | Admin / `DAP` | Consulta, edita (incluindo `carga_maxima_por_classe`) ou remove docente. |
| `GET/POST` | `/api/v1/professores/alocacoes` e `/alocar` | Autenticado / `DAP` | Lista ou cria alocações de Professor a Turma + Disciplina. |
| `DELETE` | `/api/v1/professores/alocacoes/<alocacao_id>` | `DAP` / Admin | Remove uma alocação docente. |
| `GET/POST` | `/api/v1/disciplinas` | Autenticado / `DAP` | Lista disciplinas (com auto-seed do currículo MEC) ou cria nova disciplina. |
| `POST` | `/api/v1/disciplinas/seed-curriculo` | `DAP` / Admin | Força a sincronização do Plano Curricular Nacional da 7ª à 12ª Classe. |
| `GET` | `/api/v1/disciplinas/ranking-reprovacao` | Autenticado | Devolve o ranking de disciplinas com maior taxa de reprovação (%). |
| `GET/PUT/PATCH/DELETE` | `/api/v1/disciplinas/<pk>` | `DAP` / Admin | Consulta, edita ou elimina uma disciplina. |

### 9.6 Notas, Cadernetas, Pautas, Material Escolar, Financeiro, Certificados e Documentos
| Método | Endpoint | Permissão | Descrição |
| :---: | :--- | :---: | :--- |
| `GET/POST` | `/api/v1/notas` | Autenticado / Pedagógico | Lista notas ou grava avaliações (`ACS`, `MAP`, `MAS`, `AT`, `faltas`, `anotacao`) individualmente ou em lote. |
| `GET` | `/api/v1/notas/caderneta` | Pedagógico | Devolve a Caderneta Oficial dos 3 trimestres + `MFD` + estatísticas por coluna (`H`, `M`, `HM`, `%`). |
| `GET/POST` | `/api/v1/notas/prazos-trimestrais` | Autenticado / `DAP` | Consulta ou define as datas de início e fim de lançamento de notas dos 3 trimestres. |
| `GET/POST/DELETE` | `/api/v1/notas/permissoes-edicao` e `/autorizar-edicao` | `DAP` / Direção | Lista, concede ou revoga autorizações temporárias de desbloqueio de notas. |
| `GET/POST` | `/api/v1/pautas` | Autenticado / Pedagógico | Lista pautas ou cria/consolida pauta de uma turma e período. |
| `GET` | `/api/v1/pautas/geral` | Pedagógico | Devolve a Pauta Geral da Turma e todos os cálculos demográficos da Acta do Conselho de Avaliação. |
| `POST/PATCH` | `/api/v1/pautas/<pk>/fechar` e `/reabrir` | Direção / `DAP` | Homologa/fecha uma pauta (congelando notas) ou reabre para retificação. |
| `GET/POST` | `/api/v1/material-escolar` | Autenticado / Pedagógico | Lista materiais didáticos (1ª à 12ª Classe) ou publica novo ficheiro/manual. |
| `GET` | `/api/v1/material-escolar/<pk>/download` | Autenticado | Descarrega o ficheiro binário do material escolar. |
| `GET/POST` | `/api/v1/pagamentos` e `/gerar-turma` | Financeiro / Aluno | Lista propinas, cria cobrança individual ou gera mensalidades em lote para uma turma (com bloqueio estrito contra faturas duplicadas no mesmo mês: *"A factura já foi gerada no sistema."*). |
| `GET/POST/PUT/PATCH/DELETE` | `/api/v1/pagamentos/planos-escola` | Financeiro / Admin Escola | Gestão dos planos de pagamento e tabelas de propinas próprias da escola (isolamento estrito multi-tenant). |
| `POST/PATCH` | `/api/v1/pagamentos/<pk>/liquidar` | Financeiro / Secretaria | Liquida pagamento (`MPESA`, `EMOLA`, `POS`, `TRANSFERENCIA`, `NUMERARIO`) e emite recibo oficial `REC-...`. |
| `GET` | `/api/v1/pagamentos/stats` | Financeiro / Admin | Retorna KPIs financeiros e histórico mensal de receitas. |
| `GET/POST` | `/api/v1/certificados` | Secretaria / Admin | Lista certificados emitidos ou emite novo certificado com QR Code (`CERT-...`). |
| `GET` | `/api/v1/dashboard/overview` | Autenticado | Indicadores gerais do Dashboard e validade da assinatura da escola. |
| `GET` | `/api/v1/dashboard/estatisticas-aproveitamento` | Autenticado | Relatório oficial completo de estatística pedagógica (Turma, Classe, Geral e Disciplina). |
| `GET` | `/api/v1/documentos/<tipo>/<id>/(pdf\|docx\|xlsx)` | Autenticado | Gera, persiste no cofre e descarrega `boletim`, `declaracao`, `certificado`, `recibo`, `ficha`, `pauta`, `acta`, `caderneta` ou `estatisticas`. |
| `GET` | `/api/v1/documentos/lote/<tipo>/<turma_id>/(pdf\|docx\|xlsx)` | Pedagógico / Secretaria | Gera um único documento multi-página em lote para todos os alunos da turma. |
| `GET` | `/api/v1/documentos/salvos` e `/salvos/<id>/download` | Autenticado | Lista e descarrega documentos arquivados na tabela `DocumentoSalvo`. |

---

## 10. Segurança, Defesa em Profundidade e Auditoria

O SIGE implementa **6 Pilares de Integridade** (`backend/docs/REGRAS_DE_INTEGRIDADE.md`):
1. **Isolamento Multi-Tenant:** `TenantIsolationMiddleware`, `TenantQuerySetMixin`, validação cruzada `validar_integridade_tenant()` e políticas RLS no PostgreSQL.
2. **Domínio Pedagógico MEC:** Validação estrita da escala `0.0` a `20.0`, arredondamentos regulamentares, proibição de faltas negativas e filtro rigoroso de disciplinas por secção/área na 11ª e 12ª Classe.
3. **Unicidade e Integridade Referencial:** Restrições SQL (`UniqueConstraint` e `CheckConstraint`) impedindo notas duplicadas no mesmo trimestre, faturas/propinas duplicadas no mesmo mês para o mesmo aluno (`unique_pagamento_aluno_mes`), alocações duplicadas, turmas com nomes repetidos na mesma classe ou pagamentos negativos.
4. **Imutabilidade Pós-Homologação:** Quando uma `Pauta` é fechada (`status = 'FECHADA'`), qualquer tentativa de edição de notas é bloqueada ao nível do serviço e do modelo, exceto mediante registo explícito e auditado em `PermissaoEdicaoNotas` dentro do prazo.
5. **Governança Financeira e Contratual:** Bloqueio automático `HTTP 402` para assinaturas vencidas e verificação dos limites do plano (`max_alunos`, `max_professores`).
6. **Não-Repúdio e Verificação Pública:** Registo de `LogAcesso`, `LogImpressao`, arquivo binário em `DocumentoSalvo` e validação pública de certificados por QR Code sem necessidade de autenticação.
7. **Privacidade e Isenção Total de Exposição de Origens/Links:** Todas as notificações, avisos e confirmações da interface SPA utilizam estritamente o sistema in-app (`mostrarAlerta`, `mostrarNotificacao`, `mostrarConfirmacao`), com higienização prévia via `limparTextoMensagem()`. O `window.alert` nativo do navegador foi interceptado para impedir terminantemente a exibição de cabeçalhos de domínio ou URLs (como *"sigesaas.duckdns.org diz"*) em qualquer caixa de diálogo.

---

## 11. Execução Local, Docker, CI/CD e Deploy na Cloud

### 11.1 Execução Rápida em Desenvolvimento Local (Windows / Linux)
Na raiz do projeto (`d:\SIGE`), o sistema dispõe de scripts automatizados (`scripts/sige.ps1`, `scripts/sige.bat` e `npm start`):
```powershell
# 1. No diretório backend/, aplicar migrações e popular dados de demonstração (Escola Secundária de Massinga):
cd backend
python manage.py migrate
python manage.py seed

# 2. Na raiz d:\SIGE, iniciar simultaneamente o Backend (:8000) e o Frontend (:5173):
cd ..
npm start
# Ou diretamente pelo comando global:
sige
```
- **Frontend Web (SPA):** `http://localhost:5173`
- **Backend API & Swagger:** `http://localhost:8000/api/docs/`

### 11.2 Contas de Demonstração Criadas pelo Comando `seed`
| Perfil / Papel | Identificador (E-mail ou Código Oficial) | Palavra-passe | Instituição / Contexto |
| :--- | :--- | :--- | :--- |
| **SuperAdmin Master SaaS** | `mandamulefj.@sige.com` | `Admin@123` | Gestão Global SaaS (todas as escolas) |
| **Director da Escola** | `GD0808S0001` *(ou `director@massinga.edu.mz`)* | `Massinga@2026` | Escola Secundária de Massinga (`0808S0001`) |
| **Director Adjunto Pedagógico (DAP)** | `DP0808S0001` *(ou `dap@massinga.edu.mz`)* | `Massinga@2026` | Escola Secundária de Massinga (`0808S0001`) |
| **Chefe da Secretaria** | `SECR0808S0001` *(ou `secretaria@massinga.edu.mz`)* | `Massinga@2026` | Escola Secundária de Massinga (`0808S0001`) |
| **Admin da Escola** | `admin@massinga.edu.mz` | `Massinga@2026` | Escola Secundária de Massinga (`0808S0001`) |
| **Financeiro / Tesouraria** | `financeiro@massinga.edu.mz` | `Massinga@2026` | Escola Secundária de Massinga (`0808S0001`) |
| **Professor** | `PR0808S0001.001` *(ou `carlos.mucavele@massinga.edu.mz`)* | `Prof@2026` | Escola Secundária de Massinga (`0808S0001`) |

### 11.3 Execução com Docker Compose
```bash
docker compose up -d --build
```
Sobe os 4 contentores orquestrados (`sige_postgres` na porta `5432`, `sige_backend` na porta `8000`, `sige_frontend` Nginx nas portas `80/443/5173` e `sige_pgadmin` na porta `5050`).

### 11.4 Testes Automatizados, CI/CD e Deploy na Cloud
- **Suite de Testes (`pytest`):** Localizada em `backend/tests/test_sige_api.py`, valida autenticação JWT, isolamento multi-tenant, bloqueio HTTP 402, regras pedagógicas do MEC e geração documental:
  ```bash
  cd backend
  pytest -v
  ```
- **Pipeline GitHub Actions (`.github/workflows/ci.yml` e `deploy.yml`):**
  1. Executa `python manage.py check`, `migrate`, `pytest -v` com PostgreSQL 16 e validação sintática do JavaScript do frontend (`node -c`).
  2. Realiza deploy contínuo via SSH na Máquina Virtual (`scripts/deploy-vm.sh`), atualizando primeiro a API Backend (com migrações automáticas e healthcheck) e em seguida o Frontend Nginx com HTTPS Let's Encrypt (`sigesaas.duckdns.org`), respeitando o **Budget Guardrail de Infraestrutura ($\le \$6\text{ USD/mês}$)**.

---

## 12. Módulo de Ferramentas: Gateway SMS, USSD e Pagamentos Móveis

### 12.1 Visão Geral e Arquitetura Operacional
O SIGE incorpora a **Central Operacional de Maximização do Gateway**, disponível para utilizadores com privilégios diretivos e administrativos (`SUPERADMIN`, `ADMIN_ESCOLA`, `DIRECTOR_ESCOLA`, `DAP`, `CHEFE_SECRETARIA`, `FINANCEIRO`). A central agrega as seguintes capacidades operacionais totalmente funcionais:
- **Envio de Mensagens SMS (Unitário e em Lote):**
  - Normalização automática para a numeração de Moçambique no formato internacional `+258XXXXXXXXX`.
  - Deteção e roteamento automático de operadoras: Vodacom Moçambique (`+258 84/85`), Movitel Moçambique (`+258 86/87`) e Tmcel Moçambique (`+258 82/83`).
  - Cálculo de caracteres e múltiplos segmentos SMS (GSM-7 de 160 caracteres vs. UCS-2 de 70 caracteres).
  - Modos de disparo: Manual por telemóvel, Em Lote por Turma Escolar, Encarregados com Propinas Pendentes e Todos os Alunos matriculados da escola.
  - Modelos rápidos predefinidos (Lembrete de Propinas, Convocatória de Reunião, Registo de Falta, Confirmação de Matrícula).
  - Histórico em tempo real de mensagens enviadas com estado de entrega (`ENTREGUE`, `PENDENTE`, `FALHOU`).
- **Cobranças e Pagamentos com Carteira Móvel (M-Pesa e e-Mola):**
  - Disparo de cobrança móvel C2B via STK Push (solicitação de PIN no ecrã do telemóvel).
  - Suporte completo às principais carteiras móveis nacionais: **M-Pesa** (Vodacom 84/85) e **e-Mola** (Movitel 86/87).
  - Vinculação direta a faturas/propinas pendentes do aluno no sistema financeiro escolar.
  - Liquidação automática da propina com registo de `PAGO`, método utilizado, valor recebido e emissão instantânea de recibo oficial no padrão `REC-YYYYMM-XXXXXX`.
  - Disparo imediato de SMS de quitação e confirmação ao encarregado de educação.
  - Tabela histórica de transações móveis com filtros e emissão de comprovativo.
- **Simulador Interativo de Menus USSD (`*...#`):**
  - Terminal interativo com ecrã LCD e teclado numérico (`0-9`, `*`, `#`), simulando fielmente a experiência do encarregado de educação em telemóveis básicos (feature phones sem internet).
  - Conformidade com as normas das operadoras de telecomunicações: respostas continuadas (`CON`) e de encerramento (`END`).
  - Navegação hierárquica por árvore de estados:
    1. Consulta de notas e médias trimestrais por número de matrícula do aluno (`1*MATRICULA`).
    2. Consulta de mensalidades e propinas pendentes em Meticais.
    3. Disparo de liquidação via M-Pesa / e-Mola diretamente a partir do telemóvel.
    4. Consulta do Calendário Escolar Oficial (I, II e III Trimestres).
    5. Contactos e horários de atendimento da secretaria escolar.
- **Prompt Técnico & Especificação do Microsserviço:**
  - Separador dedicado para consulta, cópia (`navigator.clipboard` com confirmação `aria-live="polite"`) e descarregamento (`.txt`) da especificação técnica completa para engenharia de software e assistentes de código.

### 12.2 Modelos de Dados
- **`apps.ferramentas.models.MensagemSMS` (`sige_mensagens_sms`):** Registo de cada SMS disparado com tenant (`escola`), destinatário canónico `+258`, nome do encarregado/aluno, operadora (`VODACOM`, `MOVITEL`, `TMCEL`), mensagem de texto, tipo (`AVISO`, `PROPINA`, `RECIBO`, `NOTAS`), contagem de caracteres, segmentos SMS e estado (`PENDENTE`, `ENVIADO`, `ENTREGUE`, `FALHOU`).
- **`apps.ferramentas.models.TransacaoGatewayMovel` (`sige_transacoes_gateway_movel`):** Registo de transações de carteira móvel com vínculo a `Escola`, `Aluno` e `Pagamento`, método (`MPESA`, `EMOLA`), telefone, valor em Meticais, referência bancária única, número do recibo emitido e estado (`PENDENTE`, `PROCESSANDO`, `CONCLUIDO`, `FALHOU`).

### 12.3 Rotas e Endpoints da API REST
| Método | Endpoint | Perfil Autorizado | Descrição |
| :--- | :--- | :--- | :--- |
| `GET` | `/api/v1/ferramentas/stats/` | Administração / Direcção | Métricas operacionais do gateway, saldo de créditos SMS, total enviado e status das operadoras. |
| `POST` | `/api/v1/ferramentas/sms/enviar/` | Administração / Direcção | Envio de SMS unitário ou em lote (suporta modo manual, turma e propinas pendentes). |
| `GET` | `/api/v1/ferramentas/sms/historico/` | Administração / Direcção | Histórico das últimas mensagens SMS disparadas pela escola. |
| `POST` | `/api/v1/ferramentas/pagamentos-moveis/iniciar/` | Administração / Direcção | Disparo de cobrança C2B M-Pesa / e-Mola, liquidação de propina e emissão de recibo. |
| `GET` | `/api/v1/ferramentas/pagamentos-moveis/transacoes/` | Administração / Direcção | Lista das transações móveis processadas com status e dados do aluno. |
| `POST` | `/api/v1/ferramentas/ussd/simular/` | Administração / Direcção | Máquina de estados USSD interativa para processamento de comandos `CON` e `END`. |
| `GET` | `/ferramentas/prompt-gateway` | Administração / Direcção | Visualização da interface completa da Central no layout do sistema com `Cache-Control: no-store` e `X-Robots-Tag: noindex`. |
| `GET` | `/ferramentas/prompt-gateway/descarregar` | Administração / Direcção | Descarrega o ficheiro `prompt-gateway-sms-ussd.txt` limpo em codificação UTF-8. |
| `GET` | `/api/v1/ferramentas/prompt-gateway/conteudo` | Administração / Direcção | Endpoint JSON com o texto de especificação para consumo da SPA. |

### 12.4 Acesso na Interface do Sistema
1. **Topbar (Cabeçalho Superior):** Botão de acesso rápido `[ Gateway SMS & Pagamentos ]` visível nos painéis administrativos.
2. **Sidebar (Menu Lateral):** Secção **Ferramentas & Integrações → Gateway SMS & Pagamentos** em `painel-superadmin`, `painel-escola` e `painel-financeiro`.
3. **URL Direto Autenticado:** `https://sigesaas.duckdns.org/ferramentas/prompt-gateway`.

