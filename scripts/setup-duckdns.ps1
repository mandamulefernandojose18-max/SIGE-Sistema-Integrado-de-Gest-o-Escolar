<#
.SYNOPSIS
    SIGE - Configurador Automatico de Dominio DuckDNS + HTTPS Let's Encrypt na VM
.DESCRIPTION
    Atualiza o IP da VM (139.84.226.46) no DuckDNS, emite certificado SSL Let's Encrypt oficial
    para https://<subdominio>.duckdns.org e atualiza os atalhos 'sige'.
#>
param(
    [Parameter(Mandatory=$true)]
    [string]$Token,

    [Parameter(Mandatory=$false)]
    [string]$Subdomain = "sigesaas",

    [Parameter(Mandatory=$false)]
    [string]$VmIp = "139.84.226.46",

    [Parameter(Mandatory=$false)]
    [string]$VmUser = "root",

    [Parameter(Mandatory=$false)]
    [string]$KeyPath = "$env:USERPROFILE\.ssh\sige_vm_key"
)

$ErrorActionPreference = "Stop"
$Subdomain = $Subdomain -replace '\.duckdns\.org$', ''
$FullDomain = "${Subdomain}.duckdns.org"

Write-Host "================================================================" -ForegroundColor Cyan
Write-Host "   SIGE - CONFIGURACAO DUCKDNS + HTTPS ($FullDomain)            " -ForegroundColor Cyan
Write-Host "================================================================" -ForegroundColor Cyan

# 1. Atualizar IP no DuckDNS via API
Write-Host "[1/4] Apontando $FullDomain para a VM ($VmIp) no DuckDNS..." -ForegroundColor Blue
$duckUrl = "https://www.duckdns.org/update?domains=${Subdomain}&token=${Token}&ip=${VmIp}"
$response = Invoke-RestMethod -Uri $duckUrl -Method Get
if ($response.Trim() -ne "OK") {
    Write-Host "  ERRO: DuckDNS retornou '$response'. Verifique se o subdominio '$Subdomain' foi criado no painel do DuckDNS e se o Token esta correto." -ForegroundColor Red
    exit 1
}
Write-Host "  OK: Dominio $FullDomain apontado para $VmIp com sucesso!" -ForegroundColor Green

# 2. Emitir Certificado SSL Let's Encrypt na VM e configurar cron de renovacao DuckDNS
Write-Host "[2/4] Emitindo certificado SSL Let's Encrypt na VM para $FullDomain..." -ForegroundColor Blue
$remoteScript = @"
set -e
# Configurar cron para manter o IP atualizado no DuckDNS
mkdir -p /var/www/sige/duckdns
echo "curl -sk 'https://www.duckdns.org/update?domains=${Subdomain}&token=${Token}&ip=${VmIp}' >/dev/null 2>&1" > /var/www/sige/duckdns/duck.sh
chmod 700 /var/www/sige/duckdns/duck.sh

# Emitir certificado Let's Encrypt incluindo o dominio DuckDNS
~/.acme.sh/acme.sh --issue --server letsencrypt -d ${FullDomain} -d sigesass.duckdns.org -d sige.8b54e22e.sslip.io -d sige.139-84-226-46.sslip.io -w /var/www/sige/frontend --force
~/.acme.sh/acme.sh --install-cert -d ${FullDomain} --key-file /var/www/sige/certs/privkey.pem --fullchain-file /var/www/sige/certs/fullchain.pem

# Atualizar Nginx e recarregar
sed -i 's/sigesass\.duckdns\.org/${FullDomain}/g' /var/www/sige/frontend/nginx.conf /var/www/sige/frontend/index.html || true
docker exec sige_frontend nginx -s reload
"@

ssh -i $KeyPath -o StrictHostKeyChecking=no "${VmUser}@${VmIp}" $remoteScript
Write-Host "  OK: Certificado HTTPS Let's Encrypt ativo em https://${FullDomain}/ !" -ForegroundColor Green

# 3. Atualizar Atalhos 'sige'
Write-Host "[3/4] Atualizando atalhos 'sige' para https://${FullDomain}/ ..." -ForegroundColor Blue
$webUrl = "https://${FullDomain}/"
$shortcutLines = @(
    "[InternetShortcut]",
    "URL=$webUrl",
    "IconIndex=0"
)
Set-Content -Path "d:\SIGE\sige.url" -Value $shortcutLines -Encoding ASCII
Set-Content -Path "$env:USERPROFILE\Desktop\sige.url" -Value $shortcutLines -Encoding ASCII -ErrorAction SilentlyContinue
Set-Content -Path "d:\SIGE\sige.cmd" -Value "@start $webUrl" -Encoding ASCII

# 4. Abrir navegador
Write-Host "[4/4] Abrindo https://${FullDomain}/ no navegador..." -ForegroundColor Green
Start-Process $webUrl
