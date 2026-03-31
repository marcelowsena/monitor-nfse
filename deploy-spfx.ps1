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
if (-not $SiteUrl) {
  if (Test-Path $ConfigFile) {
    $config  = Get-Content $ConfigFile | ConvertFrom-Json
    $SiteUrl = $config.appcatalog_url
  }
}

if (-not $SiteUrl) {
  Write-Host ""
  Write-Host "Informe a URL do App Catalog do SharePoint." -ForegroundColor Cyan
  Write-Host "Exemplo: https://seutenante.sharepoint.com/sites/appcatalog" -ForegroundColor DarkGray
  Write-Host "         https://seutenante.sharepoint.com  (tenant app catalog)" -ForegroundColor DarkGray
  Write-Host ""
  $SiteUrl = Read-Host "URL do App Catalog"
  $SiteUrl = $SiteUrl.TrimEnd("/")
  @{ appcatalog_url = $SiteUrl } | ConvertTo-Json | Set-Content $ConfigFile
  Write-Host "URL salva em .deploy-config.json" -ForegroundColor Green
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
Write-Host "Conectando em: $SiteUrl" -ForegroundColor DarkGray
Write-Host "(sera aberta uma janela de login)" -ForegroundColor DarkGray
Write-Host ""

Connect-PnPOnline -Url $SiteUrl -Interactive

# ── 5. Upload + Deploy ────────────────────────────────────────────────────────
Write-Host "Fazendo upload de monitor-nfse.sppkg..." -ForegroundColor Yellow
$app = Add-PnPApp -Path $SppkgPath -Scope Tenant -Overwrite -Publish

Write-Host ""
Write-Host "Deploy concluido!" -ForegroundColor Green
Write-Host "  App ID : $($app.Id)" -ForegroundColor DarkGray
Write-Host "  Versao : $($app.AppCatalogVersion)" -ForegroundColor DarkGray
Write-Host ""
Write-Host "Aguarde ~1 minuto e atualize a pagina do portal no SharePoint." -ForegroundColor Cyan

Disconnect-PnPOnline
