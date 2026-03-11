# luz_informer_bot

Bot de Telegram que informa sobre precios de la luz en España. Notificaciones, resúmenes diarios e integración con LLM.

## Stack

- **Lenguaje:** Python 3.12
- **Framework:** python-telegram-bot
- **Base de datos:** SQLite (en /data/precio_luz.db)
- **Deploy:** Docker Compose con override de dev
- **Tipo:** dev y prod en el mismo repo

## Arrancar

```bash
# Producción
make up
make down
make build

# Desarrollo (hot-reload via watchmedo)
make up-dev       # docker compose -f docker-compose.yml -f docker-compose.dev.yml up -d
make down-dev
make test-dev
```

## Ejecución de comandos

**Para desarrollo, usar siempre el compose de dev (`make up-dev` / `make down-dev`).**

**Todos los comandos que requieren librerías se ejecutan dentro del contenedor:**

```bash
# Tests
make test-dev
# equivale a: docker compose -f docker-compose.yml -f docker-compose.dev.yml run --rm bot python -m pytest tests/ -v

# Shell interactivo
docker compose -f docker-compose.yml -f docker-compose.dev.yml exec bot bash

# Ejecutar script
docker compose -f docker-compose.yml -f docker-compose.dev.yml exec bot python -m src.<modulo>
```

**Nunca ejecutar `python3`, `pip install` u otros comandos directamente en el host.**

**El `.venv` local es solo para IDE/linters (ruff), no para ejecutar código.**

## Estructura

```
luz_informer_bot/
├── docker-compose.yml        # prod
├── docker-compose.dev.yml    # dev override (hot-reload via watchmedo)
├── Dockerfile                # multi-stage: builder / runtime
├── Makefile
├── src/
├── tests/
├── config/
├── data/                     # SQLite DB (persistente)
├── requirements.txt
├── requirements-dev.txt
└── pyproject.toml
```

## Puertos

Sin puertos expuestos (bot de Telegram usa polling).

## Convención de commits

```
[NN] TYPE(scope): descripción breve
```

- `[NN]` secuencial por repo (último: `[23]`, siguiente: `[24]`)
- Tipos: `FEAT` `FIX` `DOCS` `REFACTOR` `CHORE` `TEST` `CI` `INFRA` `STYLE`
- Guía completa: `~/.agent/CODING.md`
