from __future__ import annotations

from typing import Any

import pandas as pd
import streamlit as st


def init_session_state(defaults: dict) -> None:
    for key, value in defaults.items():
        if key not in st.session_state:
            st.session_state[key] = value


def _normalize_cell_value(value: Any) -> Any:
    if value is None:
        return None
    if isinstance(value, float) and pd.isna(value):
        return None
    text = str(value).strip() if not isinstance(value, (int, float)) else None
    if text is not None and text.lower() in {"", "none", "nan", "null", "<na>"}:
        return None
    return value


def normalize_editor_rows(value: Any) -> list[dict]:
    if value is None:
        return []

    if isinstance(value, list):
        rows = [row for row in value if isinstance(row, dict)]
    elif isinstance(value, pd.DataFrame):
        rows = value.to_dict("records")
    elif hasattr(value, "to_dict"):
        try:
            records = value.to_dict("records")
            rows = [row for row in records if isinstance(row, dict)] if isinstance(records, list) else []
        except TypeError:
            rows = []
    else:
        try:
            rows = [row for row in list(value) if isinstance(row, dict)]
        except TypeError:
            rows = []

    normalized_rows: list[dict] = []
    for row in rows:
        normalized_rows.append({key: _normalize_cell_value(cell) for key, cell in row.items()})
    return normalized_rows


def go_to_stage(stage_name: str, *, rerun: bool = True) -> None:
    st.session_state.current_stage = stage_name
    if rerun:
        st.rerun()
