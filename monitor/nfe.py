"""
Cliente NF-e — consulta notas recebidas via DistDFeInt (SOAP mTLS).
Retorna resumos (resNFe) e eventos de cancelamento (procEventoNFe).
"""

import base64
import gzip
import time
import xml.etree.ElementTree as ET

import requests
from requests_pkcs12 import Pkcs12Adapter

WSDL_URL   = "https://www1.nfe.fazenda.gov.br/NFeDistribuicaoDFe/NFeDistribuicaoDFe.asmx"
SOAP_ACTION = "http://www.portalfiscal.inf.br/nfe/wsdl/NFeDistribuicaoDFe/nfeDistDFeInteresse"

NS_NFE  = "http://www.portalfiscal.inf.br/nfe"
NS_WSDL = "http://www.portalfiscal.inf.br/nfe/wsdl/NFeDistribuicaoDFe"

MAX_TENTATIVAS    = 5
DELAY_RETRY_429   = 30
DELAY_ENTRE_LOTES = 3

# cStat da resposta
CSTAT_SEM_DOC       = "137"   # Nenhum documento localizado (mas ultNSU ainda é atualizado)
CSTAT_COM_DOC       = "138"   # Documento localizado
CSTAT_CONS_INDEVIDO = "656"   # Consumo indevido — SEFAZ pede para usar ultNSU e aguardar 1h


