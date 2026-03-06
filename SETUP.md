# Setup — Monitor NFS-e

## Visão geral

```
GitHub Actions (cron horário)
├── Consulta SEFAZ ADN → notas novas por NSU (incremental)
├── Compara com Sienge API
├── Grava resultado em SharePoint via SharePoint Add-in (sem Azure AD)
│   ├── Lista "NFS-e Pendentes"  → lida pelo web part SPFx
│   └── Lista "NFS-e Config"     → estado interno (NSU, última verificação)
└── Notifica canal Teams

SharePoint (autenticação M365 nativa)
└── Web Part SPFx (.sppkg) — dashboard para usuários
    └── Lê lista "NFS-e Pendentes" com contexto do usuário logado
```

---

## 1. Criar listas no SharePoint

Acesse o site SharePoint e crie **duas listas**:

### Lista: `NFS-e Pendentes`

| Coluna          | Tipo              | Observação                    |
|-----------------|-------------------|-------------------------------|
| Title           | Texto (padrão)    | Número da NFS-e               |
| Obra            | Texto linha única  |                               |
| NumeroNFSe      | Texto linha única  |                               |
| DataEmissao     | Texto linha única  | formato YYYY-MM-DD            |
| Prestador       | Texto linha única  |                               |
| CNPJPrestador   | Texto linha única  |                               |
| Valor           | Número (2 dec.)   |                               |
| ChaveAcesso     | Texto linha única  |                               |
| Status          | Opção             | Opções: `Pendente`, `Lançada` |

### Lista: `NFS-e Config`

| Coluna              | Tipo              | Observação                |
|---------------------|-------------------|---------------------------|
| Title               | Texto (padrão)    | Chave da obra (ex: `max`) |
| UltimoNSU           | Número (inteiro)  |                           |
| UltimaVerificacao   | Texto linha única  | ISO 8601 UTC              |

---

## 2. Registrar SharePoint Add-in (sem Azure AD)

Este passo cria as credenciais que o GitHub Actions usa para escrever nas listas.
Feito direto no SharePoint — não requer acesso ao portal Azure.

### 2a. Gerar Client ID e Secret

Acesse (substitua pelo seu site):
```
https://empresa.sharepoint.com/sites/financeiro/_layouts/15/AppRegNew.aspx
```

Preencha:
- **Client Id** → clique em "Gerar"
- **Client Secret** → clique em "Gerar"
- **Title** → `monitor-nfse`
- **App Domain** → `github.com`
- **Redirect URI** → `https://github.com`

Clique em **Criar** e anote o Client ID e Client Secret gerados.

### 2b. Conceder permissões

Acesse:
```
https://empresa.sharepoint.com/sites/financeiro/_layouts/15/AppInv.aspx
```

- **App Id** → cole o Client ID do passo anterior → clique em **Lookup**
- Em **Permission Request XML**, cole:

```xml
<AppPermissionRequests AllowAppOnlyPolicy="true">
  <AppPermissionRequest Scope="http://sharepoint/content/sitecollection/web/list"
                        Right="Write" />
</AppPermissionRequests>
```

Clique em **Criar** → **Confiar**

---

## 3. Implantar o Web Part SPFx

### 3a. Build do pacote

```bash
cd spfx
npm install
npm run ship
# Gera: sharepoint/solution/monitor-nfse.sppkg
```

### 3b. Upload para o App Catalog

1. Acesse o **App Catalog** do SharePoint (admin)
2. Arraste o `.sppkg` para a biblioteca "Apps for SharePoint"
3. Marque **"Make this solution available to all sites"** se quiser implantação tenant-wide
4. Clique em **Deploy**

### 3c. Adicionar o web part à página

1. Edite a página desejada no SharePoint
2. Adicione um novo web part → pesquise **"Monitor NFS-e Pendentes"**
3. Configure no painel lateral:
   - **Nome da lista**: `NFS-e Pendentes` *(padrão)*
   - **Exibir lançadas**: ative apenas para auditoria

---

## 4. GitHub Secrets

Vá em: **Repositório → Settings → Secrets and variables → Actions**

| Secret | Valor |
|--------|-------|
| `CERT_MAX_B64` | Base64 do .pfx do Pulse (ver abaixo) |
| `CERT_MAX_SENHA` | Senha do certificado |
| `SIENGE_USER` | `trust-marcelo` |
| `SIENGE_PASS` | Senha do Sienge |
| `SHAREPOINT_SITE_URL` | Ex: `https://empresa.sharepoint.com/sites/financeiro` |
| `SP_ADDIN_CLIENT_ID` | Client ID gerado no passo 2a |
| `SP_ADDIN_CLIENT_SECRET` | Client Secret gerado no passo 2a |
| `TEAMS_WEBHOOK_URL` | URL do Incoming Webhook do canal Teams |

**Converter .pfx para Base64 — PowerShell:**
```powershell
[Convert]::ToBase64String([IO.File]::ReadAllBytes("C:\caminho\cert.pfx")) | clip
```

---

## 5. Criar repositório e subir

```bash
cd monitor-nfse
git init
git add .
git commit -m "feat: monitor NFS-e inicial — obra MAX"
gh repo create invcp/monitor-nfse --public --push --source .
```

---

## 6. Testar o backend localmente

```bash
pip install -r requirements.txt
cp "certificados/Pulse/cert.pfx" /tmp/cert_max.pfx

export CERT_MAX_PATH="/tmp/cert_max.pfx"
export CERT_MAX_SENHA="..."
export SIENGE_USER="trust-marcelo"
export SIENGE_PASS="..."
export SHAREPOINT_SITE_URL="https://empresa.sharepoint.com/sites/..."
export SP_ADDIN_CLIENT_ID="..."
export SP_ADDIN_CLIENT_SECRET="..."
export TEAMS_WEBHOOK_URL="..."

python -m monitor.main
```

---

## 7. Adicionar nova obra

1. Adicione em `obras.json`
2. Adicione os secrets `CERT_NOVAOBRA_B64` e `CERT_NOVAOBRA_SENHA` no GitHub
3. Adicione as linhas em `.github/workflows/monitor.yml`
4. Adicione o nome legível em `spfx/src/.../NfsePendentes.tsx` no objeto `NOMES_OBRA`

---

## Segurança — resumo

| O que | Onde fica | Quem acessa |
|-------|-----------|-------------|
| Código | GitHub público | Qualquer um — sem dados sensíveis |
| Certificados .pfx | GitHub Secrets | Apenas o Actions (criptografado) |
| Credenciais API | GitHub Secrets | Apenas o Actions (criptografado) |
| Dados das notas | SharePoint | Apenas usuários autenticados no M365 |
| Dashboard | SharePoint Web Part | Apenas usuários do tenant da empresa |
