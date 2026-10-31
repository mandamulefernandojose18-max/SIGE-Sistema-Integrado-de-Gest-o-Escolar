# CLAUDE.md — Diretrizes do Projeto SIGE para Claude

Este arquivo define o contexto arquitetural, regras inquebráveis, padrões de código e comandos operacionais do **SIGE (Sistema Integrado de Gestão Escolar)** para o Claude (Claude Code CLI, Claude Desktop e Claude Projects).

---

## 🛡️ Regras Inquebráveis de Operação (Guardrails Absolutos)

### 1. Ocultação Total de Endereços IP
- **NUNCA exibir, imprimir, sugerir ou expor endereços IP** (nem na forma bruta nem em subdomínios derivados de IP) em links, documentos, atalhos, mensagens ou documentação.
- Todos os links oficiais e públicos devem usar exclusivamente:
  - **Aplicação Web:** `https://sigesaas.duckdns.org/`
  - **API REST (HTTPS):** `https://sigesaas.duckdns.org/api/v1/`
  - **Documentação Swagger:** `https://sigesaas.duckdns.org/api/docs/`
- Os atalhos locais (`sige.url`, `sige.cmd` e atalho do Desktop) devem apontar exclusivamente para `https://sigesaas.duckdns.org/`.

### 2. Regra de Orçamento (Budget Guardrail)
- Manter o custo total de infraestrutura e serviços estritamente dentro do limite de **US$ 6/mês**.
- Proibido provisionar ou redimensionar recursos de nuvem que violem esse teto financeiro.

### 3. Proibição Absoluta de Dados Fictícios (Zero Mock / Fake Data)
- **NUNCA** gerar, cadastrar, simular ou introduzir cadernetas, turmas, notas, alunos, professores ou dados fictícios no sistema.
- O sistema opera com dados oficiais da educação de Moçambique e deve operar **100% com registros reais** persistidos no banco de dados. Caso não existam dados alocados, deve-se apresentar exclusivamente o estado vazio explicativo real.

### 4. Escalabilidade Teórica sem Limite ($n$ Cadernetas)
- Considerar sempre a escala como **$n$ cadernetas** ($n$ sem limite fixo ou pré-definido).
- **NUNCA** renderizar cadernetas, turmas ou registros em listas abertas de botões ou chips que possam encher a tela e explodir visualmente conforme $n$ cresce.
- O acesso a cadernetas deve ser feito **estritamente por filtros em cascata** (`Classe` → `Secção / Área` → `Turma da Secção` → `Trimestre`), mantendo a altura da interface compacta e constante $\mathcal{O}(1)$ para qualquer valor de $n$.

### 5. Sincronização Contínua de Documentação e Auto-Deploy
- **SEMPRE** que qualquer atualização for realizada no sistema (código, modelo de dados, regra de negócio, endpoint, telas ou infraestrutura):
  1. **Atualizar a documentação** correspondente na suite de manuais em `docs/` (`DOCUMENTACAO_COMPLETA_DO_SISTEMA.md`, `README.md`, etc.).
  2. **Executar git commit semântico** com mensagem descritiva.
  3. **Executar git push** para o repositório remoto.
  4. **Executar o deploy desacoplado** na VM de produção (`sigesaas.duckdns.org`), validando o funcionamento dos serviços e os atalhos locais `sige`.

---

## 📖 Visão Geral do Sistema & Stack

- **Domínio:** Plataforma SaaS Multi-Tenant Corporativa de Gestão Escolar em Moçambique (conformidade com MEC).
- **Backend:** Python 3.12, Django 5.1, Django REST Framework (DRF) 3.15, SimpleJWT, `drf-spectacular` (OpenAPI/Swagger).
- **Motores Documentais:** `ReportLab` (PDF vetorial oficial), `python-docx` (Word `.docx` em *Times New Roman*), `openpyxl` (Excel `.xlsx` em *Times New Roman*).
- **Banco de Dados:** PostgreSQL 16 com Row-Level Security (RLS) nativo (Produção/Supabase) e SQLite3 (Desenvolvimento local rápido).
- **Frontend:** Single-Page Application (SPA) e Progressive Web App (PWA) em HTML5, CSS3, Vanilla JavaScript (ES6+ modular), Bootstrap 5.3.3, Bootstrap Icons, Chart.js 4.4.4.
- **Produção / DevOps:** VM Ubuntu, Nginx Alpine (SSL Let's Encrypt), Docker Compose desacoplado, DuckDNS (`sigesaas.duckdns.org`).

---

## ⚡ Comandos Úteis do Projeto

### Backend (Django)
```powershell
# Ativar ambiente virtual
cd d:\SIGE\backend
.\venv\Scripts\activate

# Executar migrações
python manage.py migrate

# Iniciar servidor de desenvolvimento
python manage.py runserver 8000

# Executar testes unitários e de integração
pytest
# ou
python manage.py test
```

### Pipeline de Deploy Automatizado (1 Comando)
```powershell
# Executa commit semântico, push e deploy desacoplado na VM:
.\scripts\sige-git-deploy.ps1 -Message "tipo: descricao das mudancas"

# Com abertura automática do navegador:
.\scripts\sige-git-deploy.ps1 -Message "tipo: descricao das mudancas" -OpenBrowser
```

### Atalho Rápido do Sistema
```powershell
# Inicia a aplicação no navegador padrão
.\sige.cmd
# ou
sige
```

---

## 🏛️ Padrões de Código e Convenções

1. **Multi-Tenancy Obrigatório:** Todo modelo de dados institucional deve pertencer a uma `escola_id`. Todas as consultas na API devem respeitar o isolamento do tenant via `TenantIsolationMiddleware` ou verificação explícita.
2. **Padrão Oficial MEC de Notas:**
   - Notas de 0 a 20 valores decimais.
   - Fórmulas: `MT1`, `MT2`, `MT3` (Médias Trimestrais baseadas em ACS, MAP, MAS, AT), `MEC` (Média de Exame/Conclusão), `MFD` (Média Final de Disciplina).
   - Tipografia de relatórios e pautas: estritamente **Times New Roman**, notas negativas destacadas a vermelho, números por extenso em actas do conselho.
3. **Frontend Vanilla JS:** Estrutura modular sem dependências pesadas de frameworks, focada em alta performance, responsividade em dispositivos móveis e suporte offline/PWA.
4. **Commits Semânticos:** Usar prefixos `feat:`, `fix:`, `refactor:`, `docs:`, `style:`, `chore:`.
