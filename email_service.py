"""
Módulo de envio de email via Azure Communication Services.

Credenciais lidas exclusivamente de variáveis de ambiente:
  - AZURE_COMMUNICATION_CONNECTION_STRING  — connection string do recurso ACS
  - SENDER_EMAIL                           — endereço verificado no Azure
  - RECIPIENT_EMAIL                        — destinatário do email
"""

import logging
import os

from azure.communication.email import EmailClient


def send_email(subject: str, body_html: str, body_text: str) -> None:
    """
    Envia um email via Azure Communication Services.

    Args:
        subject:   Assunto do email.
        body_html: Corpo em HTML (versão formatada).
        body_text: Corpo em texto simples (fallback).

    Raises:
        RuntimeError: Se alguma variável de ambiente obrigatória estiver em falta.
        Exception:    Qualquer falha do SDK ACS — o erro é registado e relançado.
    """
    connection_string = os.environ.get("AZURE_COMMUNICATION_CONNECTION_STRING")
    sender_email = os.environ.get("SENDER_EMAIL")
    recipient_email = os.environ.get("RECIPIENT_EMAIL")

    variaveis_em_falta = [
        nome
        for nome, valor in {
            "AZURE_COMMUNICATION_CONNECTION_STRING": connection_string,
            "SENDER_EMAIL": sender_email,
            "RECIPIENT_EMAIL": recipient_email,
        }.items()
        if not valor
    ]

    if variaveis_em_falta:
        raise RuntimeError(
            f"Variáveis de ambiente obrigatórias não encontradas: "
            f"{', '.join(variaveis_em_falta)}"
        )

    client = EmailClient.from_connection_string(connection_string)

    message = {
        "senderAddress": sender_email,
        "recipients": {
            "to": [{"address": recipient_email}],
        },
        "content": {
            "subject": subject,
            "html": body_html,
            "plainText": body_text,
        },
    }

    logging.info(
        "[INFO] A enviar email via Azure Communication Services. "
        "Assunto: %s | Destinatário: %s",
        subject,
        recipient_email,
    )

    try:
        poller = client.begin_send(message)
        result = poller.result()
        logging.info(
            "[INFO] Email enviado com sucesso. message_id=%s",
            result.message_id,
        )
    except Exception as exc:
        logging.error(
            "[ERRO] Falha ao enviar email via Azure Communication Services. "
            "Assunto: %s | Erro: %s",
            subject,
            exc,
            exc_info=True,
        )
        raise
