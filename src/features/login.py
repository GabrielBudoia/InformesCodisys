import time
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.keys import Keys

def limpar_e_preencher(elemento, texto):
    """Limpa o campo e preenche com o texto fornecido"""
    elemento.click()
    elemento.send_keys(Keys.CONTROL, "a")
    elemento.send_keys(Keys.DELETE)
    time.sleep(0.3)
    elemento.send_keys(texto)

def fazer_login(driver, email, senha, url_login):
    """
    Realiza login no sistema Codisys.

    Usa Selenium para preencher email e senha.
    Verifica se já está logado e evita login desnecessário.
    """
    print("\n================ LOGIN ================")

    wait = WebDriverWait(driver, 30)

    # 🔎 Verifica se já está logado
    try:
        ja_logado = driver.execute_script("""
            return typeof Combobox_Empresa !== 'undefined';
        """)
        if ja_logado:
            print("[DEBUG] Já está logado. Pulando login.")
            print("=======================================\n")
            return driver
    except:
        pass

    print("[DEBUG] Acessando página de login...")
    driver.get(url_login)
    time.sleep(2)

    # 🔎 Caso precise, vai direto para tela de login
    driver.get("https://support.codisysdc.com/Account/Login")
    time.sleep(1)

    print("[DEBUG] Preenchendo email...")
    campo_email = wait.until(EC.element_to_be_clickable((By.ID, "Email_I")))
    limpar_e_preencher(campo_email, email)

    print("[DEBUG] Preenchendo senha...")
    campo_senha = wait.until(EC.element_to_be_clickable((By.ID, "Password_I")))
    limpar_e_preencher(campo_senha, senha)

    print("[DEBUG] Clicando em confirmar login...")
    botao_confirmar = wait.until(EC.element_to_be_clickable((By.ID, "Button_Confirmar")))
    botao_confirmar.click()

    # 🔎 Confirma login real esperando objeto DevExpress aparecer
    try:
        wait.until(lambda d: d.execute_script(
            "return typeof Combobox_Empresa !== 'undefined';"
        ))
        print("[DEBUG] Login confirmado com sucesso.")
    except:
        print("[ERRO] Login aparentemente falhou.")
        raise Exception("Login não confirmado.")

    print("=======================================\n")
    return driver
