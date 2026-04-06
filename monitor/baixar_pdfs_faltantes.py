"""
Script pontual: baixa do SEFAZ e sobe ao KV os PDFs de notas pendentes sem has_pdf.
"""
import os, sys, json
sys.path.insert(0, os.path.dirname(__file__))

from cloudflare import CloudflareClient
from sefaz      import SefazClient

CF_WORKER_URL = os.environ["CF_WORKER_URL"]
CF_API_TOKEN  = os.environ["CF_API_TOKEN"]

cf = CloudflareClient(worker_url=CF_WORKER_URL, api_token=CF_API_TOKEN)

with open(os.path.join(os.path.dirname(__file__), "..", "obras.json")) as f:
    obras = json.load(f)

for obra_key, obra in obras.items():
    print(f"\nObra: {obra_key}")

    cert_path  = os.environ[obra["cert_env"]]
    cert_senha = os.environ[obra["cert_senha_env"]]
    sefaz = SefazClient(cert_path, cert_senha)

    estado    = cf.carregar_estado(obra_key)
    pendentes = cf.carregar_pendentes(obra_key)

    sem_pdf = [n for n in pendentes if not n.get("has_pdf")]
    print(f"  {len(sem_pdf)} notas sem PDF")

    if not sem_pdf:
        print("  Nada a fazer.")
        continue

    alterado = False
    for nota in sem_pdf:
        chave = nota["chave"]
        print(f"  Baixando {chave[:25]}... (Nr {nota.get('numero','')})")
        pdf = sefaz.baixar_pdf(chave)
        if pdf:
            cf.salvar_pdf(chave, pdf)
            nota["has_pdf"] = True
            alterado = True
            print(f"    OK ({len(pdf)//1024} KB)")
        else:
            print(f"    Sem PDF no SEFAZ.")

    if alterado:
        cf.sincronizar(
            obra_key           = obra_key,
            pendentes          = pendentes,
            ultimo_nsu         = estado.get("ultimo_nsu", 0),
            ultima_verificacao = estado.get("ultima_verificacao", ""),
        )
        print(f"  KV atualizado.")

print("\nConcluido.")
