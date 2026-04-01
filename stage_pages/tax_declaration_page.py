from __future__ import annotations

import streamlit as st

from engines.tax_report_engine import validate_tax_report_draft
from services.show_dataset_service import ShowDatasetService
from services.tax_service import build_tax_report_from_voucher
from ui.components.file_preview import render_file_preview
from ui.components.print_views import render_print_shell
from ui.components.status_cards import render_kv_table, render_stage_header, render_status_card
from ui.session_state import go_to_stage, normalize_editor_rows


def _display_cell(value: object) -> object:
    return "" if value is None else value


def render_tax_declaration_page(base_dir: str) -> None:
    render_stage_header("纳税申报表", "这里根据已审核通过的会计凭证生成纳税申报表初稿，并允许人工修改后审核生效。")
    voucher = st.session_state.get("voucher_draft_v1")
    if voucher is None or voucher.get("approval_status") != "审核通过":
        st.warning("请先完成会计凭证审核。")
        return

    dataset = ShowDatasetService(base_dir)
    manifest = dataset.load_manifest("show")
    review_owner = st.text_input("审核人", value=st.session_state.get("tax_review_owner_v1", "王税务"), key="tax_review_owner_v1")
    recommendation, draft = build_tax_report_from_voucher(voucher, review_owner)
    working_draft = st.session_state.get("tax_draft_v1") or draft
    render_status_card(
        "纳税申报表",
        review_owner,
        working_draft.get("approval_status", "待审核") if working_draft else "待生成",
        working_draft.get("effective_status", "未生效") if working_draft else "未生效",
        voucher.get("voucher_number", manifest["voucher_number"]),
    )

    left, right = st.columns([1.0, 1.2])
    with left:
        st.markdown("#### 推荐申报项")
        st.dataframe(recommendation.get("items", []), use_container_width=True, hide_index=True)

        st.markdown("#### 推荐依据")
        reasons = [item for item in recommendation.get("reasons", []) if item]
        if reasons:
            for reason in reasons:
                st.write(f"- {reason}")
        else:
            st.info("当前未返回明确推荐依据，建议人工复核。")

        st.markdown("#### 智能体任务卡")
        llm_meta = recommendation.get("llm_meta", {}) or {}
        task_columns = st.columns(3)
        task_columns[0].metric("当前任务", "正在生成税表建议")
        task_columns[1].metric("Agent 状态", "规则回退" if llm_meta.get("fallback") else "已完成")
        task_columns[2].metric("推荐来源", llm_meta.get("source", "未知"))
        if llm_meta.get("fallback"):
            st.warning("AI 智能体已切换到规则回退模式，以保证当前流程可继续演示。")
        else:
            st.success("AI 智能体已完成本轮推荐生成，可继续人工复核。")
        if recommendation.get("llm_prompt_summary"):
            st.info(f"提示词摘要：{recommendation.get('llm_prompt_summary')}")
        risk_notes = [item for item in recommendation.get("risk_notes", []) if item]
        if risk_notes:
            st.markdown("**风险提示**")
            for risk in risk_notes:
                st.warning(risk)

        st.markdown("#### LLM 元数据")
        render_kv_table([
            {"字段": "推荐来源", "内容": llm_meta.get("source", "未知")},
            {"字段": "Provider", "内容": llm_meta.get("provider", "未配置")},
            {"字段": "Model", "内容": llm_meta.get("model", "未配置")},
            {"字段": "API Base", "内容": llm_meta.get("api_base", "未配置")},
            {"字段": "Fallback", "内容": "是" if llm_meta.get("fallback") else "否"},
        ], height=180)
    with right:
        st.markdown("#### 官方主表编辑")
        st.caption("当前按官方主表结构承接，优先展示主表固定栏位。")
        edited = st.data_editor(
            working_draft.get("main_sheet_rows", []),
            num_rows="fixed",
            use_container_width=True,
            hide_index=True,
            key="tax_editor_v1",
        )
        working_draft["main_sheet_rows"] = normalize_editor_rows(edited)
        validation = validate_tax_report_draft(working_draft)
        for error in validation["errors"]:
            st.error(error)
        action_columns = st.columns(2)
        if action_columns[0].button("审核通过并生效", type="primary", use_container_width=True, disabled=not validation["can_effective"]):
            working_draft["approval_status"] = "审核通过"
            working_draft["effective_status"] = "已生效"
            st.session_state.tax_draft_v1 = working_draft
            st.session_state.tax_status_v1 = "审核通过"
            st.success("纳税申报表已审核通过并生效。")
        if action_columns[1].button("进入下一步：会计报表", use_container_width=True, disabled=st.session_state.get("tax_status_v1") != "审核通过"):
            go_to_stage("会计报表")
        rows_html = ''.join(
            f"<tr><td style='padding:8px 10px;'>{_display_cell(row.get('项目'))}</td><td style='padding:8px 10px;text-align:center;'>{_display_cell(row.get('栏次'))}</td><td style='padding:8px 10px;text-align:right;'>{_display_cell(row.get('一般项目本月数'))}</td><td style='padding:8px 10px;text-align:right;'>{_display_cell(row.get('一般项目本年累计'))}</td><td style='padding:8px 10px;text-align:right;'>{_display_cell(row.get('即征即退项目本月数'))}</td><td style='padding:8px 10px;text-align:right;'>{_display_cell(row.get('即征即退项目本年累计'))}</td></tr>"
            for row in working_draft.get('main_sheet_rows', [])
        )
        render_print_shell(
            working_draft.get('report_name', '增值税及附加税费申报表'),
            [
                f"表号：{working_draft.get('form_code', '附件1')}",
                f"业务编号：{manifest.get('business_id', '')}",
                f"编制单位：{working_draft.get('company_name', manifest.get('company_name', ''))}",
                f"税款所属期间：{working_draft.get('period', '')}",
                f"审核人：{review_owner}",
                f"来源凭证：{voucher.get('voucher_number','')}",
                f"金额单位：{working_draft.get('unit_label', '元（列至角分）')}",
            ],
            ['项目','栏次','一般项目本月数','一般项目本年累计','即征即退本月数','即征即退本年累计'],
            rows_html,
            '打印申报表',
            'printTaxV1'
        )

    st.markdown("#### show 参考件")
    ref_left, ref_right = st.columns(2)
    with ref_left:
        render_file_preview(dataset.resolve_path(manifest["tax_show_reference"]), allow_expand=True)
    with ref_right:
        st.markdown("#### 官方样例参考")
        render_file_preview(dataset.resolve_path(manifest["tax_reference"]), allow_expand=True)
