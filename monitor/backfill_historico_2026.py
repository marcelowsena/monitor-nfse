"""
Backfill historico 2026 — busca TODAS as NFS-e recebidas em 2026 para as obras
informadas e popula lancadas_kv com as que ja estao no Sienge.

Uso local:
  CF_WORKER_URL=... CF_API_TOKEN=... SIENGE_USER=... SIENGE_PASS=... \
  CERT_ARIUM_PATH=... CERT_ARIUM_SENHA=... \
      python -m monitor.backfill_historico_2026 --obras arium cora nola confraria_benjamin

No GitHub Actions basta acionar o workflow backfill-historico-2026.yml manualmente.
"""

import argparse
import json
import os
import sys
from datetime import datetime, timezone

sys.path.insert(0, os.path.dirname(__file__))

from sefaz      import SefazClient
from sienge     import SiengeClient
from cloudflare import CloudflareClient
from cnpj_lookup import preencher_nomes


CORTE_ANO = "2026-01-01"  # so notas emitidas a partir desta data


def _carregar_obras() -> dict:
    caminho = os.path.join(os.path.dirname(__file__), "..", "obras.json")
    with open(caminho, encoding="utf-8") as f:
        return json.load(f)


def processar_obra(obra_key: str, obra: dict, cf: CloudflareClient, sienge: SiengeClient) -> None:
    print(f"\n{'─'*55}")
    print(f"  Obra : {obra['nome']}")
    print(f"  CNPJ : {obra['cnpj']}")
    print(f"{'─'*55}")

    cert_path  = os.environ[obra["cert_env"]]
    cert_senha = os.environ[obra["cert_senha_env"]]

    # 1. Carrega estado atual do KV
    estado       = cf.carregar_estado(obra_key)
    pendentes_kv = cf.carregar_pendentes(obra_key)
    lancadas_kv  = cf.carregar_lancadas(obra_key)

    chaves_pendentes = {n["chave"] for n in pendentes_kv}
    chaves_lancadas  = {n["chave"] for n in lancadas_kv}

    print(f"  NSU atual no KV  : {estado.get('ultimo_nsu', 0)}")
    print(f"  Pendentes no KV  : {len(pendentes_kv)}")
    print(f"  Lancadas no KV   : {len(lancadas_kv)}")

    # 2. Busca TODAS as notas desde NSU=0
    print(f"\n  Buscando todas as NFS-e desde NSU=0 (pode demorar)...")
    sefaz = SefazClient(cert_path, cert_senha)
    todas_notas, cancelamentos, nsu_final = sefaz.consultar_novas(0)
    todas_notas = preencher_nomes(todas_notas)
    print(f"  Total recebido do SEFAZ: {len(todas_notas)} notas | NSU final: {nsu_final}")

    # 3. Aplica cancelamentos
    chaves_canceladas = {c["chave"] for c in cancelamentos}
    if chaves_canceladas:
        antes = len(todas_notas)
        todas_notas = [n for n in todas_notas if n["chave"] not in chaves_canceladas]
        print(f"  Cancelamentos removidos: {antes - len(todas_notas)}")

    # 4. Filtra para 2026
    notas_2026 = [n for n in todas_notas if (n.get("data_emissao") or "") >= CORTE_ANO]
    print(f"  Notas em 2026 ou mais  : {len(notas_2026)}")

    if not notas_2026:
        print("  Nada a processar.")
        return

    # 5. Separa candidatas: excluindo as que ja estao em lancadas_kv (com titulo confirmado)
    candidatas = [n for n in notas_2026 if n["chave"] not in chaves_lancadas]
    print(f"  Candidatas (fora do KV lancadas): {len(candidatas)}")

    if not candidatas:
        print("  Historico ja esta completo para esta obra.")
        return

    # 6. Verifica no Sienge
    print("  Consultando Sienge...")
    confirmadas = sienge.verificar_lancadas(candidatas)  # {chave: numero_titulo}
    print(f"  Confirmadas pelo Sienge: {len(confirmadas)}")

    # 7. Adiciona ao lancadas_kv
    adicionadas = 0
    for nota in candidatas:
        chave = nota["chave"]
        if chave in confirmadas:
            numero_titulo = confirmadas[chave]
            nota_lancada = {**nota, "obra": obra_key, "numero_titulo": numero_titulo}
            # Preserva has_pdf se ja estava nos pendentes
            pendente_ref = next((p for p in pendentes_kv if p["chave"] == chave), None)
            if pendente_ref and pendente_ref.get("has_pdf"):
                nota_lancada["has_pdf"] = True
            lancadas_kv.append(nota_lancada)
            chaves_lancadas.add(chave)
            adicionadas += 1
            print(f"    + Nr {nota.get('numero','')} | Titulo {numero_titulo} | {nota.get('nome_prest','')[:35]}")

    print(f"\n  Adicionadas ao historico lancadas: {adicionadas}")
    print(f"  Total lancadas KV apos backfill  : {len(lancadas_kv)}")

    # 8. Notas de 2026 que NAO estao no Sienge e NAO estao nos pendentes → adiciona como pendente
    novas_pendentes = 0
    for nota in candidatas:
        chave = nota["chave"]
        if chave not in confirmadas and chave not in chaves_pendentes:
            pendentes_kv.append({**nota, "obra": obra_key})
            chaves_pendentes.add(chave)
            novas_pendentes += 1
            print(f"    [PENDENTE] Nr {nota.get('numero','')} | {nota.get('nome_prest','')[:35]}")

    if novas_pendentes:
        print(f"  Novas pendentes adicionadas: {novas_pendentes}")

    if adicionadas == 0 and novas_pendentes == 0:
        print("  Nada alterado no KV.")
        return

    # 9. Salva no KV
    agora = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    cf.sincronizar(
        obra_key           = obra_key,
        pendentes          = pendentes_kv,
        ultimo_nsu         = estado.get("ultimo_nsu", nsu_final),
        ultima_verificacao = agora,
        lancadas           = lancadas_kv,
    )
    print("  KV atualizado com sucesso.")


def main() -> None:
    todas_obras = list(_carregar_obras().keys())

    parser = argparse.ArgumentParser(description="Backfill historico 2026 de NFS-e")
    parser.add_argument(
        "--obras",
        nargs="+",
        default=todas_obras,
        choices=todas_obras,
        help="Chaves das obras a processar (padrao: todas)",
    )
    args = parser.parse_args()

    print("=" * 55)
    print("  Backfill Historico NFS-e 2026 — INVCP")
    print(f"  {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M:%S')} UTC")
    print(f"  Obras: {', '.join(args.obras)}")
    print("=" * 55)

    cf = CloudflareClient(
        worker_url = os.environ["CF_WORKER_URL"],
        api_token  = os.environ["CF_API_TOKEN"],
    )
    sienge = SiengeClient(
        usuario = os.environ["SIENGE_USER"],
        senha   = os.environ["SIENGE_PASS"],
    )

    obras = _carregar_obras()

    for obra_key in args.obras:
        obra = obras[obra_key]
        try:
            processar_obra(obra_key, obra, cf, sienge)
        except Exception as e:
            print(f"\n  [ERRO] Obra '{obra_key}': {e}")
            import traceback
            traceback.print_exc()

    print("\nBackfill concluido.")


if __name__ == "__main__":
    main()
