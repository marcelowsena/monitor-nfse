"""
Cliente Sienge — verifica quais NFS-e / NF-e já foram lançadas como títulos.
Usa creditorId como filtro para evitar buscar a base inteira.
"""

import re
import requests
from requests.auth import HTTPBasicAuth

SIENGE_BASE = "https://api.sienge.com.br/trust/public/api/v1"


class SiengeClient:
    def __init__(self, usuario: str, senha: str):
        self.auth = HTTPBasicAuth(usuario, senha)

    def verificar_lancadas(self, notas: list[dict]) -> dict[str, int]:
        """
        Recebe lista de notas NFS-e. Retorna {chave: id_titulo} para as já lançadas.
        """
        if not notas:
            return {}
        cnpjs = {_limpar(n.get("cnpj_prest", "")) for n in notas}
        cnpjs.discard("")
        mapa_cnpj = self._credores_por_cnpj(cnpjs)
        titulos = self._buscar_titulos(mapa_cnpj, "NFSE")
        return self._match(notas, titulos)

    def verificar_lancadas_nfe(self, notas: list[dict]) -> dict[str, int]:
        """
        Igual a verificar_lancadas mas busca títulos com documentIdentificationId=NFE.
        """
        if not notas:
            return {}
        cnpjs = {_limpar(n.get("cnpj_prest", "")) for n in notas}
        cnpjs.discard("")
        mapa_cnpj = self._credores_por_cnpj(cnpjs)
        titulos = self._buscar_titulos(mapa_cnpj, "NFE")
        return self._match(notas, titulos)

    def verificar_lancadas_ambas(
        self,
        notas_nfse: list[dict],
        notas_nfe:  list[dict],
    ) -> tuple[dict[str, int], dict[str, int]]:
        """
        Verifica NFS-e e NF-e em uma única passagem pelo /creditors.
        Retorna (lancadas_nfse, lancadas_nfe).
        Reduz pela metade as chamadas ao Sienge quando ambas têm notas.
        """
        todas = notas_nfse + notas_nfe
        if not todas:
            return {}, {}

        cnpjs = {_limpar(n.get("cnpj_prest", "")) for n in todas}
        cnpjs.discard("")

        # Uma única paginação de credores para todos os CNPJs
        mapa_cnpj = self._credores_por_cnpj(cnpjs)

        titulos_nfse = self._buscar_titulos(mapa_cnpj, "NFSE") if notas_nfse else []
        titulos_nfe  = self._buscar_titulos(mapa_cnpj, "NFE")  if notas_nfe  else []

        return self._match(notas_nfse, titulos_nfse), self._match(notas_nfe, titulos_nfe)

    # ──────────────────────────────────────────
    # Internos
    # ──────────────────────────────────────────

    def _credores_por_cnpj(self, cnpjs: set) -> dict:
        """Busca credores por CNPJ usando o filtro da API (uma chamada por CNPJ)."""
        mapa = {c: [] for c in cnpjs}
        for cnpj in cnpjs:
            offset = 0
            while True:
                r = requests.get(
                    f"{SIENGE_BASE}/creditors",
                    auth=self.auth,
                    timeout=30,
                    params={"cnpj": cnpj, "limit": 200, "offset": offset},
                )
                if r.status_code != 200:
                    break
                items = r.json().get("results", [])
                if not items:
                    break
                for c in items:
                    mapa[cnpj].append(c["id"])
                if len(items) < 200:
                    break
                offset += 200
        return mapa

    def _buscar_titulos(self, mapa_cnpj: dict, doc_id: str) -> list[dict]:
        """Busca todos os títulos de cada credor para o tipo de documento dado."""
        titulos = []
        for cnpj, ids in mapa_cnpj.items():
            for cid in ids:
                titulos.extend(self._titulos_por_credor(cid, cnpj, doc_id))
        return titulos

    def _titulos_por_credor(self, credor_id: int, cnpj: str, doc_id: str) -> list[dict]:
        titulos = []
        offset = 0
        while True:
            r = requests.get(
                f"{SIENGE_BASE}/bills",
                auth=self.auth,
                timeout=30,
                params={
                    "startDate":                "2022-01-01",
                    "endDate":                  "2030-12-31",
                    "documentIdentificationId": doc_id,
                    "creditorId":               credor_id,
                    "limit":                    200,
                    "offset":                   offset,
                },
            )
            if r.status_code != 200:
                break
            items = r.json().get("results", [])
            if not items:
                break
            for item in items:
                titulos.append({
                    "id":    item.get("id") or 0,
                    "cnpj":  cnpj,
                    "doc":   item.get("documentNumber") or "",
                    "chave": item.get("accessKeyNumber") or "",
                })
            offset += 200
        return titulos

    def _match(self, notas: list[dict], titulos: list[dict]) -> dict[str, int]:
        """Monta índice de títulos e verifica cada nota."""
        if not notas:
            return {}
        chaves_sienge = {_limpar(t["chave"]): t["id"] for t in titulos if t.get("chave")}
        pares_sienge  = [
            (_limpar(t["cnpj"]), _normalizar(t["doc"]), t["id"])
            for t in titulos
            if _limpar(t["cnpj"]) and _normalizar(t["doc"])
        ]

        lancadas: dict[str, int] = {}
        for nota in notas:
            chave_n = _limpar(nota.get("chave", ""))
            cnpj_n  = _limpar(nota.get("cnpj_prest", ""))
            num_n   = _normalizar(nota.get("numero", ""))

            if chave_n and chave_n in chaves_sienge:
                lancadas[nota["chave"]] = chaves_sienge[chave_n]
                continue

            for (cnpj_s, doc_s, id_s) in pares_sienge:
                if cnpj_n == cnpj_s and _numeros_batem(num_n, doc_s):
                    lancadas[nota["chave"]] = id_s
                    break

        return lancadas


# ──────────────────────────────────────────────────
# Funções de normalização (sem estado, reutilizáveis)
# ──────────────────────────────────────────────────

def _limpar(s: str) -> str:
    """Remove qualquer caractere não-dígito."""
    return re.sub(r"\D", "", s or "")


def _normalizar(s: str) -> str:
    """Remove não-dígitos e zeros à esquerda."""
    digits = _limpar(s)
    return str(int(digits)) if digits else ""


def _numeros_batem(a: str, b: str) -> bool:
    """
    Match com tolerância:
    - Exato normalizado
    - Sufixo: '1900000006436' == '6436'
    """
    if not a or not b:
        return False
    return a == b or a.endswith(b) or b.endswith(a)
