from __future__ import annotations

from pathlib import Path

import streamlit as st

from config import settings
from stage_pages.financial_report_page import render_financial_report_page
from stage_pages.intake_page import render_intake_page
from stage_pages.matching_page import render_matching_page
from stage_pages.tax_declaration_page import render_tax_declaration_page
from stage_pages.voucher_page import render_voucher_page
from services.demo_flow_service import get_stage_options
from ui.session_state import init_session_state

BASE_DIR = settings.PROJECT_ROOT

SESSION_DEFAULTS = {
    "current_stage": "发票/凭证采数",
    "stage_selector_v1": "发票/凭证采数",
    "intake_review_owner": "张会计",
    "intake_status": "待审核",
    "intake_effect_status": "未确认",
    "intake_invoice_data": None,
    "parsed_invoice": None,
    "review_draft": None,
    "saved_review": None,
    "submitted_review": None,
    "verify_result": None,
    "source_file_bytes": None,
    "source_page_images": [],
    "preview_page_index": 0,
    "intake_source_mode": "示例文件",
    "intake_selected_sample": None,
    "intake_uploaded_name": "",
    "matching_review_owner": "张会计",
    "matching_status": "待审核",
    "matching_effect_status": "未确认",
    "matching_result": None,
    "voucher_review_owner_v1": "张会计",
    "voucher_draft_v1": None,
    "voucher_status_v1": "待审核",
    "tax_review_owner_v1": "王税务",
    "tax_draft_v1": None,
    "tax_status_v1": "待审核",
    "report_review_owner_v1": "李会计",
    "report_draft_v1": None,
    "report_status_v1": "待审核",
}


def render_stage_navigator() -> str:
    stage_options = get_stage_options()
    current_stage = st.session_state.get("current_stage")
    if current_stage not in stage_options:
        current_stage = stage_options[0]
        st.session_state.current_stage = current_stage

    if st.session_state.get("stage_selector_v1") not in stage_options or st.session_state.get("stage_selector_v1") != current_stage:
        st.session_state.stage_selector_v1 = current_stage

    def _on_stage_change() -> None:
        st.session_state.current_stage = st.session_state.stage_selector_v1

    st.radio(
        "当前环节",
        stage_options,
        index=stage_options.index(st.session_state.stage_selector_v1),
        horizontal=True,
        key="stage_selector_v1",
        on_change=_on_stage_change,
    )
    return st.session_state.current_stage


def render_llm_config_guard() -> None:
    if not settings.is_full_mode():
        st.info("当前为演示模式：无需 API，可用于本地展示；如需启用完整 LLM 能力，请使用完整模式启动。")
        return

    missing = settings.get_missing_llm_config()
    if not missing:
        st.success("当前为完整模式：已检测到 API 配置，可启用 LLM 能力。")
        return

    st.error("当前为完整模式，但未完成 API 配置，请先配置自己的 API 后再启动。")
    st.markdown("#### 配置步骤")
    st.markdown("1. 复制项目根目录下的 `.env.example` 为 `.env`")
    st.markdown("2. 按说明填写您自己的 API 信息")
    st.markdown("3. 重新启动项目，并在启动器中选择完整模式")
    st.code(
        """LLM_ENABLED=true
LLM_PROVIDER=openai-compatible
LLM_MODEL=your_model_name
LLM_API_BASE=https://your-api-base/v1
LLM_API_KEY=your_api_key_here
"""
    )
    st.info(f"当前缺少配置：{', '.join(missing)}")
    st.stop()


def main() -> None:
    st.set_page_config(page_title="demoV1 全流程演示", layout="wide", initial_sidebar_state="expanded")
    st.title("demoV1 全流程演示")
    st.caption("发票/凭证采数 → 三单核对 → 会计凭证 → 纳税申报表 / 会计报表")
    render_llm_config_guard()

    init_session_state(SESSION_DEFAULTS)
    current_stage = render_stage_navigator()

    if current_stage == "发票/凭证采数":
        render_intake_page(str(BASE_DIR))
        return
    if current_stage == "三单核对":
        render_matching_page(str(BASE_DIR))
        return
    if current_stage == "会计凭证":
        render_voucher_page(str(BASE_DIR))
        return
    if current_stage == "纳税申报表":
        render_tax_declaration_page(str(BASE_DIR))
        return
    render_financial_report_page(str(BASE_DIR))


if __name__ == "__main__":
    main()
