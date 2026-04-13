import time
import os
from datetime import datetime, timedelta
from selenium.webdriver.support.ui import WebDriverWait

DOWNLOAD_TIMEOUT = 180

# ==========================
# ESPERAS INTELIGENTES (AJAX + DevExpress)
# ==========================
def esperar_ajax(driver, timeout=60):
    WebDriverWait(driver, timeout).until(
        lambda d: d.execute_script(
            "return (typeof jQuery !== 'undefined') ? jQuery.active == 0 : true;"
        )
    )

def esperar_callback_devexpress(driver, timeout=60):
    WebDriverWait(driver, timeout).until(
        lambda d: d.execute_script(
            "return (typeof ASPx !== 'undefined' && ASPx.GetControlCollection && !ASPx.GetControlCollection().InCallback());"
        )
    )

def esperar_grid_pronto(driver, timeout=60):
    WebDriverWait(driver, timeout).until(
        lambda d: d.execute_script(
            "return (typeof GridConsolaTickets !== 'undefined' && document.getElementById('GridConsolaTickets'));"
        )
    )

def esperar_estavel(driver):
    esperar_ajax(driver)
    esperar_callback_devexpress(driver)
    esperar_grid_pronto(driver)

# ==========================
# DOWNLOAD CONTROLADO
# ==========================
def esperar_download_novo(pasta, inicio, extensao=".xlsx", timeout=DOWNLOAD_TIMEOUT):
    print(f"[DEBUG] Aguardando novo download ({extensao})...")
    fim = time.time() + timeout
    while time.time() < fim:
        arquivos = [
            os.path.join(pasta, f)
            for f in os.listdir(pasta)
            if f.endswith(extensao) and os.path.getmtime(os.path.join(pasta, f)) > inicio
        ]
        temp = [f for f in os.listdir(pasta) if f.endswith(".crdownload")]
        if arquivos and not temp:
            print(f"[DEBUG] Download concluído: {os.path.basename(arquivos[0])}")
            return arquivos[0]
        time.sleep(1)
    return None

# ==========================
# FILTROS (EMPRESAS + ESTADOS)
# ==========================
def abrir_filtros(driver):
    driver.execute_script("if(typeof Show_Filters==='function') Show_Filters();")
    time.sleep(1)

def preencher_combo(driver, input_id, valores):
    """Preenche um input de tipo DevExpress multi-select"""
    texto = " ; ".join(valores)
    driver.execute_script(f"""
        var input = document.getElementById('{input_id}_I');
        if(input){{
            input.value=''; 
            input.value=arguments[0]; 
            input.dispatchEvent(new Event('change'));
        }}
    """, texto)
    esperar_estavel(driver)

def aplicar_datas(driver, meses=8, tentativas=3):

    from dateutil.relativedelta import relativedelta

    data_ate = datetime.now()
    data_desde = data_ate - relativedelta(months=meses)

    desde = data_desde.strftime("%d/%m/%Y")
    ate = data_ate.strftime("%d/%m/%Y")

    print(f"[DEBUG] Tentando aplicar datas {desde} até {ate}")

    for tentativa in range(tentativas):

        try:

            esperar_estavel(driver)

            driver.execute_script("""
                if(typeof DateEdit_DesdeFecha !== 'undefined'){
                    DateEdit_DesdeFecha.SetText(arguments[0]);
                    DateEdit_DesdeFecha.RaiseValueChanged();
                }

                if(typeof DateEdit_HastaFecha !== 'undefined'){
                    DateEdit_HastaFecha.SetText(arguments[1]);
                    DateEdit_HastaFecha.RaiseValueChanged();
                }
            """, desde, ate)

            time.sleep(2)

            desde_atual = driver.execute_script(
                "return DateEdit_DesdeFecha.GetText();"
            )

            ate_atual = driver.execute_script(
                "return DateEdit_HastaFecha.GetText();"
            )

            print(f"[DEBUG] Atual no sistema: {desde_atual} até {ate_atual}")

            if desde_atual == desde and ate_atual == ate:

                print("[DEBUG] Datas aplicadas com sucesso")
                return True

        except Exception as e:

            print(f"[WARN] tentativa {tentativa+1} falhou: {e}")

        time.sleep(2)

    raise Exception("Não foi possível aplicar datas após várias tentativas.")

def aplicar_filtros(driver):
    driver.execute_script("if(typeof button_Aceptar_Filtros_Init==='function') button_Aceptar_Filtros_Init();")
    esperar_estavel(driver)

# ==========================
# EXPORTAÇÃO
# ==========================
def exportar(driver):
    formatos = [("Export to XLS", ".xls"), ("Export to XLSX", ".xlsx"), ("Export to CSV", ".csv")]
    esperar_estavel(driver)
    for titulo, extensao in formatos:
        resultado = driver.execute_script(f"""
            try {{
                var el = document.querySelector("span[title='{titulo}']");
                if(el){{ el.click(); return "OK"; }} else {{ return "NAO_ENCONTRADO"; }}
            }} catch(e){{ return "ERRO_JS: "+e.message; }}
        """)
        if resultado == "OK":
            print(f"[DEBUG] Export acionado: {titulo}")
            return extensao
    raise Exception("Falha ao acionar exportação XLS/XLSX/CSV.")

# ==========================
# RENOMEAR ARQUIVO
# ==========================
def renomear_arquivo(arquivo, empresa_nome):
    if not arquivo:
        return None
    data_str = datetime.now().strftime("%d-%m-%Y")
    pasta = os.path.dirname(arquivo)
    ext = os.path.splitext(arquivo)[1]
    novo_nome = f"{empresa_nome.upper()} - {data_str}{ext}"
    novo_caminho = os.path.join(pasta, novo_nome)
    contador = 1
    while os.path.exists(novo_caminho):
        novo_nome = f"{empresa_nome.upper()} - {data_str} ({contador}){ext}"
        novo_caminho = os.path.join(pasta, novo_nome)
        contador += 1
    os.rename(arquivo, novo_caminho)
    print(f"[DEBUG] Arquivo renomeado: {novo_caminho}")
    return novo_caminho

# ==========================
# BAIXAR RELATÓRIO COMPLETO
# ==========================
def baixar_relatorio(driver, empresas, estados, pasta_download, empresa_tag="EMPRESA"):
    print(f"\n=========== BAIXANDO RELATÓRIO ({empresa_tag}) ===========")
    try:
        inicio_download = time.time()
        abrir_filtros(driver)
        # Preencher empresas
        preencher_combo(driver, "checkComboBox_Empresa", empresas)
        # Preencher estados
        preencher_combo(driver, "checkComboBox_Estados", estados)
        aplicar_datas(driver)
        aplicar_filtros(driver)
        extensao = exportar(driver)
        arquivo = esperar_download_novo(pasta_download, inicio_download, extensao=extensao)
        arquivo_final = renomear_arquivo(arquivo, empresa_tag)
        if arquivo_final:
            print(f"[SUCESSO] Relatório baixado e renomeado: {arquivo_final}")
        else:
            print("[ERRO] Nenhum arquivo foi baixado.")
        return arquivo_final
    except Exception as e:
        print(f"[ERRO CRÍTICO] {e}")
        return None
    finally:
        print("=======================================================\n")
