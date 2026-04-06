"""
Script pontual: sobe PDFs existentes localmente para o Cloudflare Worker KV
e marca has_pdf=True nas notas pendentes correspondentes.

Uso:
  cd monitor-nfse
  CF_WORKER_URL=... CF_API_TOKEN=... python -m monitor.upload_pdfs
"""
import os
import sys
import json

sys.path.insert(0, os.path.dirname(__file__))

from cloudflare import CloudflareClient

PDF_DIR = os.path.join(
    os.path.dirname(__file__), "..", "..", "Nota Fiscal", "pulse", "pdfs"
)

CF_WORKER_URL = os.environ["CF_WORKER_URL"]
CF_API_TOKEN  = os.environ["CF_API_TOKEN"]

cf = CloudflareClient(worker_url=CF_WORKER_URL, api_token=CF_API_TOKEN)

# Indexa PDFs disponíveis localmente: chave → caminho
pdfs_locais = {}
pasta = os.path.normpath(PDF_DIR)
if os.path.isdir(pasta):
    for nome in os.listdir(pasta):
        if nome.lower().endswith(".pdf"):
            chave = nome[:-4]   # remove .pdf
            pdfs_locais[chave] = os.path.join(pasta, nome)

print(f"PDFs encontrados localmente: {len(pdfs_locais)}")

with open(os.path.join(os.path.dirname(__file__), "..", "obras.json")) as f:
    obras = json.load(f)

for obra_key in obras:
    print(f"\nObra: {obra_key}")
    estado    = cf.carregar_estado(obra_key)
    pendentes = cf.carregar_pendentes(obra_key)
    print(f"  {len(pendentes)} notas pendentes")

    alterado = False
    for nota in pendentes:
        chave = nota.get("chave", "")
        if nota.get("has_pdf"):
            continue   # já marcado

        if chave in pdfs_locais:
            print(f"  Subindo {chave[:25]}...")
            with open(pdfs_locais[chave], "rb") as f:
                pdf_bytes = f.read()
            cf.salvar_pdf(chave, pdf_bytes)
            nota["has_pdf"] = True
            alterado = True
        else:
            print(f"  Sem PDF local: {chave[:25]}...")

    if alterado:
        cf.sincronizar(
            obra_key           = obra_key,
            pendentes          = pendentes,
            ultimo_nsu         = estado.get("ultimo_nsu", 0),
            ultima_verificacao = estado.get("ultima_verificacao", ""),
        )
        print(f"  KV atualizado com has_pdf.")
    else:
        print(f"  Nada alterado.")

print("\nConcluido.")
