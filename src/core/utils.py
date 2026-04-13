import time
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

def clicar(driver, by, value, timeout=30):
    print(f"[DEBUG] Tentando clicar em: {value}")
    wait = WebDriverWait(driver, timeout)
    try:
        elem = wait.until(EC.element_to_be_clickable((by, value)))
        driver.execute_script("arguments[0].click();", elem)
        time.sleep(0.3)
    except Exception as e:
        print(f"[ERRO] Falha ao clicar em {value}: {e}")
        raise

def esperar_devexpress(driver):
    print("[DEBUG] Aguardando DevExpress carregar...")
    for i in range(90):
        try:
            exists = driver.execute_script(
                "return (typeof Combobox_Empresa !== 'undefined' || typeof checkComboBox_Empresa !== 'undefined' || typeof Combobox_Empresa_LBSFEB !== 'undefined');"
            )
            print(f"[DEBUG] Tentativa {i+1}: DevExpress existe? {exists}")
            if exists:
                print("[DEBUG] DevExpress carregado!")
                return True
        except Exception as e:
            print(f"[DEBUG] Erro ao verificar DevExpress: {e}")
        time.sleep(0.5)
    raise Exception("[ERRO] DevExpress NÃO carregou após 90 tentativas.")
