#!/usr/bin/env pwsh
<#
.SYNOPSIS
  Registra um app no Entra ID para autenticacao do PnP PowerShell.
  Execute UMA VEZ como admin do tenant.
#>

Import-Module PnP.PowerShell -ErrorAction Stop

$ConfigFile = Join-Path $PSScriptRoot ".deploy-config.json"
$Tenant     = "grupoinvestcorp.onmicrosoft.com"

Write-Host ""
Write-Host "=== Registrando app no Entra ID ===" -ForegroundColor Cyan
Write-Host "Sera aberto o browser para autenticar como admin." -ForegroundColor Yellow
Write-Host ""

$app = Register-PnPEntraIDAppForInteractiveLogin `
    -ApplicationName "PnP SPFx Deploy" `
    -Tenant $Tenant `
    -SharePointDelegatePermissions "AllSites.FullControl" `
    -DeviceLogin

if (-not $app) {
    Write-Host "Falha ao registrar app." -ForegroundColor Red
    exit 1
}

$clientId = $app.'AzureAppId/ClientId'
Write-Host ""
Write-Host "App registrado com sucesso!" -ForegroundColor Green
Write-Host "  Client ID: $clientId" -ForegroundColor Cyan

# Salva client ID no config
$config = @{ appcatalog_url = "https://grupoinvestcorp.sharepoint.com"; client_id = $clientId }
$config | ConvertTo-Json | Set-Content $ConfigFile
Write-Host "  Salvo em .deploy-config.json" -ForegroundColor DarkGray
Write-Host ""
Write-Host "Agora execute: pwsh ./deploy-spfx.ps1" -ForegroundColor Green
