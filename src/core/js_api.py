def resetar_filtros(driver):
    print("[DEBUG] JS: Resetear_Filtros()")
    driver.execute_script("Resetear_Filtros();")

def selecionar_empresa(driver, empresa):
    print(f"[DEBUG] JS: Selecionando empresa {empresa}")
    driver.execute_script(f"""
        Combobox_Empresa.UnselectAll();
        Combobox_Empresa.SelectValues(['{empresa.upper()}']);
        updateText_Empresa();
    """)

def preencher_datas(driver, data_desde, data_ate):
    print(f"[DEBUG] JS: Set datas {data_desde} - {data_ate}")
    driver.execute_script(f"DateEdit_DesdeFecha.SetValue('{data_desde}');")
    driver.execute_script(f"DateEdit_HastaFecha.SetValue('{data_ate}');")

def aplicar_filtros(driver):
    print("[DEBUG] JS: button_Aceptar_Filtros_Init()")
    driver.execute_script("button_Aceptar_Filtros_Init();")
