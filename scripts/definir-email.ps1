<#
.SYNOPSIS
  Activa o envio de e-mail do SIGE (avisos de leitura dos codigos das provas) sem mostrar nem guardar a palavra-passe neste computador.

.DESCRIPTION
  Gratuito: uma conta Gmail com "palavra-passe de aplicacao" (Conta Google > Seguranca > Verificacao em 2 passos > Palavras-passe de aplicacoes),
  ou o plano gratuito de qualquer servico SMTP (ex.: Brevo). A palavra-passe e pedida num campo escondido e segue ao servidor pelo SSH
  (entrada padrao), para o .env do servidor (permissoes 600). No fim envia um e-mail de teste para o proprio endereco.
  Uso:    powershell -NoProfile -ExecutionPolicy Bypass -File .\scripts\definir-email.ps1 -Utilizador o.teu@gmail.com
  Outros: -Servidor smtp.exemplo.com -Porta 587      -Remover (desliga o e-mail)
#>
param(
    [string]$Utilizador,
    [string]$Servidor = "smtp.gmail.com",
    [int]$Porta = 587,
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
    if ($LASTEXITCODE -ne 0) { throw "O servidor devolveu um erro (codigo $LASTEXITCODE)." }
}

if ($Remover) {
    Invocar-Remoto "cd $Pasta && sed -i -e '/^EMAIL_HOST=/d' -e '/^EMAIL_PORT=/d' -e '/^EMAIL_HOST_USER=/d' -e '/^EMAIL_HOST_PASSWORD=/d' -e '/^DEFAULT_FROM_EMAIL=/d' .env && docker compose up -d backend"
    Write-Host "E-mail desligado." -ForegroundColor Yellow
    return
}

if (-not $Utilizador) { $Utilizador = Read-Host "Endereco de e-mail que envia os avisos (ex.: o.teu@gmail.com)" }
if ($Utilizador -notmatch '^[^@\s]+@[^@\s]+\.[^@\s]+$') { throw "Endereco de e-mail invalido. Nada foi alterado." }
$segura = Read-Host "Cola a palavra-passe de aplicacao (nao aparece no ecra)" -AsSecureString
$ponteiro = [Runtime.InteropServices.Marshal]::SecureStringToBSTR($segura)
try { $senha = ([Runtime.InteropServices.Marshal]::PtrToStringBSTR($ponteiro)).Replace(" ", "").Trim() }
finally { [Runtime.InteropServices.Marshal]::ZeroFreeBSTR($ponteiro) }
if ($senha.Length -lt 8 -or $senha -match '[\s''"\\$`]') { throw "Palavra-passe invalida (muito curta ou com caracteres nao suportados). Nada foi alterado." }

# utilizador e palavra-passe seguem em duas linhas pela entrada padrao do SSH: nao ficam no historico nem na lista de processos
$remoto = "read -r U && read -r P && cd $Pasta && touch .env && sed -i -e '/^EMAIL_HOST=/d' -e '/^EMAIL_PORT=/d' -e '/^EMAIL_HOST_USER=/d' -e '/^EMAIL_HOST_PASSWORD=/d' -e '/^DEFAULT_FROM_EMAIL=/d' .env && printf 'EMAIL_HOST=${Servidor}\nEMAIL_PORT=${Porta}\nEMAIL_HOST_USER=%s\nEMAIL_HOST_PASSWORD=%s\nDEFAULT_FROM_EMAIL=SIGE <%s>\n' ""`$U"" ""`$P"" ""`$U"" >> .env && chmod 600 .env && docker compose up -d backend"
Invocar-Remoto $remoto ("$Utilizador`n$senha")
$senha = $null

Start-Sleep -Seconds 15
Write-Host "A enviar e-mail de teste para $Utilizador ..." -ForegroundColor Cyan
Invocar-Remoto "docker exec sige_backend python manage.py shell -c ""from django.core.mail import send_mail; from django.conf import settings as s; print('enviados:', send_mail('[SIGE] Teste de e-mail', 'Os avisos das provas Anti-IA ja chegam a este endereco.', None, [s.EMAIL_HOST_USER]))"""
Write-Host "Pronto. Verifica a caixa de entrada (e o spam) de $Utilizador." -ForegroundColor Green