from __future__ import annotations

from config import settings
from engines.tax_report_engine import TaxReportEngine
from llm.provider_info import get_provider_display
from llm.service import build_tax_recommendation_with_llm


def build_tax_report_from_voucher(voucher_data: dict, review_owner: str) -> tuple[dict, dict | None]:
    engine = TaxReportEngine()
    llm_meta = get_provider_display()
    try:
        if settings.is_llm_runtime_enabled():
            recommendation, _, _ = build_tax_recommendation_with_llm(voucher_data)
            recommendation["can_generate"] = True
            recommendation["llm_meta"] = {**llm_meta, "source": "LLM", "fallback": False}
        else:
            raise RuntimeError("LLM disabled")
    except Exception as exc:
        recommendation = engine.generate_tax_report_recommendation(voucher_data)
        recommendation["llm_meta"] = {**llm_meta, "source": "规则回退", "fallback": True, "reason": str(exc)}
    draft = engine.build_tax_report_draft(voucher_data, recommendation, review_owner=review_owner) if recommendation.get("can_generate") else None
    return recommendation, draft
