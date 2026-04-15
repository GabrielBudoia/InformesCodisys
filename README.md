# Informes — Automatización de Informes Diarios Codisys

Script Python que accede automáticamente al portal de soporte Codisys, descarga los informes de incidencias de ALSEA y RESTALIA, extrae los datos relevantes y envía un email diario con el resumen y los ficheros Excel adjuntos.

Funciona en **Windows** (desarrollo local), **Linux/Ubuntu** (servidor VPS en producción 24/7) y **Azure Functions** (ejecución serverless programada, sin servidor propio).

---

## Índice

1. [Qué hace el script](#qué-hace-el-script)
2. [Estructura del proyecto](#estructura-del-proyecto)
3. [Prerrequisitos](#prerrequisitos)
4. [Configuración Azure (App Registration)](#configuración-azure-app-registration)
5. [**GitHub Actions — Agendamiento Gratuito (Recomendado)**](#github-actions--agendamiento-gratuito-recomendado)
6. [Azure Functions — Deploy Serverless](#azure-functions--deploy-serverless)
7. [Instalación — Windows](#instalación--windows)
8. [Instalación — Linux / Ubuntu Server](#instalación--linux--ubuntu-server)
9. [Variables de entorno](#variables-de-entorno)
10. [Fichero config.json](#fichero-configjson)
11. [Ejecutar el script manualmente](#ejecutar-el-script-manualmente)
12. [Programar ejecución automática](#programar-ejecución-automática)
13. [Logs y monitorización](#logs-y-monitorización)
14. [Troubleshooting](#troubleshooting)

---

## Qué hace el script

```
1. Abre Chrome en modo headless (sin ventana visible)
2. Hace login en el portal https://support.codisysdc.com
3. Aplica filtros: empresas ALSEA + RESTALIA, estados abiertos, últimos 8 meses
4. Exporta los informes en formato XLSX/XLS
5. Lee los ficheros descargados y cuenta incidencias por tipo y antigüedad
6. Monta el cuerpo del email con los datos resumidos
7. Envía el email via Microsoft Graph API con los ficheros Excel adjuntos
8. Borra descargas antiguas (mantiene las 10 más recientes)
```

El email enviado tiene este formato:

```
Buenas tardes,
Remitimos los datos de hoy:

Alsea en Helpdesk: 42 (7 más de un día de antigüedad)
Pendientes de cliente con más de un día: 3
Alsea Hardware ST: 15 (4 de ellas con más de un día de antigüedad)
Presupuesto: 2
Petición: 5
En el día de hoy han entrado 8 incidencias totales de Alsea.

Restalia en Helpdesk: 18 (2 más de un día de antigüedad)
...

Un saludo.
GB
```

---

## Estructura del proyecto

```
Informes/
├── src/
│   ├── main.py                  # Punto de entrada — orquesta todo el flujo
│   ├── config/
│   │   ├── config.json          # Configuración no sensible (URLs, Chrome, destinatarios)
│   │   └── config_loader.py     # Carga y valida la configuración
│   ├── core/
│   │   ├── browser.py           # Creación del Chrome (detecta SO automáticamente)
│   │   ├── email_client.py      # Envío de email via Microsoft Graph API
│   │   ├── extrair_dados.py     # Lectura de los Excel y montaje del cuerpo del email
│   │   └── utils.py             # Utilidades Selenium (clics, esperas DevExpress)
│   ├── features/
│   │   ├── login.py             # Login en el portal Codisys
│   │   └── filtros.py           # Filtros, fechas, exportación y descarga del informe
│   └── logs/
│       └── execucao.txt         # Log de ejecución (creado automáticamente)
├── informes/                    # Carpeta de descargas (creada automáticamente)
├── .env                         # Credenciales locales — NUNCA hacer commit
├── .env.example                 # Plantilla de las variables de entorno
├── requirements.txt             # Dependencias Python con versiones fijas
└── README.md
```

---

## Prerrequisitos

| Componente | Versión mínima | Notas |
|---|---|---|
| Python | 3.10+ | |
| Google Chrome | cualquier versión reciente | Instalado en el sistema |
| Cuenta Microsoft 365 | — | Para envío de email via Graph API |
| Azure Active Directory | — | Para crear la App Registration |

---

## Configuración Azure (App Registration)

El envío de email usa la Microsoft Graph API con autenticación de aplicación (sin necesidad de usuario logado). Es necesario crear una **App Registration** en Azure una única vez.

### Paso 1 — Crear la App Registration

1. Accede al [portal Azure](https://portal.azure.com)
2. Ve a **Azure Active Directory** → **App registrations** → **New registration**
3. Rellena:
   - **Name:** `InformesAutomacion` (o el nombre que prefieras)
   - **Supported account types:** *Accounts in this organizational directory only (Single tenant)*
4. Haz clic en **Register**

### Paso 2 — Añadir permiso Mail.Send

1. En la página de la app, ve a **API permissions** → **Add a permission**
2. Elige **Microsoft Graph** → **Application permissions**
3. Busca `Mail.Send` y selecciónalo
4. Haz clic en **Add permissions**
5. Haz clic en **Grant admin consent for [tenant]** y confirma

> El permiso debe ser de tipo **Application** (no Delegated) para funcionar sin intervención humana.

### Paso 3 — Crear el Client Secret

1. Ve a **Certificates & secrets** → **New client secret**
2. Elige una descripción y una validez (recomendado: 24 meses)
3. Haz clic en **Add**
4. **Copia el valor inmediatamente** — solo aparece una vez

### Paso 4 — Copiar los IDs necesarios

En la página **Overview** de la app copia:
- **Application (client) ID** → será tu `AZURE_CLIENT_ID`
- **Directory (tenant) ID** → será tu `AZURE_TENANT_ID`

---

## GitHub Actions — Agendamiento Gratuito (Recomendado)

Esta es la forma más sencilla de ejecutar el script en la nube **sin ningún servidor ni PC encendido**. GitHub Actions proporciona runners Ubuntu con Chrome incluido y 2000 minutos gratuitos al mes (este script usa ~10 minutos por ejecución).

### Prerrequisitos

- Repositorio en GitHub (público o privado)
- La configuración Azure (App Registration) ya debe estar hecha — ver sección anterior

### Paso 1 — Configurar los secrets en GitHub

Ve a tu repositorio en GitHub → **Settings** → **Secrets and variables** → **Actions** → **New repository secret**.

Crea los siguientes secrets:

| Secret | Descripción |
|---|---|
| `CODISYS_EMAIL` | Email de login en el portal Codisys (`ggbudoia@codisys.es`) |
| `SENHA` | Contraseña de login en el portal Codisys |
| `AZURE_TENANT_ID` | ID del tenant Azure AD |
| `AZURE_CLIENT_ID` | ID de la App Registration |
| `AZURE_CLIENT_SECRET` | Secret generado en la App Registration |
| `MAIL_SENDER` | Caixa de correio que envia los emails |

> **Importante:** El nombre del secret `SENHA` debe escribirse exactamente así (en mayúsculas). En el workflow se mapea a la variable de entorno `senha` que el script espera.

### Paso 2 — Subir el código a GitHub

```bash
git add .github/workflows/automation.yml
git add src/config/config.json
git add src/config/config_loader.py
git add .env.example
git commit -m "feat: adiciona workflow GitHub Actions para agendamento na cloud"
git push
```

### Paso 3 — Verificar el workflow

1. Ve a tu repositorio → pestaña **Actions**
2. Verás el workflow **"Informes Diários — ALSEA & RESTALIA"**
3. Para hacer una prueba inmediata: haz clic en el workflow → **Run workflow** → **Run workflow**
4. Espera ~5-10 minutos y verifica que el email llegue

### Paso 4 — Verificar logs

En la pestaña Actions, haz clic en cualquier ejecución para ver los logs en tiempo real:

```
✅ Instalar Google Chrome         → Chrome instalado
✅ Instalar dependências          → Paquetes Python instalados
✅ Executar automação de informes → Script ejecutado
   [2024-01-15 17:55:03] [DEBUG] Iniciando sistema...
   [2024-01-15 17:56:21] [DEBUG] Login confirmado com sucesso.
   [2024-01-15 17:58:44] [DEBUG] Email enviado com sucesso.
   [2024-01-15 17:58:44] [DEBUG] Processo finalizado.
```

Si hay un fallo, el paso "Mostrar log em caso de falha" muestra el log completo de `src/logs/execucao.txt`.

### Cambiar el horario de ejecución

Edita `.github/workflows/automation.yml` y modifica la línea `cron`:

```yaml
- cron: '55 17 * * 1-5'   # 17:55 UTC = 18:55 Lisboa (verano) / 17:55 Lisboa (invierno)
```

El formato es: `minutos horas día-del-mes mes día-de-la-semana` (siempre en UTC).

| Hora Lisboa deseada | Cron (invierno WET UTC+0) | Cron (verano WEST UTC+1) |
|---|---|---|
| 17:55 | `55 17 * * 1-5` | `55 16 * * 1-5` |
| 18:55 | `55 18 * * 1-5` | `55 17 * * 1-5` |

> GitHub Actions no ajusta el cron automáticamente para el horario de verano/invierno. El workflow actual usa `55 17 * * 1-5` (18:55 en verano). Para invierno, cámbialo a `55 18 * * 1-5`.

### Límites de uso gratuito

| Plan | Minutos/mes | Suficiente para |
|---|---|---|
| GitHub Free | 2.000 min | ~200 ejecuciones (~10 min cada una) |
| GitHub Pro | 3.000 min | ~300 ejecuciones |

Con ejecución de lunes a viernes (~22 días/mes × 10 min = 220 min), queda muy por debajo del límite gratuito.

---

## Azure Functions — Deploy Serverless

Esta sección cubre el deploy del script como **Azure Function con Timer Trigger**, eliminando la dependencia de un servidor o PC encendido 24/7.

### Prerrequisitos Azure Functions

| Componente | Versión / Notas |
|---|---|
| Python | 3.10+ |
| Azure CLI | [Instalar](https://learn.microsoft.com/cli/azure/install-azure-cli) |
| Azure Functions Core Tools | v4+ — `npm install -g azure-functions-core-tools@4` |
| Cuenta Azure | Con suscripción activa |
| Recurso Azure Communication Services | Para envío de email |

### Estructura de ficheros Azure Functions

```
Informes/
├── function_app.py          # Entry point — Timer Trigger (18:55 hora Lisboa)
├── email_service.py         # Módulo aislado para Azure Communication Services
├── host.json                # Configuración del runtime Azure Functions
├── local.settings.json      # Variables de entorno para desarrollo local (no hacer commit)
├── requirements.txt         # Dependencias Python con versiones fijas
├── src/                     # Lógica de negocio existente (browser, extracción, etc.)
└── README.md
```

### Variables de entorno Azure Functions

| Variable | Obligatoria | Descripción |
|---|---|---|
| `AZURE_COMMUNICATION_CONNECTION_STRING` | Sí | Connection string del recurso ACS (portal Azure → ACS → Keys) |
| `SENDER_EMAIL` | Sí | Email verificado como sender en ACS |
| `RECIPIENT_EMAIL` | Sí | Email destinatario del informe diario |
| `WEBSITE_TIME_ZONE` | Sí | Zona horaria para el cron — ver tabla abajo |
| `senha` | Sí | Contraseña de login en el portal Codisys |
| `AZURE_TENANT_ID` | Sí | ID del tenant Azure AD (Microsoft Graph API) |
| `AZURE_CLIENT_ID` | Sí | ID de la App Registration en Azure |
| `AZURE_CLIENT_SECRET` | Sí | Secret generado en la App Registration |

#### Zona horaria — `WEBSITE_TIME_ZONE`

Portugal continental usa WET (UTC+0 invierno) y WEST (UTC+1 verano). La expresión cron `0 55 18 * * *` se interpretará en la zona horaria configurada, con ajuste automático para DST.

| SO de la Function App | Valor correcto |
|---|---|
| Windows (por defecto en el portal) | `GMT Standard Time` |
| Linux | `Europe/Lisbon` |

> **Nota:** Para verificar el SO de tu Function App: portal Azure → Function App → Settings → Configuration → General settings → Platform.

### Configurar variables en la Function App (producción)

Nunca usar `local.settings.json` en producción. Las variables deben definirse en **Application Settings**:

```bash
# Autenticarse en Azure
az login

# Definir cada variable de entorno
az functionapp config appsettings set \
  --name <nombre-de-la-function-app> \
  --resource-group <nombre-del-resource-group> \
  --settings \
    "AZURE_COMMUNICATION_CONNECTION_STRING=<valor>" \
    "SENDER_EMAIL=<valor>" \
    "RECIPIENT_EMAIL=<valor>" \
    "WEBSITE_TIME_ZONE=GMT Standard Time" \
    "senha=<valor>" \
    "AZURE_TENANT_ID=<valor>" \
    "AZURE_CLIENT_ID=<valor>" \
    "AZURE_CLIENT_SECRET=<valor>"
```

### Probar localmente

```bash
# 1. Activar entorno virtual e instalar dependencias
python -m venv venv
venv\Scripts\activate          # Windows
# source venv/bin/activate     # Linux/Mac
pip install -r requirements.txt

# 2. Rellenar local.settings.json con los valores reales
#    (nunca hacer commit de este fichero con valores reales)

# 3. Iniciar la function localmente
func start

# El output esperado:
#   Functions:
#     informes_timer_trigger: timerTrigger
#
# Para forzar una ejecución inmediata (sin esperar al timer):
func start --run-on-startup
```

> **Nota sobre `run_on_startup`:** En `function_app.py` el parámetro `run_on_startup=False` está definido deliberadamente — evita ejecución automática al iniciar el servidor de producción. Para probar localmente usa `func start --run-on-startup` en lugar de modificar el código.

### Deploy en Azure via Azure CLI

```bash
# 1. Crear resource group (si no existe)
az group create --name informes-rg --location westeurope

# 2. Crear cuenta de storage (obligatorio para Azure Functions)
az storage account create \
  --name informesstorage \
  --location westeurope \
  --resource-group informes-rg \
  --sku Standard_LRS

# 3. Crear la Function App
#    IMPORTANTE: --os-type Windows usa "GMT Standard Time"
#                --os-type Linux usa "Europe/Lisbon"
az functionapp create \
  --resource-group informes-rg \
  --consumption-plan-location westeurope \
  --runtime python \
  --runtime-version 3.11 \
  --functions-version 4 \
  --name informes-func-app \
  --os-type Windows \
  --storage-account informesstorage

# 4. Hacer deploy del código
func azure functionapp publish informes-func-app
```

### Deploy via VS Code (alternativa)

1. Instala la extensión **Azure Functions** en VS Code.
2. Haz clic en el icono Azure en la barra lateral.
3. En **Functions**, haz clic en **Deploy to Function App...**.
4. Selecciona la suscripción y la Function App creada.
5. Confirma el deploy — VS Code empaqueta y hace upload automáticamente.

### Verificar logs en Azure

```bash
# Ver logs en tiempo real via Azure CLI (streaming)
func azure functionapp logstream informes-func-app

# O en el portal Azure:
# Function App → Monitoring → Log stream
# Function App → Monitoring → Application Insights → Logs
```

En **Application Insights**, puedes consultar ejecuciones históricas:

```kusto
-- Todas las ejecuciones de la function
requests
| where name == "informes_timer_trigger"
| project timestamp, success, duration, resultCode
| order by timestamp desc

-- Errores con traceback
traces
| where severityLevel >= 3
| project timestamp, message
| order by timestamp desc
```

### Zona horaria — verificación

El cron `0 55 18 * * *` con `WEBSITE_TIME_ZONE=GMT Standard Time`:
- **Invierno (WET = UTC+0):** se ejecuta a las 18:55 UTC = 18:55 Lisboa ✅
- **Verano (WEST = UTC+1):** Azure Function ajusta automáticamente = 18:55 Lisboa ✅

Para confirmar: portal Azure → Function App → Functions → `informes_timer_trigger` → Monitor → verifica el horario de la última ejecución.

---

## Instalación — Windows

### 1. Crear entorno virtual

Abre el terminal en la carpeta del proyecto:

```cmd
cd C:\Users\<user>\Desktop\Informes
python -m venv venv
venv\Scripts\activate
```

### 2. Instalar dependencias

```cmd
pip install -r requirements.txt
```

### 3. Crear el fichero .env

```cmd
copy .env.example .env
notepad .env
```

Rellena con tus valores:

```env
CODISYS_EMAIL=ggbudoia@codisys.es
senha=<contraseña_del_portal_codisys>

AZURE_TENANT_ID=xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx
AZURE_CLIENT_ID=xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx
AZURE_CLIENT_SECRET=xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx

MAIL_SENDER=ggbudoia@codisys.es
```

### 4. Verificar el config.json

Abre `src/config/config.json` y confirma que la ruta de Chrome es correcta:

```json
"chrome": {
    "caminho": "C:\\Program Files\\Google\\Chrome\\Application\\chrome.exe"
}
```

### 5. Probar

Crea un fichero `run.bat` en la raíz del proyecto con este contenido:

```bat
@echo off
cd /d C:\Users\<user>\Desktop\Informes
call venv\Scripts\activate
for /f "usebackq tokens=1,2 delims==" %%a in (".env") do set %%a=%%b
python -m src.main
pause
```

Haz doble clic en `run.bat` para probar.

---

## Instalación — Linux / Ubuntu Server

### 1. Instalar dependencias del sistema

```bash
sudo apt update && sudo apt upgrade -y
sudo apt install -y python3 python3-venv python3-pip wget curl
```

### 2. Instalar Google Chrome

```bash
wget -q -O - https://dl.google.com/linux/linux_signing_key.pub | sudo apt-key add -
echo "deb [arch=amd64] http://dl.google.com/linux/chrome/deb/ stable main" \
  | sudo tee /etc/apt/sources.list.d/google-chrome.list
sudo apt update && sudo apt install -y google-chrome-stable

# Verificar instalación
google-chrome --version
```

### 3. Copiar el proyecto al servidor

```bash
# Desde tu PC Windows (ejecuta en PowerShell o cmd)
scp -r C:\Users\<user>\Desktop\Informes user@<ip_servidor>:/home/user/Informes
```

### 4. Crear entorno virtual e instalar dependencias

```bash
cd /home/user/Informes
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

### 5. Crear el fichero .env

```bash
cp .env.example .env
nano .env
```

Rellena con tus valores:

```env
CODISYS_EMAIL=ggbudoia@codisys.es
senha=<contraseña_del_portal_codisys>

AZURE_TENANT_ID=xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx
AZURE_CLIENT_ID=xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx
AZURE_CLIENT_SECRET=xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx

MAIL_SENDER=ggbudoia@codisys.es

# CHROME_PATH solo es necesario si Chrome no se detecta automáticamente
# CHROME_PATH=/usr/bin/google-chrome
```

Protege el fichero (solo tu usuario puede leerlo):

```bash
chmod 600 .env
```

### 6. Probar

```bash
cd /home/user/Informes
source .venv/bin/activate
export $(grep -v '^#' .env | xargs)
python -m src.main
```

---

## Variables de entorno

| Variable | Obligatoria | Descripción |
|---|---|---|
| `CODISYS_EMAIL` | Sí | Email de login en el portal Codisys |
| `senha` | Sí | Contraseña de login en el portal Codisys |
| `AZURE_TENANT_ID` | Sí | ID del tenant Azure AD |
| `AZURE_CLIENT_ID` | Sí | ID de la App Registration en Azure |
| `AZURE_CLIENT_SECRET` | Sí | Secret generado en la App Registration |
| `MAIL_SENDER` | Sí | Email que envía los informes (buzón en el tenant Azure) |
| `CHROME_PATH` | No | Ruta de Chrome en Linux (auto-detectado si se omite) |

> **Nota:** `CODISYS_EMAIL` puede definirse en el `.env` (local) o como secret en GitHub Actions (cloud). Si el campo `email` en `config.json` también está relleno, la variable de entorno tiene prioridad.

---

## Fichero config.json

Ubicación: `src/config/config.json`

```json
{
  "url_login": "https://support.codisysdc.com/Res_Consola/ConsolaTickets_Action",
  "email": "ggbudoia@codisys.es",
  "download_path": "informes/",
  "destinatarios": [
    "gabbudoia@gmail.com"
  ],
  "chrome": {
    "caminho": "C:\\Program Files\\Google\\Chrome\\Application\\chrome.exe",
    "headless": true,
    "user_data_dir": "C:\\ChromeAutomation",
    "window_size": "1920,1080",
    "disable_gpu": true,
    "no_sandbox": true,
    "disable_dev_shm_usage": true
  }
}
```

| Campo | Descripción |
|---|---|
| `url_login` | URL del portal Codisys |
| `email` | Email para login en el portal |
| `download_path` | Carpeta donde se guardan los informes |
| `destinatarios` | Lista de emails que reciben el informe diario |
| `chrome.caminho` | Ruta del ejecutable Chrome — **usado solo en Windows** |
| `chrome.headless` | `true` = Chrome invisible (recomendado siempre) |
| `chrome.user_data_dir` | Directorio de perfil Chrome — **usado solo en Windows** |

Para añadir destinatarios edita el array `destinatarios`:

```json
"destinatarios": [
  "gabbudoia@gmail.com",
  "otro@email.com"
]
```

---

## Ejecutar el script manualmente

### Windows

```cmd
cd C:\Users\<user>\Desktop\Informes
venv\Scripts\activate
for /f "usebackq tokens=1,2 delims==" %%a in (".env") do set %%a=%%b
python -m src.main
```

### Linux

```bash
cd /home/user/Informes
source .venv/bin/activate
export $(grep -v '^#' .env | xargs)
python -m src.main
```

---

## Programar ejecución automática

### Linux — cron

```bash
crontab -e
```

Añade la siguiente línea (se ejecuta todos los días a las 08:00):

```cron
0 8 * * * cd /home/user/Informes && bash -c 'set -a; source .env; set +a; .venv/bin/python -m src.main' >> src/logs/cron.log 2>&1
```

Verificar que cron está activo:

```bash
sudo systemctl status cron

# Si no está activo:
sudo systemctl enable cron && sudo systemctl start cron
```

Ver logs del cron en tiempo real:

```bash
tail -f /home/user/Informes/src/logs/cron.log
```

### Windows — Programador de tareas

1. Abre el **Programador de tareas** (`taskschd.msc`)
2. Haz clic en **Crear tarea básica**
3. Rellena:
   - **Nombre:** `Informes Diarios`
   - **Desencadenador:** Diariamente a las 08:00
   - **Acción:** Iniciar un programa
   - **Programa:** `C:\Users\<user>\Desktop\Informes\run.bat`
4. En **Propiedades** → marca **Ejecutar tanto si el usuario inició sesión como si no**
5. En **Configurar para:** selecciona tu versión de Windows

---

## Logs y monitorización

El script escribe simultáneamente en:
- **Fichero:** `src/logs/execucao.txt` — histórico persistente de todas las ejecuciones
- **stdout** — visible en el terminal y capturado por cron

```bash
# Ver log en tiempo real
tail -f src/logs/execucao.txt

# Ver últimas 50 líneas
tail -n 50 src/logs/execucao.txt
```

### Emails de alerta automáticos

Si el script falla de forma inesperada, se envía automáticamente un email de alerta a los `destinatarios` configurados:

```
Asunto: [ALERTA] Fallo en el script de Informes — DD-MM-YYYY HH:MM:SS
```

El cuerpo incluye el traceback completo para facilitar el diagnóstico.

### Lock file

Para evitar dos instancias ejecutándose simultáneamente, se crea el fichero `src/logs/execucao.lock` al inicio de cada ejecución. Si el script se interrumpe de forma abrupta y el lock no se borra automáticamente, la siguiente ejecución falla con:

```
[ERROR] Ya existe una instancia en ejecución (lock: pid=xxxx iniciado=...)
```

Para resolverlo, borra el lock manualmente:

```bash
# Linux
rm src/logs/execucao.lock

# Windows
del src\logs\execucao.lock
```

---

## Troubleshooting

### Chrome no encontrado (Linux)

```
[ERROR] Chrome no encontrado. Define la variable de entorno CHROME_PATH...
```

```bash
which google-chrome   # verifica si está instalado y en el PATH

# Si no está en el PATH, defínelo manualmente en .env:
echo "CHROME_PATH=/usr/bin/google-chrome" >> .env
```

### Error de autenticación Azure

```
[ERROR] Fallo al obtener token Azure: ...
```

Verifica:
- Las variables `AZURE_TENANT_ID`, `AZURE_CLIENT_ID`, `AZURE_CLIENT_SECRET` son correctas en el `.env`
- El permiso `Mail.Send` tiene **admin consent** concedido en el portal Azure
- El Client Secret no ha expirado — confírmalo en Azure → App registrations → Certificates & secrets

### Login en el portal Codisys ha fallado

```
[ERROR] Login no confirmado.
```

Verifica:
- La variable `senha` es correcta en el `.env`
- El campo `email` en `config.json` es correcto
- El portal responde — pruébalo manualmente en el navegador

### El email no llega a los destinatarios

- `MAIL_SENDER` debe ser un buzón de correo real en el tenant Azure (no un alias ni un grupo de distribución)
- El permiso `Mail.Send` debe ser de tipo **Application** (no Delegated)
- Confirma los destinatarios en `src/config/config.json`

### Lock file impide nueva ejecución

```bash
rm src/logs/execucao.lock    # Linux
del src\logs\execucao.lock   # Windows
```

### La descarga tarda demasiado o no termina

El timeout de descarga es de 180 segundos. Si la conexión al servidor es lenta, aumenta el valor de `DOWNLOAD_TIMEOUT` al inicio de `src/features/filtros.py`:

```python
DOWNLOAD_TIMEOUT = 300   # aumentar a 5 minutos
```
