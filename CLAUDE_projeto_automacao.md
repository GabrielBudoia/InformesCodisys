# CLAUDE.md — Automação de Relatórios Codisys

## Visão Geral

Automação em Python que realiza login no sistema Codisys, descarrega relatórios de incidências para os grupos ALSEA e RESTALIA, processa os dados das planilhas e envia um email diário com o resumo via Outlook local. Corre exclusivamente em Windows (usa `win32com` para Outlook e Chrome instalado localmente).

---

## Estrutura do Projeto

```
projeto/
├── main.py                    # Ponto de entrada principal
├── config.json                # Configuração (URLs, emails, paths, Chrome)
├── logs/
│   └── execucao.txt           # Log de execução (gerado em runtime)
├── informes/                  # Pasta de download dos relatórios (gerada em runtime)
└── src/
    ├── config/
    │   ├── __init__.py
    │   └── config_loader.py   # Carrega e valida config.json
    ├── core/
    │   ├── __init__.py
    │   ├── browser.py         # Criação do WebDriver Chrome
    │   ├── email_client.py    # Envio de email via Outlook (win32com)
    │   ├── extrair_dados.py   # Extração de dados das planilhas + montagem do email
    │   ├── js_api.py          # Wrappers de funções JS do DevExpress
    │   └── utils.py           # Helpers Selenium (clicar, esperar DevExpress)
    └── features/
        ├── __init__.py
        ├── filtros.py         # Lógica de filtros, download e exportação
        └── login.py           # Fluxo de autenticação no Codisys
```

---

## Fluxo de Execução (`main.py`)

1. **Carregar config** — `load_config()` lê `config.json` e valida campos obrigatórios.
2. **Obter senha** — via variável de ambiente `senha` (nunca em ficheiro).
3. **Login** — `create_browser()` + `fazer_login()` abrem o Chrome e autenticam no Codisys.
4. **Download de relatórios** — `baixar_relatorio()` é chamado duas vezes (ALSEA, depois RESTALIA), aplicando filtros de empresa e estado e exportando para XLS/XLSX/CSV.
5. **Fechar browser** — sempre no bloco `finally`.
6. **Processar planilhas** — `extrair_dados_planilha()` lê cada ficheiro e compila métricas de tickets.
7. **Enviar email** — `montar_email()` + `enviar_email()` via Outlook local.
8. **Limpeza** — `manter_apenas_10_mais_recentes()` apaga os ficheiros mais antigos da pasta de informes.

---

## Configuração (`config.json`)

| Campo | Descrição |
|---|---|
| `url_login` | URL da consola Codisys |
| `email` | Email de login no site |
| `correo_login` | Email da conta Outlook usada para envio |
| `download_path` | Pasta onde os relatórios são guardados (`informes/`) |
| `destinatarios` | Lista de emails destinatários do relatório diário |
| `chrome.caminho` | Caminho do executável do Chrome |
| `chrome.headless` | `true` para correr sem janela |
| `chrome.user_data_dir` | Perfil do Chrome para automação |

**A senha nunca vai em `config.json`.** Deve ser definida como variável de ambiente:
```
set senha=XXXXXXXXX
```

---

## Dependências

```
selenium
pandas
openpyxl
xlrd
pywin32          # win32com para Outlook
python-dateutil  # relativedelta em filtros.py
```

Instalar tudo com:
```bash
pip install selenium pandas openpyxl xlrd pywin32 python-dateutil
```

Também é necessário ter o **ChromeDriver** compatível com a versão do Chrome instalado e disponível no PATH.

---

## Como Executar

```bash
set senha=XXXXXXXXX
python main.py
```

O log de execução fica em `logs/execucao.txt` com timestamps em cada linha.

---

## Módulos Principais

### `src/features/filtros.py`
Contém toda a lógica de interação com os filtros DevExpress da consola:
- `baixar_relatorio()` — função principal: abre filtros → preenche empresas e estados → aplica datas (últimos 8 meses) → exporta → aguarda download → renomeia o ficheiro.
- `esperar_estavel()` — aguarda jQuery idle + ASPx sem callback + grid carregada antes de continuar.
- `esperar_download_novo()` — polling de 180 s à espera do ficheiro novo na pasta (ignora `.crdownload`).

### `src/features/login.py`
- `fazer_login()` — acede à página de login, preenche email e senha, clica em confirmar e valida o sucesso verificando se o objeto JS `Combobox_Empresa` existe no DOM.
- Antes de fazer login, verifica se a sessão já está ativa para evitar operações desnecessárias.

