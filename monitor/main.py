"""
Monitor NFS-e — ponto de entrada.

Executado pelo GitHub Actions a cada hora.
Fluxo por obra:
  1. Carrega último NSU e pendentes do Cloudflare KV (via Worker)
  2. Consulta SEFAZ — notas desde aquele NSU (incremental)
  3. Verifica no Sienge quais já foram lançadas
  4. Atualiza KV via Worker + notifica Teams
"""

import json
import os
import sys
from datetime import datetime, timezone

sys.path.insert(0, os.path.dirname(__file__))

from sefaz       import SefazClient
from sienge      import SiengeClient
from cloudflare  import CloudflareClient
from notificacao import enviar_teams, enviar_email
from cnpj_lookup import preencher_nomes


def _carregar_obras() -> dict:
    caminho = os.path.join(os.path.dirname(__file__), "..", "obras.json")
    with open(caminho, encoding="utf-8") as f:
        return json.load(f)


def processar_obra(
    obra_key: str,
    obra: dict,
    cf: CloudflareClient,
    sienge: SiengeClient,
) -> None:
    print(f"\n{'─'*55}")
    print(f"  Obra : {obra['nome']}")
    print(f"  CNPJ : {obra['cnpj']}")
    print(f"{'─'*55}")

    # ── Etapa 1: carrega estado do Cloudflare KV ──
    estado       = cf.carregar_estado(obra_key)
    ultimo_nsu   = estado.get("ultimo_nsu", 0)
    pendentes_cf = cf.carregar_pendentes(obra_key)
    lancadas_kv  = cf.carregar_lancadas(obra_key)

    conhecidas          = {n["chave"] for n in pendentes_cf}
    chaves_lancadas_kv  = {n["chave"] for n in lancadas_kv}

    print(f"  NSU atual        : {ultimo_nsu}")
    print(f"  Pendentes no KV  : {len(pendentes_cf)}")

    # ── Etapa 2: consulta SEFAZ ──
    # cert_env aponta para a variável de ambiente com o CAMINHO do .pfx
    cert_path  = os.environ[obra["cert_env"]]
    cert_senha = os.environ[obra["cert_senha_env"]]

    sefaz = SefazClient(cert_path, cert_senha)
    notas_novas, cancelamentos, novo_nsu = sefaz.consultar_novas(ultimo_nsu)
    notas_novas = preencher_nomes(notas_novas)

    print(f"  Notas desde NSU {ultimo_nsu}: {len(notas_novas)} | Novo NSU: {novo_nsu}")

    # ── Etapa 3: aplica cancelamentos e filtra novas ──
    chaves_canceladas = {c["chave"] for c in cancelamentos}
    if chaves_canceladas:
        removidas = [p for p in pendentes_cf if p["chave"] in chaves_canceladas]
        for r in removidas:
            print(f"  [CANCELADA] Removendo nota {r.get('numero','')} ({r['chave'][:25]}...)")
        pendentes_cf = [p for p in pendentes_cf if p["chave"] not in chaves_canceladas]
        conhecidas   = {n["chave"] for n in pendentes_cf}

    realmente_novas = [n for n in notas_novas if n["chave"] not in conhecidas]
    print(f"  Novas (nao conhecidas): {len(realmente_novas)}")

    # ── Etapa 4: verifica no Sienge ──
    para_verificar = realmente_novas + pendentes_cf
    lancadas = sienge.verificar_lancadas(para_verificar) if para_verificar else set()

    # ── Etapa 5: classifica ──
    pendentes_novos = [n for n in realmente_novas if n["chave"] not in lancadas]
    pendentes_atualizados = (
        [p for p in pendentes_cf if p["chave"] not in lancadas]
        + [{**n, "obra": obra_key} for n in pendentes_novos]
    )

    recem_lancadas = {p["chave"] for p in pendentes_cf if p["chave"] in lancadas}

    # Acumula as recém-lançadas no histórico do KV
    for p in pendentes_cf:
        if p["chave"] in lancadas and p["chave"] not in chaves_lancadas_kv:
            nota_lancada = {**p, "numero_titulo": lancadas[p["chave"]]}
            lancadas_kv.append(nota_lancada)
            chaves_lancadas_kv.add(p["chave"])

    print(f"  Pendentes novas   : {len(pendentes_novos)}")
    print(f"  Recem lancadas    : {len(recem_lancadas)}")
    print(f"  Historico lancadas: {len(lancadas_kv)}")

    # ── Etapa 6: baixa PDFs (novas + pendentes antigas sem PDF) ──
    sem_pdf = [n for n in pendentes_atualizados if not n.get("has_pdf")]
    if sem_pdf:
        print(f"  Baixando PDFs faltantes: {len(sem_pdf)}")
    for nota in sem_pdf:
        chave = nota["chave"]
        try:
            pdf = sefaz.baixar_pdf(chave)
            if pdf:
                cf.salvar_pdf(chave, pdf)
                nota["has_pdf"] = True
                print(f"    PDF salvo: {chave[:20]}...")
        except Exception as e:
            print(f"    Erro ao salvar PDF {chave[:20]}...: {e}")

    # ── Etapa 7: sincroniza com Cloudflare KV ──
    agora = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    cf.sincronizar(obra_key, pendentes_atualizados, novo_nsu, agora, lancadas=lancadas_kv)
    print(f"  KV atualizado. NSU salvo: {novo_nsu}")

    # ── Etapa 8: notifica ──
    if pendentes_novos:
        webhook = os.environ.get("TEAMS_WEBHOOK_URL", "")
        if webhook:
            enviar_teams(webhook, obra["nome"], pendentes_novos)

        emails = obra.get("alertar_emails", [])
        if emails:
            enviar_email(emails, obra["nome"], pendentes_novos)


def main() -> None:
    print("=" * 55)
    print("  Monitor NFS-e - INVCP")
    print(f"  {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M:%S')} UTC")
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

    for obra_key, obra in obras.items():
        try:
            processar_obra(obra_key, obra, cf, sienge)
        except Exception as e:
            print(f"\n  [ERRO] Obra '{obra_key}': {e}")

    print("\nMonitoramento concluido.")


if __name__ == "__main__":
    main()
