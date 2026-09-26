#!/usr/bin/env bash
# ==============================================================================
# SIGE — Script de Setup Inicial da VM Google Cloud
# Executa UMA VEZ para preparar a VM para receber o SIGE em produção
# Uso: bash scripts/setup-vm.sh <IP_EXTERNO_DA_VM> <URL_DO_REPO_GITHUB>
# Exemplo: bash scripts/setup-vm.sh 34.90.123.45 https://github.com/usuario/SIGE.git
# ==============================================================================

set -eo pipefail

# Cores
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
NC='\033[0m'

VM_IP="${1:-}"
REPO_URL="${2:-}"
DEPLOY_DIR="/var/www/sige"
BRANCH="main"

log_info()    { echo -e "${BLUE}[INFO]${NC} $1"; }
log_success() { echo -e "${GREEN}[OK]${NC} $1"; }
log_warn()    { echo -e "${YELLOW}[AVISO]${NC} $1"; }
log_error()   { echo -e "${RED}[ERRO]${NC} $1"; exit 1; }

echo -e "${CYAN}==========================================================${NC}"
echo -e "${CYAN}   🚀 SIGE — SETUP INICIAL DA VM GOOGLE CLOUD            ${NC}"
echo -e "${CYAN}==========================================================${NC}"

# Validações iniciais
if [ -z "$VM_IP" ]; then
    log_warn "IP da VM não fornecido. Tentando detectar automaticamente..."
    VM_IP=$(curl -sf "http://metadata.google.internal/computeMetadata/v1/instance/network-interfaces/0/access-configs/0/external-ip" \
            -H "Metadata-Flavor: Google" 2>/dev/null || echo "")
    if [ -z "$VM_IP" ]; then
        log_error "Não foi possível detectar o IP. Execute: bash setup-vm.sh <IP_DA_VM> <REPO_URL>"
    fi
fi

log_info "IP da VM detectado: ${VM_IP}"

if [ -z "$REPO_URL" ]; then
    log_warn "URL do repositório não fornecida. O clone será ignorado (assumindo que o código já existe em ${DEPLOY_DIR})."
fi

# ==============================================================================
# 1. Actualizar sistema e instalar dependências
# ==============================================================================
log_info "Actualizando pacotes do sistema..."
sudo apt-get update -qq
sudo apt-get upgrade -y -qq

log_info "Instalando Docker, Git, Curl..."
sudo apt-get install -y -qq \
    docker.io \
    docker-compose-plugin \
    git \
    curl \
    htop \
    nano

# Adicionar utilizador ao grupo docker
sudo usermod -aG docker "$USER" || true
log_success "Docker instalado: $(docker --version)"
log_success "Docker Compose instalado: $(docker compose version --short)"

# ==============================================================================
# 2. Clonar ou actualizar o repositório
# ==============================================================================
sudo mkdir -p "$DEPLOY_DIR"
sudo chown "$USER:$USER" "$DEPLOY_DIR"

if [ -n "$REPO_URL" ]; then
    if [ -d "${DEPLOY_DIR}/.git" ]; then
        log_info "Repositório já existe. Actualizando para branch '${BRANCH}'..."
        git -C "$DEPLOY_DIR" fetch origin "$BRANCH"
        git -C "$DEPLOY_DIR" reset --hard "origin/${BRANCH}"
    else
        log_info "Clonando repositório de ${REPO_URL}..."
        git clone "$REPO_URL" "$DEPLOY_DIR"
        git -C "$DEPLOY_DIR" checkout "$BRANCH"
    fi
    log_success "Repositório actualizado!"
else
    if [ ! -d "${DEPLOY_DIR}/.git" ]; then
        log_warn "Repositório não encontrado em ${DEPLOY_DIR}. Cria o .env manualmente antes de continuar."
    fi
fi

# ==============================================================================
# 3. Criar ficheiro .env de produção se não existir
# ==============================================================================
ENV_FILE="${DEPLOY_DIR}/.env"

if [ -f "$ENV_FILE" ]; then
    log_warn ".env já existe. Não será substituído automaticamente."
else
    log_info "Criando .env de produção para o IP ${VM_IP}..."
    cat > "$ENV_FILE" << ENVEOF
# ============================================================
# SIGE — Variáveis de Ambiente de PRODUÇÃO (VM Google Cloud)
# Gerado automaticamente por setup-vm.sh
# ============================================================

# Django Backend
DJANGO_SETTINGS_MODULE=config.settings.production
SECRET_KEY=sige_django_super_secret_enterprise_2026_mz!
DEBUG=False

# Hosts permitidos (inclui o IP da VM)
ALLOWED_HOSTS=${VM_IP},localhost,127.0.0.1

# PostgreSQL
DATABASE_URL=postgresql://sige_user:sige_secure_pass_2026@postgres:5432/sige_db
POSTGRES_DB=sige_db
POSTGRES_USER=sige_user
POSTGRES_PASSWORD=sige_secure_pass_2026
POSTGRES_HOST=postgres
POSTGRES_PORT=5432

# JWT
JWT_SECRET_KEY=sige_super_secret_jwt_key_enterprise_2026_xpto!
JWT_ACCESS_LIFETIME_MINUTES=120
JWT_REFRESH_LIFETIME_DAYS=7

# CORS — Permite pedidos do Frontend ao Backend
CORS_ALLOWED_ORIGINS=http://${VM_IP}:5173,http://${VM_IP},http://localhost:5173,http://localhost

