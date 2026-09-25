"""
SIGE — Instalador de Gatilhos e Git Hooks para Push e Deploy Automático na VM.
Permite ativar hooks locais (post-commit para auto-push, pre-push para validação)
e gera o hook post-receive para o servidor/VM.
"""

from pathlib import Path
import os
import sys
import argparse

ROOT_DIR = Path(__file__).resolve().parent.parent
GIT_DIR = ROOT_DIR / '.git'
HOOKS_DIR = GIT_DIR / 'hooks'

POST_COMMIT_HOOK_CONTENT = """#!/bin/sh
# Git Hook: Post-Commit para Gatilho de Push e Deploy Automático SIGE
echo ""
echo "================================================================="
echo "[GATILHO AUTOMÁTICO] Commit detectado! Iniciando Git Push e Deploy..."
echo "================================================================="

CURRENT_BRANCH=$(git branch --show-current)

if [ -z "$CURRENT_BRANCH" ]; then
    echo "[AVISO] Nenhuma branch ativa identificada. Push ignorado."
    exit 0
fi

# Evita loop se o push for acionado por automações
if [ "$SIGE_NO_AUTO_PUSH" = "1" ]; then
    echo "[INFO] Auto-push desabilitado via SIGE_NO_AUTO_PUSH=1."
    exit 0
fi

echo "[INFO] Enviando alterações da branch '$CURRENT_BRANCH' para origin..."
git push origin "$CURRENT_BRANCH"

if [ $? -eq 0 ]; then
    echo "[SUCESSO] Código enviado! A esteira do GitHub Actions foi acionada para deploy na VM."
else
    echo "[ERRO] Falha no git push. Verifique sua conexão e permissões."
fi

echo "================================================================="
echo ""
exit 0
"""

PRE_PUSH_HOOK_CONTENT = """#!/bin/sh
# Git Hook: Pre-Push para validação de Backend e Frontend antes do Deploy
echo ""
echo "================================================================="
echo "[VALIDAÇÃO PRE-PUSH] Verificando integridade antes do Deploy..."
echo "================================================================="

# 1. Checagem Frontend
if command -v node >/dev/null 2>&1; then
    echo "[INFO] Validando sintaxe do Frontend..."
    node -c frontend/server.js 2>/dev/null && node -c frontend/js/config.js 2>/dev/null && node -c frontend/js/app.js 2>/dev/null
    if [ $? -ne 0 ]; then
        echo "[ERRO] Erro de sintaxe no código do Frontend. Corrija antes de fazer push."
        exit 1
    fi
    echo "[SUCESSO] Sintaxe do Frontend aprovada!"
fi

# 2. Checagem Backend Django
PYTHON_EXE=""
if [ -f "backend/venv/Scripts/python.exe" ]; then
    PYTHON_EXE="backend/venv/Scripts/python.exe"
elif [ -f "backend/venv/bin/python" ]; then
    PYTHON_EXE="backend/venv/bin/python"
elif command -v python >/dev/null 2>&1; then
    PYTHON_EXE="python"
fi

if [ -n "$PYTHON_EXE" ]; then
    echo "[INFO] Executando checagem do Django ($PYTHON_EXE)..."
    $PYTHON_EXE backend/manage.py check --settings=config.settings.development >/dev/null 2>&1
    if [ $? -ne 0 ]; then
        echo "[AVISO] Django check reportou problemas com as configurações locais."
    else
        echo "[SUCESSO] Django check aprovado!"
    fi
fi

echo "[SUCESSO] Código validado com sucesso! Prosseguindo com o push e deploy..."
echo "================================================================="
echo ""
exit 0
"""

