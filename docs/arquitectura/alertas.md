# Sistema de alertas

Descripción del sistema de alertas: clasificación de zonas, generación de mensajes y envío programado.

---

## Diagrama de flujo

```
┌─────────────────────────────────────────────────────────────────┐
│                    SCHEDULER (APScheduler)                      │
│  Cron: 20:30 → job_fetch_precios()                              │
│  Cron: 21:00 → job_diseno_alertas()                             │
│  Cron: :00,:30 → job_enviar_alertas_hora_async()                │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│  src/scheduler/jobs.py                                          │
│  ├─ job_fetch_precios() → fetch_precios_dia()                   │
│  ├─ job_diseno_alertas() → generar_alertas_dia()                │
│  └─ job_enviar_alertas_hora_async() → enviar_alertas_hora()     │
├─────────────────────────────────────────────────────────────────┤
│  src/scheduler/alertas_ia.py                                    │
│  ├─ _zonas_dia() → clasifica horas (verde/naranja/neutro)       │
│  ├─ _precios_texto(), _tabla_franja(), _emoji_precio()           │
│  └─ generar_alertas_dia() → lista (hora_envio, tipo, mensaje)  │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│  src/storage/repository.py                                      │
│  guardar_alertas_programadas()  ·  obtener_alertas_pendientes_hora() │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│  src/telegram_bot/alerts.py  →  enviar_alertas_hora()            │
│  Solo en franja ALERTAS_HORA_INICIO..ALERTAS_HORA_FIN            │
└─────────────────────────────────────────────────────────────────┘
```

---

## Clasificación de zonas

- **Franja analizada:** 7:00–02:00 (horas 7..23 y 0..2 en orden cronológico).
- **Umbrales:** definidos en [Configuración](../configuracion.md#umbrales-de-precio). Entre semana usa `PRECIO_UMBRAL_BAJO` / `PRECIO_UMBRAL_ALTO`; fin de semana usa `PRECIO_UMBRAL_BAJO_FINDE` / `PRECIO_UMBRAL_ALTO_FINDE`.
- **Verde:** precio ≤ umbral bajo.
- **Naranja:** precio ≥ umbral alto.
- **Neutro:** resto (no generan alerta).

---

## Tipos de alerta

| Tipo | Cuándo se envía | Contenido |
|------|------------------|-----------|
| `verde_antes` | 30 min antes del bloque verde: (h-1):30 | Cabecera franja barata (horas inicio–fin) |
| `verde_inicio` | Al inicio del bloque verde: h:00 | Cabecera + tabla de precios de la franja |
| `naranja` | 30 min antes del bloque naranja: (h-1):30 | Cabecera franja cara |
| `naranja_inicio` | Al inicio del bloque naranja: h:00 | Cabecera + tabla de precios de la franja |

Los mensajes son **sin IA**: texto fijo con cabecera y, en "inicio", tabla con emojis 🟢🟡🔴 según umbrales.

---

## Franja de notificaciones

Solo se **generan** y **envían** alertas cuya hora de envío cae dentro de la franja configurada (`ALERTAS_HORA_INICIO`–`ALERTAS_HORA_FIN`). Por defecto 7–24 (de 7:00 a 24:00). Ver [Configuración](../configuracion.md#franja-horaria-de-notificaciones).

---

## Quién dispara la generación

- **Automático:** job `job_diseno_alertas` a las 21:00 (tras el fetch de las 20:30).
- **Manual:** comando `/generate_tips`. Opcionalmente hace fetch de hoy si faltan datos; luego llama a `generar_alertas_dia(hoy)` y envía cada alerta en vivo al usuario que ejecutó el comando.

---

## Archivos

- `src/scheduler/alertas_ia.py`: `generar_alertas_dia`, `_zonas_dia`, `_precios_texto`, `_tabla_franja`, `job_diseno_alertas`
- `src/telegram_bot/alerts.py`: `enviar_alertas_hora`
- `config/settings.py`: umbrales, `get_umbrales_fecha`, `hora_en_franja_notificacion`

Detalle del flujo paso a paso: [Flujo: generación de alertas](flujo-alertas.md).
