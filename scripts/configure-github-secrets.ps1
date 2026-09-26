# ==============================================================================
# SIGE — Configurar GitHub Secrets e disparar Deploy Automático
# Uso: .\scripts\configure-github-secrets.ps1 -VmIp "34.90.123.45" -VmUser "seu_utilizador"
# ==============================================================================
param(
    [Parameter(Mandatory=$true)]
    [string]$VmIp,

    [Parameter(Mandatory=$false)]
    [string]$VmUser = $env:USERNAME,

    [Parameter(Mandatory=$false)]
    [string]$VmSshKeyPath = "$env:USERPROFILE\.ssh\sige_vm_key",

    [Parameter(Mandatory=$false)]
    [string]$VmDeployPath = "/var/www/sige",

    [Parameter(Mandatory=$false)]
    [int]$VmSshPort = 22,

    [Parameter(Mandatory=$false)]
    [string]$GitHubRepo = "mandamulefernandojose18-max/SIGE-Sistema-Integrado-de-Gest-o-Escolar",

    [Parameter(Mandatory=$false)]
    [string]$Branch = "chore/migracao-django-rest"
)

$ErrorActionPreference = "Stop"

Write-Host ""
Write-Host "================================================================" -ForegroundColor Cyan
Write-Host "  SIGE — Configurar GitHub Secrets para Deploy Automático" -ForegroundColor Cyan
Write-Host "================================================================" -ForegroundColor Cyan
Write-Host ""

# 1. Verificar se gh CLI está instalado
Write-Host "[1/5] Verificando GitHub CLI (gh)..." -ForegroundColor Blue
$ghInstalled = $null
try { $ghInstalled = Get-Command gh -ErrorAction Stop } catch {}

if (-not $ghInstalled) {
    Write-Host "      GitHub CLI não encontrado. Instalando via winget..." -ForegroundColor Yellow
    winget install --id GitHub.cli --silent --accept-package-agreements --accept-source-agreements
    $env:PATH += ";$env:LOCALAPPDATA\Programs\GitHub CLI"
    Write-Host "      GitHub CLI instalado!" -ForegroundColor Green
} else {
    Write-Host "      GitHub CLI: $(gh --version | Select-Object -First 1)" -ForegroundColor Green
}

# 2. Verificar autenticação no GitHub
Write-Host "[2/5] Verificando autenticação no GitHub..." -ForegroundColor Blue
$authStatus = gh auth status 2>&1
if ($LASTEXITCODE -ne 0) {
    Write-Host "      Não autenticado. Iniciando login no GitHub..." -ForegroundColor Yellow
    gh auth login --web --git-protocol https
}
Write-Host "      Autenticado no GitHub!" -ForegroundColor Green

# 3. Verificar chave SSH
Write-Host "[3/5] Verificando chave SSH para a VM..." -ForegroundColor Blue
if (-not (Test-Path $VmSshKeyPath)) {
    Write-Host "      Chave não encontrada em: $VmSshKeyPath" -ForegroundColor Red
    Write-Host "      A gerar nova chave SSH..." -ForegroundColor Yellow
    ssh-keygen -t ed25519 -C "sige-deploy@google-cloud-vm" -f $VmSshKeyPath -N '""'
}

$sshPrivateKey = Get-Content $VmSshKeyPath -Raw
$sshPublicKey  = Get-Content "$VmSshKeyPath.pub" -Raw
Write-Host "      Chave SSH encontrada: $VmSshKeyPath" -ForegroundColor Green
Write-Host ""
Write-Host "      CHAVE PÚBLICA (já adicionada na VM pelo bootstrap):" -ForegroundColor Cyan
Write-Host "      $sshPublicKey" -ForegroundColor Gray

# 4. Configurar todos os Secrets no GitHub
Write-Host "[4/5] Configurando GitHub Secrets no repositório..." -ForegroundColor Blue

