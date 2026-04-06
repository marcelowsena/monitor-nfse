"""
Baixar PDFs de NFS-e via portal público https://www.nfse.gov.br/consultapublica
Sem necessidade de certificado - apenas chave de acesso.
"""

import time
import requests
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.options import Options
from webdriver_manager.chrome import ChromeDriverManager
from selenium.webdriver.chrome.service import Service


def baixar_pdf_portal(chave: str, timeout: int = 30) -> bytes | None:
    """
    Baixa PDF de uma NFS-e usando o portal público.

    Args:
        chave: Chave de acesso da NFS-e (50 dígitos)
        timeout: Timeout em segundos

    Returns:
        Bytes do PDF ou None se falhar
    """
    print(f"  Abrindo navegador para chave: {chave[:20]}...")

    chrome_options = Options()
    chrome_options.add_argument("--no-sandbox")
    chrome_options.add_argument("--disable-dev-shm-usage")
    chrome_options.add_argument("--disable-blink-features=AutomationControlled")
    chrome_options.add_argument("--user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36")
    chrome_options.add_argument("--disable-gpu")

    # Comentar a linha abaixo para ver o navegador:
    chrome_options.add_argument("--headless")

    try:
        driver = webdriver.Chrome(
            service=Service(ChromeDriverManager().install()),
            options=chrome_options
        )

        # Acessa portal
        driver.get("https://www.nfse.gov.br/consultapublica")
        print("  OK - Portal carregado")

        # Aguarda campo de chave
        wait = WebDriverWait(driver, timeout)
        campo_chave = wait.until(
            EC.presence_of_element_located((By.CSS_SELECTOR, "input[placeholder*='chave'], input[name*='chave']"))
        )
        print("  OK - Campo de chave encontrado")

        # Limpa e preenche
        campo_chave.clear()
        campo_chave.send_keys(chave)
        print("  OK - Chave preenchida")

        time.sleep(1)

        # Tenta clicar em Consultar (pode estar desabilitado por causa do captcha)
        try:
            btn_consultar = driver.find_element(By.XPATH, "//button[contains(text(), 'Consultar')]")
            btn_consultar.click()
            print("  OK - Clicou em Consultar")
        except:
            print("  AVISO - Não conseguiu clicar em Consultar (captcha pode estar bloqueando)")

        # Aguarda resultado
        time.sleep(3)

        # Tenta clicar em "Download DANFSe"
        try:
            btn_download = wait.until(
                EC.element_to_be_clickable((By.XPATH, "//button[contains(text(), 'Download DANFSe')]"))
            )
            print("  OK - Botão Download encontrado, clicando...")
            btn_download.click()

            # Aguarda download
            time.sleep(2)

            # Tenta achar o arquivo baixado
            # Nota: isso é complexo com Selenium. Alternativa melhor é tentar pegar a URL direto.

        except Exception as e:
            print(f"  ERRO ao clicar download: {e}")
            return None

        # Tira print da página (debug)
        driver.save_screenshot(f"/tmp/nfse_{chave[:10]}.png")
        print(f"  Screenshot salvo: /tmp/nfse_{chave[:10]}.png")

        driver.quit()

        return None  # Placeholder

    except Exception as e:
        print(f"  ERRO: {e}")
        import traceback
        traceback.print_exc()
        return None


def baixar_pdf_portal_requisicao(chave: str) -> bytes | None:
    """
    Alternativa: tenta acessar URL de download direto.
    Baseado em tentar descobrir o padrão de URL.
    """
    print(f"  Tentando requisição direta para: {chave[:20]}...")

    # Tenta vários padrões de URL possíveis
    urls_possiveis = [
        f"https://www.nfse.gov.br/portal/consulta-publica/download-pdf/{chave}",
        f"https://www.nfse.gov.br/download/danfse/{chave}",
        f"https://api.nfse.gov.br/danfse/{chave}",
    ]

    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
    }

    for url in urls_possiveis:
        try:
            resp = requests.get(url, timeout=10, headers=headers)
            if resp.status_code == 200 and len(resp.content) > 100:
                print(f"  OK - PDF obtido! URL: {url}")
                return resp.content
        except Exception as e:
            print(f"  Tentou {url}: {e}")

    print("  ERRO - Nenhuma URL funcionou")
    return None


if __name__ == "__main__":
    chave = "42091021215197671000161000000000214526040113016287"

    print(f"Testando download via portal público...")
    print(f"Chave: {chave}\n")

    # Tenta requisição direta primeiro (mais rápido)
    pdf = baixar_pdf_portal_requisicao(chave)

    if not pdf:
        # Se não conseguir, tenta com Selenium
        print("\nTentando com Selenium...\n")
        pdf = baixar_pdf_portal(chave)

    if pdf:
        print(f"\n✓ PDF baixado com sucesso! Tamanho: {len(pdf)} bytes")
    else:
        print(f"\n✗ Falha ao baixar PDF")
