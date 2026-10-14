<#
.SYNOPSIS
    SIGE - Pipeline Completa: Git Commit, Git Push, Deploy Separado (API + Web) e Link 'sige'
#>
param(
    [Parameter(Position=0, Mandatory=$false)]
    [string]$Message = "chore: atualizacao e deploy automatico na vm",

    [Parameter(Mandatory=$false)]
    [string]$Branch = "chore/migracao-django-rest",

    [Parameter(Mandatory=$false)]
    [string]$VmIp = "139.84.226.46",

    [Parameter(Mandatory=$false)]
    [string]$VmUser = "root",

    [Parameter(Mandatory=$false)]
    [string]$KeyPath = "$env:USERPROFILE\.ssh\sige_vm_key",

    [Parameter(Mandatory=$false)]
    [switch]$OpenBrowser
)

$ErrorActionPreference = "Stop"

Write-Host ""
Write-Host "================================================================" -ForegroundColor Cyan
Write-Host "   SIGE - PIPELINE: COMMIT, PUSH E DEPLOY SEPARADO NA VM        " -ForegroundColor Cyan
Write-Host "================================================================" -ForegroundColor Cyan
Write-Host "  Ambiente: Producao | Branch: $Branch" -ForegroundColor Gray
Write-Host "  Mensagem: $Message" -ForegroundColor Gray
Write-Host ""

# 1. GIT COMMIT
Write-Host "[1/5] Verificando e comitando alteracoes locais..." -ForegroundColor Blue
git add .
$statusOutput = git status -s
if ($statusOutput) {
    git commit -m "$Message"
    Write-Host "  OK: Alteracoes comitadas com sucesso!" -ForegroundColor Green
} else {
    Write-Host "  AVISO: Nenhuma alteracao pendente para commit." -ForegroundColor Yellow
}

# 2. GIT PUSH
Write-Host "[2/5] Enviando alteracoes para o GitHub (git push)..." -ForegroundColor Blue
git push origin "$Branch"
Write-Host "  OK: Push concluido com sucesso!" -ForegroundColor Green

# 3. DEPLOY SEPARADO NA VM
Write-Host "[3/5] Disparando deploy desacoplado na VM de producao..." -ForegroundColor Blue
$remoteCmd = "cd /var/www/sige && git fetch origin $Branch && git checkout $Branch && git reset --hard origin/$Branch && chmod +x scripts/*.sh && bash scripts/deploy-separated.sh $Branch"

ssh -i $KeyPath -o StrictHostKeyChecking=no "${VmUser}@${VmIp}" "$remoteCmd"
if ($LASTEXITCODE -ne 0) {
    Write-Host "  ERRO: Falha durante o deploy na VM!" -ForegroundColor Red
    exit $LASTEXITCODE
}
Write-Host "  OK: Deploy separado concluido com sucesso na VM!" -ForegroundColor Green

# 4. CRIAR LINK PARA WEB CUJO NOME É 'sige' (HTTPS SEGURO DUCKDNS - IP OCULTO)
Write-Host "[4/5] Criando atalho/link seguro HTTPS para a Web cujo nome e 'sige' (sigesaas.duckdns.org)..." -ForegroundColor Blue
$sslDomain = "sigesaas.duckdns.org"
$webUrl = "https://${sslDomain}/"

$shortcutLines = @(
    "[InternetShortcut]",
    "URL=$webUrl",
    "IconIndex=0"
)

# A. Raiz do projeto
$localShortcut = "d:\SIGE\sige.url"
Set-Content -Path $localShortcut -Value $shortcutLines -Encoding ASCII
Write-Host "  OK: Link web HTTPS criado no projeto: $localShortcut" -ForegroundColor Green

# B. Desktop
$desktopShortcut = "$env:USERPROFILE\Desktop\sige.url"
try {
    Set-Content -Path $desktopShortcut -Value $shortcutLines -Encoding ASCII
    Write-Host "  OK: Link web HTTPS criado no Desktop: $desktopShortcut" -ForegroundColor Green
} catch {
    Write-Host "  AVISO: Nao foi possivel gravar no Desktop." -ForegroundColor Yellow
}

# C. Script utilitário 'sige.cmd'
$cmdContent = "@start $webUrl"
Set-Content -Path "d:\SIGE\sige.cmd" -Value $cmdContent -Encoding ASCII
Write-Host "  OK: Atalho CLI 'sige' criado (digite .\sige para abrir)" -ForegroundColor Green

# 5. RESUMO FINAL
Write-Host ""
Write-Host "================================================================" -ForegroundColor Green
Write-Host "   PIPELINE SIGE CONCLUIDA COM SUCESSO (HTTPS SEGURO)!          " -ForegroundColor Green
Write-Host "================================================================" -ForegroundColor Green
Write-Host "  Link Web (sige): $webUrl" -ForegroundColor Cyan
Write-Host "  Link API HTTPS:  ${webUrl}api/v1/" -ForegroundColor Cyan
Write-Host "  Swagger Docs:    ${webUrl}api/docs/" -ForegroundColor Cyan
Write-Host ""

if ($OpenBrowser) {
    Start-Process $webUrl
}
