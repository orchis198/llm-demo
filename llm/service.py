from __future__ import annotations

from llm.client import LLMClient
from llm.prompts import (
    REPORT_PROMPT_SUMMARY,
    REPORT_SYSTEM_PROMPT,
    REPORT_USER_TEMPLATE,
    TAX_PROMPT_SUMMARY,
    TAX_SYSTEM_PROMPT,
    TAX_USER_TEMPLATE,
    VOUCHER_PROMPT_SUMMARY,
    VOUCHER_SYSTEM_PROMPT,
    VOUCHER_USER_TEMPLATE,
)
from llm.schemas import REPORT_SCHEMA_KEYS, TAX_SCHEMA_KEYS, VOUCHER_SCHEMA_KEYS


def ensure_required_keys(data: dict, required_keys: list[str]) -> dict:
    missing = [key for key in required_keys if key not in data]
    if missing:
        raise ValueError(f"LLM 返回缺少字段：{', '.join(missing)}")
    return data


def build_voucher_recommendation_with_llm(payload: dict) -> tuple[dict, bool, str | None]:
    client = LLMClient()
    if not client.is_available():
        raise RuntimeError("LLM client is not available")
    result = client.generate_json(
        system_prompt=VOUCHER_SYSTEM_PROMPT,
        user_prompt=VOUCHER_USER_TEMPLATE.format(payload=payload),
    )
    result = ensure_required_keys(result, VOUCHER_SCHEMA_KEYS)
    result["llm_prompt_summary"] = VOUCHER_PROMPT_SUMMARY
    return result, True, None


def build_tax_recommendation_with_llm(payload: dict) -> tuple[dict, bool, str | None]:
    client = LLMClient()
    if not client.is_available():
        raise RuntimeError("LLM client is not available")
    result = client.generate_json(
        system_prompt=TAX_SYSTEM_PROMPT,
        user_prompt=TAX_USER_TEMPLATE.format(payload=payload),
    )
    result = ensure_required_keys(result, TAX_SCHEMA_KEYS)
    result["llm_prompt_summary"] = TAX_PROMPT_SUMMARY
    return result, True, None


def build_report_recommendation_with_llm(payload: dict) -> tuple[dict, bool, str | None]:
    client = LLMClient()
    if not client.is_available():
        raise RuntimeError("LLM client is not available")
    result = client.generate_json(
        system_prompt=REPORT_SYSTEM_PROMPT,
        user_prompt=REPORT_USER_TEMPLATE.format(payload=payload),
    )
    result = ensure_required_keys(result, REPORT_SCHEMA_KEYS)
    result["llm_prompt_summary"] = REPORT_PROMPT_SUMMARY
    return result, True, None
