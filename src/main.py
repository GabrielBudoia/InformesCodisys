import os
import sys
import time
import signal
import traceback
from datetime import datetime
from dotenv import load_dotenv

load_dotenv()

from src.features.login import fazer_login
from src.features.filtros import baixar_relatorio
from src.config.config_loader import load_config
from src.core.browser import create_browser
from src.core.email_client import enviar_email
from src.core.extrair_dados import extrair_dados_planilha, montar_email


BASE_DIR = os.path.dirname(os.path.abspath(__file__))
LOG_DIR = os.path.join(BASE_DIR, "logs")
LOG_FILE = os.path.join(LOG_DIR, "execucao.txt")
LOCK_FILE = os.path.join(LOG_DIR, "execucao.lock")


# ──────────────────────────────────────────
# LOGGING DUPLO: ficheiro + stdout
# ──────────────────────────────────────────

def escrever_log(mensagem):
    os.makedirs(LOG_DIR, exist_ok=True)
    linha = f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] {mensagem}\n"
    with open(LOG_FILE, "a", encoding="utf-8") as f:
        f.write(linha)
    sys.stdout.write(linha)
    sys.stdout.flush()


# ──────────────────────────────────────────
# LOCK FILE — evita duas instâncias simultâneas
# ──────────────────────────────────────────

def criar_lock():
    if os.path.exists(LOCK_FILE):
        with open(LOCK_FILE, "r", encoding="utf-8") as f:
            conteudo = f.read().strip()
        raise RuntimeError(
            f"[ERRO] Já existe uma instância em execução (lock: {conteudo}). "
            "Se o processo anterior terminou de forma inesperada, apaga manualmente: "
            f"{LOCK_FILE}"
        )
    os.makedirs(LOG_DIR, exist_ok=True)
    with open(LOCK_FILE, "w", encoding="utf-8") as f:
        f.write(f"pid={os.getpid()} iniciado={datetime.now().isoformat()}")


def remover_lock():
    if os.path.exists(LOCK_FILE):
        try:
            os.remove(LOCK_FILE)
        except Exception:
            pass


# ──────────────────────────────────────────
# EMAIL DE ALERTA EM FALHA FATAL
# ──────────────────────────────────────────

def enviar_alerta_falha(config, tb):
    """Envia email com traceback quando o script falha de forma irrecuperável."""
    try:
        data_atual = datetime.now().strftime("%d-%m-%Y %H:%M:%S")
        assunto = f"[ALERTA] Falha no script de Informes — {data_atual}"
        corpo = (
            "O script de geração de relatórios terminou com um erro irrecuperável.\n\n"
            f"Data/hora: {data_atual}\n\n"
            "─── TRACEBACK ───\n"
            f"{tb}"
        )
        enviar_email(config, assunto=assunto, corpo=corpo, anexos=None)
        escrever_log("[INFO] Email de alerta de falha enviado.")
    except Exception:
        escrever_log("[WARN] Não foi possível enviar email de alerta:")
        escrever_log(traceback.format_exc())


# ──────────────────────────────────────────
# UTILITÁRIOS
# ──────────────────────────────────────────

def arquivo_mais_recente(pasta, prefixo):
    arquivos = [
        os.path.join(pasta, f)
        for f in os.listdir(pasta)
        if f.upper().startswith(prefixo.upper())
    ]
    if not arquivos:
        return None
    return max(arquivos, key=os.path.getmtime)


def manter_apenas_10_mais_recentes(caminho_pasta):
    if not os.path.exists(caminho_pasta):
        escrever_log(f"[WARN] Pasta não encontrada para limpeza: {caminho_pasta}")
        return

    arquivos = [
        os.path.join(caminho_pasta, f)
        for f in os.listdir(caminho_pasta)
        if os.path.isfile(os.path.join(caminho_pasta, f))
    ]

    if len(arquivos) <= 10:
        escrever_log(f"[DEBUG] Pasta com {len(arquivos)} arquivo(s). Nenhuma limpeza necessária.")
        return

    arquivos.sort(key=os.path.getmtime, reverse=True)
    arquivos_para_apagar = arquivos[10:]

    for arquivo in arquivos_para_apagar:
        try:
            os.remove(arquivo)
            escrever_log(f"[DEBUG] Arquivo apagado: {arquivo}")
        except Exception as e:
            escrever_log(f"[ERRO] Não foi possível apagar {arquivo}: {e}")

    escrever_log(f"[DEBUG] Limpeza concluída. {len(arquivos_para_apagar)} arquivo(s) removido(s).")


# ──────────────────────────────────────────
# MAIN
# ──────────────────────────────────────────

