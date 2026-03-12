"""
Remove dos pendentes do KV as notas cuja data_emissao e anterior a data_inicio
definida em obras.json para cada obra.

Uso: python -m monitor.limpar_pendentes_antigos
"""
import json
import os
import sys
from datetime import datetime, timezone

sys.path.insert(0, os.path.dirname(__file__))
from cloudflare import CloudflareClient


def _carregar_obras() -> dict:
    caminho = os.path.join(os.path.dirname(__file__), "..", "obras.json")
    with open(caminho, encoding="utf-8") as f:
        return json.load(f)


def main() -> None:
    cf = CloudflareClient(
        worker_url=os.environ["CF_WORKER_URL"],
        api_token=os.environ["CF_API_TOKEN"],
    )
    obras = _carregar_obras()

    for obra_key, obra in obras.items():
        data_inicio = obra.get("data_inicio", "")
        if not data_inicio:
            print(f"\n{obra_key}: sem data_inicio definida, pulando.")
            continue

        pendentes = cf.carregar_pendentes(obra_key)
        lancadas  = cf.carregar_lancadas(obra_key)
        estado    = cf.carregar_estado(obra_key)

        antes = len(pendentes)
        antigos = [p for p in pendentes if (p.get("data_emissao") or "") < data_inicio]
        pendentes_novos = [p for p in pendentes if (p.get("data_emissao") or "") >= data_inicio]

        print(f"\n{obra_key} — data_inicio: {data_inicio}")
        print(f"  Pendentes antes: {antes} | A remover: {len(antigos)} | Ficam: {len(pendentes_novos)}")

        if not antigos:
            print("  Nada a remover.")
            continue

        for p in antigos:
            print(f"  [REMOVENDO] {p.get('data_emissao','')} | Nr {p.get('numero','')} | {p.get('nome_prest','')[:40]}")

        agora = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
        cf.sincronizar(
            obra_key           = obra_key,
            pendentes          = pendentes_novos,
            ultimo_nsu         = estado.get("ultimo_nsu", 0),
            ultima_verificacao = agora,
            lancadas           = lancadas,
        )
        print(f"  KV atualizado: {antes} -> {len(pendentes_novos)} pendentes.")

    print("\nLimpeza concluida.")


if __name__ == "__main__":
    main()
