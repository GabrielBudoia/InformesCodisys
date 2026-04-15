import os
import base64
import msal
import requests


# Scope obrigatório para envio de email via Graph API com client credentials
GRAPH_SCOPE = ["https://graph.microsoft.com/.default"]
GRAPH_SEND_URL = "https://graph.microsoft.com/v1.0/users/{sender}/sendMail"


def _obter_token_azure():
    """
    Obtém token de acesso via client credentials flow (sem interação do utilizador).
    Requer as variáveis de ambiente: AZURE_TENANT_ID, AZURE_CLIENT_ID, AZURE_CLIENT_SECRET.
    """
    tenant_id = os.getenv("AZURE_TENANT_ID")
    client_id = os.getenv("AZURE_CLIENT_ID")
    client_secret = os.getenv("AZURE_CLIENT_SECRET")

    if not all([tenant_id, client_id, client_secret]):
        raise RuntimeError(
            "[ERRO] Variáveis de ambiente Azure em falta: "
            "AZURE_TENANT_ID, AZURE_CLIENT_ID, AZURE_CLIENT_SECRET são obrigatórias."
        )

    authority = f"https://login.microsoftonline.com/{tenant_id}"
    app = msal.ConfidentialClientApplication(
        client_id,
        authority=authority,
        client_credential=client_secret,
    )

    resultado = app.acquire_token_for_client(scopes=GRAPH_SCOPE)

    if "access_token" not in resultado:
        erro = resultado.get("error_description", resultado.get("error", "Erro desconhecido"))
        raise RuntimeError(f"[ERRO] Falha ao obter token Azure: {erro}")

    return resultado["access_token"]


def _codificar_anexo(caminho_arquivo):
    """
    Lê um ficheiro e retorna o seu conteúdo em base64 (formato exigido pela Graph API).
    """
    with open(caminho_arquivo, "rb") as f:
        return base64.b64encode(f.read()).decode("utf-8")


def enviar_email(config, assunto, corpo, anexos=None):
    """
    Envia email via Microsoft Graph API com autenticação por client credentials (Azure App Registration).
    Não depende do Outlook local nem de nenhuma aplicação instalada.

    Variáveis de ambiente obrigatórias:
        AZURE_TENANT_ID     — ID do tenant Azure AD
        AZURE_CLIENT_ID     — ID da App Registration
        AZURE_CLIENT_SECRET — Secret da App Registration
        MAIL_SENDER         — Endereço de email que envia (caixa de correio no tenant)
    """
    mail_sender = os.getenv("MAIL_SENDER")
    if not mail_sender:
        raise RuntimeError("[ERRO] Variável de ambiente 'MAIL_SENDER' não encontrada.")

    token = _obter_token_azure()

    # Montar lista de destinatários no formato da Graph API
    destinatarios = [
        {"emailAddress": {"address": dest}}
        for dest in config["destinatarios"]
    ]

    # Montar lista de anexos em base64
    lista_anexos = []
    if anexos:
        for caminho in anexos:
            if os.path.exists(caminho):
                lista_anexos.append({
                    "@odata.type": "#microsoft.graph.fileAttachment",
                    "name": os.path.basename(caminho),
                    "contentBytes": _codificar_anexo(caminho),
                })

    payload = {
        "message": {
            "subject": assunto,
            "body": {
                "contentType": "Text",
                "content": corpo,
            },
            "toRecipients": destinatarios,
            "attachments": lista_anexos,
        }
    }

    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json",
    }

    url = GRAPH_SEND_URL.format(sender=mail_sender)
    resposta = requests.post(url, headers=headers, json=payload, timeout=30)

    # Graph API retorna 202 Accepted em caso de sucesso (sem corpo de resposta)
    if resposta.status_code == 202:
        print("[SUCESSO] Email enviado via Microsoft Graph API!")
    else:
        raise RuntimeError(
            f"[ERRO] Falha ao enviar email via Graph API. "
            f"Status: {resposta.status_code} | Resposta: {resposta.text}"
        )
