# 🤖 Guia Completo de Migração e Operação com Claude no SIGE

Este documento estabelece o protocolo oficial para desenvolvimento e manutenção do **SIGE (Sistema Integrado de Gestão Escolar)** utilizando o ecossistema **Claude** (Claude Code CLI, Claude Desktop com MCP e Claude Projects na Web).

---

## 🎯 1. Arquitetura de Configuração para o Claude

A estrutura foi padronizada na raiz do repositório para fornecer contexto imediato e impor os guardrails inquebráveis do projeto:

```
D:\SIGE\
├── CLAUDE.md                    # Arquivo mestre lido automaticamente pelo Claude Code e Claude Projects
├── .claude/
│   ├── settings.json            # Permissões de comandos PowerShell e regras de segurança do CLI
│   ├── mcp.json                 # Configuração de MCP (Model Context Protocol) para PostgreSQL e Filesystem
│   └── commands/                # Slash commands customizados do Claude Code
│       ├── deploy.md            # Comando /deploy (executa pipeline desacoplado)
│       ├── sync-docs.md         # Comando /sync-docs (auditoria e atualização de manuais)
│       ├── budget-check.md      # Comando /budget-check (guardrail US$ 6/mês)
│       └── test.md              # Comando /test (execução de testes Django/pytest)
```

---

## 🛡️ 2. Regras Inquebráveis Incorporadas no Claude

Qualquer instância do Claude operando no SIGE respeitará automaticamente:

1. **Ocultação Total de Endereços IP:**
   - Proibição de exibição de IPs em links, logs ou documentação.
   - Domínio oficial exclusivo: `https://sigesaas.duckdns.org/`
   - API oficial: `https://sigesaas.duckdns.org/api/v1/`
   - Documentação da API: `https://sigesaas.duckdns.org/api/docs/`
2. **Guardrail de Orçamento:**
   - Custo total de infraestrutura limitado a no máximo **US$ 6/mês**.
3. **Zero Fake Data:**
   - Nenhuma inserção ou geração de dados fictícios. O sistema opera 100% com dados reais ou estados vazios padronizados.
4. **Interface Escalável ($n$ Cadernetas):**
   - Filtros em cascata estritos (`Classe` → `Secção / Área` → `Turma da Secção` → `Trimestre`), mantendo altura constante $\mathcal{O}(1)$.
5. **Auto-Deploy e Sincronização de Docs:**
   - Toda alteração exige atualização em `docs/`, commit semântico, git push e deploy desacoplado.

---

## 🚀 3. Como Utilizar o Claude Code CLI

### Instalação
O Claude Code é a ferramenta de terminal oficial da Anthropic para desenvolvimento agentic no repositório.

1. **Instalar via npm:**
   ```powershell
   npm install -g @anthropic-ai/claude-code
   ```
2. **Autenticar:**
   ```powershell
   claude login
   ```
   *(Ou defina a variável de ambiente `$env:ANTHROPIC_API_KEY="sua_chave"`)*

3. **Iniciar na pasta do projeto SIGE:**
   ```powershell
   cd d:\SIGE
   claude
   ```

Ao abrir, o Claude Code detecta automaticamente o arquivo [`CLAUDE.md`](../CLAUDE.md) e o diretório [`.claude/`](../.claude/).

### Comandos Rápidos Disponíveis no Claude Code:
- `/deploy [mensagem]` — Realiza o ciclo completo de commit, push e deploy desacoplado na VM.
- `/sync-docs` — Lista os manuais a sincronizar após modificações de código.
- `/budget-check` — Audita as diretrizes de custo (< US$ 6/mês).
- `/test` — Executa a bateria de testes automatizados do Django.

---

## 🖥️ 4. Como Configurar no Claude Desktop (com MCP)

Se utilizar o aplicativo de desktop do Claude (Claude Desktop):

1. Abra o arquivo de configuração do Claude Desktop em:
   `%APPDATA%\Claude\claude_desktop_config.json`
2. Adicione as configurações de servidores MCP contidas em [`.claude/mcp.json`](../.claude/mcp.json):
   ```json
   {
     "mcpServers": {
       "postgres": {
         "command": "npx",
         "args": [
           "-y",
           "@modelcontextprotocol/server-postgres",
           "postgresql://postgres:postgres@localhost:5432/sige"
         ]
       },
       "filesystem": {
         "command": "npx",
         "args": [
           "-y",
           "@modelcontextprotocol/server-filesystem",
           "D:\\SIGE"
         ]
       }
     }
   }
   ```
3. Reinicie o Claude Desktop. O Claude agora conseguirá interagir diretamente com a estrutura do projeto e o banco de dados.

---

## 🌐 5. Como Configurar no Claude Projects (claude.ai)

Para quem utiliza a interface web em **claude.ai**:

1. Crie um novo projeto chamado **SIGE**.
2. No campo **Project Instructions**, copie e cole integralmente o conteúdo de [`CLAUDE.md`](../CLAUDE.md).
3. Adicione aos **Project Files** os documentos de referência:
   - `CLAUDE.md`
   - `docs/DOCUMENTACAO_COMPLETA_DO_SISTEMA.md`
   - `docs/REGRAS_PEDAGOGICAS_MEC.md`
   - `docs/REFERENCIA_COMPLETA_API.md`

---

## ✅ 6. Checklist de Verificação da Migração

- [x] Arquivo [`CLAUDE.md`](../CLAUDE.md) criado com regras inquebráveis, stack e comandos.
- [x] Diretório [`.claude/`](../.claude/) configurado com permissões e segurança (`settings.json`).
- [x] Slash commands do Claude Code criados em [`.claude/commands/`](../.claude/commands/).
- [x] Configuração MCP padronizada em [`.claude/mcp.json`](../.claude/mcp.json).
- [x] Atalhos locais `sige.url` e `sige.cmd` intactos e apontando para `https://sigesaas.duckdns.org/`.
- [x] Documentação sincronizada em `docs/MIGRACAO_CLAUDE.md` e indexada em `docs/README.md`.
