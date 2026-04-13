@echo off
cd /d C:\Users\gabbu\Desktop\Informes

if not exist logs mkdir logs

echo [%date% %time%] BAT INICIOU >> logs\teste_bat.txt

REM Abre o Chrome sem bloquear o .bat
start "" "C:\Program Files\Google\Chrome\Application\chrome.exe" --remote-debugging-port=9222 --user-data-dir="C:\Users\gabbu\AppData\Local\Google\Chrome\User Data"

timeout /t 5 /nobreak > nul

echo [%date% %time%] ANTES DO PYTHON >> logs\teste_bat.txt

venv\Scripts\python.exe -m src.main >> logs\saida_agendador.txt 2>&1

echo [%date% %time%] DEPOIS DO PYTHON >> logs\teste_bat.txt