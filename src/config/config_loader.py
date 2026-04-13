import os
import json

def load_config():
    """
    Carrega config.json e valida campos obrigatórios.
    Versão limpa para uso com SMTP (sem OAuth).
    """
    print("[DEBUG] Carregando config.json...")

    # Caminho do config.json (mesma pasta do script)
    caminho = os.path.join(os.path.dirname(__file__), "config.json")
    if not os.path.exists(caminho):
        raise FileNotFoundError(f"[ERRO] config.json não encontrado em: {caminho}")

    # Leitura do arquivo JSON
    try:
        with open(caminho, "r", encoding="utf-8") as f:
            config = json.load(f)
    except Exception as e:
        raise RuntimeError(f"[ERRO] Falha ao ler config.json: {e}")

    # ==============================
    # CAMPOS OBRIGATÓRIOS (SMTP)
    # ==============================
    campos_obrigatorios = [
        "url_login",     # usado no login do site
        "email",         # usado no login do site
        "correo_login",  # usado no envio SMTP
        "download_path",
        "destinatarios"
    ]

    for campo in campos_obrigatorios:
        if campo not in config or not config[campo]:
            raise ValueError(f"[ERRO] Campo obrigatório ausente no config.json: {campo}")

    # ==============================
    # VALIDAÇÕES EXTRAS
    # ==============================
    if not isinstance(config["destinatarios"], list) or not config["destinatarios"]:
        raise ValueError("[ERRO] 'destinatarios' deve ser uma lista não vazia.")

    # ==============================
    # LOG SEGURO (SEM EXPOR DADOS SENSÍVEIS)
    # ==============================
    config_safe = config.copy()
    print("[DEBUG] Config carregada com sucesso:")
    print({
        "url_login": config_safe["url_login"],
        "email": config_safe["email"],
        "correo_login": config_safe["correo_login"],
        "download_path": config_safe["download_path"],
        "destinatarios": config_safe["destinatarios"]
    })

    return config