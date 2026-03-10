"""
Script pontual: lê todos os XMLs locais da obra, verifica no Sienge quais
estão lançadas e popula {obra}:lancadas no KV com o histórico completo.

Uso:
  cd monitor-nfse
  CF_WORKER_URL=... CF_API_TOKEN=... SIENGE_USER=... SIENGE_PASS=... \\
      py -3 -m monitor.popular_lancadas
"""
import os
import sys
import json
import xml.etree.ElementTree as ET

sys.path.insert(0, os.path.dirname(__file__))

from cloudflare import CloudflareClient
from sienge     import SiengeClient

NS = {"nfse": "http://www.sped.fazenda.gov.br/nfse"}

XML_DIRS = {
    "max": os.path.normpath(
        os.path.join(os.path.dirname(__file__), "..", "..", "Nota Fiscal", "pulse", "xmls")
    ),
}

CF_WORKER_URL = os.environ["CF_WORKER_URL"]
CF_API_TOKEN  = os.environ["CF_API_TOKEN"]
SIENGE_USER   = os.environ["SIENGE_USER"]
SIENGE_PASS   = os.environ["SIENGE_PASS"]

cf     = CloudflareClient(worker_url=CF_WORKER_URL, api_token=CF_API_TOKEN)
sienge = SiengeClient(usuario=SIENGE_USER, senha=SIENGE_PASS)


def _txt(el, *path):
    cur = el
    for tag in path:
        if cur is None:
            return ""
        cur = cur.find(f"nfse:{tag}", NS)
    return (cur.text or "").strip() if cur is not None else ""


def parsear_xml_local(caminho: str) -> dict | None:
    """Lê um arquivo XML local e extrai os campos da NFS-e."""
    chave = os.path.splitext(os.path.basename(caminho))[0]
    try:
        tree = ET.parse(caminho)
        root = tree.getroot()
    except Exception as e:
        print(f"  Erro ao parsear {chave[:20]}...: {e}")
        return None

    tag_raiz = root.tag.split("}")[-1]
    # Arquivo de cancelamento — ignora
    if tag_raiz == "evento":
        return None

    # Suporta root = <NFSe> ou <CompNFSe>
    if tag_raiz == "NFSe":
        inf = root.find("nfse:infNFSe", NS)
    else:
        inf = root.find("nfse:NFSe/nfse:infNFSe", NS) or root.find("nfse:infNFSe", NS)

    if inf is None:
        return None

    dps      = inf.find("nfse:DPS/nfse:infDPS", NS)
    prest    = dps.find("nfse:prest", NS)   if dps is not None else None
    vals_dps = dps.find("nfse:valores", NS) if dps is not None else None
    vals_inf = inf.find("nfse:valores", NS)

    data_raw = _txt(dps, "dhEmi") if dps is not None else _txt(inf, "dhProc")

    v_serv = ""
    if vals_dps is not None:
        v_serv = (
            _txt(vals_dps, "vServPrest", "vServ")
            or _txt(vals_dps, "vServPrest", "vServTot")
        )
    v_liq = _txt(vals_inf, "vLiq") if vals_inf is not None else ""

    nome = (
        (_txt(prest, "xNome") if prest is not None else "")
        or _txt(inf, "emit", "xNome")
        or (_txt(prest, "xFant") if prest is not None else "")
    )
    cnpj = (
        (_txt(prest, "CNPJ") if prest is not None else "")
        or _txt(inf, "emit", "CNPJ")
    )

    try:
        valor = float(v_serv or v_liq or "0")
    except ValueError:
        valor = 0.0

    return {
        "chave":        chave,
        "obra":         "",   # preenchido abaixo
        "numero":       _txt(inf, "nNFSe"),
        "data_emissao": data_raw[:10] if data_raw else "",
        "cnpj_prest":   cnpj,
        "nome_prest":   nome,
        "valor":        valor,
    }


