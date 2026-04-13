import os
import time
from datetime import datetime, timedelta
import pandas as pd

from src.features.login import fazer_login
from src.features.filtros import baixar_relatorio
from src.config.config_loader import load_config
from src.core.browser import create_browser
from src.core.email_client import enviar_email

# ==========================
# FUNÇÕES AUXILIARES
# ==========================

def excel_date_to_datetime(serial):
    """Converte número serial Excel para datetime."""
    try:
        epoch = datetime(1899, 12, 30)
        return epoch + timedelta(days=serial)
    except:
        return None

def format_date_ddmmyy(value):
    """Transforma qualquer valor de data em string dd/MM/yy"""
    if isinstance(value, datetime):
        return value.strftime("%d/%m/%y")
    elif isinstance(value, (int, float)):
        dt = excel_date_to_datetime(value)
        return dt.strftime("%d/%m/%y") if dt else ""
    elif isinstance(value, str):
        parts = value.split(" ")[0].split("/")
        if len(parts) != 3:
            return ""
        day = parts[1].zfill(2)
        month = parts[0].zfill(2)
        year = parts[2][-2:]
        return f"{day}/{month}/{year}"
    else:
        return ""

def arquivo_mais_recente(pasta, prefixo):
    """Retorna o arquivo mais recente na pasta que começa com o prefixo"""
    arquivos = [os.path.join(pasta, f) for f in os.listdir(pasta) if f.upper().startswith(prefixo)]
    if not arquivos:
        return None
    return max(arquivos, key=os.path.getmtime)

# ==========================
# EXTRAÇÃO DE DADOS
# ==========================

def extrair_dados_planilha(arquivo, empresa_tag):
    if not arquivo or not os.path.exists(arquivo):
        print(f"[WARN] Arquivo não encontrado para {empresa_tag}: {arquivo}")
        return {}

    try:
        ext = os.path.splitext(arquivo)[1].lower()
        if ext == ".xls":
            df = pd.read_excel(arquivo, header=None, engine="xlrd")
        else:
            df = pd.read_excel(arquivo, header=None, engine="openpyxl")

        hoje_str = datetime.now().strftime("%d/%m/%y")

        df_f_str = df.iloc[:, 5].apply(format_date_ddmmyy)

        # Inicializa contadores
        P2 = P3 = P4 = P5 = P6 = P7 = P8 = P9 = 0
        # RESTALIA adicionais
        R_comercial = 0
        R_solicitudes = 0

        for idx, row in df.iterrows():
            valorM = str(row[12]).strip().upper()  # COLUNA M
            valorK = str(row[10]).strip().upper()
            valorB = str(row[1]).strip().upper()
            dataF = df_f_str[idx]

            # HELP DESK
            if valorM == "CODISYS - HELP DESK":
                P2 += 1
                if dataF != hoje_str:
                    P3 += 1
                if valorK == "PENDIENTE CLIENTE":
                    P4 += 1

            # HARDWARE ST
            if valorM == "CODISYS - RESOLUTOR HARDWARE ST":
                if valorK == "ASIGNADO" and valorB == "INCIDENCIA":
                    P5 += 1
                    if dataF != hoje_str:
                        P6 += 1
                if valorK == "PENDIENTE PRESUPUESTO":
                    P7 += 1
                if valorB == "PETICION":
                    P8 += 1

            # TOTAL DO DIA
            if dataF == hoje_str:
                P9 += 1

            # RESTALIA - COMERCIAL / SOLICITUDES
            if empresa_tag == "RESTALIA":
                if valorM == "COMERCIAL":
                    R_comercial += 1
                if valorM == "SOLICITUDES RESTALIA":
                    R_solicitudes += 1

        result = {
            "total_helpdesk": P2,
            "helpdesk_antigo": P3,
            "pendientes_cliente_antigo": P4,
            "hardware_st_total": P5,
            "hardware_st_antigo": P6,
            "presupuesto_total": P7,
            "peticion_total": P8,
            "total_hoje": P9
        }

        if empresa_tag == "RESTALIA":
            result.update({
                "comercial_total": R_comercial,
                "solicitudes_total": R_solicitudes
            })

        return result

    except Exception as e:
        print(f"[ERRO] Falha ao extrair dados de {empresa_tag}: {e}")
        return {}

# ==========================
# MONTA EMAIL
# ==========================

