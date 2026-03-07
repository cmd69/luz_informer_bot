# Desarrollo

Ejecución del proyecto, tests y estructura del código.

---

## Estructura del proyecto

```
luz_informer_bot/
├── config/
│   └── settings.py          # Variables de entorno y helpers
├── src/
│   ├── main.py              # Entrypoint: bot + scheduler
│   ├── precios/
│   │   ├── tarifaluzhora.py # Scraping tarifaluzhora.es
│   │   └── models.py        # PreciosDia, TramoPrecio
│   ├── storage/
│   │   └── repository.py    # SQLite: precios, alertas, modelo por chat
│   ├── scheduler/
│   │   ├── jobs.py          # job_fetch_precios, job_diseno_alertas, job_enviar_alertas_hora_async
│   │   └── alertas_ia.py    # generar_alertas_dia, _zonas_dia, mensajes
│   ├── telegram_bot/
│   │   ├── handlers.py      # Comandos /price, /today, /ask, etc.
│   │   ├── alerts.py        # enviar_alertas_hora
│   │   └── logging_middleware.py
│   └── llm/
│       └── client.py        # Ollama: chat_completion, list_models, health
├── tests/
│   ├── test_alerts_commands.py
│   ├── test_scheduler.py
│   └── manual_test_alerts.py
├── docs/                    # Documentación (este directorio)
├── data/                    # Volumen: DB y datos persistentes
├── .env.example
├── .env                     # No versionado
├── docker-compose.yml
├── Dockerfile
├── requirements.txt
└── README.md
```

---

## Ejecución con Docker

**Recomendado.** No hace falta instalar Python ni dependencias en el host.

1. Copiar `.env.example` a `.env` y rellenar al menos `TELEGRAM_BOT_TOKEN` y, si quieres restringir, `TELEGRAM_CHAT_IDS`.
2. Levantar el servicio:

```bash
docker compose up -d
```

La base de datos y datos persistentes van en `./data` (volumen montado). El bot arranca con polling y el scheduler (jobs a las 20:30, 21:00 y cada :00/:30).

### Modo desarrollo (hot reload)

Si tienes `docker-compose.dev.yml` o similar con montaje de código y `watchmedo`, los cambios en `.py` reinician el proceso sin reconstruir la imagen.

### Logs

```bash
docker compose logs -f bot
```

---

## Tests

Los tests usan pytest y pytest-asyncio. El directorio `tests/` no está incluido en la imagen por defecto; hay que montarlo o ejecutar los tests desde el host si tienes el entorno.

### Dentro del contenedor (montando tests)

```bash
docker compose run --rm -v "$(pwd)/tests:/app/tests:ro" bot python -m pytest tests/test_alerts_commands.py tests/test_scheduler.py -v
```

Variables útiles para tests que usan `TELEGRAM_CHAT_IDS`:

```bash
docker compose run --rm -v "$(pwd)/tests:/app/tests:ro" -e TELEGRAM_CHAT_IDS=123456789 bot python -m pytest tests/ -v
```

### Test manual de alertas

Script que hace fetch real y genera alertas (sin pytest):

```bash
docker compose run --rm -v "$(pwd)/tests:/app/tests:ro" bot python tests/manual_test_alerts.py
```

---

## Requisitos del sistema

- Docker y Docker Compose.
- Para ejecutar sin Docker: Python 3.12+, dependencias en `requirements.txt`, y base de datos en la ruta indicada por `DB_PATH`. La zona horaria y el scheduler asumen `TIMEZONE` (p. ej. Europe/Madrid).

---

## Documentación relacionada

- [Configuración](configuracion.md) — Variables de entorno.
- [Arquitectura](arquitectura/README.md) — Componentes y flujos.
- [Comandos del bot](comandos.md) — Referencia de comandos.
