# Cria as listas do SharePoint para o monitor de NFS-e
# Requer: Install-Module PnP.PowerShell (se nao tiver)
#
# Uso: .\criar_listas.ps1

Import-Module PnP.PowerShell -ErrorAction Stop

$siteUrl = "https://grupoinvestcorp.sharepoint.com/sites/notasfiscais"

Write-Host "Conectando ao SharePoint..." -ForegroundColor Cyan
Connect-PnPOnline -Url $siteUrl -Interactive

# ─────────────────────────────────────────────
# Lista: NFS-e Pendentes
# ─────────────────────────────────────────────
$listaPendentes = "NFS-e Pendentes"

if (-not (Get-PnPList -Identity $listaPendentes -ErrorAction SilentlyContinue)) {
    Write-Host "Criando lista '$listaPendentes'..." -ForegroundColor Yellow
    New-PnPList -Title $listaPendentes -Template GenericList -EnableVersioning $false | Out-Null

    Add-PnPField -List $listaPendentes -DisplayName "Obra"          -InternalName "Obra"          -Type Text   -AddToDefaultView | Out-Null
    Add-PnPField -List $listaPendentes -DisplayName "NumeroNFSe"    -InternalName "NumeroNFSe"    -Type Text   -AddToDefaultView | Out-Null
    Add-PnPField -List $listaPendentes -DisplayName "DataEmissao"   -InternalName "DataEmissao"   -Type Text   -AddToDefaultView | Out-Null
    Add-PnPField -List $listaPendentes -DisplayName "Prestador"     -InternalName "Prestador"     -Type Text   -AddToDefaultView | Out-Null
    Add-PnPField -List $listaPendentes -DisplayName "CNPJPrestador" -InternalName "CNPJPrestador" -Type Text   -AddToDefaultView | Out-Null
    Add-PnPField -List $listaPendentes -DisplayName "Valor"         -InternalName "Valor"         -Type Number -AddToDefaultView | Out-Null
    Add-PnPField -List $listaPendentes -DisplayName "ChaveAcesso"   -InternalName "ChaveAcesso"   -Type Text   -AddToDefaultView | Out-Null

    # Campo Status com opções
    $xmlStatus = '<Field Type="Choice" DisplayName="Status" Name="Status" Required="FALSE">
      <CHOICES>
        <CHOICE>Pendente</CHOICE>
        <CHOICE>Lancada</CHOICE>
      </CHOICES>
      <Default>Pendente</Default>
    </Field>'
    Add-PnPFieldFromXml -List $listaPendentes -FieldXml $xmlStatus | Out-Null

    Write-Host "Lista '$listaPendentes' criada com sucesso." -ForegroundColor Green
} else {
    Write-Host "Lista '$listaPendentes' ja existe, pulando." -ForegroundColor Gray
}

# ─────────────────────────────────────────────
# Lista: NFS-e Config
# ─────────────────────────────────────────────
$listaConfig = "NFS-e Config"

if (-not (Get-PnPList -Identity $listaConfig -ErrorAction SilentlyContinue)) {
    Write-Host "Criando lista '$listaConfig'..." -ForegroundColor Yellow
    New-PnPList -Title $listaConfig -Template GenericList -EnableVersioning $false | Out-Null

    Add-PnPField -List $listaConfig -DisplayName "UltimoNSU"          -InternalName "UltimoNSU"          -Type Number -AddToDefaultView | Out-Null
    Add-PnPField -List $listaConfig -DisplayName "UltimaVerificacao"  -InternalName "UltimaVerificacao"  -Type Text   -AddToDefaultView | Out-Null

    # Item inicial para a obra "max"
    Add-PnPListItem -List $listaConfig -Values @{
        Title              = "max"
        UltimoNSU          = 0
        UltimaVerificacao  = ""
    } | Out-Null

    Write-Host "Lista '$listaConfig' criada com sucesso." -ForegroundColor Green
} else {
    Write-Host "Lista '$listaConfig' ja existe, pulando." -ForegroundColor Gray
}

Write-Host ""
Write-Host "Concluido! Acesse o site para confirmar:" -ForegroundColor Cyan
Write-Host "$siteUrl/_layouts/15/viewlsts.aspx" -ForegroundColor White
