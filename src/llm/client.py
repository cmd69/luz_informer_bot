"""Cliente OpenAI-compatible para Ollama (u otro servidor)."""
import logging
import time
from typing import Optional

from openai import OpenAI

from config.settings import LLM_API_KEY, LLM_BASE_URL, LLM_MODEL, LLM_TIMEOUT

logger = logging.getLogger(__name__)
MAX_PROMPT_LOG_LEN = 150


def get_client(api_key: Optional[str] = None, base_url: Optional[str] = None) -> OpenAI:
    return OpenAI(
        api_key=api_key or LLM_API_KEY,
        base_url=base_url or LLM_BASE_URL.rstrip("/") + "/",
        timeout=LLM_TIMEOUT,
    )


def _prompt_summary(messages: list[dict]) -> str:
    parts = []
    for m in messages:
        role = m.get("role", "?")
        content = (m.get("content") or "")
        length = len(content)
        preview = content[:MAX_PROMPT_LOG_LEN] + "..." if len(content) > MAX_PROMPT_LOG_LEN else content
        parts.append(f"{role}(len={length}): {preview!r}")
    return " | ".join(parts)


def chat_completion(
    messages: list[dict],
    model: Optional[str] = None,
    api_key: Optional[str] = None,
    base_url: Optional[str] = None,
    caller: Optional[str] = None,
    log_context: Optional[str] = None,
) -> str:
    client = get_client(api_key=api_key, base_url=base_url)
    model = model or LLM_MODEL
    caller_str = caller or "llm"
    if log_context:
        caller_str = f"{caller_str} {log_context}"
    prompt_summary = _prompt_summary(messages)
    started = time.perf_counter()
    try:
        resp = client.chat.completions.create(model=model, messages=messages)
        elapsed = time.perf_counter() - started
        content = ""
        if resp.choices and resp.choices[0].message:
            content = resp.choices[0].message.content or ""
        usage_info = ""
        if getattr(resp, "usage", None) is not None:
            u = resp.usage
            prompt_tokens = getattr(u, "prompt_tokens", None)
            completion_tokens = getattr(u, "completion_tokens", None)
            total = getattr(u, "total_tokens", None)
            if prompt_tokens is not None or completion_tokens is not None:
                usage_info = f" prompt_tokens={prompt_tokens or '?'} completion_tokens={completion_tokens or '?'} total_tokens={total or '?'}"
        logger.info(
            "llm_completion caller=%s model=%s elapsed_sec=%.2f response_len=%d%s | prompts: %s",
            caller_str, model, elapsed, len(content), usage_info,
            prompt_summary[:500] + "..." if len(prompt_summary) > 500 else prompt_summary,
        )
        return content
    except Exception as e:
        elapsed = time.perf_counter() - started
        logger.warning("llm_error caller=%s model=%s elapsed_sec=%.2f error=%s", caller_str, model, elapsed, e)
        raise RuntimeError(f"LLM error: {e}") from e


def ollama_health(base_url: Optional[str] = None) -> tuple[bool, str]:
    import httpx
    url = (base_url or LLM_BASE_URL).rstrip("/")
    base = url.replace("/v1", "").rstrip("/")
    try:
        r = httpx.get(f"{base}/api/tags", timeout=10.0)
        r.raise_for_status()
        data = r.json()
        models = data.get("models", [])
        names = [m.get("name", "?") for m in models[:5]]
        return True, f"Ollama correcto. Modelos: {', '.join(names) or 'ninguno'}."
    except httpx.TimeoutException:
        return False, "Error de Ollama: tiempo agotado"
    except httpx.ConnectError as e:
        return False, f"Error de Ollama: conexión rechazada ({e})"
    except Exception as e:
        return False, f"Error de Ollama: {e}"


def list_models(base_url: Optional[str] = None) -> list[str]:
    import httpx
    url = (base_url or LLM_BASE_URL).rstrip("/").replace("/v1", "").rstrip("/")
    try:
        r = httpx.get(f"{url}/api/tags", timeout=10.0)
        r.raise_for_status()
        data = r.json()
        return [m.get("name", "") for m in data.get("models", []) if m.get("name")]
    except Exception:
        return []