POST_RECEIVE_VM_TEMPLATE = """#!/usr/bin/env bash
# ==============================================================================
# SIGE — Git Hook: post-receive para Servidor / VM
# Localização recomendada na VM: /var/repo/sige.git/hooks/post-receive
# ==============================================================================
set -eo pipefail

DEPLOY_DIR="/var/www/sige"
TARGET_BRANCH="main"

echo "================================================================"
echo " [VM GATILHO] Recebido novo push no repositório bare do servidor!"
echo " Atualizando arquivos em: $DEPLOY_DIR"
echo "================================================================"

while read oldrev newrev refname; do
    BRANCH=$(git rev-parse --symbolic --abbrev-ref "$refname")
    
    if [ "$BRANCH" = "$TARGET_BRANCH" ]; then
        echo "[INFO] Fazendo checkout da branch '$TARGET_BRANCH' em '$DEPLOY_DIR'..."
        git --work-tree="$DEPLOY_DIR" --git-dir="$(pwd)" checkout -f "$TARGET_BRANCH"
        
        cd "$DEPLOY_DIR"
        chmod +x scripts/deploy-vm.sh
        bash scripts/deploy-vm.sh "$TARGET_BRANCH"
    else
        echo "[INFO] Push recebido na branch '$BRANCH' (não é $TARGET_BRANCH). Deploy ignorado."
    fi
done

echo "================================================================"
echo " [VM GATILHO] Finalizado processamento do post-receive!"
echo "================================================================"
exit 0
"""

def install_hook(hook_name: str, content: str) -> bool:
    if not GIT_DIR.exists():
        print(f"[ERRO] Diretório .git não encontrado em {GIT_DIR}.")
        return False

    HOOKS_DIR.mkdir(parents=True, exist_ok=True)
    target_file = HOOKS_DIR / hook_name
    target_file.write_text(content, encoding='utf-8')

    try:
        os.chmod(target_file, 0o755)
    except Exception:
        pass

    print(f"[SUCESSO] Hook '{hook_name}' instalado com sucesso em: {target_file}")
    return True

def generate_vm_template():
    target_file = ROOT_DIR / 'scripts' / 'post-receive-vm.sample'
    target_file.write_text(POST_RECEIVE_VM_TEMPLATE, encoding='utf-8')
    print(f"[SUCESSO] Template post-receive da VM gerado em: {target_file}")

def main():
    parser = argparse.ArgumentParser(description="Instala gatilhos Git para Push e Deploy Automático do SIGE.")
    parser.add_argument('--post-commit', action='store_true', help="Instala o hook post-commit para disparar git push automaticamente em cada commit.")
    parser.add_argument('--pre-push', action='store_true', help="Instala o hook pre-push para validar o código antes de enviar ao servidor.")
    parser.add_argument('--all', action='store_true', help="Instala todos os hooks locais recomendados (pre-push e post-commit).")
    parser.add_argument('--uninstall', action='store_true', help="Remove os hooks instalados.")

    args = parser.parse_args()

    # Sempre gera o template do servidor na pasta scripts
    generate_vm_template()

    if args.uninstall:
        for name in ['post-commit', 'pre-push']:
            hook_path = HOOKS_DIR / name
            if hook_path.exists():
                hook_path.unlink()
                print(f"[REMOVIDO] Hook '{name}' removido.")
        return

    # Se nenhum argumento especificado, instala o recomendado (pre-push + post-commit opcional via prompt ou all)
    if args.all or (not args.post-commit and not args.pre-push):
        install_hook('pre-push', PRE_PUSH_HOOK_CONTENT)
        install_hook('post-commit', POST_COMMIT_HOOK_CONTENT)
        print("\n[INFO] Hooks pre-push e post-commit configurados com sucesso!")
        print("[INFO] Agora, cada 'git commit' enviará as mudanças automaticamente para o GitHub e disparará o deploy na VM.")
    else:
        if args.pre-push:
            install_hook('pre-push', PRE_PUSH_HOOK_CONTENT)
        if args.post-commit:
            install_hook('post-commit', POST_COMMIT_HOOK_CONTENT)

if __name__ == '__main__':
    main()
