#!/usr/bin/env pwsh
<#
.SYNOPSIS
  Build, package e deploy do SPFx para o SharePoint App Catalog.

.USAGE
  ./deploy-spfx.ps1
  ./deploy-spfx.ps1 -SiteUrl "https://seutenante.sharepoint.com/sites/appcatalog"
#>

param(
  [string]$SiteUrl = ""
)

$ErrorActionPreference = "Stop"
$ConfigFile = Join-Path $PSScriptRoot ".deploy-config.json"
$SppkgPath  = Join-Path $PSScriptRoot "spfx/sharepoint/solution/monitor-nfse.sppkg"

# ── 1. Carrega / pede URL do App Catalog ──────────────────────────────────────
$ClientId = ""
if (Test-Path $ConfigFile) {
  $config   = Get-Content $ConfigFile | ConvertFrom-Json
  if (-not $SiteUrl) { $SiteUrl  = $config.appcatalog_url }
  $ClientId = $config.client_id
}

if (-not $ClientId) {
  Write-Host ""
  Write-Host "Client ID nao encontrado. Execute primeiro: pwsh ./setup-pnp-consent.ps1" -ForegroundColor Red
  exit 1
}

if (-not $SiteUrl) {
  Write-Host ""
  Write-Host "Informe a URL RAIZ do tenant SharePoint (nao a URL de uma pagina)." -ForegroundColor Cyan
  Write-Host "Exemplo: https://grupoinvestcorp.sharepoint.com" -ForegroundColor DarkGray
  Write-Host ""
  $SiteUrl = Read-Host "URL do tenant"
  $SiteUrl = $SiteUrl.TrimEnd("/")
  # Remove qualquer path extra, deixa so a raiz
  $uri = [System.Uri]$SiteUrl
  $SiteUrl = "$($uri.Scheme)://$($uri.Host)"
  @{ appcatalog_url = $SiteUrl } | ConvertTo-Json | Set-Content $ConfigFile
  Write-Host "URL salva em .deploy-config.json: $SiteUrl" -ForegroundColor Green
}

# ── 2. Verifica PnP.PowerShell ────────────────────────────────────────────────
if (-not (Get-Module -ListAvailable -Name PnP.PowerShell)) {
  Write-Host ""
  Write-Host "Instalando PnP.PowerShell..." -ForegroundColor Yellow
  Install-Module PnP.PowerShell -Scope CurrentUser -Force -AllowClobber
}

# ── 3. Build + Package ────────────────────────────────────────────────────────
Write-Host ""
Write-Host "=== Build + Package SPFx ===" -ForegroundColor Cyan
Push-Location (Join-Path $PSScriptRoot "spfx")
try {
  npm run ship
  if ($LASTEXITCODE -ne 0) { throw "npm run ship falhou (exit $LASTEXITCODE)" }
} finally {
  Pop-Location
}

if (-not (Test-Path $SppkgPath)) {
  throw "Arquivo .sppkg nao encontrado: $SppkgPath"
}
Write-Host "Package gerado: $SppkgPath" -ForegroundColor Green

# ── 4. Conecta ao SharePoint ──────────────────────────────────────────────────
Write-Host ""
Write-Host "=== Deploy para o App Catalog ===" -ForegroundColor Cyan
$AppCatalogUrl = "https://grupoinvestcorp.sharepoint.com/sites/appcatalog"
Write-Host "Conectando em: $AppCatalogUrl" -ForegroundColor DarkGray
Write-Host "Abra https://microsoft.com/devicelogin e insira o codigo que aparecer:" -ForegroundColor Yellow
Write-Host ""

Connect-PnPOnline -Url $AppCatalogUrl -DeviceLogin -ClientId $ClientId -Tenant "grupoinvestcorp.onmicrosoft.com"
Write-Host "Conectado!" -ForegroundColor Green

# ── 5. Upload via REST + Deploy ───────────────────────────────────────────────
$fileBytes   = [System.IO.File]::ReadAllBytes($SppkgPath)
$fileName    = "monitor-nfse.sppkg"
$uploadUrl   = "$AppCatalogUrl/_api/web/GetFolderByServerRelativeUrl('AppCatalog')/Files/Add(url='$fileName',overwrite=true)"
$token       = Get-PnPAccessToken
$digest      = (Invoke-PnPSPRestMethod -Method Post -Url "/_api/contextinfo" | Select-Object -ExpandProperty FormDigestValue)
$headers     = @{
    "Authorization"  = "Bearer $token"
    "Accept"         = "application/json;odata=verbose"
    "X-RequestDigest" = $digest
}

Write-Host "Fazendo upload de monitor-nfse.sppkg..." -ForegroundColor Yellow
$resp = Invoke-RestMethod -Uri $uploadUrl -Method Post -Headers $headers -Body $fileBytes -ContentType "application/octet-stream"

$appId     = $resp.d.UniqueId
$deployUrl = "$AppCatalogUrl/_api/web/tenantappcatalog/AvailableApps/GetById('$appId')/Deploy"
Invoke-RestMethod -Uri $deployUrl -Method Post -Headers $headers -ContentType "application/json" | Out-Null

Write-Host ""
Write-Host "Deploy concluido!" -ForegroundColor Green
Write-Host ""
Write-Host "Aguarde ~1 minuto e atualize a pagina do portal no SharePoint." -ForegroundColor Cyan

Disconnect-PnPOnline
