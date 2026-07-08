"""Base LLM client shared by every agent.

The project uses Volcengine Ark through its OpenAI-compatible API surface.
Secrets must be supplied through environment variables and are never written
to audit logs or persisted analysis state.
"""

from __future__ import annotations

from functools import lru_cache
from typing import Any

from langchain_openai import ChatOpenAI
from pydantic import SecretStr

from multiple_agent_finance.config.settings import settings


def get_base_llm_metadata() -> dict[str, Any]:
    """Return non-secret base LLM metadata for audit and diagnostics."""

    return {
        "provider": settings.llm_provider,
        "model": settings.llm_model,
        "runtime_model": settings.llm_runtime_model,
        "endpoint_id_configured": bool(settings.llm_endpoint_id),
        "base_url": settings.llm_base_url,
        "temperature": settings.llm_temperature,
        "timeout": settings.llm_timeout,
        "api_key_configured": bool(settings.llm_api_key),
    }


@lru_cache(maxsize=1)
def get_base_llm() -> ChatOpenAI:
    """Create the shared base LLM client.

    Required environment variables:
    - `MAF_LLM_API_KEY`: Volcengine-managed API key.

    Optional overrides:
    - `MAF_LLM_MODEL`: model or Ark endpoint id.
    - `MAF_LLM_BASE_URL`: OpenAI-compatible base URL.
    - `MAF_LLM_TEMPERATURE`
    - `MAF_LLM_TIMEOUT`
    """

    if not settings.llm_api_key:
        raise RuntimeError(
            "MAF_LLM_API_KEY is not set. Configure it in the environment or local .env file."
        )

    return ChatOpenAI(
        model=settings.llm_runtime_model,
        api_key=SecretStr(settings.llm_api_key),
        base_url=settings.llm_base_url,
        temperature=settings.llm_temperature,
        timeout=settings.llm_timeout,
    )


def get_agent_llm(agent_name: str | None = None) -> ChatOpenAI:
    """Return the shared base LLM for an agent.

    `agent_name` is accepted for future routing but all agents currently share
    the same Volcengine DeepSeek base model.
    """

    return get_base_llm()
