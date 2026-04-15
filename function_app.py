"""
Azure Function — Timer Trigger
Executa os Informes diários às 18:55 hora de Espanha (UTC+1/+2 — CET/CEST).

O fuso horário é controlado pela variável de ambiente WEBSITE_TIME_ZONE
configurada na Function App:
  - Windows (App Service Plan): WEBSITE_TIME_ZONE = "Romance Standard Time"
  - Linux (Consumption/Flex):   WEBSITE_TIME_ZONE = "Europe/Madrid"

Expressão NCRONTAB: {segundo} {minuto} {hora} {dia} {mês} {dia_semana}
  0 55 18 * * *  →  todos os dias às 18:55:00 no fuso configurado
"""

import logging
import azure.functions as func

from src.main import main as executar_informes

app = func.FunctionApp()


@app.timer_trigger(
    schedule="0 55 18 * * *",
    arg_name="myTimer",
    run_on_startup=False,
    use_monitor=False,
)
def informes_timer_trigger(myTimer: func.TimerRequest) -> None:
    """Ponto de entrada do trigger diário de Informes."""
    logging.info("Azure Function iniciada — Informes diários.")

    if myTimer.past_due:
        logging.warning(
            "O timer está em atraso (past_due=True). "
            "A execução prossegue na mesma."
        )

    try:
        executar_informes()
        logging.info("Azure Function concluída com sucesso.")
    except Exception:
        # O logging.exception inclui o traceback completo — visível no Application Insights.
        logging.exception(
            "Falha irrecuperável durante a execução da Azure Function. "
            "Consulta os logs no portal Azure para o traceback completo."
        )
        # Relançar para que a Azure Function registe a execução como falhada.
        raise
