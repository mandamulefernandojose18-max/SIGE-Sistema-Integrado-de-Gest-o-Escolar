---
name: sige-commit-push-deploy
description: >-
  Skill operacional completa para o fluxo de desenvolvimento e entrega do SIGE: realiza git commit semântico, git push para o GitHub, executa o deploy desacoplado na VM (API primeiro, depois Web), valida a ligação da API na Web e cria o atalho/link web com o nome 'sige'. Ative sempre que o usuário pedir para commitar, dar push ou fazer deploy no SIGE.
---

# 🚀 SIGE — Pipeline de Commit, Push, Deploy Separado e Link 'sige'

Esta skill guia e automatiza o ciclo completo de entrega contínua do **SIGE**: desde as alterações locais até a entrada em produção na VM, com validação de saúde em cada camada e geração de link direto.

---

## 📋 Arquitetura do Fluxo

```
[Código Local] 
     │
     ├── 1. git commit (semântico)
     ├── 2. git push (origem GitHub)
     │
     ▼
[VM de Produção (sigesaas.duckdns.org)]
     │
     ├── 3. Deploy Isolado da API (Django REST + PostgreSQL + Migrations)
     │      └─► Health check: http://localhost:8000/health/ (200 OK)
     │
     ├── 4. Deploy Isolado da Web (Frontend SPA / Nginx)
     │      └─► Health check: http://localhost:5173/ (200 OK)
     │
     ├── 5. Ligar a API da Web (Validação do Proxy Reverso Web ➔ API)
     │      └─► Teste: http://localhost:5173/api/v1/health/ (200 OK)
     │
     ▼
[Acesso do Usuário]
     └── 6. Criação do Link 'sige' (Desktop, Projeto e CLI)
            └─► https://sigesaas.duckdns.org/
```

---

## ⚡ Execução Automatizada em 1 Comando

Para executar todo o ciclo de uma só vez a partir do terminal PowerShell:

```powershell
.\scripts\sige-git-deploy.ps1 -Message "feat: descricao das alteracoes implementadas"
```

*Com abertura automática do navegador:*
```powershell
.\scripts\sige-git-deploy.ps1 -Message "fix: correcao no modulo de notas" -OpenBrowser
```

---

## 🛠️ Passo a Passo Detalhado dos Procedimentos

### Passo 1: Git Commit Local
Verificar arquivos alterados e realizar commit estruturado:
```powershell
git add .
git commit -m "tipo: mensagem descritiva"
```
*Tipos semânticos:* `feat:`, `fix:`, `refactor:`, `style:`, `docs:`, `chore:`.

### Passo 2: Git Push
Enviar o código para a branch ativa no GitHub:
```powershell
git push origin chore/migracao-django-rest
```

### Passo 3: Deploy Isolado da API na VM
Via SSH na VM de produção:
```bash
cd /var/www/sige
git pull origin chore/migracao-django-rest

# Build e subida isolada da API
docker compose build backend
docker compose up -d postgres backend

# Migrações e coleta de estáticos
docker compose exec -T backend python manage.py migrate --noinput
docker compose exec -T backend python manage.py collectstatic --noinput

# Health check da API
curl -sf http://localhost:8000/health/
```

### Passo 4: Deploy Isolado da Web na VM
```bash
# Build e subida isolada da Web
docker compose build frontend
docker compose up -d frontend

# Health check da Web
curl -sf http://localhost:5173/
```

### Passo 5: Ligar a API da Web (Validação Integrada)
O Nginx da Web funciona como proxy reverso para `/api/` direcionando para `backend:8000`:
```bash
# Validar se a chamada pela Web chega até a API
curl -sf http://localhost:5173/api/v1/health/
```

### Passo 6: Criação do Link para Web com o nome 'sige'
1. **Atalho Windows no Desktop (`sige.url`):**
   ```powershell
   Set-Content -Path "$env:USERPROFILE\Desktop\sige.url" -Value "[InternetShortcut]`nURL=https://sigesaas.duckdns.org/"
   ```
2. **Atalho Windows na Raiz do Projeto (`d:\SIGE\sige.url`):**
   ```powershell
   Set-Content -Path "d:\SIGE\sige.url" -Value "[InternetShortcut]`nURL=https://sigesaas.duckdns.org/"
   ```
3. **Comando Rápido no Terminal CLI (`sige`):**
   O comando `.\sige` ou `sige` abre o navegador direto no sistema.