### `src/core/extrair_dados.py`
- `extrair_dados_planilha()` — itera linha a linha da planilha e conta tickets por categoria (Help Desk, Hardware ST, Comercial, etc.) e por data (hoje vs. antigos).
- `montar_email()` — constrói o corpo do email em espanhol com as métricas de ALSEA e RESTALIA.
- `format_date_ddmmyy()` — normaliza datas vindas do Excel (serial, string ou datetime) para `dd/MM/yy`.

### `src/core/email_client.py`
- `enviar_email()` — usa `win32com.client` para criar e enviar um email via Outlook já autenticado no Windows. Não usa SMTP nem credenciais adicionais.

### `src/core/browser.py`
- `create_browser()` — instancia o Chrome com as opções do `config.json`: headless, user-data-dir, tamanho da janela e preferências de download automático.

---

## Convenções e Decisões de Arquitetura

- **Senha via env var** — nunca persistida em disco. O `main.py` lança `RuntimeError` se não encontrar `os.getenv("senha")`.
- **Log centralizado** — toda a lógica de logging passa por `escrever_log()` em `main.py`. Módulos filhos usam `print()` para debug, o `main.py` captura exceções e escreve no log.
- **Sem SMTP** — o envio é 100% via Outlook local (`win32com`). Não há senhas de email em nenhum lado.
- **Tolerância a erros por fase** — cada fase (login, download, processamento, email, limpeza) tem o seu próprio `try/except`, por isso uma falha numa fase não impede as seguintes.
- **DevExpress** — o sistema Codisys usa DevExpress ASP.NET. As esperas (`esperar_ajax`, `esperar_callback_devexpress`, `esperar_grid_pronto`) são essenciais antes de qualquer interação — nunca usar `time.sleep` fixo como substituto.
- **Renomeação de ficheiros** — os relatórios são renomeados para `ALSEA - DD-MM-YYYY.xlsx` / `RESTALIA - DD-MM-YYYY.xlsx` imediatamente após o download, com sufixo numérico em caso de colisão.
- **Limpeza automática** — mantém apenas os 10 ficheiros mais recentes em `informes/` para não acumular disco.

---

## Empresas e Estados Configurados

**ALSEA:** ALSEA SEDE - EU, ARCHIES - ALSEA CO, BURGER KING - ALSEA EU, CHILLIS - ALSEA MX, DOMINO´S PIZZA - ALSEA EU, FOSTER'S HOLLYWOOD - ALSEA EU, GINOS - ALSEA EU, ITALIANNIS - ALSEA MX, OLE MOLE - ALSEA, PF CHANGS - ALSEA MX, STARBUCKS - ALSEA EU, VIPS - ALSEA EU, VIPS - ALSEA MX

**RESTALIA:** 100M - RESTALIA, CLS / MLS - RESTALIA, PANTHER - RESTALIA, PEPETACO - RESTALIA, RESTALIA - SEDE, TGB - RESTALIA

**Estados filtrados:** ASIGNADO, ASIGNADO PENDIENTE, EN ESPERA, REABIERTO, EN PROCESO, PENDIENTE, PENDIENTE CLIENTE, PENDIENTE MATERIAL, PENDIENTE PRESUPUESTO, PENDIENTE DE PROVEEDOR

---

## Troubleshooting Comum

| Sintoma | Causa Provável | Solução |
|---|---|---|
| `RuntimeError: Variável de ambiente 'senha' não encontrada` | Env var não definida | `set senha=XXXX` antes de correr |
| `[ERRO] Login não confirmado` | Credenciais erradas ou sessão bloqueada | Verificar email/senha; limpar `user_data_dir` |
| Download nunca termina (timeout 180s) | Exportação não foi acionada ou rede lenta | Verificar se `esperar_estavel()` não faz timeout antes |
| `[ERRO] Não foi possível aplicar datas` | DevExpress não carregou ou API JS mudou | Inspecionar `DateEdit_DesdeFecha` no browser manual |
| Email não enviado | Outlook não está aberto / conta não configurada | Garantir que o Outlook está autenticado no Windows |
| `xlrd` error em `.xlsx` | Versão antiga do xlrd (só suporta `.xls`) | O código já usa `openpyxl` para `.xlsx` — verificar extensão real do ficheiro |
