<#
.SYNOPSIS
  Define a chave da IA do SIGE (ANTHROPIC_API_KEY) no servidor, sem a mostrar nem a guardar em lado nenhum deste computador.

.DESCRIPTION
  Pede a chave num campo escondido, envia-a ao servidor pelo SSH (entrada padrão, nunca na linha de comandos),
  grava-a no .env do servidor (permissões 600), reinicia o backend e confirma que a IA ficou activada.
  Uso:  .\scripts\definir-chave-ia.ps1
  Para remover a chave:  .\scripts\definir-chave-ia.ps1 -Remover
#>
param(
    [string]$VmIp = "sigesaas.duckdns.org",
    [string]$VmUser = "root",
    [string]$KeyPath = "$env:USERPROFILE\.ssh\sige_vm_key",
    [string]$Pasta = "/var/www/sige",
    [switch]$Remover
)
$ErrorActionPreference = "Stop"

function Invocar-Remoto([string]$comando, [string]$entrada = $null) {
    $args_ssh = @("-i", $KeyPath, "-o", "StrictHostKeyChecking=no", "${VmUser}@${VmIp}", $comando)
    if ($null -ne $entrada) { $entrada | & ssh @args_ssh } else { & ssh @args_ssh }
    if ($LASTEXITCODE -ne 0) { throw "O servidor devolveu um erro (código $LASTEXITCODE)." }
}

if ($Remover) {
    Invocar-Remoto "cd $Pasta && sed -i '/^ANTHROPIC_API_KEY=/d' .env && docker compose up -d backend"
    Write-Host "Chave removida. A IA do SIGE ficou desactivada." -ForegroundColor Yellow
    return
}

$segura = Read-Host "Cola a chave da API da Anthropic (comeca por sk-ant-; nao aparece no ecra)" -AsSecureString
$ponteiro = [Runtime.InteropServices.Marshal]::SecureStringToBSTR($segura)
try { $chave = [Runtime.InteropServices.Marshal]::PtrToStringBSTR($ponteiro).Trim() }
finally { [Runtime.InteropServices.Marshal]::ZeroFreeBSTR($ponteiro) }

if ($chave -notmatch '^sk-ant-[A-Za-z0-9_\-]{20,}$') {
    throw "Isso nao parece uma chave da Anthropic (deve comecar por sk-ant-). Nada foi alterado."
}

# a chave segue pela entrada padrao do SSH: nao fica no historico nem na lista de processos
$remoto = "read -r K && cd $Pasta && touch .env && sed -i '/^ANTHROPIC_API_KEY=/d' .env && printf 'ANTHROPIC_API_KEY=%s\n' ""`$K"" >> .env && chmod 600 .env && docker compose up -d backend"
Invocar-Remoto $remoto $chave
$chave = $null

Start-Sleep -Seconds 12
Write-Host "A confirmar no servidor..." -ForegroundColor Cyan
Invocar-Remoto "docker exec sige_backend python -c ""import os; print('IA do SIGE activada:', bool(os.environ.get('ANTHROPIC_API_KEY')))"""
Write-Host "Pronto. O Guiao ja pode ser gerado em Selos e copias > Gerar > Com Guiao." -ForegroundColor Green
