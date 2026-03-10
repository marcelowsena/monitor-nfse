"""
Cliente Sienge — verifica quais NFS-e já foram lançadas como títulos.
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
        Recebe lista de notas (cada uma com 'chave' e 'cnpj_prest' e 'numero').
        Retorna dict {chave: numero_titulo_sienge} para notas já lançadas.
        O numero_titulo é o ID interno do título no Sienge.
        """
        if not notas:
            return {}

        # CNPJs únicos dos prestadores
        cnpjs = {_limpar(n.get("cnpj_prest", "")) for n in notas}
        cnpjs.discard("")

        # Mapeia CNPJ → [creditorId]
        mapa_cnpj = self._credores_por_cnpj(cnpjs)

        # Busca títulos NFS-e de cada credor
        titulos = []
        for cnpj, ids in mapa_cnpj.items():
            for cid in ids:
                titulos.extend(self._titulos_por_credor(cid, cnpj))

        # Monta índices de match: chave_limpa → id_titulo e (cnpj, doc) → id_titulo
        chaves_sienge = {_limpar(t["chave"]): t["id"] for t in titulos if t.get("chave")}
        pares_sienge  = [
            (_limpar(t["cnpj"]), _normalizar(t["doc"]), t["id"])
            for t in titulos
            if _limpar(t["cnpj"]) and _normalizar(t["doc"])
        ]

        # Verifica cada nota
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

    # ──────────────────────────────────────────
    # Internos
    # ──────────────────────────────────────────

    def _credores_por_cnpj(self, cnpjs: set) -> dict:
        """Pagina /creditors e retorna {cnpj: [ids]}."""
        mapa = {c: [] for c in cnpjs}
        offset = 0
        while True:
            r = requests.get(
                f"{SIENGE_BASE}/creditors",
                auth=self.auth,
                timeout=30,
                params={"limit": 200, "offset": offset},
            )
            if r.status_code != 200:
                break
            items = r.json().get("results", [])
            if not items:
                break
            for c in items:
                cnpj = _limpar(c.get("cnpj") or c.get("cpf") or "")
                if cnpj in mapa:
                    mapa[cnpj].append(c["id"])
            offset += 200
        return mapa

    def _titulos_por_credor(self, credor_id: int, cnpj: str) -> list[dict]:
        """Busca todos os títulos NFS-e de um credor."""
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
                    "documentIdentificationId": "NFSE",
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
