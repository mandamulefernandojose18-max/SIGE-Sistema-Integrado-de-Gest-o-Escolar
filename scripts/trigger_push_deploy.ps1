# ==============================================================================
# SIGE — Gatilho Local de Git Push e Deploy Automático na VM (PowerShell)
# Executa verificações locais, commit, git push e aciona o deploy na VM.
# ==============================================================================

[CmdletBinding()]
param (
    [Parameter(Mandatory = $false, Position = 0)]
    [string]$Message,

    [Parameter(Mandatory = $false)]
    [string]$Branch,

    [Parameter(Mandatory = $false)]
    [string]$Remote = "origin",

    [Parameter(Mandatory = $false)]
    [switch]$SkipCheck,

    [Parameter(Mandatory = $false)]
    [switch]$DirectSSH,

    [Parameter(Mandatory = $false)]
    [string]$VMHost,

    [Parameter(Mandatory = $false)]
    [string]$VMUser,

    [Parameter(Mandatory = $false)]
    [string]$VMDeployPath = "/var/www/sige"
)

$ErrorActionPreference = "Stop"

function Write-Info {
    param([string]$Text)
    Write-Host "[INFO] $Text" -ForegroundColor Cyan
}

function Write-Success {
    param([string]$Text)
    Write-Host "[SUCESSO] $Text" -ForegroundColor Green
}

function Write-WarningMsg {
    param([string]$Text)
    Write-Host "[AVISO] $Text" -ForegroundColor Yellow
}

function Write-ErrorMsg {
    param([string]$Text)
    Write-Host "[ERRO] $Text" -ForegroundColor Red
}

Write-Host "======================================================================" -ForegroundColor Magenta
Write-Host "   🚀 SIGE — Gatilho de Push e Deploy Automático na VM (Local CLI)   " -ForegroundColor Magenta
Write-Host "======================================================================" -ForegroundColor Magenta

# 1. Determinar branch atual
if (-not $Branch) {
    $Branch = (git branch --show-current).Trim()
    if (-not $Branch) {
        Write-ErrorMsg "Não foi possível identificar a branch atual do Git."
        exit 1
    }
}
Write-Info "Branch selecionada: $Branch (Remote: $Remote)"

# 2. Executar checagem de sintaxe rápida se não for ignorada
if (-not $SkipCheck) {
    Write-Info "Executando checagem rápida de integridade..."
    
    # Checagem Backend Django se Python estiver acessível
    if (Test-Path "backend/manage.py") {
        try {
            $pythonCmd = if (Test-Path "backend/venv/Scripts/python.exe") { "backend/venv/Scripts/python.exe" } else { "python" }
            & $pythonCmd backend/manage.py check --settings=config.settings.development 2>$null
            if ($LASTEXITCODE -eq 0) {
                Write-Success "Django check passou com sucesso!"
            } else {
                Write-WarningMsg "Django check reportou avisos ou o ambiente virtual não está ativo localmente."
            }
        } catch {
            Write-WarningMsg "Python local não disponível para checagem rápida; a esteira remota executará os testes completos."
        }
    }
}

# 3. Verificar status do Git
$gitStatus = (git status --porcelain)
if ($gitStatus) {
    Write-Info "Arquivos alterados detectados no repositório local:"
    git status -s

    if (-not $Message) {
        $Message = Read-Host "`nDigite a mensagem do commit para o Deploy (ou ENTER para 'feat: deploy automatico SIGE')"
        if ([string]::IsNullOrWhiteSpace($Message)) {
            $Message = "feat: deploy automatico SIGE [$(Get-Date -Format 'yyyy-MM-dd HH:mm')]"
        }
    }

    Write-Info "Adicionando alterações e criando commit..."
    git add -A
    git commit -m "$Message"
    Write-Success "Commit criado: $Message"
} else {
    Write-Info "Nenhuma alteração pendente de commit. Verificando commits locais à frente da branch remota..."
}

# 4. Executar Git Push
Write-Info "Executando 'git push $Remote $Branch'..."
try {
    git push $Remote $Branch
    Write-Success "Código de Backend e Frontend enviado com sucesso para $Remote/$Branch!"
} catch {
    Write-ErrorMsg "Falha ao enviar código para o repositório remoto via git push."
    exit 1
}

# 5. Informações sobre o acionamento do Deploy
$remoteUrl = (git remote get-url $Remote)
$actionsUrl = ""
if ($remoteUrl -match "github\.com[:/](.+?)(?:\.git)?$") {
    $repoPath = $Matches[1]
    $actionsUrl = "https://github.com/$repoPath/actions"
}

Write-Host "`n======================================================================" -ForegroundColor Green
Write-Host "   ⚡ GATILHO DISPARADO COM SUCESSO!                                  " -ForegroundColor Green
Write-Host "======================================================================" -ForegroundColor Green
Write-Host "1. O push acionou a esteira do GitHub Actions automaticamente."
if ($actionsUrl) {
    Write-Host "2. Acompanhe a execução do Deploy ao vivo em: $actionsUrl" -ForegroundColor Cyan
}

# 6. Modo DirectSSH (Opcional - caso queira disparar SSH diretamente do terminal local)
if ($DirectSSH) {
    if (-not $VMHost -or -not $VMUser) {
        Write-WarningMsg "Para deploy direto via SSH, informe -VMHost <IP> e -VMUser <usuario>."
    } else {
        Write-Info "Iniciando trigger direto via SSH na VM ($VMUser@$VMHost)..."
        $sshCmd = "cd $VMDeployPath && chmod +x scripts/deploy-vm.sh && bash scripts/deploy-vm.sh $Branch"
        ssh -o StrictHostKeyChecking=no "$VMUser@$VMHost" $sshCmd
        Write-Success "Comando de deploy executado na VM via SSH!"
    }
}

Write-Host "======================================================================`n"
exit 0
