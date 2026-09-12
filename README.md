# 🏫 SIGE — Sistema Integrado de Gestão Escolar
### Plataforma SaaS Multi-Tenant Corporativa de Gestão Educacional

[![SIGE CI/CD Pipeline](https://github.com/empresa/sige/actions/workflows/ci.yml/badge.svg)](https://github.com/empresa/sige/actions/workflows/ci.yml)
[![Node.js](https://img.shields.io/badge/Node.js-v20%2B-green.svg)](https://nodejs.org)
[![TypeScript](https://img.shields.io/badge/TypeScript-5.6-blue.svg)](https://www.typescriptlang.org/)
[![Prisma ORM](https://img.shields.io/badge/Prisma-ORM-2D3748.svg)](https://www.prisma.io/)
[![PostgreSQL](https://img.shields.io/badge/PostgreSQL-16-336791.svg)](https://www.postgresql.org/)
[![Docker](https://img.shields.io/badge/Docker-Ready-2496ED.svg)](https://www.docker.com/)

---

## 📖 Visão Geral

O **SIGE (Sistema Integrado de Gestão Escolar)** é uma solução corporativa de software como serviço (**SaaS Multi-Tenant**) projetada para centralizar e automatizar integralmente as operações pedagógicas, financeiras, administrativas e de certificação digital de redes escolares e instituições de ensino independentes.

---

## 🎯 Requisitos de Arquitetura Multi-Tenant & Assinaturas

### 1. Isolamento Estrito de Dados (Multi-Tenancy)
- Cada instituição opera como um **Tenant** isolado.
- Todas as tabelas principais de negócio contêm `escola_id` com índices e restrições de integridade referencial.
- O contexto do tenant é extraído automaticamente do token JWT ou pelo cabeçalho `X-Tenant-ID` (para o SuperAdmin).
- Nenhuma escola tem visibilidade ou capacidade de alteração sobre os dados de outra.

### 2. Gestão de Planos & Assinaturas
- Modalidades de assinatura: **Mensal**, **Trimestral** e **Anual**.
- Ciclo de vida e status da assinatura: `ATIVA`, `PENDENTE`, `EXPIRADA`, `SUSPENSA`.

### 3. Bloqueio Automático por Expiração (Job Agendado + HTTP 402)
- **Job Diário (node-cron)**: Executa à meia-noite (`0 0 * * *`) varrendo assinaturas com vigência vencida (`data_fim < agora`) e atualizando o status da escola para `EXPIRADA`.
- **Middleware `tenantMiddleware`**: Intercepta **todas as requisições das rotas escolares**. Se o status for `EXPIRADA`, retorna imediatamente o código **HTTP 402 (Payment Required)** com a mensagem oficial:
  > *"Assinatura expirada. Entre em contato com a administração do sistema para renovação."*
- Usuários com papel `SUPERADMIN` possuem acesso irrestrito para gerenciar métricas e renovar assinaturas a qualquer momento.

---

## 📁 Os 10 Módulos & Painéis de Estatísticas em Tempo Real

| # | Módulo | Funcionalidades de Gestão (CRUD) | Estatísticas e Métricas em Tempo Real |
| :-: | :--- | :--- | :--- |
| **1** | 🔐 **Login & Autenticação** | JWT com Refresh Tokens rotativos e RBAC (`SUPERADMIN`, `ADMIN_ESCOLA`, `PROFESSOR`, `ALUNO`, `FINANCEIRO`). | Gráfico diário de logins dos últimos 7 dias, usuários ativos por perfil e contagem de sessões bloqueadas. |
| **2** | 👨‍🎓 **Alunos** | Matrícula, vinculação de turma, cadastro de responsável legal e dados demográficos. | Total ativos vs inativos, pirâmide etária, proporção de gênero e taxas de retenção vs evasão escolar. |
| **3** | 👨‍🏫 **Professores** | Especialidades, alocação de disciplinas e turmas, carga horária semanal. | Proporção Aluno/Professor (Student-Teacher Ratio) e total estimado de aulas ministradas no mês. |
| **4** | 📚 **Disciplinas** | Matriz curricular por grau/ano letivo, carga horária e código da ementa. | Ranking das disciplinas com maior índice de reprovação (%) e média geral de aproveitamento. |
| **5** | 📝 **Notas & Avaliações** | Lançamento trimestral (Trabalho, Teste, Exame e Faltas), notas ponderadas e lançamento em lote. | Média geral da turma, percentual de notas positivas vs negativas em relação à média de corte (10/20). |
| **6** | 📊 **Pautas Oficiais** | Consolidação de atas de avaliação por período letivo, homologação e encerramento. | Percentual de turmas com pautas fechadas vs pendentes/em consolidação. |
| **7** | 📄 **Certificados Digitais** | Emissão de certificados com **QR Code** de autenticidade e página pública de verificação. | Histórico mensal de emissão por tipo (Conclusão, Transferência, Matrícula). |
| **8** | 💰 **Pagamentos & Financeiro** | Emissão de mensalidades individuais ou em lote por turma, recibos numerados e liquidação. | Faturamento mensal, taxa de inadimplência (%), projeção de receita e alunos em dia (adimplência). |
| **9** | 🖨️ **Central de Impressão/PDF** | Geração e visualização para impressão A4 de Boletins, Pautas, Recibos e Fichas de Alunos. | Volume de documentos gerados por período e por tipologia documental. |
| **10** | ⚙️ **Administração (SaaS & Local)** | **SuperAdmin**: Métricas SaaS (MRR, ARR, Churn, Escolas Ativas vs Expiradas).<br>**Admin Local**: Dados da escola, ano letivo e turmas. | Gráficos financeiros do SaaS, churn rate, distribuição de planos contratados. |

---

## 🛠️ Stack Tecnológica

- **Backend**: Node.js 20+, TypeScript, Express.js.
- **ORM & Banco de Dados**: Prisma ORM, PostgreSQL 16 (produção/Docker) e SQLite (desenvolvimento ágil local).
- **Agendamento em Background**: `node-cron`.
- **Segurança**: JSON Web Token (JWT), `bcryptjs`, `helmet`, `cors`.
- **Validação**: `zod`.
- **Frontend**: Single Page Application responsiva com Bootstrap 5, Chart.js, Bootstrap Icons e layout de impressão otimizado (`@media print`).
- **DevOps & CI/CD**: Docker, Docker Compose, GitHub Actions (`.github/workflows/ci.yml`).

---

## 🚀 Como Executar o Projeto

### Pré-requisitos
- Node.js v18+ instalado
- npm ou yarn

### 1. Clonar e Instalar Dependências
```bash
git clone https://github.com/seu-usuario/sige.git
cd sige
npm install
```

### 2. Configurar Variáveis de Ambiente
O arquivo `.env` já vem pré-configurado para execução imediata:
```env
PORT=3000
DATABASE_URL="file:./dev.db"
JWT_SECRET=sige_super_secret_jwt_key_enterprise_2026_xpto!
JWT_REFRESH_SECRET=sige_super_secret_refresh_token_enterprise_2026!
CRON_SCHEDULE="0 0 * * *"
```

### 3. Gerar o Banco de Dados e Popular Dados Iniciais (Seed)
```bash
npx prisma generate
npx prisma db push
npx ts-node-dev prisma/seed.ts
```

### 4. Iniciar a Aplicação
```bash
npm run dev
```

Acesse o sistema no seu navegador: **`http://localhost:3000`**

---

## 👥 Contas de Demonstração Pré-configuradas

| Perfil / Papel | E-mail de Login | Senha | Cenário / Comportamento Demonstrado |
| :--- | :--- | :--- | :--- |
| **SuperAdmin (Master SaaS)** | `admin.master@sige.com` | `admin123` | Acesso global, gráficos de MRR/ARR/Churn, listagem de escolas e botão para renovar assinaturas. |
| **Admin Escola (ATIVA)** | `admin.saofrancisco@saofrancisco.edu` | `escola123` | **Colégio São Francisco**: Acesso irrestrito a todos os módulos, alunos, notas, pautas e pagamentos. |
| **Admin Escola (EXPIRADA)** | `admin.progresso@sige.com` | `escola123` | **Instituto Progresso**: Assinatura vencida propositalmente. Qualquer tentativa de requisição retorna **HTTP 402 (Payment Required)**. |
| **Financeiro** | `financeiro.saofrancisco@sige.com` | `financeiro123` | Gestão financeira de mensalidades e emissão de recibos. |
| **Professor** | `manuel.silva@saofrancisco.edu` | `professor123` | Lançamento de notas nas turmas alocadas. |

---

## 🧪 Execução de Testes Automatizados

O SIGE inclui testes automatizados de integração com Jest e Supertest cobrindo:
1. Emissão e renovação de tokens JWT e controle RBAC.
2. Bloqueio por assinatura expirada retornando HTTP 402 com mensagem exigida.
3. Isolamento multi-tenant entre escolas.
4. Lógica do agendador automático de expiração (Cron Job).

Para rodar a suíte de testes:
```bash
npm test
```

---

## 🐳 Executando com Docker & PostgreSQL

Para subir a stack corporativa completa (Aplicação SIGE + PostgreSQL 16 + pgAdmin 4):
```bash
docker-compose up -d --build
```
- **Aplicação SIGE**: `http://localhost:3000`
- **pgAdmin 4**: `http://localhost:5050` (Login: `admin@sige.com` / Senha: `sige_admin_pass`)

---

## 🔒 Verificação Pública de Certificados (QR Code)

Cada certificado gerado contém um QR Code criptográfico que aponta para:
```
http://localhost:3000/verificar-certificado.html?codigo={UUID}
```
A página pública valida os dados diretamente no banco de dados e exibe o carimbo de fé pública sem exigir autenticação.

---

## 📄 Licença

Este projeto está sob a licença [MIT](LICENSE).
Desenvolvido com excelência técnica para gestão escolar corporativa.
