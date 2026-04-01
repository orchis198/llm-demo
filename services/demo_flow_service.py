from __future__ import annotations

from typing import Any


def get_stage_options() -> list[str]:
    return [
        "发票/凭证采数",
        "三单核对",
        "会计凭证",
        "纳税申报表",
        "会计报表",
    ]


def build_status_summary(*, current_stage: str, source_label: str, status: str, effect_status: str) -> dict[str, Any]:
    return {
        "current_stage": current_stage,
        "source_label": source_label,
        "status": status,
        "effect_status": effect_status,
    }
