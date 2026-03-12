"""
Verifica o status de uma nota especifica: consulta o KV e re-busca o SEFAZ
para confirmar se existe evento de cancelamento para a chave.

Variaveis de ambiente:
  OBRA_KEY, NR_BUSCA, CNPJ_BUSCA
  CF_WORKER_URL, CF_API_TOKEN
  CERT_<OBRA>_PATH, CERT_<OBRA>_SENHA  (mesmos do monitor principal)
"""

import json
import os
import sys

sys.path.insert(0, os.path.dirname(__file__))

from cloudflare import CloudflareClient
from sefaz      import SefazClient

import requests as _req


def _carregar_obras() -> dict:
    import json as _json
    caminho = os.path.join(os.path.dirname(__file__), "..", "obras.json")
    with open(caminho, encoding="utf-8") as f:
        return _json.load(f)


def main():
    obra_key   = os.environ.get("OBRA_KEY", "").strip()
    nr_busca   = os.environ.get("NR_BUSCA", "").strip()
    cnpj_busca = os.environ.get("CNPJ_BUSCA", "").strip().replace(".", "").replace("/", "").replace("-", "")

    if not obra_key:
        print("OBRA_KEY nao definida.")
        sys.exit(1)

    # ── 1. Busca no KV ──────────────────────────────────────────────
    cf = CloudflareClient(
        worker_url=os.environ["CF_WORKER_URL"],
        api_token=os.environ["CF_API_TOKEN"],
    )

    url   = cf._url + "/api/pendentes"
    token = cf._token
    data  = _req.get(url, params={"token": token}, timeout=30).json()

    obra_kv = next((o for o in data if o["key"] == obra_key), None)
    if not obra_kv:
        print(f"Obra '{obra_key}' nao encontrada no KV.")
        sys.exit(0)

    print(f"Obra: {obra_key}")
    print(f"Pendentes KV: {len(obra_kv.get('pendentes',[]))} | Lancadas KV: {len(obra_kv.get('lancadas',[]))}")
    print()

    nota_encontrada = None
    for lista, label in [(obra_kv.get("pendentes", []), "PENDENTE"), (obra_kv.get("lancadas", []), "LANCADA")]:
        for n in lista:
            cnpj_n = (n.get("cnpj_prest", "") or "").replace(".", "").replace("/", "").replace("-", "")
            nr_match   = nr_busca   and str(n.get("numero", "")) == nr_busca
            cnpj_match = cnpj_busca and cnpj_n == cnpj_busca
            if nr_match or cnpj_match:
                print(f"[{label}]")
                for k, v in n.items():
                    print(f"  {k}: {v}")
                print()
                if nota_encontrada is None and nr_match:
                    nota_encontrada = n

    if not nota_encontrada:
        print("Nota nao encontrada pelo numero informado no KV.")

    # ── 2. Verifica no SEFAZ se existe cancelamento ─────────────────
    obras = _carregar_obras()
    obra  = obras.get(obra_key)
    if not obra:
        print(f"Obra '{obra_key}' nao encontrada em obras.json.")
        sys.exit(0)

    cert_path  = os.environ[obra["cert_env"]]
    cert_senha = os.environ[obra["cert_senha_env"]]

    # A chave da nota a verificar
    chave_alvo = (nota_encontrada or {}).get("chave")
    if not chave_alvo:
        print("Chave de acesso nao encontrada — nao e possivel verificar cancelamento no SEFAZ.")
        sys.exit(0)

    print(f"Verificando cancelamentos no SEFAZ para chave: {chave_alvo[:30]}...")
    print("(buscando todos os NSUs desde 0 para capturar eventos)")

    sefaz = SefazClient(cert_path, cert_senha)
    _, cancelamentos, _ = sefaz.consultar_novas(0)

    chaves_canceladas = {c["chave"] for c in cancelamentos}
    if chave_alvo in chaves_canceladas:
        print(f"\n[CANCELADA NO SEFAZ] A nota Nr {nr_busca} tem evento de cancelamento registrado no SEFAZ.")
    else:
        print(f"\n[NAO CANCELADA] Nenhum evento de cancelamento encontrado no SEFAZ para esta nota.")


if __name__ == "__main__":
    main()
