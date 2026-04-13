import os
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from src.config.config_loader import load_config  # Importa a função de config

def create_browser():
    """
    Cria um navegador Chrome configurado para downloads automáticos.
    Rodando em headless se configurado no config.json.
    """
    config = load_config()
    pasta_download = os.path.abspath(config["download_path"])
    os.makedirs(pasta_download, exist_ok=True)

    print("[DEBUG] Criando navegador Chrome...")

    chrome_cfg = config.get("chrome", {})
    caminho_chrome = chrome_cfg.get("caminho", "C:\\Program Files\\Google\\Chrome\\Application\\chrome.exe")
    headless = chrome_cfg.get("headless", True)
    user_data = chrome_cfg.get("user_data_dir", r"C:\ChromeAutomation")
    window_size = chrome_cfg.get("window_size", "1920,1080")
    disable_gpu = chrome_cfg.get("disable_gpu", True)
    no_sandbox = chrome_cfg.get("no_sandbox", True)
    disable_dev_shm = chrome_cfg.get("disable_dev_shm_usage", True)

    os.makedirs(user_data, exist_ok=True)

    options = Options()
    options.binary_location = caminho_chrome
    options.add_argument(f"--user-data-dir={user_data}")
    options.add_argument(f"--window-size={window_size}")

    if headless:
        options.add_argument("--headless=new")  # Chrome 109+ suporta "--headless=new"
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

    # Cria o driver do Chrome
    driver = webdriver.Chrome(options=options)

    print(f"[DEBUG] Chrome criado com sucesso. Downloads liberados em: {pasta_download}")
    return driver