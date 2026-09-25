#!/usr/bin/env bash
# ==============================================================================
# SIGE — Gatilho Local de Git Push e Deploy Automático na VM (Bash)
# ==============================================================================

set -eo pipefail

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
NC='\033[0m'

COMMIT_MSG="${1:-}"
BRANCH="${2:-$(git branch --show-current)}"
REMOTE="${3:-origin}"

echo -e "${CYAN}======================================================================${NC}"
echo -e "${CYAN}   🚀 SIGE — Gatilho de Push e Deploy Automático na VM (Bash CLI)    ${NC}"
echo -e "${CYAN}======================================================================${NC}"

if [ -z "${BRANCH}" ]; then
    echo -e "${RED}[ERRO] Não foi possível identificar a branch atual do Git.${NC}"
    exit 1
fi

echo -e "${BLUE}[INFO] Branch selecionada: ${BRANCH} (Remote: ${REMOTE})${NC}"

# Checar alterações pendentes
if [ -n "$(git status --porcelain)" ]; then
    echo -e "${BLUE}[INFO] Mudanças detectadas no Backend ou Frontend:${NC}"
    git status -s

    if [ -z "${COMMIT_MSG}" ]; then
        read -r -p "Digite a mensagem do commit para o Deploy [ENTER para padrão]: " USER_MSG
        if [ -n "${USER_MSG}" ]; then
            COMMIT_MSG="${USER_MSG}"
        else
            COMMIT_MSG="feat: deploy automatico SIGE [$(date '+%Y-%m-%d %H:%M')]"
        fi
    fi

    echo -e "${BLUE}[INFO] Adicionando arquivos e realizando commit...${NC}"
    git add -A
    git commit -m "${COMMIT_MSG}"
    echo -e "${GREEN}[SUCESSO] Commit criado: ${COMMIT_MSG}${NC}"
else
    echo -e "${BLUE}[INFO] Repositório de trabalho limpo. Verificando commits locais pendentes de push...${NC}"
fi

# Executar Git Push
echo -e "${BLUE}[INFO] Enviando código para ${REMOTE}/${BRANCH}...${NC}"
git push "${REMOTE}" "${BRANCH}"
echo -e "${GREEN}[SUCESSO] Código enviado com sucesso para ${REMOTE}/${BRANCH}!${NC}"

# Obter URL do repositório para exibição
REPO_URL=$(git remote get-url "${REMOTE}" | sed -E 's/git@github\.com:/https:\/\/github\.com\//' | sed -E 's/\.git$//')

echo -e "\n${GREEN}======================================================================${NC}"
echo -e "${GREEN}   ⚡ GATILHO DISPARADO COM SUCESSO!                                  ${NC}"
echo -e "${GREEN}======================================================================${NC}"
echo -e "O push ativou o fluxo de deploy automático do GitHub Actions na VM."
if [ -n "${REPO_URL}" ]; then
    echo -e "Acompanhe o status do Deploy em tempo real:"
    echo -e "${CYAN}${REPO_URL}/actions${NC}"
fi
echo -e "${GREEN}======================================================================${NC}\n"

exit 0