def montar_email(dados_alsea, dados_restalia=None):
    lines = ["Buenas tardes,", "Remitimos los datos de hoy:\n"]

    if dados_alsea:
        lines.append(f"Alsea en Helpdesk: {dados_alsea.get('total_helpdesk',0)} ({dados_alsea.get('helpdesk_antigo',0)} más de un día de antigüedad)")
        lines.append(f"Pendientes de cliente con más de un día: {dados_alsea.get('pendientes_cliente_antigo',0)}\n")
        lines.append(f"Alsea Hardware ST: {dados_alsea.get('hardware_st_total',0)} ({dados_alsea.get('hardware_st_antigo',0)} de ellas con más de un día de antigüedad)")
        lines.append(f"Presupuesto: {dados_alsea.get('presupuesto_total',0)}")
        lines.append(f"Petición: {dados_alsea.get('peticion_total',0)}")
        lines.append(f"En el día de hoy han entrado {dados_alsea.get('total_hoje',0)} incidencias totales de Alsea.")
    else:
        lines.append("Alsea: Nenhum dado disponível")

    if dados_restalia:
        lines.append("\n")
        lines.append(f"Restalia en Helpdesk: {dados_restalia.get('total_helpdesk',0)} ({dados_restalia.get('helpdesk_antigo',0)} más de un día de antigüedad)")
        lines.append(f"Pendientes de cliente con más de un día: {dados_restalia.get('pendientes_cliente_antigo',0)}\n")
        lines.append(f"Restalia Hardware ST: {dados_restalia.get('hardware_st_total',0)} ({dados_restalia.get('hardware_st_antigo',0)} de ellas con más de un día de antigüedad)")
        lines.append(f"Presupuesto en ST: {dados_restalia.get('presupuesto_total',0)}")
        lines.append(f"Petición ST: {dados_restalia.get('peticion_total',0)}")
        lines.append(f"Restalia en Comercial: {dados_restalia.get('comercial_total',0)}")
        lines.append(f"Restalia en Solicitudes Restalia: {dados_restalia.get('solicitudes_total',0)}\n")
        lines.append(f"En el día de hoy han entrado {dados_restalia.get('total_hoje',0)} incidencias totales de RESTALIA.")

    lines.append("Un saludo.\nGB")
    return "\n".join(lines)

# ==========================
# SCRIPT PRINCIPAL
# ==========================

def main():
    print("[DEBUG] Iniciando sistema...\n")

    # Carrega config
    config = load_config()
    pasta_download = os.path.abspath(config["download_path"])
    os.makedirs(pasta_download, exist_ok=True)

    # Cria navegador e faz login
    driver = create_browser(pasta_download)
    driver = fazer_login(driver, config["email"], config["senha"], config["url_login"])
    time.sleep(2)

    # Empresas e estados
    empresas_alsea = [
        "ALSEA SEDE - EU", "ARCHIES - ALSEA CO", "BURGER KING - ALSEA EU",
        "CHILLIS - ALSEA MX", "DOMINO´S PIZZA - ALSEA EU", "FOSTER'S HOLLYWOOD - ALSEA EU",
        "GINOS - ALSEA EU", "ITALIANNIS - ALSEA MX", "OLE MOLE - ALSEA",
        "PF CHANGS - ALSEA MX", "STARBUCKS - ALSEA EU", "VIPS - ALSEA EU", "VIPS - ALSEA MX"
    ]
    empresas_restalia = [
        "100M - RESTALIA", "CLS / MLS - RESTALIA", "PANTHER - RESTALIA",
        "PEPETACO - RESTALIA", "RESTALIA - SEDE", "TGB - RESTALIA"
    ]
    estados = [
        "ASIGNADO", "ASIGNADO PENDIENTE", "EN ESPERA", "REABIERTO", "EN PROCESO",
        "PENDIENTE", "PENDIENTE CLIENTE", "PENDIENTE MATERIAL",
        "PENDIENTE PRESUPUESTO", "PENDIENTE DE PROVEEDOR"
    ]

    # Baixa relatórios
    print("[DEBUG] Baixando relatórios...\n")
    baixar_relatorio(driver, empresas_alsea, estados, pasta_download, empresa_tag="ALSEA")
    baixar_relatorio(driver, empresas_restalia, estados, pasta_download, empresa_tag="RESTALIA")
    driver.quit()
    print("[DEBUG] Downloads concluídos.\n")

    # Arquivos mais recentes
    arquivo_alsea = arquivo_mais_recente(pasta_download, "ALSEA")
    arquivo_restalia = arquivo_mais_recente(pasta_download, "RESTALIA")

    # Extrai dados
    dados_alsea = extrair_dados_planilha(arquivo_alsea, "ALSEA")
    dados_restalia = extrair_dados_planilha(arquivo_restalia, "RESTALIA")

    # Monta email
    corpo_email = montar_email(dados_alsea, dados_restalia)
    print("\n========== CORPO DO EMAIL ==========\n")
    print(corpo_email)
    print("\n===================================\n")

    # Anexos
    anexos = [a for a in [arquivo_alsea, arquivo_restalia] if a]

    # Envia email
    if anexos:
        data_atual = datetime.now().strftime("%d-%m-%Y")
        assunto_email = f"REPORTE DIARIO - INCIDENCIAS ALSEA & RESTALIA - {data_atual}"
        enviar_email(config, assunto=assunto_email, corpo=corpo_email, anexos=anexos)
        print("[DEBUG] Email enviado com sucesso.")
    else:
        print("[WARN] Nenhum arquivo para enviar.")

    print("[DEBUG] Processo finalizado.")

if __name__ == "__main__":
    main()