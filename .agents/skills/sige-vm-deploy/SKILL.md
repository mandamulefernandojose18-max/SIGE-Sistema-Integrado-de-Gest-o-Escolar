---
name: sige-vm-deploy
description: >-
  Guia operacional e automação completa para configurar, atualizar, gerenciar e realizar deploy do SIGE (Sistema Integrado de Gestão Escolar) na VM da Google Cloud ou qualquer VPS Ubuntu/Debian. Ative esta skill sempre que o usuário pedir para configurar a VM, fazer deploy, checar o status da VM na nuvem, atualizar serviços na VM, rodar migrações remotas ou configurar chaves SSH e segredos de CI/CD.
---

# 🚀 SIGE — Skill de Deploy e Gestão da VM Google Cloud

Esta skill reúne todos os parâmetros de infraestrutura, comandos, scripts e passos operacionais para provisionar, configurar e atualizar a Máquina Virtual (VM) de produção do **SIGE** no Google Cloud Compute Engine ou qualquer VPS Linux.

---

## 📋 Parâmetros e Credenciais de Infraestrutura

- **Repositório GitHub:** `https://github.com/mandamulefernandojose18-max/SIGE-Sistema-Integrado-de-Gest-o-Escolar.git`
- **Branch Padrão de Produção:** `main` (ou `chore/migracao-django-rest`)
- **Diretório da Aplicação na VM:** `/var/www/sige`
- **Chave Privada SSH (Local Windows):** `C:\Users\Fernando Mandamule\.ssh\sige_vm_key`
- **Chave Pública SSH (Local Windows):** `C:\Users\Fernando Mandamule\.ssh\sige_vm_key.pub`
- **Utilizador SSH Padrão:** `$env:USERNAME` (ex: `Fernando Mandamule` ou `ubuntu` ou usuário da conta Google Cloud)
- **Portas de Serviço:**
  - `8000` — Backend Django REST Framework (WSGI / Waitress / Gunicorn)
  - `5173` — Frontend SPA (PWA com Proxy Reverso nativo)
  - `5432` — PostgreSQL Supabase (remoto via pooler)
  - `22` — SSH seguro

---

## 🗄️ Base de Dados de Produção (Supabase)

O SIGE utiliza Supabase PostgreSQL em produção. A VM **não precisa** rodar um banco PostgreSQL pesado localmente se estiver conectada ao Supabase:

```env
DATABASE_URL=postgresql://postgres:Deusamo8Mandamule@db.pkokhrdsffwqsmscirrl.supabase.co:5432/postgres
```
> **Nota de Rede:** O backend Django possui fallback inteligente automático configurado para direcionar o hostname ao pooler IPv4 `aws-0-us-west-2.pooler.supabase.com:5432` com SSL obrigatório (`sslmode=require`).

---

## 🛠️ Procedimento 1: Primeira Configuração de uma Nova VM (Bootstrap)

Quando criar uma nova instância no Google Cloud (ex: Ubuntu 22.04 LTS ou 24.04 LTS):

### 1. Injetar a Chave Pública SSH na VM
No painel do Google Cloud Console ➔ **Compute Engine** ➔ **Instâncias de VM** ➔ **Editar instância** ➔ **Chaves SSH** ➔ Adicionar o conteúdo de `C:\Users\Fernando Mandamule\.ssh\sige_vm_key.pub`:
```text
ssh-ed25519 AAAAC3NzaC1lZDI1NTE5AAAAIAh3Nykbg+9QJxlonqSwu6GBUA8WHhpSFTypTTN6bXe1 sige-deploy@google-cloud-vm
```

### 2. Executar o Script de Setup Automatizado na VM
Conecte-se à VM e rode o script unificado de configuração:
```bash
# Conectar via SSH:
ssh -i ~/.ssh/sige_vm_key <USER>@<IP_DA_VM>

# Executar setup (instala Docker, Docker Compose, Git, Firewall e clona o SIGE):
curl -fsSL https://raw.githubusercontent.com/mandamulefernandojose18-max/SIGE-Sistema-Integrado-de-Gest-o-Escolar/main/scripts/setup-vm.sh | bash
```

Caso o repositório já esteja clonado em `/var/www/sige`:
```bash
cd /var/www/sige
chmod +x scripts/*.sh
bash scripts/setup-vm.sh
```

---

## 🔄 Procedimento 2: Fazer Deploy / Atualizar Aplicação na VM

### Método A: Deploy Automático via Git Push (CI/CD GitHub Actions)
Qualquer push na branch `main` executa a pipeline do arquivo `.github/workflows/deploy.yml`:
1. Executa verificação do Django (`check`) e testes (`pytest`).
2. Conecta à VM via SSH com os segredos configurados.
3. Executa o script `scripts/deploy-vm.sh` na VM.

Para configurar os segredos no repositório do GitHub automaticamente:
```powershell
.\scripts\configure-github-secrets.ps1 -VmIp "<IP_PUBLICO_DA_VM>" -VmUser "ubuntu"
```

### Método B: Deploy Manual via SSH Direto
A partir da máquina local (PowerShell):
```powershell
$VM_IP = "<IP_DA_VM>"
$VM_USER = "ubuntu"
$KEY = "$env:USERPROFILE\.ssh\sige_vm_key"

ssh -i $KEY -o StrictHostKeyChecking=no "${VM_USER}@${VM_IP}" "cd /var/www/sige && bash scripts/deploy-vm.sh main"
```

### Método C: Execução Direta Dentro da VM
Conectado na VM:
```bash
cd /var/www/sige
git pull origin main
docker compose down
docker compose up -d --build
docker compose exec -T backend python manage.py migrate
docker compose exec -T backend python manage.py collectstatic --noinput
```

---

## 🩺 Procedimento 3: Testar e Verificar Saúde do Backend e Frontend

### 1. Teste HTTP Remoto (a partir da máquina local Windows):
```powershell
$VM_IP = "<IP_DA_VM>"

# Health check do backend (deve responder 200 OK com status "ok")
Invoke-RestMethod -Uri "http://${VM_IP}:8000/health/"

# Documentação OpenAPI / Swagger UI
Invoke-WebRequest -Uri "http://${VM_IP}:8000/api/docs/"

# Frontend SPA
Invoke-WebRequest -Uri "http://${VM_IP}:5173/"
```

### 2. Teste Dentro da VM (via SSH):
```bash
# Status dos containers
docker compose ps

# Logs em tempo real do backend
docker compose logs -f backend --tail=100

# Teste interno de health
curl -s http://localhost:8000/health/
```

---

## 🔒 Regras de Firewall do Google Cloud (VPC)

Certifique-se de que a rede da VM permite as seguintes portas de entrada (Ingress):
- `tcp:22` (SSH)
- `tcp:80` e `tcp:443` (HTTP/HTTPS se usar Nginx/Cloudflare)
- `tcp:8000` (Backend API Django REST)
- `tcp:5173` (Frontend Web SPA)
- `tcp:5050` (PgAdmin - Opcional)
