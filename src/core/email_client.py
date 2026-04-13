import os
import win32com.client


def enviar_email(config, assunto, corpo, anexos=None):
    """
    Envia email usando Outlook instalado no Windows.
    Não usa SMTP.
    Não usa senha.
    Usa a conta já logada no Outlook.
    """

    try:
        outlook = win32com.client.Dispatch("Outlook.Application")
        mail = outlook.CreateItem(0)

        mail.Subject = assunto
        mail.Body = corpo
        mail.To = ";".join(config["destinatarios"])

        # Anexos
        if anexos:
            for arquivo in anexos:
                if os.path.exists(arquivo):
                    mail.Attachments.Add(os.path.abspath(arquivo))

        mail.Send()

        print("[SUCESSO] Email enviado via Outlook local!")

    except Exception as e:
        raise RuntimeError(f"[ERRO] Falha ao enviar via Outlook: {e}")