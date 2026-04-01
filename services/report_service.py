from __future__ import annotations

from config import settings
from engines.reporting_engine import ReportingEngine
from llm.provider_info import get_provider_display
from llm.service import build_report_recommendation_with_llm


def build_report_from_voucher(voucher_data: dict, report_type: str, review_owner: str) -> tuple[dict, dict | None]:
    engine = ReportingEngine()
    llm_meta = get_provider_display()
    payload = {**voucher_data, "report_type": report_type}
    try:
        if settings.is_llm_runtime_enabled():
            recommendation, _, _ = build_report_recommendation_with_llm(payload)
            recommendation["can_generate"] = True
            recommendation["llm_meta"] = {**llm_meta, "source": "LLM", "fallback": False}
        else:
            raise RuntimeError("LLM disabled")
    except Exception as exc:
        recommendation = engine.generate_report_recommendation(voucher_data, report_type)
        recommendation["llm_meta"] = {**llm_meta, "source": "规则回退", "fallback": True, "reason": str(exc)}
    draft = engine.build_report_draft(voucher_data, recommendation, review_owner=review_owner) if recommendation.get("can_generate") else None
    return recommendation, draft
