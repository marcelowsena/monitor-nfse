"""
Remove uma nota específica dos pendentes do KV pelo número da NFS-e.
Uso: python -m monitor.remover_nota <obra_key> <numero_nfse>
"""

import os
import sys
from datetime import datetime, timezone

sys.path.insert(0, os.path.dirname(__file__))
from cloudflare import CloudflareClient


def main() -> None:
    if len(sys.argv) != 3:
        print("Uso: python -m monitor.remover_nota <obra_key> <numero_nfse>")
        sys.exit(1)

    obra_key   = sys.argv[1]
    numero_alvo = sys.argv[2].strip()

    cf = CloudflareClient(
        worker_url=os.environ["CF_WORKER_URL"],
        api_token=os.environ["CF_API_TOKEN"],
    )

    pendentes = cf.carregar_pendentes(obra_key)
    lancadas  = cf.carregar_lancadas(obra_key)
    estado    = cf.carregar_estado(obra_key)

    print(f"Obra '{obra_key}': {len(pendentes)} pendentes carregados.")

    antes = len(pendentes)
    removidas = [n for n in pendentes if n.get("numero") == numero_alvo]
    pendentes = [n for n in pendentes if n.get("numero") != numero_alvo]

    if not removidas:
        print(f"Nota '{numero_alvo}' nao encontrada nos pendentes da obra '{obra_key}'.")
        sys.exit(1)

    for n in removidas:
        print(f"  Removendo: nr={n.get('numero')} | chave={n.get('chave','')[:25]}... | {n.get('nome_prest','')}")

    agora = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    cf.sincronizar(
        obra_key,
        pendentes,
        estado.get("ultimo_nsu", 0),
        agora,
        lancadas=lancadas,
    )

    print(f"KV atualizado: {antes} -> {len(pendentes)} pendentes.")


if __name__ == "__main__":
    main()
