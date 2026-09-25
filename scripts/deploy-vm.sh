#!/usr/bin/env bash
# ==============================================================================
# SIGE — Script de Deploy Automatizado para Máquina Virtual (VM)
# Backend (Django REST Framework) + Frontend (Nginx/SPA) + PostgreSQL
# ==============================================================================

set -eo pipefail

# Cores para saída no terminal
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
NC='\033[0m' # No Color

# Configurações com fallback
DEPLOY_BRANCH="${1:-${BRANCH:-main}}"
PROJECT_DIR="${PROJECT_DIR:-$(pwd)}"
BACKEND_HEALTH_URL="${BACKEND_HEALTH_URL:-http://localhost:8000/health/}"
FRONTEND_HEALTH_URL="${FRONTEND_HEALTH_URL:-http://localhost:5173/}"

log_info() {
    echo -e "${BLUE}[INFO]${NC} $(date '+%Y-%m-%d %H:%M:%S') — $1"
}

log_success() {
    echo -e "${GREEN}[SUCESSO]${NC} $(date '+%Y-%m-%d %H:%M:%S') — $1"
}

log_warn() {
    echo -e "${YELLOW}[AVISO]${NC} $(date '+%Y-%m-%d %H:%M:%S') — $1"
}

log_error() {
    echo -e "${RED}[ERRO]${NC} $(date '+%Y-%m-%d %H:%M:%S') — $1"
}

echo -e "${CYAN}====================================================================${NC}"
echo -e "${CYAN}   🚀 INICIANDO DEPLOY AUTOMATIZADO DO SIGE NA VM                  ${NC}"
echo -e "${CYAN}   Branch: ${DEPLOY_BRANCH} | Diretório: ${PROJECT_DIR}           ${NC}"
echo -e "${CYAN}====================================================================${NC}"

# 1. Navegar para o diretório do projeto
cd "${PROJECT_DIR}" || {
    log_error "Diretório do projeto não encontrado: ${PROJECT_DIR}"
    exit 1
}

# 2. Verificar dependências de sistema (Git, Docker, Docker Compose)
log_info "Verificando dependências de sistema..."
command -v git >/dev/null 2>&1 || { log_error "Git não está instalado na VM."; exit 1; }
command -v docker >/dev/null 2>&1 || { log_error "Docker não está instalado na VM."; exit 1; }

# Determinar comando docker compose (plugin v2 ou binário v1)
if docker compose version >/dev/null 2>&1; then
    DOCKER_COMPOSE="docker compose"
elif command -v docker-compose >/dev/null 2>&1; then
    DOCKER_COMPOSE="docker-compose"
else
    log_error "Docker Compose não foi encontrado na VM."
    exit 1
fi
log_info "Utilizando: ${DOCKER_COMPOSE}"

# 3. Atualizar código do repositório Git
log_info "Sincronizando repositório Git com a branch '${DEPLOY_BRANCH}'..."
git fetch origin "${DEPLOY_BRANCH}"
git checkout "${DEPLOY_BRANCH}"
git reset --hard "origin/${DEPLOY_BRANCH}"

COMMIT_HASH=$(git rev-parse --short HEAD)
COMMIT_MSG=$(git log -1 --pretty=%B | head -n 1)
log_info "Código atualizado para o commit ${COMMIT_HASH}: \"${COMMIT_MSG}\""

# 4. Validar arquivos de configuração de ambiente (.env)
if [ ! -f ".env" ] && [ -f ".env.example" ]; then
    log_warn "Arquivo .env raiz não encontrado. Criando cópia a partir de .env.example..."
    cp .env.example .env
fi

if [ ! -f "backend/.env" ] && [ -f "backend/.env.example" ]; then
    log_warn "Arquivo backend/.env não encontrado. Criando cópia a partir de backend/.env.example..."
    cp backend/.env.example backend/.env
fi

# 5. Build e Inicialização dos Containers (Backend, Frontend, Postgres)
log_info "Construindo imagens Docker atualizadas para Backend e Frontend..."
${DOCKER_COMPOSE} build backend frontend