def main():
    # --- Lock file ---
    try:
        criar_lock()
    except RuntimeError as e:
        # Usa print directo porque o log ainda pode não estar pronto
        print(str(e), file=sys.stderr)
        sys.exit(1)

    escrever_log("[DEBUG] Iniciando sistema...")

    config = None
    driver = None

    # --- Handler de sinais (SIGTERM / SIGINT) para encerramento limpo no servidor ---
    def handle_signal(signum, frame):
        escrever_log(f"[WARN] Sinal {signum} recebido. Encerrando graciosamente...")
        if driver:
            try:
                driver.quit()
                escrever_log("[DEBUG] Navegador fechado por sinal.")
            except Exception:
                pass
        remover_lock()
        sys.exit(0)

    signal.signal(signal.SIGTERM, handle_signal)
    signal.signal(signal.SIGINT, handle_signal)

    # --- Carregar configuração ---
    try:
        config = load_config()
        escrever_log("[DEBUG] Configuração carregada com sucesso.")
    except Exception:
        tb = traceback.format_exc()
        escrever_log("[ERRO] Falha ao carregar configuração.")
        escrever_log(tb)
        remover_lock()
        return

    # --- Senha via variável de ambiente ---
    senha_web = os.getenv("senha")
    if not senha_web:
        escrever_log("[ERRO] Variável de ambiente 'senha' não encontrada.")
        remover_lock()
        raise RuntimeError("Variável de ambiente 'senha' não encontrada.")

    pasta_download = os.path.abspath(config["download_path"])
    os.makedirs(pasta_download, exist_ok=True)
    escrever_log(f"[DEBUG] Pasta de download: {pasta_download}")

    try:
        # ==========================
        # LOGIN E DOWNLOADS
        # ==========================
        escrever_log("[DEBUG] Criando navegador Chrome...")
        driver = create_browser()

        escrever_log("[DEBUG] Realizando login...")
        driver = fazer_login(
            driver,
            config["email"],
            senha_web,
            config["url_login"]
        )

        time.sleep(2)

        # ==========================
        # EMPRESAS
        # ==========================
        empresas_alsea = [
            "ALSEA SEDE - EU", "ARCHIES - ALSEA CO", "BURGER KING - ALSEA EU",
            "CHILLIS - ALSEA MX", "DOMINO´S PIZZA - ALSEA EU",
            "FOSTER'S HOLLYWOOD - ALSEA EU", "GINOS - ALSEA EU",
            "ITALIANNIS - ALSEA MX", "OLE MOLE - ALSEA",
            "PF CHANGS - ALSEA MX", "STARBUCKS - ALSEA EU",
            "VIPS - ALSEA EU", "VIPS - ALSEA MX"
        ]

        empresas_restalia = [
            "100M - RESTALIA", "CLS / MLS - RESTALIA",
            "PANTHER - RESTALIA", "PEPETACO - RESTALIA",
            "RESTALIA - SEDE", "TGB - RESTALIA"
        ]

        estados = [
            "ASIGNADO", "ASIGNADO PENDIENTE", "EN ESPERA", "REABIERTO",
            "EN PROCESO", "PENDIENTE", "PENDIENTE CLIENTE",
            "PENDIENTE MATERIAL", "PENDIENTE PRESUPUESTO",
            "PENDIENTE DE PROVEEDOR"
        ]

        # ==========================
        # DOWNLOAD RELATÓRIOS
        # ==========================
        escrever_log("[DEBUG] Baixando relatórios ALSEA...")
        baixar_relatorio(driver, empresas_alsea, estados, pasta_download, empresa_tag="ALSEA")

        escrever_log("[DEBUG] Baixando relatórios RESTALIA...")
        baixar_relatorio(driver, empresas_restalia, estados, pasta_download, empresa_tag="RESTALIA")

        escrever_log("[DEBUG] Downloads concluídos.")

    except Exception:
        tb = traceback.format_exc()
        escrever_log("[ERRO] Falha durante automação.")
        escrever_log(tb)
        if config:
            enviar_alerta_falha(config, tb)

    finally:
        if driver:
            try:
                escrever_log("[DEBUG] Fechando navegador...")
                driver.quit()
                escrever_log("[DEBUG] Navegador fechado.")
            except Exception:
                escrever_log("[ERRO] Falha ao fechar navegador.")
                escrever_log(traceback.format_exc())

    # ==========================
    # PROCESSAMENTO DOS ARQUIVOS
    # ==========================
    try:
        arquivo_alsea = arquivo_mais_recente(pasta_download, "ALSEA")
        arquivo_restalia = arquivo_mais_recente(pasta_download, "RESTALIA")

        escrever_log(f"[DEBUG] Arquivo ALSEA encontrado: {arquivo_alsea}")
        escrever_log(f"[DEBUG] Arquivo RESTALIA encontrado: {arquivo_restalia}")

        dados_alsea = extrair_dados_planilha(arquivo_alsea, "ALSEA") if arquivo_alsea else None
        dados_restalia = extrair_dados_planilha(arquivo_restalia, "RESTALIA") if arquivo_restalia else None

        corpo_email = montar_email(dados_alsea, dados_restalia)
        anexos = [a for a in [arquivo_alsea, arquivo_restalia] if a]

        data_atual = datetime.now().strftime("%d-%m-%Y")
        assunto_email = f"REPORTE DIARIO - INCIDENCIAS ALSEA & RESTALIA - {data_atual}"

        if anexos:
            enviar_email(
                config,
                assunto=assunto_email,
                corpo=corpo_email,
                anexos=anexos
            )
            escrever_log("[DEBUG] Email enviado com sucesso.")
        else:
            escrever_log("[WARN] Nenhum arquivo para enviar.")

    except Exception:
        tb = traceback.format_exc()
        escrever_log("[ERRO] Falha ao processar arquivos ou enviar email.")
        escrever_log(tb)
        if config:
            enviar_alerta_falha(config, tb)

    # ==========================
    # LIMPEZA DA PASTA
    # ==========================
    try:
        manter_apenas_10_mais_recentes(pasta_download)
    except Exception:
        escrever_log("[ERRO] Falha durante limpeza da pasta de downloads.")
        escrever_log(traceback.format_exc())

    escrever_log("[DEBUG] Processo finalizado.")
    remover_lock()


if __name__ == "__main__":
    main()
