# InformesCodisys — Automatización de Reportes Diarios

Sistema de automatización que descarga los informes de incidencias de **ALSEA** y **RESTALIA** desde el portal Codisys, procesa los datos y envía un correo diario con el resumen y los archivos adjuntos.

---

## ¿Qué hace el programa?

Cada vez que se ejecuta, el programa realiza las siguientes acciones de forma automática:

1. **Inicia sesión** en el portal `support.codisysdc.com` con las credenciales configuradas
2. **Aplica filtros** en la consola de tickets: empresas, estados y rango de fechas (últimos 8 meses)
3. **Descarga el informe ALSEA** en formato `.xls`
4. **Descarga el informe RESTALIA** en formato `.xls`
5. **Procesa los archivos** extraídos: cuenta incidencias por categoría, antigüedad y estado
6. **Genera el cuerpo del correo** con el resumen estadístico del día
7. **Envía el correo** vía Outlook con los dos archivos adjuntos
8. **Limpia la carpeta** `informes/`, conservando solo los 10 archivos más recientes

---

## Estructura del proyecto

```
InformesCodisys/
├── src/
│   ├── main.py                  # Punto de entrada principal
│   ├── config/
│   │   ├── config.json          # Configuración general (URLs, emails, rutas)
│   │   └── config_loader.py     # Carga y valida config.json
│   ├── core/
│   │   ├── browser.py           # Inicializa Chrome con Selenium
│   │   ├── email_client.py      # Envío de correo via Outlook (win32com)
│   │   ├── extrair_dados.py     # Procesamiento de Excel y generación del email
│   │   ├── js_api.py            # Helpers de JavaScript para DevExpress
│   │   └── utils.py             # Utilidades de espera y clicks Selenium
│   └── features/
│       ├── login.py             # Flujo de inicio de sesión
│       └── filtros.py           # Filtros, exportación y descarga de informes
├── scripts/
│   └── executar_informes.bat    # Script BAT para ejecutar via Agendador de tareas
├── .env                         # Contraseña (NO se sube al repositorio)
├── .gitignore
└── README.md
```

---

## Cómo funciona internamente

### 1. Login (`src/features/login.py`)

El programa accede a `https://support.codisysdc.com/Account/Login`, rellena los campos de email y contraseña con Selenium y hace clic en "Confirmar". Después espera a que el objeto JavaScript `Combobox_Empresa` esté disponible en la página para confirmar que el login fue exitoso. Si ya hay una sesión activa, omite el paso de login.

### 2. Descarga de informes (`src/features/filtros.py`)

Para cada grupo de empresas (ALSEA y RESTALIA):

- **Abre el panel de filtros** ejecutando la función JavaScript `Show_Filters()`
- **Aplica las empresas** usando los combos DevExpress (`checkComboBox_Empresa`)
- **Aplica los estados** de incidencia: *Asignado, En Proceso, Pendiente, Reabierto*, etc.
- **Aplica el rango de fechas**: desde hace 8 meses hasta hoy, usando las APIs JavaScript de DevExpress (`DateEdit_DesdeFecha`, `DateEdit_HastaFecha`)
- **Exporta a XLS** buscando el botón "Export to XLS" en la página y haciendo clic
- **Espera el archivo**: detecta cuando el `.xls` aparece en la carpeta de descargas y ya no hay ningún `.crdownload` (descarga en progreso)
- **Renombra el archivo** al formato: `ALSEA - DD-MM-YYYY.xls`

Para garantizar la estabilidad con el framework DevExpress, el sistema espera a que:
- `jQuery.active == 0` (sin peticiones AJAX activas)
- `ASPx.GetControlCollection().InCallback() == false` (sin callbacks DevExpress en curso)
- `GridConsolaTickets` esté disponible en el DOM

### 3. Procesamiento de datos (`src/core/extrair_dados.py`)

Lee cada archivo `.xls` con `pandas` y recorre fila por fila calculando:

| Variable | Descripción |
|---|---|
| `total_helpdesk` | Tickets en *CODISYS - HELP DESK* |
| `helpdesk_antigo` | Tickets de Help Desk con más de 1 día de antigüedad |
| `pendientes_cliente_antigo` | Tickets *Pendiente Cliente* con más de 1 día |
| `hardware_st_total` | Incidencias *CODISYS - RESOLUTOR HARDWARE ST* asignadas |
| `hardware_st_antigo` | Hardware ST con más de 1 día de antigüedad |
| `presupuesto_total` | Tickets en estado *Pendiente Presupuesto* |
| `peticion_total` | Tickets de tipo *Petición* en Hardware ST |
| `total_hoje` | Total de incidencias abiertas hoy |
| `comercial_total` *(solo RESTALIA)* | Tickets en categoría *Comercial* |
| `solicitudes_total` *(solo RESTALIA)* | Tickets en *Solicitudes Restalia* |

Las fechas se normalizan al formato `dd/MM/yy` independientemente de si vienen como número serial de Excel, objeto `datetime` o cadena de texto.

### 4. Envío de correo (`src/core/email_client.py`)

Utiliza **Outlook instalado en Windows** (via `win32com.client`) con la cuenta ya conectada. No requiere contraseña SMTP ni configuración adicional. Adjunta los dos archivos descargados y envía el correo a los destinatarios definidos en `config.json`.

---

## Requisitos

- **Windows** (el envío de correo usa Outlook de Windows)
- **Python 3.10+**
- **Google Chrome** instalado en `C:\Program Files\Google\Chrome\Application\chrome.exe`
- **Microsoft Outlook** instalado y con sesión activa
- **Selenium Manager** incluido en Selenium 4.6+ (descarga el ChromeDriver automáticamente)

