"""Utilitários para carregar configuração de obras."""

import json
import os


def carregar_obras() -> dict:
    """Carrega configuração de obras do arquivo obras.json."""
    caminho = os.path.join(os.path.dirname(__file__), "..", "obras.json")
    with open(caminho, encoding="utf-8") as f:
        return json.load(f)
