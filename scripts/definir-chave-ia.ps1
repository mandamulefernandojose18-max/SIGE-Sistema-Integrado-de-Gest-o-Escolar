<#
.SYNOPSIS
  Activa a IA do SIGE no servidor com uma chave GRATUITA (Google Gemini por omissão), sem mostrar nem guardar a chave neste computador.

.DESCRIPTION
  Pede a chave num campo escondido, envia-a ao servidor pelo SSH (entrada padrão, nunca na linha de comandos), grava-a no .env do
  servidor (permissões 600), reinicia o backend e confirma qual IA ficou activa.
  Chave gratuita do Google Gemini (sem cartão): https://aistudio.google.com/apikey  ("Create API key")
  Uso:     powershell -NoProfile -ExecutionPolicy Bypass -File .\scripts\definir-chave-ia.ps1
  Outros:  -Provedor groq | openrouter | anthropic (pago)      -Remover (desliga a IA)
#>
param(
    [ValidateSet("gemini", "groq", "openrouter", "anthropic")][string]$Provedor = "gemini",
    [string]$VmIp = "sigesaas.duckdns.org",
    [string]$VmUser = "root",
    [string]$KeyPath = "$env:USERPROFILE\.ssh\sige_vm_key",
    [string]$Pasta = "/var/www/sige",
    [switch]$Remover
)
$ErrorActionPreference = "Stop"

$variavel = @{ gemini = "GEMINI_API_KEY"; groq = "GROQ_API_KEY"; openrouter = "OPENROUTER_API_KEY"; anthropic = "ANTHROPIC_API_KEY" }[$Provedor]
$formato = @{ gemini = '^AIza[0-9A-Za-z_\-]{30,}$'; groq = '^gsk_[0-9A-Za-z]{20,}$'; openrouter = '^sk-or-[0-9A-Za-z_\-]{20,}$'; anthropic = '^sk-ant-[0-9A-Za-z_\-]{20,}$' }[$Provedor]
$gratis = @{ gemini = "GRATUITA (Google Gemini)"; groq = "GRATUITA (Groq)"; openrouter = "gratuita (OpenRouter, modelos :free)"; anthropic = "PAGA (Anthropic)" }[$Provedor]

function Invocar-Remoto([string]$comando, [string]$entrada = $null) {
    $args_ssh = @("-i", $KeyPath, "-o", "StrictHostKeyChecking=no", "${VmUser}@${VmIp}", $comando)
    if ($null -ne $entrada) { $entrada | & ssh @args_ssh } else { & ssh @args_ssh }
    if ($LASTEXITCODE -ne 0) { throw "O servidor devolveu um erro (código $LASTEXITCODE)." }
}

if ($Remover) {
    Invocar-Remoto "cd $Pasta && sed -i -e '/^GEMINI_API_KEY=/d' -e '/^GROQ_API_KEY=/d' -e '/^OPENROUTER_API_KEY=/d' -e '/^ANTHROPIC_API_KEY=/d' -e '/^SIGE_IA_PROVEDOR=/d' .env && docker compose up -d backend"
    Write-Host "Chaves removidas. A IA do SIGE ficou desactivada." -ForegroundColor Yellow
    return
}

Write-Host "IA $gratis. Chave: " -NoNewline
if ($Provedor -eq "gemini") { Write-Host "https://aistudio.google.com/apikey (Create API key, sem cartão)" -ForegroundColor Cyan } else { Write-Host "a do teu painel $Provedor" }
$segura = Read-Host "Cola a chave (nao aparece no ecra)" -AsSecureString
$ponteiro = [Runtime.InteropServices.Marshal]::SecureStringToBSTR($segura)
try { $chave = [Runtime.InteropServices.Marshal]::PtrToStringBSTR($ponteiro).Trim() }
finally { [Runtime.InteropServices.Marshal]::ZeroFreeBSTR($ponteiro) }

if ($chave -notmatch $formato) {
    throw "Isso nao parece uma chave $Provedor valida (formato errado ou incompleta). Nada foi alterado."
}

# a chave segue pela entrada padrao do SSH: nao fica no historico nem na lista de processos
$remoto = "read -r K && cd $Pasta && touch .env && sed -i -e '/^${variavel}=/d' -e '/^SIGE_IA_PROVEDOR=/d' .env && printf '${variavel}=%s\nSIGE_IA_PROVEDOR=${Provedor}\n' ""`$K"" >> .env && chmod 600 .env && docker compose up -d backend"
Invocar-Remoto $remoto $chave
$chave = $null

Start-Sleep -Seconds 15
Write-Host "A confirmar no servidor..." -ForegroundColor Cyan
Invocar-Remoto "docker exec sige_backend python manage.py shell -c ""from apps.escudo.services import ia_sige as i; print('IA do SIGE:', i.provedor(), '| modelo:', i.modelo(), '| gratuito:', i.gratuito())"""
Write-Host "Pronto. O Guiao ja pode ser gerado em Selos e copias > Gerar > Com Guiao." -ForegroundColor Green
