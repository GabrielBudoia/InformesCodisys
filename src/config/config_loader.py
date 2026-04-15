import os
import json


def load_config():
    """
    Carrega config.json e valida campos obrigatórios.
    As credenciais Azure para envio de email são lidas de variáveis de ambiente,
    nunca do config.json.
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
    # CAMPOS OBRIGATÓRIOS (config.json)
    # ==============================
    # Nota: "email" foi removido daqui — é lido da variável de ambiente CODISYS_EMAIL
    campos_obrigatorios = [
        "url_login",     # URL de login no site Codisys
        "download_path", # Pasta de destino dos relatórios
        "destinatarios", # Lista de destinatários do email
    ]

    for campo in campos_obrigatorios:
        if campo not in config or not config[campo]:
            raise ValueError(f"[ERRO] Campo obrigatório ausente no config.json: {campo}")

    # ==============================
    # EMAIL DE LOGIN — env var tem prioridade sobre config.json
    # CODISYS_EMAIL sobrepõe o campo "email" do config.json
    # Permite configurar sem modificar o ficheiro de configuração (útil em CI/cloud)
    # ==============================
    codisys_email = os.getenv("CODISYS_EMAIL")
    if codisys_email:
        config["email"] = codisys_email
    elif not config.get("email"):
        raise RuntimeError(
            "[ERRO] Email de login não configurado. "
            "Define a variável de ambiente 'CODISYS_EMAIL' ou preenche o campo 'email' no config.json."
        )

    # ==============================
    # VALIDAÇÕES EXTRAS
    # ==============================
    if not isinstance(config["destinatarios"], list) or not config["destinatarios"]:
        raise ValueError("[ERRO] 'destinatarios' deve ser uma lista não vazia.")

    # ==============================
    # VARIÁVEIS DE AMBIENTE OBRIGATÓRIAS (Graph API / Azure)
    # ==============================
    vars_azure = ["AZURE_TENANT_ID", "AZURE_CLIENT_ID", "AZURE_CLIENT_SECRET", "MAIL_SENDER"]
    em_falta = [v for v in vars_azure if not os.getenv(v)]
    if em_falta:
        raise RuntimeError(
            f"[ERRO] Variáveis de ambiente em falta: {', '.join(em_falta)}. "
            "Consulta o ficheiro .env.example para configuração."
        )

    # ==============================
    # LOG SEGURO (SEM EXPOR DADOS SENSÍVEIS)
    # ==============================
    print("[DEBUG] Config carregada com sucesso:")
    print({
        "url_login": config["url_login"],
        "email": config["email"],
        "download_path": config["download_path"],
        "destinatarios": config["destinatarios"],
        "MAIL_SENDER": os.getenv("MAIL_SENDER"),
    })

    return config
