"""
Cliente SEFAZ ADN — consulta NFS-e recebidas via mTLS.
Processa tudo em memoria: nenhum dado e gravado em disco.
"""

import base64
import gzip
import time
import xml.etree.ElementTree as ET

import requests
from requests_pkcs12 import Pkcs12Adapter

API_BASE = "https://adn.nfse.gov.br"
NS = {"nfse": "http://www.sped.fazenda.gov.br/nfse"}

MAX_TENTATIVAS    = 5
DELAY_RETRY_429   = 30   # segundos (multiplicado pela tentativa)
DELAY_ENTRE_LOTES = 3    # segundos entre paginas de NSU


class SefazClient:
    def __init__(self, cert_path: str, cert_senha: str):
        self.session = requests.Session()
        self.session.mount(
            API_BASE,
            Pkcs12Adapter(pkcs12_filename=cert_path, pkcs12_password=cert_senha),
        )
        self.session.headers.update({
            "Content-Type": "application/json",
            "Accept": "application/json",
        })

    def baixar_pdf(self, chave: str) -> bytes | None:
        """Baixa o DANFSe (PDF) de uma nota pelo chave de acesso. Retorna bytes ou None."""
        url = f"{API_BASE}/danfse/{chave}"
        for tentativa in range(1, MAX_TENTATIVAS + 1):
            try:
                resp = self.session.get(url, timeout=30)
            except Exception as e:
                print(f"    Erro ao baixar PDF {chave[:20]}...: {e}")
                return None
            if resp.status_code == 200:
                return resp.content
            if resp.status_code == 429:
                espera = DELAY_RETRY_429 * tentativa
                print(f"    429 aguardando {espera}s...")
                time.sleep(espera)
                continue
            print(f"    PDF {chave[:20]}... HTTP {resp.status_code}")
            return None
        return None

    def consultar_novas(self, nsu_inicial: int) -> tuple[list[dict], list[dict], int]:
        notas = []
        cancelamentos = []
        nsu = nsu_inicial

        while True:
            dados = self._get_lote(nsu)
            if dados is None:
                break

            status = dados.get("StatusProcessamento", "")
            if status == "NENHUM_DOCUMENTO_LOCALIZADO":
                print(f"    Sem documentos a partir do NSU {nsu}.")
                break

            lote = dados.get("LoteDFe") or []
            if not lote:
                break

            for item in lote:
                chave   = item.get("ChaveAcesso")
                xml_b64 = item.get("ArquivoXml")
                if chave and xml_b64:
                    resultado = self._parsear_xml(chave, xml_b64)
                    if resultado:
                        if resultado.get("tipo") == "cancelamento":
                            cancelamentos.append(resultado)
                        else:
                            notas.append(resultado)

            nsus = [item["NSU"] for item in lote if "NSU" in item]
            if not nsus:
                break

            proximo_nsu = max(nsus)
            if proximo_nsu <= nsu:
                break

            nsu = proximo_nsu
            print(f"    Lote processado. Proximo NSU: {nsu}")
            time.sleep(DELAY_ENTRE_LOTES)

        return notas, cancelamentos, nsu

    # ──────────────────────────────────────────
    # Internos
    # ──────────────────────────────────────────

    def _get_lote(self, nsu: int) -> dict | None:
        url = f"{API_BASE}/contribuintes/DFe/{nsu}"
        for tentativa in range(1, MAX_TENTATIVAS + 1):
            try:
                resp = self.session.get(url, timeout=30)
            except Exception as e:
                print(f"    Erro de conexao: {e}")
                return None

            if resp.status_code == 204:
                return None
            if resp.status_code == 429:
                espera = DELAY_RETRY_429 * tentativa
                print(f"    429 aguardando {espera}s (tentativa {tentativa})...")
                time.sleep(espera)
                continue
            if resp.status_code in (200, 404):
                return resp.json()

            print(f"    Erro HTTP {resp.status_code}")
            return None

        return None

    def _parsear_xml(self, chave: str, xml_b64: str) -> dict | None:
        """Decodifica Base64+Gzip e extrai campos relevantes em memoria."""
        try:
            raw = base64.b64decode(xml_b64)
            if raw[:2] == b"\x1f\x8b":
                raw = gzip.decompress(raw)
            root = ET.fromstring(raw)
        except Exception:
            return None

        # Detecta evento de cancelamento (root = <evento>, não <CompNFSe>)
        tag_raiz = root.tag.split("}")[-1]
        if tag_raiz == "evento":
            inf_evt = root.find("nfse:infEvento", NS)
            if inf_evt is not None:
                ped = inf_evt.find("nfse:pedRegEvento/nfse:infPedReg", NS)
                if ped is not None:
                    for cod_evt, label in [("e101101", "Cancelamento"), ("e101106", "Substituicao")]:
                        no_evt = ped.find(f"nfse:{cod_evt}", NS)
                        if no_evt is None:
                            continue
                        # chave da nota cancelada/substituída pode estar no evento ou no nó pai
                        el = no_evt.find("nfse:chNFSe", NS) or ped.find("nfse:chNFSe", NS)
                        chave_canc = (el.text or "").strip() if el is not None else chave
                        motivo_el = no_evt.find("nfse:xMotivo", NS)
                        motivo = (motivo_el.text or "").strip() if motivo_el is not None else ""
                        print(f"    [{label}] Removendo nota {chave_canc[:25]}... | {motivo}")
                        return {"tipo": "cancelamento", "chave": chave_canc}
            return None

        inf = root.find("nfse:infNFSe", NS)
        if inf is None:
            return None

        dps      = inf.find("nfse:DPS/nfse:infDPS", NS)
        prest    = dps.find("nfse:prest", NS)    if dps is not None else None
        serv     = dps.find("nfse:serv", NS)     if dps is not None else None
        vals_dps = dps.find("nfse:valores", NS)  if dps is not None else None
        vals_inf = inf.find("nfse:valores", NS)

        def txt(el, *path):
            cur = el
            for tag in path:
                if cur is None:
                    return ""
                cur = cur.find(f"nfse:{tag}", NS)
            return (cur.text or "").strip() if cur is not None else ""

        data_raw = txt(dps, "dhEmi") if dps is not None else txt(inf, "dhProc")

        v_serv = ""
        if vals_dps is not None:
            v_serv = (
                txt(vals_dps, "vServPrest", "vServ")
                or txt(vals_dps, "vServPrest", "vServTot")
            )
        v_liq = txt(vals_inf, "vLiq") if vals_inf is not None else ""

        # Nome do prestador: tenta vários caminhos (nem sempre presente no XML)
        nome = (
            (txt(prest, "xNome") if prest is not None else "")
            or txt(inf, "emit", "xNome")
            or txt(inf, "emit", "xFant")
            or (txt(prest, "xFant") if prest is not None else "")
            or txt(dps, "prest", "xNome")
            or txt(dps, "prest", "xFant")
            or txt(inf, "emiNome")
        )

        if not nome:
            # Debug: mostra tags disponíveis para diagnostico
            tags = [child.tag.split("}")[-1] for child in (inf or [])]
            tags_dps = [child.tag.split("}")[-1] for child in (dps or [])]
            tags_prest = [child.tag.split("}")[-1] for child in (prest or [])]
            print(f"    [DEBUG] Sem nome para CNPJ {chave[:14]} | inf={tags} | dps={tags_dps} | prest={tags_prest}")

        cnpj = (
            (txt(prest, "CNPJ") if prest is not None else "")
            or txt(inf, "emit", "CNPJ")
        )

        return {
            "chave":        chave,
            "numero":       txt(inf, "nNFSe"),
            "data_emissao": data_raw[:10] if data_raw else "",
            "cnpj_prest":   cnpj,
            "nome_prest":   nome,
            "descricao":    txt(serv, "cServ", "xDescServ") if serv is not None else "",
            "valor":        v_serv or v_liq,
        }
