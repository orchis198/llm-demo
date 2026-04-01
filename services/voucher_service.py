from __future__ import annotations

from typing import Any

from config import settings
from engines.accounting_engine import AccountingEngine
from llm.provider_info import get_provider_display
from llm.service import build_voucher_recommendation_with_llm


def build_voucher_from_invoice(invoice_data: dict[str, Any], review_owner: str) -> tuple[dict[str, Any], dict[str, Any]]:
    engine = AccountingEngine()
    llm_meta = get_provider_display()
    fallback_reason = None
    try:
        if settings.is_llm_runtime_enabled():
            recommendation, _, _ = build_voucher_recommendation_with_llm(invoice_data)
            recommendation["llm_meta"] = {**llm_meta, "source": "LLM", "fallback": False}
        else:
            raise RuntimeError("LLM disabled")
    except Exception as exc:
        recommendation = engine.generate_ai_recommendation(invoice_data)
        fallback_reason = str(exc)
        recommendation["llm_meta"] = {**llm_meta, "source": "规则回退", "fallback": True, "reason": fallback_reason}
    voucher_draft = engine.build_voucher_draft(invoice_data, recommendation, review_owner=review_owner)
    return recommendation, voucher_draft
