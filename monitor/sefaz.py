"""
Cliente SEFAZ ADN — consulta NFS-e recebidas via mTLS.
Processa tudo em memória: nenhum dado é gravado em disco.
"""

import base64
import gzip
import time
import xml.etree.ElementTree as ET

import requests
from requests_pkcs12 import Pkcs12Adapter

API_BASE = "https://adn.nfse.gov.br"
NS = {"nfse": "http://www.sped.fazenda.gov.br/nfse"}

MAX_TENTATIVAS  = 5
DELAY_RETRY_429 = 30   # segundos (multiplicado pela tentativa)
DELAY_ENTRE_LOTES = 3  # segundos entre páginas de NSU


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

    def consultar_novas(self, nsu_inicial: int) -> tuple[list[dict], int]:
        """
        Consulta NFS-e a partir do NSU informado.
        Retorna (lista_de_notas, ultimo_nsu_processado).
        Notas são processadas em memória — nenhum arquivo é gerado.
        """
        notas = []
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
                    nota = self._parsear_xml(chave, xml_b64)
                    if nota:
                        notas.append(nota)

            nsus = [item["NSU"] for item in lote if "NSU" in item]
            if not nsus:
                break

            proximo_nsu = max(nsus)
            if proximo_nsu <= nsu:
                break

            nsu = proximo_nsu
            print(f"    Lote processado. Próximo NSU: {nsu}")
            time.sleep(DELAY_ENTRE_LOTES)

        return notas, nsu

    # ──────────────────────────────────────────
    # Internos
    # ──────────────────────────────────────────

    def _get_lote(self, nsu: int) -> dict | None:
        url = f"{API_BASE}/contribuintes/DFe/{nsu}"
        for tentativa in range(1, MAX_TENTATIVAS + 1):
            try:
                resp = self.session.get(url, timeout=30)
            except Exception as e:
                print(f"    Erro de conexão: {e}")
                return None

            if resp.status_code == 204:
                return None
            if resp.status_code == 429:
                espera = DELAY_RETRY_429 * tentativa
                print(f"    429 — aguardando {espera}s (tentativa {tentativa})...")
                time.sleep(espera)
                continue
            if resp.status_code in (200, 404):
                return resp.json()

            print(f"    Erro HTTP {resp.status_code}")
            return None

        return None

    def _parsear_xml(self, chave: str, xml_b64: str) -> dict | None:
        """Decodifica Base64+Gzip e extrai campos relevantes em memória."""
        try:
            raw = base64.b64decode(xml_b64)
            if raw[:2] == b"\x1f\x8b":
                raw = gzip.decompress(raw)
            root = ET.fromstring(raw)
        except Exception:
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

        return {
            "chave":        chave,
            "numero":       txt(inf, "nNFSe"),
            "data_emissao": data_raw[:10] if data_raw else "",   # só data, sem hora
            "cnpj_prest":   txt(prest, "CNPJ") if prest is not None else txt(inf, "emit", "CNPJ"),
            "nome_prest":   txt(prest, "xNome") if prest is not None else txt(inf, "emit", "xNome"),
            "descricao":    txt(serv, "cServ", "xDescServ") if serv is not None else "",
            "valor":        v_serv or v_liq,
        }
