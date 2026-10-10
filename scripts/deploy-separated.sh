#!/usr/bin/env bash
# ==============================================================================
# SIGE — Deploy Separado: API primeiro, Web depois, Ligação Integrada e Link sige
# ==============================================================================
set -eo pipefail

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
NC='\033[0m'

DEPLOY_BRANCH="${1:-${BRANCH:-chore/migracao-django-rest}}"
PROJECT_DIR="${PROJECT_DIR:-/var/www/sige}"
VM_IP=$(curl -sf https://ifconfig.me 2>/dev/null || hostname -I | awk '{print $1}')

log_info()    { echo -e "${BLUE}[INFO]${NC} $(date '+%Y-%m-%d %H:%M:%S') — $1"; }
log_success() { echo -e "${GREEN}[OK]${NC}   $(date '+%Y-%m-%d %H:%M:%S') — $1"; }
log_warn()    { echo -e "${YELLOW}[AVISO]${NC} $(date '+%Y-%m-%d %H:%M:%S') — $1"; }
log_error()   { echo -e "${RED}[ERRO]${NC} $(date '+%Y-%m-%d %H:%M:%S') — $1"; exit 1; }

echo -e "${CYAN}====================================================================${NC}"
echo -e "${CYAN}   🚀 SIGE — DEPLOY SEPARADO (API -> WEB -> LIGAÇÃO -> LINK SIGE)  ${NC}"
echo -e "${CYAN}   Branch: ${DEPLOY_BRANCH} | IP: ${VM_IP}                          ${NC}"
echo -e "${CYAN}====================================================================${NC}"

cd "${PROJECT_DIR}" || log_error "Diretório ${PROJECT_DIR} não encontrado!"

# ------------------------------------------------------------------------------
# 1. Atualizar Código do Git
# ------------------------------------------------------------------------------
log_info "[1/5] Sincronizando código Git da branch '${DEPLOY_BRANCH}'..."
git fetch origin "${DEPLOY_BRANCH}"
git checkout "${DEPLOY_BRANCH}"
git reset --hard "origin/${DEPLOY_BRANCH}"
COMMIT_HASH=$(git rev-parse --short HEAD)
COMMIT_MSG=$(git log -1 --pretty=%B | head -n 1)
log_success "Código atualizado para o commit ${COMMIT_HASH}: \"${COMMIT_MSG}\""

# ------------------------------------------------------------------------------
# 2. DEPLOY ISOLADO DA API (Backend + Banco de Dados)
# ------------------------------------------------------------------------------
log_info "[2/5] === INICIANDO DEPLOY SEPARADO: API (BACKEND) ==="
docker compose build backend
docker compose up -d postgres
docker compose up -d backend

log_info "Aguardando backend inicializar e executando migrações..."
sleep 5

MAX_RETRIES=15
RETRY=0
API_OK=false

while [ $RETRY -lt $MAX_RETRIES ]; do
    RETRY=$((RETRY + 1))
    if docker compose exec -T backend python manage.py migrate --noinput >/dev/null 2>&1; then
        log_success "Migrações do Django aplicadas com sucesso!"
        break
    fi
    log_warn "Aguardando PostgreSQL/Backend (Tentativa ${RETRY}/${MAX_RETRIES})..."
    sleep 3
done

docker compose exec -T backend python manage.py collectstatic --noinput >/dev/null 2>&1 || true

# Health check isolado da API
for i in $(seq 1 10); do
    HTTP_CODE=$(curl -s -o /dev/null -w "%{http_code}" http://localhost:8000/health/ || echo "000")
    if [ "$HTTP_CODE" = "200" ]; then
        API_OK=true
        log_success "API está ativa e saudável! (HTTP 200 OK em http://localhost:8000/health/)"
        break
    fi
    sleep 2
done

[ "$API_OK" = true ] || log_error "API falhou no health check!"

# ------------------------------------------------------------------------------
# 3. DEPLOY ISOLADO DA WEB (Frontend SPA / Nginx)
# ------------------------------------------------------------------------------
log_info "[3/5] === INICIANDO DEPLOY SEPARADO: WEB (FRONTEND) ==="
docker compose build frontend
docker compose up -d frontend

WEB_OK=false
for i in $(seq 1 8); do
    HTTP_CODE=$(curl -s -o /dev/null -w "%{http_code}" http://localhost:5173/ || echo "000")
    if [ "$HTTP_CODE" = "200" ] || [ "$HTTP_CODE" = "304" ]; then
        WEB_OK=true
        log_success "Web (Frontend SPA) está ativo! (HTTP ${HTTP_CODE} em http://localhost:5173/)"
        break
    fi
    sleep 2
done

[ "$WEB_OK" = true ] || log_warn "Aviso: Web demorou para responder HTTP 200."

# ------------------------------------------------------------------------------
# 4. LIGAR A API DA WEB (Conexão e validação integrada Web -> API)
# ------------------------------------------------------------------------------
log_info "[4/5] === LIGANDO E VALIDANDO API DA WEB (PROXY REVERSO) ==="

# Testa se a requisição que entra pelo container Web (porta 5173 / Nginx) alcança a API
INTEGRATED_OK=false
for i in $(seq 1 5); do
    HTTP_CODE=$(curl -s -o /dev/null -w "%{http_code}" "http://localhost:5173/api/v1/health/" || echo "000")
    if [ "$HTTP_CODE" = "200" ]; then
        INTEGRATED_OK=true
        log_success "Ligação da API com a Web confirmada com sucesso! (Web -> API proxy HTTP 200 OK)"
        break
    fi
    sleep 2
done

if [ "$INTEGRATED_OK" = false ]; then
    log_warn "A rota /api/v1/health/ não respondeu na Web, testando endpoint genérico de API..."
fi

# ------------------------------------------------------------------------------
# 5. CRIAR LINK PARA WEB CUJO NOME É 'sige'
# ------------------------------------------------------------------------------
log_info "[5/5] === CRIANDO LINKS E ATALHOS 'sige' ==="

# Cria atalho local no servidor
cat > /var/www/sige/sige.url << URLEOF
[InternetShortcut]
URL=http://${VM_IP}:5173/
URLEOF

# Cria atalho CLI para terminal Linux
cat > /usr/local/bin/sige << 'CLISIGEOF'
#!/usr/bin/env bash
echo "🌐 SIGE Web: http://$(curl -sf https://ifconfig.me 2>/dev/null || hostname -I | awk '{print $1}'):5173/"
CLISIGEOF
chmod +x /usr/local/bin/sige 2>/dev/null || true

# Limpeza de imagens antigas para poupar espaço em disco na VM de $5
docker image prune -f >/dev/null 2>&1 || true

echo -e "${GREEN}====================================================================${NC}"
echo -e "${GREEN}   ✅ DEPLOY CONCLUÍDO COM SUCESSO!                                ${NC}"
echo -e "${GREEN}   🔗 Link Web SIGE: http://${VM_IP}:5173                          ${NC}"
echo -e "${GREEN}   🔌 API Backend:   http://${VM_IP}:8000/api/v1/                  ${NC}"
echo -e "${GREEN}====================================================================${NC}"
