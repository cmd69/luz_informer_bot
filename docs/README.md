# Documentación del bot Luz Informer

Índice de la documentación del proyecto. Desde aquí puedes navegar a cada sección.

---

## Navegación

| Sección | Descripción |
|--------|-------------|
| [**Configuración**](configuracion.md) | Variables de entorno, umbrales, franja de notificaciones, zona horaria |
| [**Comandos del bot**](comandos.md) | Referencia de todos los comandos disponibles para el usuario |
| [**Arquitectura**](arquitectura/README.md) | Diseño del sistema, flujos y componentes |
| [**Desarrollo**](desarrollo.md) | Ejecución, tests, Docker y estructura del código |

---

## Resumen del proyecto

**luz_informer_bot** (Luz Informer Bot) es un bot de Telegram que:

- Obtiene el **precio PVPC** en España por scraping de [tarifaluzhora.es](https://tarifaluzhora.es/).
- Guarda historial en SQLite y permite consultar precios de hoy y mañana.
- Genera **alertas diarias** (franjas baratas/caras) según umbrales configurables.
- Envía notificaciones en la franja horaria configurada (por defecto 7:00–24:00).
- Responde preguntas sobre precios mediante **Ollama** (LLM local).

Los datos se actualizan con un job diario (20:30) y las alertas se generan a las 21:00; además el usuario puede forzar fetch y generación con `/fetchtoday`, `/fetchtomorrow` y `/generate_tips`.

---

## Enlaces rápidos

- [Configuración (`.env`)](configuracion.md#variables-de-entorno)
- [Lista de comandos](comandos.md#lista-de-comandos)
- [Flujo del scheduler (jobs)](arquitectura/scheduler.md)
- [Flujo de alertas](arquitectura/flujo-alertas.md)
- [Ejecución con Docker](desarrollo.md#ejecución-con-docker)