for obra_key, xml_dir in XML_DIRS.items():
    print(f"\nObra: {obra_key}")
    print(f"  Pasta XMLs: {xml_dir}")

    if not os.path.isdir(xml_dir):
        print("  Pasta não encontrada, pulando.")
        continue

    # 1. Carrega estado atual do KV
    pendentes_kv = cf.carregar_pendentes(obra_key)
    lancadas_kv  = cf.carregar_lancadas(obra_key)
    chaves_lancadas = {n["chave"] for n in lancadas_kv}
    chaves_pendentes = {n["chave"] for n in pendentes_kv}

    print(f"  Pendentes no KV : {len(pendentes_kv)}")
    print(f"  Lancadas no KV  : {len(lancadas_kv)}")

    # 2. Parseia todos os XMLs locais
    todas_notas = []
    arquivos = [f for f in os.listdir(xml_dir) if f.lower().endswith(".xml")]
    print(f"  XMLs encontrados: {len(arquivos)}")

    for nome_arquivo in arquivos:
        caminho = os.path.join(xml_dir, nome_arquivo)
        nota = parsear_xml_local(caminho)
        if nota:
            nota["obra"] = obra_key
            todas_notas.append(nota)

    print(f"  XMLs parseados  : {len(todas_notas)}")

    # 3. Candidatas: novas + já lançadas sem numero_titulo
    candidatas_novas    = [n for n in todas_notas if n["chave"] not in chaves_lancadas]
    lancadas_sem_titulo = [n for n in lancadas_kv if not n.get("numero_titulo")]
    print(f"  Candidatas novas         : {len(candidatas_novas)}")
    print(f"  Lancadas sem titulo      : {len(lancadas_sem_titulo)}")

    para_verificar = candidatas_novas + lancadas_sem_titulo
    if not para_verificar:
        print("  Nada a verificar.")
        continue

    # 4. Verifica no Sienge
    print("  Consultando Sienge...")
    confirmadas = sienge.verificar_lancadas(para_verificar)  # dict {chave: numero_titulo}
    print(f"  Confirmadas pelo Sienge: {len(confirmadas)}")

    # 5a. Atualiza as já lançadas sem numero_titulo
    mapa_notas = {n["chave"]: n for n in todas_notas}
    atualizadas = 0
    for nota in lancadas_kv:
        if not nota.get("numero_titulo") and nota["chave"] in confirmadas:
            nota["numero_titulo"] = confirmadas[nota["chave"]]
            atualizadas += 1
            print(f"    ~ Nr {nota.get('numero','')} | Titulo {confirmadas[nota['chave']]} | {nota.get('nome_prest','')[:30]}")

    # 5b. Adiciona novas lançadas detectadas
    adicionadas = 0
    for chave, numero_titulo in confirmadas.items():
        if chave not in chaves_lancadas:
            nota = mapa_notas.get(chave)
            if nota:
                nota = {**nota, "numero_titulo": numero_titulo}
                pendente_ref = next((p for p in pendentes_kv if p["chave"] == chave), None)
                if pendente_ref and pendente_ref.get("has_pdf"):
                    nota["has_pdf"] = True
                lancadas_kv.append(nota)
                chaves_lancadas.add(chave)
                adicionadas += 1
                print(f"    + Nr {nota.get('numero','')} | Titulo {numero_titulo} | {nota.get('nome_prest','')[:30]}")

    print(f"  Atualizadas com titulo: {atualizadas}")
    print(f"  Total adicionadas     : {adicionadas}")
    print(f"  Total lancadas KV     : {len(lancadas_kv)}")

    # 6. Salva no KV
    if adicionadas > 0 or atualizadas > 0:
        estado = cf.carregar_estado(obra_key)
        cf.sincronizar(
            obra_key           = obra_key,
            pendentes          = pendentes_kv,
            ultimo_nsu         = estado.get("ultimo_nsu", 0),
            ultima_verificacao = estado.get("ultima_verificacao", ""),
            lancadas           = lancadas_kv,
        )
        print("  KV atualizado.")
    else:
        print("  Nada alterado.")

print("\nConcluido.")
