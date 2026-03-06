"""
Gerenciamento de estado via Cloudflare KV.
Persiste entre execuções do GitHub Actions.

Chaves usadas por obra (prefixo = obra_key):
  {obra}:ultimo_nsu          → int
  {obra}:pendentes           → lista de dicts (notas não lançadas)
  {obra}:notas_conhecidas    → lista de chaves já processadas
  {obra}:ultima_verificacao  → ISO timestamp UTC
"""

import json
import requests


class CloudflareKV:
    def __init__(self, account_id: str, namespace_id: str, api_token: str):
        self._base = (
            f"https://api.cloudflare.com/client/v4/accounts/{account_id}"
            f"/storage/kv/namespaces/{namespace_id}"
        )
        self._headers = {"Authorization": f"Bearer {api_token}"}

    def get(self, key: str, default=None):
        r = requests.get(
            f"{self._base}/values/{key}",
            headers=self._headers,
            timeout=15,
        )
        if r.status_code == 404:
            return default
        if r.status_code != 200:
            print(f"  [KV] Erro ao ler '{key}': {r.status_code}")
            return default
        try:
            return json.loads(r.text)
        except json.JSONDecodeError:
            return r.text

    def put(self, key: str, value) -> bool:
        data = json.dumps(value, ensure_ascii=False) if not isinstance(value, str) else value
        r = requests.put(
            f"{self._base}/values/{key}",
            headers=self._headers,
            data=data.encode("utf-8"),
            timeout=15,
        )
        if r.status_code not in (200, 201):
            print(f"  [KV] Erro ao gravar '{key}': {r.status_code} — {r.text[:100]}")
            return False
        return True
