# Flujo: /ask y pregunta sobre precios

Cuando el usuario envía **/ask** y una pregunta sobre los precios (por ejemplo "¿cuánto cuesta la luz ahora?" o "¿cuándo es más barato hoy?"), el flujo es el siguiente.

```mermaid
sequenceDiagram
    participant U as Usuario
    participant H as Handler cmd_ask
    participant R as Repository (SQLite)
    participant L as LLM (Ollama)

    U->>H: /ask &lt;pregunta sobre precios&gt;
    H->>H: _reject_if_not_allowed(chat_id)
    alt Chat no permitido
        H->>U: "No tienes permiso..."
    else Chat permitido
        H->>R: obtener_precios_fecha(hoy)
        R-->>H: tramos hoy [(hora, precio), ...]
        H->>R: obtener_precios_fecha(mañana)
        R-->>H: tramos mañana
        H->>H: Construir contexto texto (today/tomorrow 24h €/kWh)
        H->>R: get_modelo_chat(chat_id)
        R-->>H: modelo o None
        H->>L: chat_completion(system + contexto + pregunta, model)
        L-->>H: respuesta texto
        H->>U: respuesta (en español)
    end
```

## Resumen de pasos

1. **Permisos**: se comprueba si el `chat_id` está en `TELEGRAM_CHAT_IDS` (o si la lista está vacía, se permite todo).
2. **Contexto de precios**: se leen de la BD los tramos de **hoy** y **mañana**. Con ellos se arma un texto tipo:  
   `today (24h in €/kWh): 00:00=0.108, 01:00=0.095, ...`  
   `tomorrow (24h in €/kWh): ...`
3. **Modelo**: se usa el modelo guardado para ese chat (`/models <nombre>`) o, si no hay, `LLM_MODEL` de configuración.
4. **LLM**: se llama a Ollama con un system prompt fijo (asistente PVPC, respuestas en español) y un mensaje de usuario que incluye el contexto de precios y la pregunta.
5. **Respuesta**: el texto devuelto por la IA se envía al usuario. Si no hay datos de precios, el contexto indica "Sin datos de precios recientes" y la IA puede decir que no tiene esa información.

## Archivos implicados

- `src/telegram_bot/handlers.py`: `cmd_ask`
- `src/storage/repository.py`: `obtener_precios_fecha`, `get_modelo_chat`
- `src/llm/client.py`: `chat_completion`
- `config/settings.py`: `LLM_MODEL`, `TELEGRAM_CHAT_IDS`
