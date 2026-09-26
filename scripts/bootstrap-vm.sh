#!/usr/bin/env bash
# ==============================================================================
# SIGE — Script de Bootstrap da VM Google Cloud
# Cola este script INTEIRO no terminal SSH da VM no browser do Google Cloud
# ==============================================================================
set -eo pipefail

VM_IP=$(curl -sf "http://metadata.google.internal/computeMetadata/v1/instance/network-interfaces/0/access-configs/0/external-ip" \
        -H "Metadata-Flavor: Google" 2>/dev/null || hostname -I | awk '{print $1}')

REPO_URL="https://github.com/mandamulefernandojose18-max/SIGE-Sistema-Integrado-de-Gest-o-Escolar.git"
DEPLOY_DIR="/var/www/sige"
BRANCH="chore/migracao-django-rest"
SSH_PUB_KEY="ssh-ed25519 AAAAC3NzaC1lZDI1NTE5AAAAIAh3Nykbg+9QJxlonqSwu6GBUA8WHhpSFTypTTN6bXe1 sige-deploy@google-cloud-vm"
DEPLOY_USER="${USER:-$(whoami)}"

echo "=================================================================="
echo " SIGE — Bootstrap Automático da VM Google Cloud"
echo " IP detectado: ${VM_IP}"
echo " Utilizador:   ${DEPLOY_USER}"
echo "=================================================================="

# --------------------------------------------------------------------------
# 1. Instalar Docker e dependências
# --------------------------------------------------------------------------
echo "[1/8] Instalando Docker e dependências..."
export DEBIAN_FRONTEND=noninteractive
sudo apt-get update -qq
sudo apt-get install -y -qq docker.io docker-compose-plugin git curl nano htop

sudo systemctl enable docker
sudo systemctl start docker
sudo usermod -aG docker "$DEPLOY_USER"

echo "      Docker: $(docker --version)"
echo "      Docker Compose: $(docker compose version --short)"

# --------------------------------------------------------------------------
# 2. Autorizar a chave SSH do PC do developer para deploy automático
# --------------------------------------------------------------------------
echo "[2/8] Autorizando chave SSH para deploy automático..."
mkdir -p ~/.ssh
chmod 700 ~/.ssh

if ! grep -qF "$SSH_PUB_KEY" ~/.ssh/authorized_keys 2>/dev/null; then
    echo "$SSH_PUB_KEY" >> ~/.ssh/authorized_keys
    echo "      Chave SSH adicionada a ~/.ssh/authorized_keys"
else
    echo "      Chave SSH já estava autorizada."
fi
chmod 600 ~/.ssh/authorized_keys

# --------------------------------------------------------------------------
# 3. Clonar ou actualizar o repositório
# --------------------------------------------------------------------------
echo "[3/8] Clonando/actualizando repositório SIGE..."
sudo mkdir -p "$DEPLOY_DIR"
sudo chown "$DEPLOY_USER:$DEPLOY_USER" "$DEPLOY_DIR"

if [ -d "${DEPLOY_DIR}/.git" ]; then
    git -C "$DEPLOY_DIR" fetch origin "$BRANCH"
    git -C "$DEPLOY_DIR" reset --hard "origin/$BRANCH"
    echo "      Repositório actualizado para branch '${BRANCH}'"
else
    git clone -b "$BRANCH" "$REPO_URL" "$DEPLOY_DIR"
    echo "      Repositório clonado!"
fi

# --------------------------------------------------------------------------
# 4. Criar ficheiro .env de produção
# --------------------------------------------------------------------------
echo "[4/8] Criando ficheiro .env de produção..."
ENV_FILE="${DEPLOY_DIR}/.env"

if [ ! -f "$ENV_FILE" ]; then
cat > "$ENV_FILE" << ENVEOF
# SIGE — Produção Google Cloud VM — gerado automaticamente
DJANGO_SETTINGS_MODULE=config.settings.production
SECRET_KEY=sige_django_super_secret_enterprise_2026_mz!
DEBUG=False
ALLOWED_HOSTS=${VM_IP},localhost,127.0.0.1
DATABASE_URL=postgresql://sige_user:sige_secure_pass_2026@postgres:5432/sige_db
POSTGRES_DB=sige_db
POSTGRES_USER=sige_user
POSTGRES_PASSWORD=sige_secure_pass_2026
POSTGRES_HOST=postgres
POSTGRES_PORT=5432
JWT_SECRET_KEY=sige_super_secret_jwt_key_enterprise_2026_xpto!
JWT_ACCESS_LIFETIME_MINUTES=120
JWT_REFRESH_LIFETIME_DAYS=7
CORS_ALLOWED_ORIGINS=http://${VM_IP}:5173,http://${VM_IP},http://localhost:5173,http://localhost
PGADMIN_DEFAULT_EMAIL=admin@sige.com
PGADMIN_DEFAULT_PASSWORD=sige_admin_pass
ENVEOF
    echo "      .env criado com IP ${VM_IP}"
