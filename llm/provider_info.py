from __future__ import annotations

from config import settings


def get_provider_display() -> dict[str, str]:
    api_base = settings.LLM_API_BASE
    display_base = api_base.replace("https://", "").replace("http://", "")
    return {
        "provider": settings.LLM_PROVIDER,
        "model": settings.LLM_MODEL,
        "api_base": display_base,
        "mode": "LLM" if settings.is_llm_runtime_enabled() else "规则",
    }
