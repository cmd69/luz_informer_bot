# Comandos del bot

Referencia de todos los comandos que el usuario puede usar en Telegram. Los mensajes del bot están en español.

---

## Lista de comandos

| Comando | Descripción |
|---------|-------------|
| `/start` | Mensaje de bienvenida y enlace a la ayuda. |
| `/help` o `/ayuda` | Lista de comandos con breve descripción. |
| `/price` | Precios alrededor de ahora (3 h antes + actual + 3 h después). Al final/inicio del día incluye horas de mañana/ayer. |
| `/today` | Resumen de precios de hoy: min, max, media y desglose por hora con 🟢🟡🔴. |
| `/tomorrow` | Resumen de precios de mañana (mismo formato que /today). |
| `/fetchtoday` | Descarga precios de hoy desde la web y los guarda. |
| `/fetchtomorrow` | Descarga precios de mañana desde la web y los guarda. |
| `/ask <pregunta>` | Pregunta sobre precios (IA con contexto de hoy y mañana). |
| `/models` | Lista modelos disponibles en Ollama. |
| `/models <nombre>` | Elige el modelo a usar en este chat. |
| `/testollama` | Comprueba conexión con Ollama. |
| `/generate_tips` | Obtiene precios de hoy si faltan, genera alertas del día y las envía en vivo al chat; luego las guarda. |
| `/show_alerts` | Muestra las alertas programadas para hoy (hora, tipo, mensaje, enviada/pendiente). |
| `/test_alerts` | Envía la primera alerta del día como mensaje de prueba. |

---

## Detalle por categoría

### Consulta de precios

- **`/price`**: Tabla con la hora actual marcada (⬅️ AHORA). Emojis según umbrales del día (fin de semana usa umbrales más bajos). Si estás cerca del cambio de día, puede mostrar "(ayer)" o "(mañana)" en algunas horas.
- **`/today`**, **`/tomorrow`**: Resumen del día con mínimo, máximo, media y todas las horas con 🟢🟡🔴.

### Obtención de datos

- **`/fetchtoday`**, **`/fetchtomorrow`**: Llamada HTTP a tarifaluzhora.es (para mañana se usa `?date=YYYY-MM-DD`). Si la web no tiene datos para esa fecha, el bot lo indica. Los datos se guardan en la base de datos.

### Alertas

- **`/generate_tips`**: Si no hay 24 tramos de hoy, hace fetch de hoy primero. Genera las alertas del día (franjas verdes y naranjas) y **te va enviando cada alerta en el acto**; al final las guarda para el envío programado. Solo se generan alertas en la franja configurada (p. ej. 7:00–24:00).
- **`/show_alerts`**: Lista las alertas de hoy con ✅ (enviada) o ⏳ (pendiente).
- **`/test_alerts`**: Envía la primera alerta como prueba (formato "🧪 ALERTA DE PRUEBA").

### IA

- **`/ask <pregunta>`**: Envía a Ollama el contexto de precios de hoy y mañana más tu pregunta. Respuestas en español. Usa el modelo por defecto o el elegido con `/models <nombre>`.
- **`/models`**: Lista modelos. **`/models <nombre>`**: Fija el modelo para este chat.

---

## Permisos

Si `TELEGRAM_CHAT_IDS` está configurado, solo esos `chat_id` pueden usar el bot. Cualquier otro recibe un mensaje indicando que no tiene permiso. Para obtener tu `chat_id` puedes usar [@userinfobot](https://t.me/userinfobot).

---

## Resumen rápido (para el usuario)

- **¿Cuánto cuesta ahora?** → `/price`
- **¿Cómo está el día?** → `/today` o `/tomorrow`
- **Actualizar precios** → `/fetchtoday` o `/fetchtomorrow`
- **Generar y recibir alertas en vivo** → `/generate_tips`
- **Ver alertas guardadas** → `/show_alerts`
- **Preguntar algo sobre precios** → `/ask ¿a qué hora es más barato hoy?`

Flujos técnicos: [Arquitectura > Flujo comandos de precios](arquitectura/flujo-comandos-precios.md).
