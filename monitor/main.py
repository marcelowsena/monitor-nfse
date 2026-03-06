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
import tempfile
import base64
from datetime import datetime, timezone

sys.path.insert(0, os.path.dirname(__file__))

from sefaz      import SefazClient
from sienge     import SiengeClient
from cloudflare import CloudflareClient
from notificacao import enviar_teams, enviar_email


def _carregar_obras() -> dict:
    caminho = os.path.join(os.path.dirname(__file__), "..", "obras.json")
    with open(caminho, encoding="utf-8") as f:
        return json.load(f)


def _cert_para_tempfile(env_var_b64: str) -> str:
    conteudo = base64.b64decode(os.environ[env_var_b64])
    fd, caminho = tempfile.mkstemp(suffix=".pfx")
    with os.fdopen(fd, "wb") as f:
        f.write(conteudo)
    return caminho


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

    # Chaves já conhecidas (evita reprocessar)
    conhecidas = {n["chave"] for n in pendentes_cf}

    print(f"  NSU atual        : {ultimo_nsu}")
    print(f"  Pendentes no KV  : {len(pendentes_cf)}")

    # ── Etapa 2: consulta SEFAZ ──
    cert_path  = _cert_para_tempfile(obra["cert_env"])
    cert_senha = os.environ[obra["cert_senha_env"]]

    try:
        sefaz = SefazClient(cert_path, cert_senha)
        notas_novas, novo_nsu = sefaz.consultar_novas(ultimo_nsu)
    finally:
        os.unlink(cert_path)

    print(f"  Notas desde NSU {ultimo_nsu}: {len(notas_novas)} | Novo NSU: {novo_nsu}")

    # ── Etapa 3: filtra realmente novas ──
    realmente_novas = [n for n in notas_novas if n["chave"] not in conhecidas]
    print(f"  Novas (não conhecidas): {len(realmente_novas)}")

    # ── Etapa 4: verifica no Sienge ──
    para_verificar = realmente_novas + pendentes_cf
    lancadas = sienge.verificar_lancadas(para_verificar) if para_verificar else set()

    # ── Etapa 5: classifica ──
    pendentes_novos = [n for n in realmente_novas if n["chave"] not in lancadas]
    # Atualiza lista: remove as que foram lançadas, adiciona as novas
    pendentes_atualizados = (
        [p for p in pendentes_cf if p["chave"] not in lancadas]
        + [{**n, "obra": obra_key} for n in pendentes_novos]
    )

    recem_lancadas = {p["chave"] for p in pendentes_cf if p["chave"] in lancadas}

    print(f"  Pendentes novas   : {len(pendentes_novos)}")
    print(f"  Recém lançadas    : {len(recem_lancadas)}")

    # ── Etapa 6: sincroniza com Cloudflare KV ──
    agora = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    cf.sincronizar(obra_key, pendentes_atualizados, novo_nsu, agora)
    print(f"  ✓ KV atualizado. NSU salvo: {novo_nsu}")

    # ── Etapa 7: notifica ──
    if pendentes_novos:
        webhook = os.environ.get("TEAMS_WEBHOOK_URL", "")
        if webhook:
            enviar_teams(webhook, obra["nome"], pendentes_novos)

        emails = obra.get("alertar_emails", [])
        if emails:
            enviar_email(emails, obra["nome"], pendentes_novos)


def main() -> None:
    print("=" * 55)
    print("  Monitor NFS-e — INVCP")
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

    print("\n✓ Monitoramento concluído.")


if __name__ == "__main__":
    main()
