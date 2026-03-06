"""
Cliente SharePoint REST API — autenticação via SharePoint Add-in.

Não usa Azure AD App Registration.
O registro é feito diretamente no SharePoint via AppRegNew.aspx (ver SETUP.md).

Gerencia duas listas:
  - "NFS-e Pendentes" : notas não lançadas no Sienge
  - "NFS-e Config"    : estado por obra (NSU, última verificação)
"""

import re
import requests


class SharePointClient:
    def __init__(self, site_url: str, client_id: str, client_secret: str):
        """
        site_url:      URL do site, ex: https://empresa.sharepoint.com/sites/financeiro
        client_id:     gerado em /_layouts/15/AppRegNew.aspx
        client_secret: gerado em /_layouts/15/AppRegNew.aspx
        """
        self._site_url     = site_url.rstrip("/")
        self._client_id    = client_id
        self._client_secret = client_secret
        self._token        = self._obter_token()

    # ──────────────────────────────────────────
    # Pendentes
    # ──────────────────────────────────────────

    def carregar_pendentes(self, obra_key: str) -> list[dict]:
        """Retorna itens com Status='Pendente' da obra."""
        filtro = f"Obra eq '{obra_key}' and Status eq 'Pendente'"
        items  = self._listar_items("NFS-e Pendentes", filtro=filtro)
        return [self._item_para_nota(i) for i in items]

    def adicionar_pendentes(self, obra_key: str, notas: list[dict]) -> None:
        """Cria novos itens na lista para notas pendentes novas."""
        for nota in notas:
            try:
                valor_num = float(str(nota.get("valor", "0")).replace(",", "."))
            except (ValueError, TypeError):
                valor_num = 0.0

            self._criar_item("NFS-e Pendentes", {
                "Title":         nota.get("numero", ""),
                "Obra":          obra_key,
                "NumeroNFSe":    nota.get("numero", ""),
                "DataEmissao":   nota.get("data_emissao", ""),
                "Prestador":     (nota.get("nome_prest") or "")[:255],
                "CNPJPrestador": nota.get("cnpj_prest", ""),
                "Valor":         valor_num,
                "ChaveAcesso":   nota.get("chave", ""),
                "Status":        "Pendente",
            })

    def marcar_lancadas(self, chaves_lancadas: set[str]) -> None:
        """Atualiza para 'Lançada' os itens cujas chaves estão no set."""
        if not chaves_lancadas:
            return
        items = self._listar_items(
            "NFS-e Pendentes",
            filtro="Status eq 'Pendente'",
            selecionar="Id,ChaveAcesso",
        )
        for item in items:
            if item.get("ChaveAcesso", "") in chaves_lancadas:
                self._atualizar_item("NFS-e Pendentes", item["Id"], {"Status": "Lançada"})

    # ──────────────────────────────────────────
    # Config / NSU
    # ──────────────────────────────────────────

    def carregar_nsu(self, obra_key: str) -> int:
        items = self._listar_items(
            "NFS-e Config",
            filtro=f"Title eq '{obra_key}'",
            selecionar="Id,UltimoNSU",
        )
        if items:
            try:
                return int(items[0].get("UltimoNSU", 0))
            except (ValueError, TypeError):
                return 0
        return 0

    def salvar_nsu(self, obra_key: str, nsu: int, ultima_verificacao: str) -> None:
        items = self._listar_items(
            "NFS-e Config",
            filtro=f"Title eq '{obra_key}'",
            selecionar="Id",
        )
        campos = {"UltimoNSU": nsu, "UltimaVerificacao": ultima_verificacao}
        if items:
            self._atualizar_item("NFS-e Config", items[0]["Id"], campos)
        else:
            self._criar_item("NFS-e Config", {"Title": obra_key, **campos})

    def carregar_chaves_conhecidas(self, obra_key: str) -> set[str]:
        """Retorna chaves de TODOS os itens da obra (pendentes + lançadas)."""
        items = self._listar_items(
            "NFS-e Pendentes",
            filtro=f"Obra eq '{obra_key}'",
            selecionar="Id,ChaveAcesso",
        )
        return {i.get("ChaveAcesso", "") for i in items}

    # ──────────────────────────────────────────
    # Internos — SharePoint REST API
    # ──────────────────────────────────────────

    def _obter_token(self) -> str:
        """
        Obtém token via SharePoint Add-in (ACS).
        Documentação: https://learn.microsoft.com/en-us/sharepoint/dev/solution-guidance/security-apponly-azureacs
        """
        # Extrai hostname e realm do site
        hostname = self._site_url.split("/")[2]            # ex: empresa.sharepoint.com
        realm    = self._obter_realm(hostname)

        token_url = f"https://accounts.accesscontrol.windows.net/{realm}/tokens/OAuth/2"

        # client_id no formato "id@realm"
        client_id_full = f"{self._client_id}@{realm}"
        # resource no formato "id-do-sharepoint/hostname@realm"
        resource = f"00000003-0000-0ff1-ce00-000000000000/{hostname}@{realm}"

        resp = requests.post(token_url, data={
            "grant_type":    "client_credentials",
            "client_id":     client_id_full,
            "client_secret": self._client_secret,
            "resource":      resource,
        }, timeout=15)
        resp.raise_for_status()
        return resp.json()["access_token"]

    def _obter_realm(self, hostname: str) -> str:
        """Descobre o Realm (tenant ID) via endpoint de autenticação do SharePoint."""
        resp = requests.get(
            f"https://{hostname}/_vti_bin/client.svc",
            headers={"Authorization": "Bearer"},
            timeout=10,
        )
        # WWW-Authenticate: Bearer realm="xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx",...
        auth_header = resp.headers.get("WWW-Authenticate", "")
        match = re.search(r'realm="([^"]+)"', auth_header)
        if not match:
            raise ValueError(f"Não foi possível determinar o Realm do SharePoint: {auth_header}")
        return match.group(1)

    def _headers(self) -> dict:
        return {
            "Authorization": f"Bearer {self._token}",
            "Accept":        "application/json;odata=nometadata",
            "Content-Type":  "application/json;odata=nometadata",
        }

    def _api(self, lista: str) -> str:
        return f"{self._site_url}/_api/web/lists/getbytitle('{lista}')/items"

    def _listar_items(self, lista: str, filtro: str = "", selecionar: str = "") -> list[dict]:
        params = {"$top": "5000"}
        if filtro:
            params["$filter"] = filtro
        if selecionar:
            params["$select"] = selecionar

        items = []
        url   = self._api(lista)
        while url:
            r = requests.get(url, headers=self._headers(), params=params, timeout=30)
            r.raise_for_status()
            data  = r.json()
            items.extend(data.get("value", []))
            url    = data.get("odata.nextLink")
            params = {}
        return items

    def _criar_item(self, lista: str, campos: dict) -> dict:
        r = requests.post(
            self._api(lista),
            headers=self._headers(),
            json=campos,
            timeout=15,
        )
        r.raise_for_status()
        return r.json()

    def _atualizar_item(self, lista: str, item_id: int, campos: dict) -> None:
        headers = {
            **self._headers(),
            "IF-MATCH":      "*",
            "X-HTTP-Method": "MERGE",
        }
        r = requests.post(
            f"{self._api(lista)}({item_id})",
            headers=headers,
            json=campos,
            timeout=15,
        )
        r.raise_for_status()

    @staticmethod
    def _item_para_nota(item: dict) -> dict:
        return {
            "_sp_id":       item.get("Id"),
            "chave":        item.get("ChaveAcesso", ""),
            "numero":       item.get("NumeroNFSe", ""),
            "data_emissao": item.get("DataEmissao", ""),
            "cnpj_prest":   item.get("CNPJPrestador", ""),
            "nome_prest":   item.get("Prestador", ""),
            "valor":        str(item.get("Valor", "")),
        }
