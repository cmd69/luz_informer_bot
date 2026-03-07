# Luz Informer Bot

Bot de Telegram para consultar precios PVPC en España, alertas y preguntas con IA (Ollama).

## Ejecución con Docker

1. Copiar `.env.example` a `.env` y rellenar al menos `TELEGRAM_BOT_TOKEN` y, opcionalmente, `TELEGRAM_CHAT_IDS`.
2. Levantar el servicio:

```bash
docker compose up -d
```

La base de datos y datos persistentes se guardan en `./data`. El bot arranca con polling y el scheduler (jobs a las 20:30, 21:00 y cada :00/:30).

### Modo desarrollo (hot reload)

```bash
docker compose -f docker-compose.yml -f docker-compose.dev.yml up
```

### Logs

```bash
docker compose logs -f bot
```

## Requisitos

- Docker y Docker Compose.
- Para ejecutar sin Docker: Python 3.12+, ver `requirements.txt`. Variable `DB_PATH` para la base SQLite; `TIMEZONE` (p. ej. Europe/Madrid).

## Documentación

Ver [documentación completa](docs/README.md): configuración, comandos, arquitectura, desarrollo.
