---
name: sige-docs-auto-sync-deploy
description: >-
  Skill obrigatória e contínua do SIGE: deve actuar SEMPRE em qualquer actualização feita no sistema, sincronizando imediatamente a documentação técnica e operacional em docs/, realizando git commit semântico, git push para o GitHub e executando o deploy desacoplado na VM de produção (sigesaas.duckdns.org), validando a ligação da API na Web e atualizando os atalhos 'sige'.
---

# 📚 SIGE — Sincronização Contínua de Documentação, Commit, Push e Deploy

Esta skill estabelece a **obrigatoriedade de ciclo fechado** para qualquer alteração no ecossistema **SIGE**: nenhuma alteração de código, modelo de dados, regra de negócio, endpoint ou tela é considerada concluída sem a atualização imediata da documentação correspondente, seguida de commit semântico, envio ao GitHub e deploy desacoplado na máquina virtual de produção.

---

## ⚡ Ciclo Obrigatório de 4 Etapas em Toda e Qualquer Atualização

```
[Qualquer Atualização no SIGE]
         │
         ├── 1. Sincronização Imediata da Documentação (docs/*)
         │      ├── Arquitetura & Segurança -> ARQUITETURA_E_SEGURANCA.md
         │      ├── Telas & 18 Módulos     -> MANUAL_DE_MODULOS_E_OPERACAO.md
         │      ├── Regras Pedagógicas MEC -> REGRAS_PEDAGOGICAS_MEC.md
         │      ├── Tabelas & Campos SQL   -> DICIONARIO_DE_DADOS.md
         │      ├── Rotas & Parâmetros API -> REFERENCIA_COMPLETA_API.md
         │      ├── Deploy & Infraestrutura -> GUIA_DE_IMPLANTACAO_E_DEVOPS.md
         │      └── Documento Mestre       -> DOCUMENTACAO_COMPLETA_DO_SISTEMA.md
         │
         ├── 2. Git Commit Semântico Local
         │      └─► git add . && git commit -m "tipo: mensagem descritiva"
         │
         ├── 3. Git Push para o Repositório Remoto
         │      └─► git push origin <branch_ativa>
         │
         ▼
[VM de Produção (sigesaas.duckdns.org)]
         └── 4. Deploy Desacoplado Automatizado
                ├── Deploy isolado da API Django REST (migrações + estáticos)
                ├── Deploy isolado da Web Nginx SPA
                ├── Validação da Ligação Integrada (Web HTTPS -> API 200 OK)
                └── Atualização dos atalhos oficiais 'sige' (sigesaas.duckdns.org)
```

---

## 📋 1. Mapeamento de Sincronização Documental

Sempre que um ficheiro do sistema for modificado, o agente deve sincronizar os manuais específicos em `docs/`:

| Natureza da Alteração | Ficheiros de Código Envolvidos | Documentos que DEVEM ser Atualizados |
| :--- | :--- | :--- |
| **Modelos de Dados / ORM** | `backend/apps/*/models.py`, migrações | `docs/DICIONARIO_DE_DADOS.md`<br>`docs/DOCUMENTACAO_COMPLETA_DO_SISTEMA.md` |
| **Rotas e Endpoints REST** | `backend/config/urls.py`, `backend/apps/*/urls.py`, `views.py` | `docs/REFERENCIA_COMPLETA_API.md`<br>`backend/docs/API_REFERENCE.md`<br>`docs/DOCUMENTACAO_COMPLETA_DO_SISTEMA.md` |
| **Regras Pedagógicas / MEC** | `common/utils/avaliacoes_mocambique.py`, `pautas/services.py` | `docs/REGRAS_PEDAGOGICAS_MEC.md`<br>`docs/DOCUMENTACAO_COMPLETA_DO_SISTEMA.md` |
| **Telas / Módulos da SPA** | `frontend/index.html`, `frontend/js/app.js`, `pages/*` | `docs/MANUAL_DE_MODULOS_E_OPERACAO.md`<br>`docs/DOCUMENTACAO_COMPLETA_DO_SISTEMA.md` |
| **Segurança / Multi-Tenant** | `common/middleware/*`, `common/integrity/*`, RLS SQL | `docs/ARQUITETURA_E_SEGURANCA.md`<br>`docs/DOCUMENTACAO_COMPLETA_DO_SISTEMA.md` |
| **Infra / Nginx / Deploy** | `scripts/*`, `docker-compose.yml`, `Dockerfile`, `.github/*` | `docs/GUIA_DE_IMPLANTACAO_E_DEVOPS.md`<br>`docs/README.md` |

---

## 🚀 2. Execução Automatizada em 1 Comando (PowerShell)

A automação unificada do fluxo local ao deploy na nuvem é disparada diretamente por:

```powershell
.\scripts\sige-git-deploy.ps1 -Message "tipo: descricao detalhada da actualizacao"
```

O script executa sequencialmente:
1. `git add .` com verificação de arquivos alterados;
2. `git commit -m "<mensagem>"`;
3. `git push origin <branch_ativa>` (padrão: `chore/migracao-django-rest`);
4. Execução remota via SSH na VM (`sigesaas.duckdns.org`):
   ```bash
   cd /var/www/sige && git fetch origin $Branch && git checkout $Branch && git reset --hard origin/$Branch && chmod +x scripts/*.sh && bash scripts/deploy-separated.sh $Branch
   ```
5. Validação da saúde da API (`:8000/health/`), da Web (`:5173/`) e do proxy HTTPS (`sigesaas.duckdns.org/api/v1/health/`);
6. Recriação dos atalhos `sige.url`, `sige.cmd` e atalho no Desktop apontando para `https://sigesaas.duckdns.org/`.

---

## 🛡️ 3. Guardrails Inquebráveis Obrigatórios

1. **Ocultação Absoluta de Endereços IP:**
   - **NUNCA** imprimir, exibir ou registrar endereços IP brutos ou derivados em terminais, mensagens, commits, documentações ou atalhos.
   - Todos os links oficiais utilizam exclusivamente:
     - Web: `https://sigesaas.duckdns.org/`
     - API: `https://sigesaas.duckdns.org/api/v1/`
     - Swagger: `https://sigesaas.duckdns.org/api/docs/`
2. **Teto de Custo de Infraestrutura:**
   - Manter a infraestrutura rigorosamente dentro do limite de **US\$ 6/mês**.
