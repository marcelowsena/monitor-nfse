"""
Script para recuperar PDFs que faltam.

Tenta baixar PDFs de todas as notas sem PDF no KV.
Mostra detalhes de sucesso/falha para cada tentativa.
"""

import argparse
import json
import os
import sys
from datetime import datetime, timezone

sys.path.insert(0, os.path.dirname(__file__))

from sefaz       import SefazClient
from cloudflare  import CloudflareClient
from obras_utils import carregar_obras


def recuperar_pdfs(
    obra_key: str,
    obra: dict,
    cf: CloudflareClient,
    sefaz: SefazClient,
) -> None:
    """Tenta recuperar PDFs para uma obra específica."""
    print(f"\n{'─'*70}")
    print(f"  Obra: {obra['nome']}")
    print(f"{'─'*70}")

    # Carrega pendentes e lançadas
    pendentes = cf.carregar_pendentes(obra_key)
    lancadas = cf.carregar_lancadas(obra_key)

    # Filtra notas sem PDF
    sem_pdf_pend = [n for n in pendentes if not n.get("has_pdf")]
    sem_pdf_lanc = [n for n in lancadas if not n.get("has_pdf")]
    todos_sem_pdf = sem_pdf_pend + sem_pdf_lanc

    print(f"  Pendentes sem PDF: {len(sem_pdf_pend)}")
    print(f"  Lançadas sem PDF:  {len(sem_pdf_lanc)}")
    print(f"  Total:             {len(todos_sem_pdf)}")

    if not todos_sem_pdf:
        print("  ✓ Nenhuma nota sem PDF!")
        return

    # Tenta baixar cada uma
    sucesso = 0
    falha = 0
    indisponivel = 0

    for i, nota in enumerate(todos_sem_pdf, 1):
        chave = nota["chave"]
        numero = nota.get("numero", "?")
        data = nota.get("data_emissao", "?")

        try:
            pdf = sefaz.baixar_pdf(chave)
            if pdf:
                # Conseguiu baixar
                cf.salvar_pdf(chave, pdf)
                nota["has_pdf"] = True
                nota.pop("pdf_falhou", None)
                sucesso += 1
                print(f"    [{i:3d}] ✓ {data} | {numero:6s} | {len(pdf):6d} bytes")
            else:
                # SEFAZ retornou None (404, indisponível)
                indisponivel += 1
                nota["pdf_falhou"] = True
                print(f"    [{i:3d}] ✗ {data} | {numero:6s} | Indisponível na SEFAZ")

        except Exception as e:
            falha += 1
            nota["pdf_falhou"] = True
            print(f"    [{i:3d}] ✗ {data} | {numero:6s} | Erro: {str(e)[:50]}")

    # Atualiza KV com as mudanças
    if sucesso > 0:
        agora = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
        # Reconstrói as listas
        pendentes_atualizado = [
            n for n in pendentes if n["chave"] not in {x["chave"] for x in todos_sem_pdf}
        ] + [n for n in sem_pdf_pend if n.get("has_pdf")]
        lancadas_atualizado = [
            n for n in lancadas if n["chave"] not in {x["chave"] for x in todos_sem_pdf}
        ] + [n for n in sem_pdf_lanc if n.get("has_pdf")]

        cf.sincronizar(obra_key, pendentes_atualizado, 0, agora, lancadas=lancadas_atualizado)
        print(f"\n  KV atualizado com {sucesso} novo(s) PDF(s)")

    print(f"\n  Resumo:")
    print(f"    ✓ Sucesso:      {sucesso}")
    print(f"    ✗ Indisponível: {indisponivel}")
    print(f"    ✗ Erro:         {falha}")


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Recuperar PDFs que faltam em notas do Monitor NFS-e"
    )
    parser.add_argument(
        "--obras",
        nargs="+",
        default=None,
        metavar="OBRA",
        help="Obras específicas (ex: --obras max arium). Padrão: todas.",
    )

    args = parser.parse_args()

    # Carrega configuração
    obras_config = carregar_obras()

    # Filtra obras se solicitado
    if args.obras:
        obras_config = {k: v for k, v in obras_config.items() if k in args.obras}

    if not obras_config:
        print("Nenhuma obra encontrada!")
        sys.exit(1)

    # Inicializa clientes
    worker_url = os.environ.get("CF_WORKER_URL")
    api_token = os.environ.get("CF_API_TOKEN")

    if not worker_url or not api_token:
        print("Erro: Configure CF_WORKER_URL e CF_API_TOKEN")
        sys.exit(1)

    cf = CloudflareClient(worker_url, api_token)

    print("\n" + "="*70)
    print("  Recuperador de PDFs — Monitor NFS-e")
    print("="*70)

    for obra_key, obra in obras_config.items():
        cert_path = os.environ[obra["cert_env"]]
        cert_senha = os.environ[obra["cert_senha_env"]]
        sefaz = SefazClient(cert_path, cert_senha)

        try:
            recuperar_pdfs(obra_key, obra, cf, sefaz)
        except Exception as e:
            print(f"  Erro ao processar obra: {e}")


if __name__ == "__main__":
    main()
