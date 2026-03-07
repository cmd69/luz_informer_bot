# Configuración

Toda la configuración se hace mediante variables de entorno. Se usa un archivo `.env` en la raíz del proyecto (copiar desde `.env.example`).

---

## Variables de entorno

### Telegram

| Variable | Obligatoria | Descripción |
|----------|-------------|-------------|
| `TELEGRAM_BOT_TOKEN` | Sí | Token del bot obtenido con [@BotFather](https://t.me/BotFather). |
| `TELEGRAM_CHAT_IDS` | No* | Lista de `chat_id` separados por coma. Solo esos chats pueden usar el bot. Si está vacía, se permite cualquier chat. |

\* Recomendado rellenarla para no dejar el bot abierto a cualquiera.

### Precios (scraping)

| Variable | Default | Descripción |
|----------|---------|-------------|
| `PRECIO_LUZ_FUENTE` | `tarifaluzhora` | Fuente de precios (actualmente solo esta). |
| `TARIFALUZHORA_URL` | `https://tarifaluzhora.es/` | URL base. Para otro día se usa `?date=YYYY-MM-DD`. |

### LLM (Ollama)

| Variable | Default | Descripción |
|----------|---------|-------------|
| `LLM_BASE_URL` | `http://192.168.1.52:11434/v1/` | URL de la API de Ollama. |
| `LLM_MODEL` | `llama3.2` | Modelo por defecto para /ask y (si se usara) generación de texto. |
| `LLM_API_KEY` | `ollama` | Clave API (Ollama suele no requerirla). |
| `LLM_TIMEOUT` | `60` | Timeout en segundos para llamadas al LLM. |

### Umbrales de precio

Se usan para clasificar horas en verde (barato), amarillo (medio) o rojo (caro) en tablas y alertas.

**Entre semana**

| Variable | Default | Descripción |
|----------|---------|-------------|
| `PRECIO_UMBRAL_BAJO` | `0.12` | Precio ≤ este valor → 🟢 verde. |
| `PRECIO_UMBRAL_ALTO` | `0.25` | Precio ≥ este valor → 🔴 rojo. |

**Fin de semana** (sábado y domingo; suelen tener precios más bajos)

| Variable | Default | Descripción |
|----------|---------|-------------|
| `PRECIO_UMBRAL_BAJO_FINDE` | `0.105` | Verde en fin de semana. |
| `PRECIO_UMBRAL_ALTO_FINDE` | `0.17` | Rojo en fin de semana. |

La función `get_umbrales_fecha(fecha)` en `config/settings.py` devuelve el par (bajo, alto) según el día.

### Zona horaria

| Variable | Default | Descripción |
|----------|---------|-------------|
| `TIMEZONE` | `Europe/Madrid` | Zona horaria para "hoy", jobs programados y franja de alertas. |

### Franja horaria de notificaciones

Solo se **generan** y **envían** alertas cuya hora de envío cae dentro de esta ventana. Evita notificaciones de madrugada.

| Variable | Default | Descripción |
|----------|---------|-------------|
| `ALERTAS_HORA_INICIO` | `7` | Hora de inicio (inclusive), 0–24. |
| `ALERTAS_HORA_FIN` | `24` | Hora de fin (exclusive), 0–24. Default 7–24 = de 7:00 a 24:00 (medianoche). |

Ejemplos:

- `7` y `24` → notificar entre 7:00 y 23:59.
- `8` y `23` → entre 8:00 y 22:59.

### Base de datos

| Variable | Default | Descripción |
|----------|---------|-------------|
| `DB_PATH` | `./data/precio_luz.db` | Ruta del archivo SQLite. En Docker suele ser `/data/precio_luz.db` con volumen montado. |

---

## Archivo de ejemplo

Ver `.env.example` en la raíz del proyecto. Copiarlo a `.env` y ajustar valores:

```bash
cp .env.example .env
# Editar .env con tu TELEGRAM_BOT_TOKEN, TELEGRAM_CHAT_IDS, LLM_BASE_URL, etc.
```

---

## Dónde se usa cada cosa

- **Handlers y respuestas al usuario**: umbrales (por fecha), zona horaria, `TELEGRAM_CHAT_IDS`.
- **Scraper**: `TARIFALUZHORA_URL`, zona horaria para "hoy".
- **Alertas**: umbrales, `ALERTAS_HORA_INICIO`/`ALERTAS_HORA_FIN`, `TELEGRAM_CHAT_IDS`.
- **LLM**: `LLM_BASE_URL`, `LLM_MODEL`, `LLM_TIMEOUT`, modelo por chat en BD.
