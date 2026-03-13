"""
Cliente para o Cloudflare Worker KV — substitui sharepoint.py.

O Worker expõe:
  GET  /api/estado/:obra?token=...  → {ultimo_nsu, ultima_verificacao}
  GET  /api/pendentes?token=...     → [{obra, chave, numero, ...}]
  POST /api/sync  Bearer token      → {obra, pendentes, ultimo_nsu, ultima_verificacao}
"""

import requests


class CloudflareClient:
    def __init__(self, worker_url: str, api_token: str):
        self._url   = worker_url.rstrip("/")
        self._token = api_token

    # ── Leitura ────────────────────────────────────────────────────

    def carregar_estado(self, obra_key: str) -> dict:
        """Retorna {ultimo_nsu: int, ultima_verificacao: str}."""
        r = requests.get(
            f"{self._url}/api/estado/{obra_key}",
            params={"token": self._token},
            timeout=30,
        )
        r.raise_for_status()
        return r.json()

    def _carregar_obras_raw(self) -> list:
        r = requests.get(
            f"{self._url}/api/pendentes",
            params={"token": self._token},
            timeout=30,
        )
        r.raise_for_status()
        return r.json()

    def carregar_pendentes(self, obra_key: str) -> list:
        """Retorna lista de notas pendentes desta obra."""
        for item in self._carregar_obras_raw():
            if item.get("key") == obra_key:
                return item.get("pendentes", [])
        return []

    def carregar_lancadas(self, obra_key: str) -> list:
        """Retorna lista de notas já lançadas no Sienge desta obra."""
        for item in self._carregar_obras_raw():
            if item.get("key") == obra_key:
                return item.get("lancadas", [])
        return []

    def carregar_pendentes_nfe(self, obra_key: str) -> list:
        """Retorna lista de NF-e pendentes desta obra."""
        for item in self._carregar_obras_raw():
            if item.get("key") == obra_key:
                return item.get("pendentes_nfe", [])
        return []

    def carregar_lancadas_nfe(self, obra_key: str) -> list:
        """Retorna lista de NF-e já lançadas no Sienge desta obra."""
        for item in self._carregar_obras_raw():
            if item.get("key") == obra_key:
                return item.get("lancadas_nfe", [])
        return []

    def pdf_existe(self, chave: str) -> bool:
        """Verifica se o PDF já está armazenado no Worker (HEAD request)."""
        try:
            r = requests.get(
                f"{self._url}/api/pdf/{chave}",
                params={"token": self._token},
                timeout=10,
                stream=True,
            )
            r.close()
            return r.status_code == 200
        except Exception:
            return False

    # ── Escrita ────────────────────────────────────────────────────

    def salvar_pdf(self, chave: str, pdf_bytes: bytes) -> None:
        """Envia PDF ao Worker para armazenamento no KV."""
        r = requests.post(
            f"{self._url}/api/pdf/{chave}",
            data=pdf_bytes,
            headers={
                "Authorization": f"Bearer {self._token}",
                "Content-Type": "application/pdf",
            },
            timeout=60,
        )
        r.raise_for_status()

    def sincronizar(
        self,
        obra_key: str,
        pendentes: list,
        ultimo_nsu: int,
        ultima_verificacao: str,
        lancadas: list | None = None,
        pendentes_nfe: list | None = None,
        lancadas_nfe: list | None = None,
        ultimo_nsu_nfe: int | None = None,
    ) -> None:
        """Atualiza pendentes + lancadas + estado no KV via POST /api/sync."""
        payload = {
            "obra":               obra_key,
            "pendentes":          pendentes,
            "ultimo_nsu":         ultimo_nsu,
            "ultima_verificacao": ultima_verificacao,
        }
        if lancadas is not None:
            payload["lancadas"] = lancadas
        if pendentes_nfe is not None:
            payload["pendentes_nfe"] = pendentes_nfe
        if lancadas_nfe is not None:
            payload["lancadas_nfe"] = lancadas_nfe
        if ultimo_nsu_nfe is not None:
            payload["ultimo_nsu_nfe"] = ultimo_nsu_nfe
        r = requests.post(
            f"{self._url}/api/sync",
            json=payload,
            headers={"Authorization": f"Bearer {self._token}"},
            timeout=30,
        )
        if not r.ok:
            print(f"    [SYNC ERROR] status={r.status_code} body={r.text[:500]}")
        r.raise_for_status()