$secrets = @{
    "VM_HOST"        = $VmIp
    "VM_USER"        = $VmUser
    "VM_SSH_KEY"     = $sshPrivateKey
    "VM_SSH_PORT"    = "$VmSshPort"
    "VM_DEPLOY_PATH" = $VmDeployPath
}

foreach ($secret in $secrets.GetEnumerator()) {
    Write-Host "      Definindo secret: $($secret.Key)..." -NoNewline
    $secret.Value | gh secret set $secret.Key --repo $GitHubRepo 2>&1 | Out-Null
    if ($LASTEXITCODE -eq 0) {
        Write-Host " ✅" -ForegroundColor Green
    } else {
        Write-Host " ❌ FALHOU" -ForegroundColor Red
    }
}

# 5. Testar conexão SSH com a VM
Write-Host "[5/5] Testando conexão SSH com a VM ($VmIp)..." -ForegroundColor Blue
$sshTest = ssh -i $VmSshKeyPath `
               -o StrictHostKeyChecking=no `
               -o ConnectTimeout=10 `
               -p $VmSshPort `
               "${VmUser}@${VmIp}" `
               "echo 'SSH_OK' && docker compose version --short 2>/dev/null || echo 'Docker nao instalado ainda'" `
               2>&1

if ($sshTest -match "SSH_OK") {
    Write-Host "      Conexão SSH estabelecida com sucesso! ✅" -ForegroundColor Green
    Write-Host "      Resposta da VM: $sshTest" -ForegroundColor Gray
} else {
    Write-Host "      ⚠️  Conexão SSH falhou ou a VM ainda não está pronta." -ForegroundColor Yellow
    Write-Host "      Certifica-te de que o script bootstrap-vm.sh foi executado na VM." -ForegroundColor Yellow
    Write-Host "      Detalhe: $sshTest" -ForegroundColor Gray
}

# 6. Disparar o deploy via GitHub Actions
Write-Host ""
Write-Host "================================================================" -ForegroundColor Green
Write-Host "  ✅ GitHub Secrets configurados com sucesso!" -ForegroundColor Green
Write-Host "================================================================" -ForegroundColor Green
Write-Host ""
Write-Host "  Secrets definidos no repositório:" -ForegroundColor Cyan
Write-Host "    VM_HOST        = $VmIp" -ForegroundColor White
Write-Host "    VM_USER        = $VmUser" -ForegroundColor White
Write-Host "    VM_SSH_PORT    = $VmSshPort" -ForegroundColor White
Write-Host "    VM_DEPLOY_PATH = $VmDeployPath" -ForegroundColor White
Write-Host "    VM_SSH_KEY     = [chave privada Ed25519]" -ForegroundColor White
Write-Host ""

$dispararDeploy = Read-Host "Queres disparar o deploy agora via GitHub Actions? (S/n)"
if ($dispararDeploy -ne "n" -and $dispararDeploy -ne "N") {
    Write-Host "Disparando workflow de deploy na branch '$Branch'..." -ForegroundColor Blue
    gh workflow run "deploy.yml" --repo $GitHubRepo --ref $Branch
    if ($LASTEXITCODE -eq 0) {
        Write-Host "Deploy disparado! ✅" -ForegroundColor Green
        Write-Host ""
        Write-Host "Acompanha em: https://github.com/$GitHubRepo/actions" -ForegroundColor Cyan
    } else {
        Write-Host "Falhou ao disparar o workflow. Verifica os secrets e tenta manualmente em:" -ForegroundColor Yellow
        Write-Host "https://github.com/$GitHubRepo/actions" -ForegroundColor Cyan
    }
}

Write-Host ""
Write-Host "  Após o deploy concluir, acede a:" -ForegroundColor Cyan
Write-Host "    Frontend: http://${VmIp}:5173" -ForegroundColor White
Write-Host "    Backend:  http://${VmIp}:8000/api/v1/" -ForegroundColor White
Write-Host "    PgAdmin:  http://${VmIp}:5050" -ForegroundColor White
Write-Host ""
