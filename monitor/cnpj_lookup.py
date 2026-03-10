"""
Lookup de nome de empresa pelo CNPJ via API publica (cnpj.ws).
Limite: 3 consultas por minuto. Aguarda automaticamente ao receber 429.
"""

import time
import requests

_cache: dict[str, str] = {}

DELAY      = 21    # segundos entre chamadas (3/min = 20s + margem)
DELAY_429  = 62    # aguarda ao receber 429


def buscar_nome(cnpj: str) -> str:
    """Retorna o nome da empresa ou string vazia se nao encontrar."""
    cnpj_digits = "".join(c for c in (cnpj or "") if c.isdigit())
    if len(cnpj_digits) != 14:
        return ""

    if cnpj_digits in _cache:
        return _cache[cnpj_digits]

    for tentativa in range(3):
        try:
            time.sleep(DELAY)
            r = requests.get(
                f"https://publica.cnpj.ws/cnpj/{cnpj_digits}",
                timeout=10,
                headers={"Accept": "application/json"},
            )
            if r.status_code == 200:
                data = r.json()
                nome = data.get("razao_social") or data.get("nome_fantasia") or ""
                _cache[cnpj_digits] = nome
                return nome
            if r.status_code == 429:
                print(f"      429 rate limit — aguardando {DELAY_429}s...")
                time.sleep(DELAY_429)
                continue
        except Exception:
            pass

    _cache[cnpj_digits] = ""
    return ""


def preencher_nomes(notas: list[dict]) -> list[dict]:
    """Preenche nome_prest vazio via lookup de CNPJ. Retorna lista atualizada."""
    sem_nome = [n for n in notas if not n.get("nome_prest")]
    if not sem_nome:
        return notas

    # Deduplica CNPJs para minimizar chamadas
    cnpjs_unicos = list(dict.fromkeys(n.get("cnpj_prest", "") for n in sem_nome))
    print(f"    Buscando nomes para {len(cnpjs_unicos)} CNPJs distintos (~{len(cnpjs_unicos) * DELAY // 60 + 1} min)...")

    for nota in sem_nome:
        nome = buscar_nome(nota.get("cnpj_prest", ""))
        if nome:
            nota["nome_prest"] = nome

    encontrados = sum(1 for n in sem_nome if n.get("nome_prest"))
    print(f"    Nomes encontrados: {encontrados}/{len(sem_nome)}")
    return notas