class NFeClient:
    def __init__(self, cert_path: str, cert_senha: str, cnpj: str, cuf: str = "42"):
        self.cnpj = cnpj
        self.cuf  = cuf
        self.session = requests.Session()
        self.session.mount(
            "https://www1.nfe.fazenda.gov.br",
            Pkcs12Adapter(pkcs12_filename=cert_path, pkcs12_password=cert_senha),
        )
        self.session.headers.update({
            "Content-Type": f'application/soap+xml; charset=utf-8; action="{SOAP_ACTION}"',
        })

    def consultar_novas(self, nsu_inicial: int) -> tuple[list[dict], list[dict], int]:
        """
        Retorna (notas, cancelamentos, ultimo_nsu).
        notas: lista de dicts com campos compatíveis com NFS-e (chave, numero, etc.)
        cancelamentos: lista de dicts {tipo, chave}
        """
        notas        = []
        cancelamentos = []
        nsu          = nsu_inicial

        while True:
            dados = self._consultar_lote(nsu)
            if dados is None:
                break

            cstat   = dados.get("cStat", "")
            ult_nsu = int(dados.get("ultNSU", "0") or "0")

            if cstat == CSTAT_SEM_DOC:
                nsu = max(nsu, ult_nsu)
                print(f"    [NF-e] Sem novos documentos. ultNSU={nsu}.")
                break

            if cstat == CSTAT_CONS_INDEVIDO:
                nsu = max(nsu, ult_nsu)
                print(f"    [NF-e] Rate limit (656) — aguarde ~1h. ultNSU={nsu} salvo.")
                break

            docs = dados.get("docs", [])
            if not docs:
                break

            for doc in docs:
                schema = doc.get("schema", "")
                xml_b64 = doc.get("xml_b64", "")
                if not xml_b64:
                    continue

                try:
                    raw = base64.b64decode(xml_b64)
                    if raw[:2] == b"\x1f\x8b":
                        raw = gzip.decompress(raw)
                except Exception:
                    continue

                if "procEventoNFe" in schema:
                    resultado = self._parsear_evento(raw)
                    if resultado:
                        cancelamentos.append(resultado)
                elif "resNFe" in schema or "procNFe" in schema:
                    resultado = self._parsear_nota(raw, schema)
                    if resultado:
                        notas.append(resultado)

            try:
                proximo = int(dados.get("ultNSU", "0") or "0")
            except ValueError:
                break

            if proximo <= nsu:
                break

            nsu = proximo
            print(f"    [NF-e] Lote processado. Próximo NSU: {nsu}")
            time.sleep(DELAY_ENTRE_LOTES)

        return notas, cancelamentos, nsu

    # ──────────────────────────────────────────
    # Internos
    # ──────────────────────────────────────────

    def _consultar_lote(self, nsu: int) -> dict | None:
        nsu_str = str(nsu).zfill(15)
        envelope = f"""<?xml version="1.0" encoding="utf-8"?>
<soap12:Envelope xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance"
                 xmlns:xsd="http://www.w3.org/2001/XMLSchema"
                 xmlns:soap12="http://www.w3.org/2003/05/soap-envelope">
  <soap12:Header>
    <nfeCabecMsg xmlns="{NS_WSDL}">
      <cUF>{self.cuf}</cUF>
      <versaoDados>1.01</versaoDados>
    </nfeCabecMsg>
  </soap12:Header>
  <soap12:Body>
    <nfeDistDFeInteresse xmlns="{NS_WSDL}">
      <nfeDadosMsg>
        <distDFeInt versao="1.01" xmlns="{NS_NFE}">
          <tpAmb>1</tpAmb>
          <cUFAutor>{self.cuf}</cUFAutor>
          <CNPJ>{self.cnpj}</CNPJ>
          <distNSU>
            <ultNSU>{nsu_str}</ultNSU>
          </distNSU>
        </distDFeInt>
      </nfeDadosMsg>
    </nfeDistDFeInteresse>
  </soap12:Body>
</soap12:Envelope>"""

        for tentativa in range(1, MAX_TENTATIVAS + 1):
            try:
                resp = self.session.post(WSDL_URL, data=envelope.encode("utf-8"), timeout=90)
            except requests.exceptions.Timeout:
                espera = 15 * tentativa
                print(f"    [NF-e] Timeout no NSU {nsu} (tentativa {tentativa}), aguardando {espera}s...")
                time.sleep(espera)
                continue
            except Exception as e:
                print(f"    [NF-e] Erro de conexão: {e}")
                return None

            if resp.status_code == 429:
                espera = DELAY_RETRY_429 * tentativa
                print(f"    [NF-e] 429 aguardando {espera}s...")
                time.sleep(espera)
                continue

            if resp.status_code != 200:
                print(f"    [NF-e] Erro HTTP {resp.status_code}")
                return None

            return self._parsear_resposta_soap(resp.text)

        return None

    def _parsear_resposta_soap(self, xml_text: str) -> dict | None:
        try:
            root = ET.fromstring(xml_text)
        except Exception:
            return None

        # Localiza retDistDFeInt dentro do envelope SOAP
        ret = None
        for el in root.iter(f"{{{NS_NFE}}}retDistDFeInt"):
            ret = el
            break
        if ret is None:
            return None

        def txt(tag):
            el = ret.find(f"{{{NS_NFE}}}{tag}")
            return (el.text or "").strip() if el is not None else ""

        cstat   = txt("cStat")
        ult_nsu = txt("ultNSU").lstrip("0") or "0"

        docs = []
        lote = ret.find(f"{{{NS_NFE}}}loteDistDFeInt")
        if lote is not None:
            for doc_el in lote.findall(f"{{{NS_NFE}}}docZip"):
                docs.append({
                    "schema": doc_el.get("schema", ""),
                    "nsu":    doc_el.get("NSU", ""),
                    "xml_b64": (doc_el.text or "").strip(),
                })

        return {"cStat": cstat, "ultNSU": ult_nsu, "docs": docs}

    def _parsear_nota(self, raw: bytes, schema: str) -> dict | None:
        """Parseia resNFe (resumo) ou procNFe (completo)."""
        try:
            root = ET.fromstring(raw)
        except Exception:
            return None

        NS = {"nfe": NS_NFE}

        def txt(*path):
            cur = root
            for tag in path:
                if cur is None:
                    return ""
                cur = cur.find(f"nfe:{tag}", NS)
            return (cur.text or "").strip() if cur is not None else ""

        # resNFe: campos diretos no root
        if "resNFe" in schema:
            chave = txt("chNFe")
            if not chave:
                return None
            # Só interessa NF-e de entrada (tpNF=0) ou saída destinada a nós (tpNF=1)
            # Para monitorar recebidas: qualquer uma que chegou no nosso DFe
            return {
                "chave":        chave,
                "numero":       txt("nNF"),
                "data_emissao": txt("dEmi")[:10] if txt("dEmi") else "",
                "cnpj_prest":   txt("CNPJ"),
                "nome_prest":   txt("xNome"),
                "valor":        txt("vNF"),
                "tipo":         "nfe",
            }

        # procNFe: estrutura mais complexa
        inf = root.find(".//{%s}infNFe" % NS_NFE)
        if inf is None:
            return None

        emit = inf.find(f"nfe:emit", NS)
        total = inf.find(f"nfe:total/nfe:ICMSTot", NS)

        def inf_txt(*path):
            cur = inf
            for tag in path:
                if cur is None:
                    return ""
                cur = cur.find(f"nfe:{tag}", NS)
            return (cur.text or "").strip() if cur is not None else ""

        ide = inf.find("nfe:ide", NS)

        return {
            "chave":        inf.get("Id", "").lstrip("NFe"),
            "numero":       inf_txt("ide", "nNF"),
            "data_emissao": (inf_txt("ide", "dhEmi") or inf_txt("ide", "dEmi"))[:10],
            "cnpj_prest":   emit.findtext(f"{{{NS_NFE}}}CNPJ", "") if emit is not None else "",
            "nome_prest":   emit.findtext(f"{{{NS_NFE}}}xNome", "") or emit.findtext(f"{{{NS_NFE}}}xFant", "") if emit is not None else "",
            "valor":        total.findtext(f"{{{NS_NFE}}}vNF", "") if total is not None else "",
            "tipo":         "nfe",
        }

    def _parsear_evento(self, raw: bytes) -> dict | None:
        """Parseia procEventoNFe — extrai cancelamentos (tpEvento 110111)."""
        try:
            root = ET.fromstring(raw)
        except Exception:
            return None

        NS = {"nfe": NS_NFE}

        inf = root.find(".//{%s}infEvento" % NS_NFE)
        if inf is None:
            return None

        tp_evento = (inf.findtext(f"{{{NS_NFE}}}tpEvento") or "").strip()
        if tp_evento not in ("110111", "110112"):  # 110111=Cancelamento, 110112=Cancelamento fora prazo
            return None

        chave = (inf.findtext(f"{{{NS_NFE}}}chNFe") or "").strip()
        det   = inf.find(f"{{{NS_NFE}}}detEvento")
        motivo = ""
        if det is not None:
            motivo = (det.findtext(f"{{{NS_NFE}}}xJust") or "").strip()

        print(f"    [NF-e Cancelamento] {chave[:25]}... | {motivo}")
        return {"tipo": "cancelamento", "chave": chave}
