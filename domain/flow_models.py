from __future__ import annotations

from dataclasses import dataclass


@dataclass(slots=True)
class StageStatus:
    stage_name: str
    review_owner: str = ""
    status: str = "待审核"
    effect_status: str = "未生效"
