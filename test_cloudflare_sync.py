#!/usr/bin/env python3
"""
Script de teste: Verifica se consegue sincronizar dados com o Cloudflare Worker
"""

import os
import json
import sys
sys.path.insert(0, os.path.dirname(__file__))

from monitor.cloudflare import CloudflareClient

# Variáveis de ambiente
CF_WORKER_URL = os.environ.get("CF_WORKER_URL", "").strip()
CF_API_TOKEN = os.environ.get("CF_API_TOKEN", "").strip()

print("="*80)
print("TESTE DE SINCRONIZAÇÃO CLOUDFLARE")
print("="*80)

# 1. Verificar se variáveis estão definidas
print("\n[1] VERIFICANDO VARIÁVEIS DE AMBIENTE")
print(f"  CF_WORKER_URL: {CF_WORKER_URL if CF_WORKER_URL else '❌ NÃO DEFINIDA'}")
print(f"  CF_API_TOKEN:  {CF_API_TOKEN[:20]+'...' if CF_API_TOKEN else '❌ NÃO DEFINIDA'}")

if not CF_WORKER_URL or not CF_API_TOKEN:
    print("\n❌ ERRO: Variáveis não definidas!")
    print("   Configure:")
    print("   export CF_WORKER_URL='https://...'")
    print("   export CF_API_TOKEN='token...'")
    sys.exit(1)

# 2. Criar cliente Cloudflare
print("\n[2] CRIANDO CLIENTE CLOUDFLARE")
try:
    cf = CloudflareClient(worker_url=CF_WORKER_URL, api_token=CF_API_TOKEN)
    print(f"  ✅ Cliente criado")
except Exception as e:
    print(f"  ❌ Erro ao criar cliente: {e}")
    sys.exit(1)

# 3. Testar leitura (GET)
print("\n[3] TESTANDO LEITURA - GET /api/pendentes")
try:
    dados = cf._carregar_obras_raw()
    print(f"  ✅ Conectou ao Worker")
    print(f"  📊 Obras encontradas: {len(dados)}")

    total_pendentes = 0
    for obra in dados:
        obra_key = obra.get("key", "?")
        pendentes = len(obra.get("pendentes", []))
        total_pendentes += pendentes
        print(f"     - {obra_key}: {pendentes} pendente(s)")

    print(f"  📈 TOTAL: {total_pendentes} notas pendentes")

    if total_pendentes == 0:
        print("\n  ⚠️  NENHUMA NOTA NO KV!")
except Exception as e:
    print(f"  ❌ Erro ao ler: {e}")
    print(f"     URL: {CF_WORKER_URL}/api/pendentes")

# 4. Testar escrita (POST)
print("\n[4] TESTANDO ESCRITA - POST /api/sync")
test_data = {
    "obra": "test",
    "pendentes": [
        {
            "tipo": "nfse",
            "chave": "999999999999999999999999999999999999999999999",
            "numero": "TEST001",
            "prestador_cnpj": "00000000000000",
            "prestador_nome": "TESTE LTDA",
            "valor": 1000.00
        }
    ],
    "ultimo_nsu": 999,
    "ultima_verificacao": "2026-04-06T16:30:00-03:00",
    "lancadas": []
}

try:
    cf.sincronizar(
        obra_key="test",
        pendentes=test_data["pendentes"],
        ultimo_nsu=999,
        ultima_verificacao="2026-04-06T16:30:00-03:00",
        lancadas=[]
    )
    print(f"  ✅ Sincronização bem-sucedida!")
    print(f"     Enviou 1 nota de teste para obra 'test'")
except Exception as e:
    print(f"  ❌ Erro ao sincronizar: {e}")
    print(f"     URL: {CF_WORKER_URL}/api/sync")
    print(f"     Método: POST")

# 5. Verificar se foi salvo
print("\n[5] VERIFICANDO SE FOI SALVO")
try:
    dados = cf._carregar_obras_raw()
    for obra in dados:
        if obra.get("key") == "test":
            print(f"  ✅ Obra 'test' encontrada com {len(obra.get('pendentes', []))} notas")
            break
    else:
        print(f"  ❌ Obra 'test' NÃO encontrada")
        print(f"     Obras disponíveis: {[o.get('key') for o in dados]}")
except Exception as e:
    print(f"  ❌ Erro ao verificar: {e}")

# 6. Resumo
print("\n" + "="*80)
print("RESUMO")
print("="*80)
print("""
Se todos os testes passaram (✅):
  → O Worker está funcionando
  → O KV está acessível
  → Problema pode estar na lógica de sincronização do monitor.main

Se houver erro (❌):
  → Verifique as credenciais Cloudflare
  → Verifique se o Worker está deployado
  → Verifique se o KV namespace está configurado
""")