log_info "Iniciando serviços no Docker Compose..."
${DOCKER_COMPOSE} up -d postgres
${DOCKER_COMPOSE} up -d backend frontend pgadmin

# 6. Aguardar banco de dados e aplicar migrações do Django
log_info "Aguardando inicialização do banco de dados e executando migrações..."
sleep 5

MAX_RETRIES=10
RETRY_COUNT=0
MIGRATION_SUCCESS=false

while [ $RETRY_COUNT -lt $MAX_RETRIES ]; do
    RETRY_COUNT=$((RETRY_COUNT + 1))
    log_info "Tentando aplicar migrações Django (Tentativa ${RETRY_COUNT}/${MAX_RETRIES})..."
    if ${DOCKER_COMPOSE} exec -T backend python manage.py migrate --noinput; then
        MIGRATION_SUCCESS=true
        log_success "Migrações aplicadas com sucesso!"
        break
    else
        log_warn "Banco ainda não disponível ou ocupado. Aguardando 4s..."
        sleep 4
    fi
done

if [ "$MIGRATION_SUCCESS" = false ]; then
    log_error "Falha crítica ao executar migrações do Django."
    exit 1
fi

# 7. Checagem de integridade do sistema Django
log_info "Executando checagem de sistema Django (manage.py check)..."
${DOCKER_COMPOSE} exec -T backend python manage.py check

# 8. Verificação de Saúde dos Serviços (Health Checks HTTP)
log_info "Executando Health Check nos endpoints de produção..."

# Backend Health Check
BACKEND_OK=false
for i in $(seq 1 10); do
    HTTP_CODE=$(curl -s -o /dev/null -w "%{http_code}" "${BACKEND_HEALTH_URL}" || echo "000")
    if [ "$HTTP_CODE" = "200" ]; then
        BACKEND_OK=true
        log_success "Backend respondendo com HTTP 200 OK em ${BACKEND_HEALTH_URL}!"
        break
    fi
    log_warn "Backend ainda não respondeu HTTP 200 (código: ${HTTP_CODE}). Tentativa ${i}/10..."
    sleep 3
done

if [ "$BACKEND_OK" = false ]; then
    log_error "Health check do Backend falhou após 10 tentativas."
    ${DOCKER_COMPOSE} logs --tail=50 backend
    exit 1
fi

# Frontend Health Check
FRONTEND_OK=false
for i in $(seq 1 5); do
    HTTP_CODE=$(curl -s -o /dev/null -w "%{http_code}" "${FRONTEND_HEALTH_URL}" || echo "000")
    if [ "$HTTP_CODE" = "200" ] || [ "$HTTP_CODE" = "304" ]; then
        FRONTEND_OK=true
        log_success "Frontend SPA respondendo com sucesso em ${FRONTEND_HEALTH_URL}!"
        break
    fi
    log_warn "Frontend ainda não respondeu (código: ${HTTP_CODE}). Tentativa ${i}/5..."
    sleep 2
done

if [ "$FRONTEND_OK" = false ]; then
    log_warn "Aviso: Frontend não retornou 200 no health check local. Verifique os logs."
    ${DOCKER_COMPOSE} logs --tail=30 frontend
fi

# 9. Limpeza de imagens Docker órfãs/antigas para poupar disco na VM
log_info "Limpando imagens antigas e dangling containers..."
docker image prune -f >/dev/null 2>&1 || true

# 10. Resumo final
echo -e "${GREEN}====================================================================${NC}"
echo -e "${GREEN}   ✅ DEPLOY CONCLUÍDO COM SUCESSO NA VM!                         ${NC}"
echo -e "${GREEN}   Commit: ${COMMIT_HASH} | Mensagem: ${COMMIT_MSG}               ${NC}"
echo -e "${GREEN}   Backend: ${BACKEND_HEALTH_URL}                                 ${NC}"
echo -e "${GREEN}   Frontend: ${FRONTEND_HEALTH_URL}                                ${NC}"
echo -e "${GREEN}====================================================================${NC}"

exit 0