# PgAdmin
PGADMIN_DEFAULT_EMAIL=admin@sige.com
PGADMIN_DEFAULT_PASSWORD=sige_admin_pass
ENVEOF
    log_success ".env criado em ${ENV_FILE}"
fi

# ==============================================================================
# 4. Criar serviço systemd para arranque automático
# ==============================================================================
log_info "Configurando serviço systemd para arranque automático..."

sudo tee /etc/systemd/system/sige.service > /dev/null << 'SVCEOF'
[Unit]
Description=SIGE — Sistema Integrado de Gestão Escolar
Documentation=https://github.com/mandamulefernandojose18-max/SIGE
After=docker.service network-online.target
Requires=docker.service
Wants=network-online.target

[Service]
Type=oneshot
RemainAfterExit=yes
WorkingDirectory=/var/www/sige
ExecStart=/usr/bin/docker compose up -d --remove-orphans
ExecStop=/usr/bin/docker compose down
ExecReload=/usr/bin/docker compose restart
TimeoutStartSec=300
Restart=on-failure
RestartSec=10

[Install]
WantedBy=multi-user.target
SVCEOF

sudo systemctl daemon-reload
sudo systemctl enable sige
log_success "Serviço systemd 'sige' configurado e activado!"

# ==============================================================================
# 5. Build e arranque do Docker Compose
# ==============================================================================
cd "$DEPLOY_DIR"
chmod +x scripts/deploy-vm.sh 2>/dev/null || true

log_info "Construindo imagens Docker (Backend + Frontend)..."
docker compose build backend frontend

log_info "Iniciando todos os serviços..."
docker compose up -d

# Aguardar o PostgreSQL ficar pronto
log_info "Aguardando PostgreSQL ficar pronto..."
sleep 10

MAX_RETRIES=15
RETRY=0
until docker compose exec -T postgres pg_isready -U sige_user -d sige_db > /dev/null 2>&1; do
    RETRY=$((RETRY + 1))
    if [ "$RETRY" -ge "$MAX_RETRIES" ]; then
        log_error "PostgreSQL não ficou disponível a tempo."
    fi
    log_warn "PostgreSQL ainda não disponível. Aguardando... (${RETRY}/${MAX_RETRIES})"
    sleep 5
done
log_success "PostgreSQL disponível!"

# ==============================================================================
# 6. Aplicar migrações e seed
# ==============================================================================
log_info "Aplicando migrações Django..."
docker compose exec -T backend python manage.py migrate --noinput
log_success "Migrações aplicadas!"

log_info "Executando seed de dados iniciais..."
docker compose exec -T backend python manage.py seed 2>/dev/null && \
    log_success "Seed executado!" || \
    log_warn "Seed falhou ou já foi executado anteriormente. Ignorando."

# ==============================================================================
# 7. Verificações de saúde
# ==============================================================================
log_info "Verificando saúde dos serviços..."

sleep 5

BACKEND_OK=false
for i in $(seq 1 10); do
    HTTP=$(curl -sf -o /dev/null -w "%{http_code}" http://localhost:8000/health/ 2>/dev/null || echo "000")
    if [ "$HTTP" = "200" ]; then
        BACKEND_OK=true
        log_success "Backend: HTTP ${HTTP} OK!"
        break
    fi
    log_warn "Backend ainda não respondeu (${HTTP}). Tentativa ${i}/10..."
    sleep 4
done

FRONTEND_OK=false
for i in $(seq 1 5); do
    HTTP=$(curl -sf -o /dev/null -w "%{http_code}" http://localhost:5173/ 2>/dev/null || echo "000")
    if [ "$HTTP" = "200" ] || [ "$HTTP" = "304" ]; then
        FRONTEND_OK=true
        log_success "Frontend: HTTP ${HTTP} OK!"
        break
    fi
    log_warn "Frontend ainda não respondeu (${HTTP}). Tentativa ${i}/5..."
    sleep 3
done

# ==============================================================================
# 8. Resumo Final
# ==============================================================================
echo ""
echo -e "${GREEN}==========================================================${NC}"
echo -e "${GREEN}   ✅ SIGE EM PRODUÇÃO NA VM GOOGLE CLOUD!               ${NC}"
echo -e "${GREEN}==========================================================${NC}"
echo ""
echo -e "  🌐 Frontend (App):    ${CYAN}http://${VM_IP}:5173${NC}"
echo -e "  🔌 Backend API:       ${CYAN}http://${VM_IP}:8000/api/v1/${NC}"
echo -e "  📖 Swagger (Docs):    ${CYAN}http://${VM_IP}:8000/api/schema/swagger-ui/${NC}"
echo -e "  🗄️  PgAdmin:           ${CYAN}http://${VM_IP}:5050${NC}"
echo -e "     (admin@sige.com / sige_admin_pass)"
echo ""

if [ "$BACKEND_OK" = false ]; then
    echo -e "${YELLOW}  ⚠️  Backend não respondeu no health check. Verifique os logs:${NC}"
    echo -e "     docker compose logs --tail=50 backend"
fi
if [ "$FRONTEND_OK" = false ]; then
    echo -e "${YELLOW}  ⚠️  Frontend não respondeu. Verifique os logs:${NC}"
    echo -e "     docker compose logs --tail=30 frontend"
fi

echo ""
echo -e "  📋 Comandos úteis:"
echo -e "     docker compose ps         — ver estado dos containers"
echo -e "     docker compose logs -f    — ver logs em tempo real"
echo -e "     docker compose restart    — reiniciar todos os serviços"
echo ""
echo -e "${GREEN}==========================================================${NC}"