### Dependencias Python

```
selenium
pandas
openpyxl
xlrd
pywin32
python-dotenv
python-dateutil
```

---

## Instalación y configuración

### 1. Crear el entorno virtual e instalar dependencias

```cmd
cd C:\Users\gabbu\Desktop\InformesCodisys-main
python -m venv .venv
.venv\Scripts\activate
pip install selenium pandas openpyxl xlrd pywin32 python-dotenv python-dateutil
```

### 2. Configurar `src/config/config.json`

```json
{
  "url_login": "https://support.codisysdc.com/Res_Consola/ConsolaTickets_Action",
  "email": "tu_usuario@codisys.es",
  "correo_login": "tu_cuenta@outlook.com",
  "download_path": "informes/",
  "destinatarios": ["destinatario@ejemplo.com"],
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

### 3. Crear el archivo `.env`

Crea un archivo `.env` en la raíz del proyecto (nunca lo subas al repositorio):

```env
senha=TU_CONTRASEÑA_DEL_PORTAL_CODISYS
```

### 4. Ejecutar

```cmd
cd C:\Users\gabbu\Desktop\InformesCodisys-main
.venv\Scripts\python.exe -m src.main
```

---

## Automatización con el Programador de Tareas de Windows

Para ejecutarlo automáticamente cada día sin abrir ninguna ventana:

1. Abre el **Programador de tareas** de Windows
2. Crea una nueva tarea básica
3. En *Acción*, selecciona **Iniciar un programa**
4. Programa: `C:\Users\gabbu\Desktop\InformesCodisys-main\scripts\executar_informes.bat`
5. Define el horario deseado (por ejemplo, todos los días laborables a las 17:00)

El script `.bat` ya redirige la salida a `logs/saida_agendador.txt` para que puedas revisar si algo falló.

---

## Alternativa con Microsoft Azure

En lugar de ejecutar el programa en un PC con Windows, es posible migrarlo completamente a **Azure** para que funcione en la nube sin depender de ningún equipo local. A continuación se describe la arquitectura equivalente:

### Componentes Azure

| Componente local | Equivalente en Azure |
|---|---|
| Programador de tareas de Windows | **Azure Logic Apps** o **Azure Functions** con trigger Timer (cron) |
| Script Python corriendo en el PC | **Azure Container Instance** con la imagen Docker del programa |
| Contraseña en `.env` | **Azure Key Vault** — almacenamiento seguro de secretos |
| Carpeta `informes/` local | **Azure Blob Storage** — almacenamiento de los archivos descargados |
| Outlook local para envío de email | **Microsoft Graph API** con una cuenta M365 |
| Logs en disco | **Azure Monitor / Application Insights** |

### Arquitectura sugerida

```
Azure Logic Apps (cron diario)
        │
        ▼
Azure Container Instance
  └─ Imagen Docker con:
       ├─ Python + Selenium
       ├─ Chrome headless
       └─ src/main.py
        │
        ├──► Azure Key Vault        → lee la contraseña del portal Codisys
        ├──► Azure Blob Storage     → guarda los archivos .xls descargados
        └──► Microsoft Graph API    → envía el correo desde una cuenta M365
```

### Ventajas de migrar a Azure

- **Sin dependencia de hardware local**: el programa corre aunque el PC esté apagado
- **Alta disponibilidad**: Azure garantiza la ejecución aunque haya fallos puntuales
- **Gestión de secretos segura**: las contraseñas solo existen en Key Vault, nunca en archivos
- **Escalabilidad**: si en el futuro hay más empresas o más informes, solo se ajusta el contenedor
- **Trazabilidad y alertas**: Application Insights permite ver logs y configurar alertas si algo falla

### Cómo sería el envío de correo con Microsoft Graph API

En lugar de `win32com.client` (que requiere Outlook instalado localmente), se usaría la Microsoft Graph API con una cuenta de servicio M365:

```python
import requests
import base64

def enviar_email_graph(access_token, destinatarios, asunto, cuerpo, rutas_adjuntos):
    adjuntos = []
    for ruta in rutas_adjuntos:
        with open(ruta, "rb") as f:
            contenido = base64.b64encode(f.read()).decode("utf-8")
        adjuntos.append({
            "@odata.type": "#microsoft.graph.fileAttachment",
            "name": os.path.basename(ruta),
            "contentBytes": contenido
        })

    payload = {
        "message": {
            "subject": asunto,
            "body": {"contentType": "Text", "content": cuerpo},
            "toRecipients": [{"emailAddress": {"address": d}} for d in destinatarios],
            "attachments": adjuntos
        }
    }

    headers = {
        "Authorization": f"Bearer {access_token}",
        "Content-Type": "application/json"
    }

    requests.post(
        "https://graph.microsoft.com/v1.0/me/sendMail",
        json=payload,
        headers=headers
    )
```

El `access_token` se obtiene automáticamente con una **Managed Identity** de Azure, sin ninguna contraseña en el código.

---

## Logs

El programa genera logs en `src/logs/execucao.txt` con los siguientes niveles:

| Nivel | Significado |
|---|---|
| `[DEBUG]` | Progreso normal del flujo |
| `[WARN]` | Situación inesperada pero recuperable |
| `[ERRO]` | Fallo que impide completar una fase |

---

## Seguridad

- La contraseña del portal se lee **siempre desde la variable de entorno `senha`** — nunca escrita en el código
- El archivo `.env` está en `.gitignore` y **nunca se sube al repositorio**
- `config.json` solo contiene URLs, rutas y emails — sin contraseñas
- Los logs nunca exponen contraseñas ni tokens
