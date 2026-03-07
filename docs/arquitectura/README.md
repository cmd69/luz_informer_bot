# Arquitectura

Visión general del sistema y enlaces a los flujos detallados.

---

## Diagrama de alto nivel

```
┌─────────────────────────────────────────────────────────────────┐
│                    SCHEDULER (APScheduler)                      │
│  20:30 → job_fetch_precios   21:00 → job_diseno_alertas         │
│  :00 y :30 → job_enviar_alertas_hora_async                      │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│  Capa de negocio                                                │
│  src/scheduler/jobs.py  ·  src/scheduler/alertas_ia.py          │
│  src/telegram_bot/handlers.py  ·  src/telegram_bot/alerts.py    │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│  Datos: src/storage/repository.py  →  SQLite                    │
│  precios_historico  ·  alertas_programadas  ·  modelo por chat   │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│  Externos: tarifaluzhora.es (HTTP)  ·  Ollama (LLM)  ·  Telegram │
└─────────────────────────────────────────────────────────────────┘
```

---

## Documentos de esta carpeta

| Documento | Contenido |
|-----------|-----------|
| [**Alertas**](alertas.md) | Sistema de alertas: clasificación de zonas, generación, envío y diagrama de capas |
| [**Scheduler**](scheduler.md) | Jobs programados (fetch precios, diseño de alertas, envío cada :00 y :30) |
| [**Flujo: comandos de precios**](flujo-comandos-precios.md) | /price, /today, /tomorrow, /fetchtoday, /fetchtomorrow, /generate_tips, /show_alerts, /test_alerts |
| [**Flujo: generación de alertas**](flujo-alertas.md) | Cómo se generan las alertas a partir de precios (zonas verde/naranja) |
| [**Flujo: /ask**](flujo-ask.md) | Preguntas al LLM con contexto de precios de hoy y mañana |

---

## Estructura del código

| Ruta | Responsabilidad |
|------|-----------------|
| `src/main.py` | Entrypoint: bot Telegram, scheduler, registro de comandos |
| `config/settings.py` | Variables de entorno y helpers (umbrales por fecha, franja notificaciones) |
| `src/precios/tarifaluzhora.py` | Scraping de tarifaluzhora.es y extracción de fecha/precios |
| `src/precios/models.py` | Modelos de datos (PreciosDia, TramoPrecio) |
| `src/storage/repository.py` | Persistencia: precios, alertas, modelo por chat |
| `src/scheduler/jobs.py` | Jobs: fetch precios, diseño alertas, envío por hora |
| `src/scheduler/alertas_ia.py` | Lógica de zonas, mensajes de alerta y generación del día |
| `src/telegram_bot/handlers.py` | Handlers de comandos y respuestas al usuario |
| `src/telegram_bot/alerts.py` | Envío de alertas a TELEGRAM_CHAT_IDS |
| `src/telegram_bot/logging_middleware.py` | Middleware de logging (chat_id, comando, tiempo) |
| `src/llm/client.py` | Cliente Ollama (chat_completion, list_models, health) |
