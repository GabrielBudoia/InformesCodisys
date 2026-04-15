import os
import sys
import shutil
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from src.config.config_loader import load_config


def _resolver_caminho_chrome(chrome_cfg):
    """
    Devolve o caminho do executável do Chrome de acordo com o SO:
    - Windows → usa config.json (campo chrome.caminho)
    - Linux   → usa variável de ambiente CHROME_PATH, ou auto-detecção
    """
    if sys.platform == "win32":
        return chrome_cfg.get(
            "caminho",
            r"C:\Program Files\Google\Chrome\Application\chrome.exe"
        )

    # Linux / macOS — variável de ambiente tem prioridade
    caminho_env = os.getenv("CHROME_PATH")
    if caminho_env:
        return caminho_env

    # Auto-detecção: candidatos comuns em Linux
    candidatos = [
        "google-chrome",
        "google-chrome-stable",
        "chromium-browser",
        "chromium",
    ]
    for candidato in candidatos:
        encontrado = shutil.which(candidato)
        if encontrado:
            return encontrado

    raise RuntimeError(
        "[ERRO] Chrome não encontrado. "
        "Define a variável de ambiente CHROME_PATH com o caminho do executável."
    )


def _resolver_user_data_dir(chrome_cfg):
    """
    Devolve o directório de perfil do Chrome:
    - Windows → usa config.json (campo chrome.user_data_dir)
    - Linux   → pasta chrome_data/ relativa ao projecto (sem caminhos fixos de Windows)
    """
    if sys.platform == "win32":
        return chrome_cfg.get("user_data_dir", r"C:\ChromeAutomation")

    # No Linux usamos um caminho relativo ao projecto
    base = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    return os.path.join(base, "chrome_data")


def create_browser():
    """
    Cria um navegador Chrome configurado para downloads automáticos.
    Funciona em Windows (desenvolvimento) e Linux (servidor).
    """
    config = load_config()
    pasta_download = os.path.abspath(config["download_path"])
    os.makedirs(pasta_download, exist_ok=True)

    print("[DEBUG] Criando navegador Chrome...")

    chrome_cfg = config.get("chrome", {})
    caminho_chrome = _resolver_caminho_chrome(chrome_cfg)
    user_data = _resolver_user_data_dir(chrome_cfg)
    headless = chrome_cfg.get("headless", True)
    window_size = chrome_cfg.get("window_size", "1920,1080")
    disable_gpu = chrome_cfg.get("disable_gpu", True)
    no_sandbox = chrome_cfg.get("no_sandbox", True)
    disable_dev_shm = chrome_cfg.get("disable_dev_shm_usage", True)

    os.makedirs(user_data, exist_ok=True)

    print(f"[DEBUG] Chrome: {caminho_chrome}")
    print(f"[DEBUG] User data dir: {user_data}")

    options = Options()
    options.binary_location = caminho_chrome
    options.add_argument(f"--user-data-dir={user_data}")
    options.add_argument(f"--window-size={window_size}")

    if headless:
        options.add_argument("--headless=new")
    if disable_gpu:
        options.add_argument("--disable-gpu")
    if no_sandbox:
        options.add_argument("--no-sandbox")
    if disable_dev_shm:
        options.add_argument("--disable-dev-shm-usage")

    # Preferências de download
    prefs = {
        "download.default_directory": pasta_download,
        "download.prompt_for_download": False,
        "download.directory_upgrade": True,
        "safebrowsing.enabled": True,
        "profile.default_content_setting_values.automatic_downloads": 1
    }
    options.add_experimental_option("prefs", prefs)

    driver = webdriver.Chrome(options=options)

    print(f"[DEBUG] Chrome criado com sucesso. Downloads em: {pasta_download}")
    return driver
