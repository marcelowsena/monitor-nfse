"""
Script pontual: preenche nome_prest nas notas já salvas no KV via CNPJ lookup.
Executa uma vez, pode ser deletado depois.
"""
import os
import sys
import json
import time

# Garante que o pacote monitor está no path
sys.path.insert(0, os.path.dirname(__file__))

from cloudflare  import CloudflareClient
from cnpj_lookup import preencher_nomes

CF_WORKER_URL = os.environ["CF_WORKER_URL"]
CF_API_TOKEN  = os.environ["CF_API_TOKEN"]

cf = CloudflareClient(worker_url=CF_WORKER_URL, api_token=CF_API_TOKEN)

# Carrega obras
with open(os.path.join(os.path.dirname(__file__), "..", "obras.json")) as f:
    obras = json.load(f)

for obra_key in obras:
    print(f"\nObra: {obra_key}")

    estado    = cf.carregar_estado(obra_key)
    pendentes = cf.carregar_pendentes(obra_key)
    print(f"  {len(pendentes)} notas no KV")

    sem_nome = [n for n in pendentes if not n.get("nome_prest")]
    print(f"  {len(sem_nome)} sem nome — consultando CNPJ API...")

    if not sem_nome:
        print("  Nada a fazer.")
        continue

    pendentes_atualizadas = preencher_nomes(pendentes)

    preenchidos = sum(1 for n in pendentes_atualizadas if n.get("nome_prest"))
    print(f"  Nomes encontrados: {preenchidos}/{len(pendentes_atualizadas)}")

    cf.sincronizar(
        obra_key          = obra_key,
        pendentes         = pendentes_atualizadas,
        ultimo_nsu        = estado.get("ultimo_nsu", 0),
        ultima_verificacao= estado.get("ultima_verificacao", ""),
    )
    print("  KV atualizado.")

print("\nConcluido.")