else
    echo "      .env já existe, a manter configuração actual."
fi

# --------------------------------------------------------------------------
# 5. Criar serviço systemd (arranque automático)
# --------------------------------------------------------------------------
echo "[5/8] Configurando serviço systemd para arranque automático..."
sudo tee /etc/systemd/system/sige.service > /dev/null << SVCEOF
[Unit]
Description=SIGE — Sistema Integrado de Gestão Escolar
After=docker.service network-online.target
Requires=docker.service
Wants=network-online.target

[Service]
Type=oneshot
RemainAfterExit=yes
WorkingDirectory=${DEPLOY_DIR}
ExecStart=/usr/bin/docker compose up -d --remove-orphans
ExecStop=/usr/bin/docker compose down
TimeoutStartSec=300

[Install]
WantedBy=multi-user.target
SVCEOF

sudo systemctl daemon-reload
sudo systemctl enable sige
echo "      Serviço systemd 'sige' activado!"

# --------------------------------------------------------------------------
# 6. Build e arranque dos containers
# --------------------------------------------------------------------------
echo "[6/8] Fazendo build e arrancando containers (pode demorar 2-5 min)..."
cd "$DEPLOY_DIR"
chmod +x scripts/setup-vm.sh scripts/deploy-vm.sh 2>/dev/null || true

# Usar newgrp para executar docker sem sudo (grupo acabou de ser adicionado)
sg docker -c "docker compose build backend frontend 2>&1 | tail -5"
sg docker -c "docker compose up -d"

echo "      Containers arrancados!"

# --------------------------------------------------------------------------
# 7. Aguardar BD e aplicar migrações
# --------------------------------------------------------------------------
echo "[7/8] Aguardando PostgreSQL e aplicando migrações Django..."
sleep 12

MAX=15; i=0
until sg docker -c "docker compose exec -T postgres pg_isready -U sige_user -d sige_db" > /dev/null 2>&1; do
    i=$((i+1)); [ $i -ge $MAX ] && { echo "ERRO: PostgreSQL não ficou pronto!"; exit 1; }
    echo "      Aguardando BD... ($i/$MAX)"
    sleep 4
done

sg docker -c "docker compose exec -T backend python manage.py migrate --noinput"
echo "      Migrações aplicadas!"

sg docker -c "docker compose exec -T backend python manage.py seed" 2>/dev/null && \
    echo "      Seed executado!" || echo "      Seed já foi executado antes (ignorado)."

# --------------------------------------------------------------------------
# 8. Health checks e resumo final
# --------------------------------------------------------------------------
echo "[8/8] Verificando saúde dos serviços..."
sleep 5

BACKEND_STATUS="❌ FALHOU"
for i in $(seq 1 10); do
    HTTP=$(curl -sf -o /dev/null -w "%{http_code}" http://localhost:8000/health/ 2>/dev/null || echo "000")
    if [ "$HTTP" = "200" ]; then BACKEND_STATUS="✅ HTTP 200 OK"; break; fi
    sleep 3
done

FRONTEND_STATUS="❌ FALHOU"
for i in $(seq 1 5); do
    HTTP=$(curl -sf -o /dev/null -w "%{http_code}" http://localhost:5173/ 2>/dev/null || echo "000")
    if [ "$HTTP" = "200" ] || [ "$HTTP" = "304" ]; then FRONTEND_STATUS="✅ HTTP ${HTTP} OK"; break; fi
    sleep 2
done

echo ""
echo "=================================================================="
echo "  ✅ SIGE EM PRODUÇÃO NA VM GOOGLE CLOUD!"
echo "=================================================================="
echo ""
echo "  🌐 Frontend (App):    http://${VM_IP}:5173"
echo "  🔌 Backend API:       http://${VM_IP}:8000/api/v1/"
echo "  📖 Swagger (Docs):    http://${VM_IP}:8000/api/docs/"
echo "  🗄️  PgAdmin:           http://${VM_IP}:5050"
echo "     Login: admin@sige.com / sige_admin_pass"
echo ""
echo "  Backend:  ${BACKEND_STATUS}"
echo "  Frontend: ${FRONTEND_STATUS}"
echo ""
echo "  IP da VM: ${VM_IP}"
echo "  (Guarda este IP para configurar os Secrets do GitHub)"
echo ""
echo "  📋 Comandos úteis:"
echo "     docker compose ps           — estado dos containers"
echo "     docker compose logs -f      — logs em tempo real"
echo "     docker compose restart      — reiniciar tudo"
echo "=================================================================="
