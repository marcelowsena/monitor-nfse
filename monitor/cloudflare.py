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

    def carregar_pendentes(self, obra_key: str) -> list:
        """Retorna lista de notas pendentes desta obra."""
        r = requests.get(
            f"{self._url}/api/pendentes",
            params={"token": self._token},
            timeout=30,
        )
        r.raise_for_status()
        todas = r.json()
        # A resposta é [{key, nome, pendentes, ...}] — filtra pela obra
        for item in todas:
            if item.get("key") == obra_key:
                return item.get("pendentes", [])
        return []

    # ── Escrita ────────────────────────────────────────────────────

    def sincronizar(
        self,
        obra_key: str,
        pendentes: list,
        ultimo_nsu: int,
        ultima_verificacao: str,
    ) -> None:
        """Atualiza pendentes + estado no KV via POST /api/sync."""
        payload = {
            "obra":               obra_key,
            "pendentes":          pendentes,
            "ultimo_nsu":         ultimo_nsu,
            "ultima_verificacao": ultima_verificacao,
        }
        r = requests.post(
            f"{self._url}/api/sync",
            json=payload,
            headers={"Authorization": f"Bearer {self._token}"},
            timeout=30,
        )
        r.raise_for_status()
