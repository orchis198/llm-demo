from __future__ import annotations

import streamlit as st

from engines.reporting_engine import validate_report_draft
from services.report_service import build_report_from_voucher
from services.show_dataset_service import ShowDatasetService
from ui.components.file_preview import render_file_preview
from ui.components.print_views import render_print_shell
from ui.components.status_cards import render_kv_table, render_stage_header, render_status_card
from ui.session_state import normalize_editor_rows


def _display_cell(value: object) -> object:
    return "" if value is None else value


def render_financial_report_page(base_dir: str) -> None:
    render_stage_header("会计报表", "这里根据已审核通过的会计凭证生成会计报表初稿，并允许人工修改后审核生效。")
    voucher = st.session_state.get("voucher_draft_v1")
    if voucher is None or voucher.get("approval_status") != "审核通过":
        st.warning("请先完成会计凭证审核。")
        return

    dataset = ShowDatasetService(base_dir)
    manifest = dataset.load_manifest("show")
    review_owner = st.text_input("审核人", value=st.session_state.get("report_review_owner_v1", "李会计"), key="report_review_owner_v1")
    report_type = st.radio("报表类型", ["资产负债表", "利润表"], horizontal=True, key="report_type_v1")
    recommendation, draft = build_report_from_voucher(voucher, report_type, review_owner)
    working_draft = st.session_state.get("report_draft_v1") or draft
    render_status_card(
        "会计报表",
        review_owner,
        working_draft.get("approval_status", "待审核") if working_draft else "待生成",
        working_draft.get("effective_status", "未生效") if working_draft else "未生效",
        voucher.get("voucher_number", manifest["voucher_number"]),
    )

    left, right = st.columns([1.0, 1.2])
    with left:
        st.markdown("#### 推荐报表项")
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
        task_columns[0].metric("当前任务", "正在生成报表建议")
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
        if report_type == "资产负债表":
            st.markdown("#### 官方主体编辑")
            st.caption("当前按资产负债表官方主体结构承接，左右两侧分别对应资产与负债/所有者权益。")
            left_rows = normalize_editor_rows(st.data_editor(
                working_draft.get("left_rows", []),
                num_rows="fixed",
                use_container_width=True,
                hide_index=True,
                key="report_editor_left_v1",
            ))
            right_rows = normalize_editor_rows(st.data_editor(
                working_draft.get("right_rows", []),
                num_rows="fixed",
                use_container_width=True,
                hide_index=True,
                key="report_editor_right_v1",
            ))
            working_draft["left_rows"] = left_rows
            working_draft["right_rows"] = right_rows
        else:
            st.markdown("#### 官方主体编辑")
            st.caption("当前按利润表官方主体结构承接，展示项目、行次、本月数、本年累计数。")
            working_draft["main_rows"] = normalize_editor_rows(st.data_editor(
                working_draft.get("main_rows", []),
                num_rows="fixed",
                use_container_width=True,
                hide_index=True,
                key="report_editor_main_v1",
            ))

        validation = validate_report_draft(working_draft)
        for error in validation["errors"]:
            st.error(error)
        action_columns = st.columns(2)
        if action_columns[0].button("审核通过并生效", type="primary", use_container_width=True, disabled=not validation["can_effective"]):
            working_draft["approval_status"] = "审核通过"
            working_draft["effective_status"] = "已生效"
            st.session_state.report_draft_v1 = working_draft
            st.session_state.report_status_v1 = "审核通过"
            st.success("会计报表已审核通过并生效。")
        action_columns[1].button("全流程演示完成", use_container_width=True, disabled=st.session_state.get("report_status_v1") != "审核通过")

        if report_type == "资产负债表":
            left_html = ''.join(
                f"<tr><td style='padding:8px 10px;'>{_display_cell(row.get('项目'))}</td><td style='padding:8px 10px;text-align:center;'>{_display_cell(row.get('行次'))}</td><td style='padding:8px 10px;text-align:right;'>{_display_cell(row.get('年初数'))}</td><td style='padding:8px 10px;text-align:right;'>{_display_cell(row.get('期末数'))}</td></tr>"
                for row in working_draft.get('left_rows', [])
            )
            right_html = ''.join(
                f"<tr><td style='padding:8px 10px;'>{_display_cell(row.get('项目'))}</td><td style='padding:8px 10px;text-align:center;'>{_display_cell(row.get('行次'))}</td><td style='padding:8px 10px;text-align:right;'>{_display_cell(row.get('年初数'))}</td><td style='padding:8px 10px;text-align:right;'>{_display_cell(row.get('期末数'))}</td></tr>"
                for row in working_draft.get('right_rows', [])
            )
            rows_html = f"<tr><td colspan='4' style='padding:6px 10px;background:#f8fafc;font-weight:800;'>资产</td></tr>{left_html}<tr><td colspan='4' style='padding:6px 10px;background:#f8fafc;font-weight:800;'>负债和所有者权益（或股东权益）</td></tr>{right_html}"
            headers = ['项目','行次','年初数','期末数']
        else:
            rows_html = ''.join(
                f"<tr><td style='padding:8px 10px;'>{_display_cell(row.get('项目'))}</td><td style='padding:8px 10px;text-align:center;'>{_display_cell(row.get('行次'))}</td><td style='padding:8px 10px;text-align:right;'>{_display_cell(row.get('本月数'))}</td><td style='padding:8px 10px;text-align:right;'>{_display_cell(row.get('本年累计数'))}</td></tr>"
                for row in working_draft.get('main_rows', [])
            )
            headers = ['项目','行次','本月数','本年累计数']

        render_print_shell(
            report_type,
            [
                f"表号：{working_draft.get('form_code', '会企01表' if report_type == '资产负债表' else '会企02表')}",
                f"业务编号：{manifest.get('business_id', '')}",
                f"编制单位：{working_draft.get('company_name', manifest.get('company_name', ''))}",
                f"期间：{working_draft.get('period', '')}",
                f"审核人：{review_owner}",
                f"来源凭证：{voucher.get('voucher_number','')}",
                f"金额单位：{working_draft.get('unit_label', '元')}",
            ],
            headers,
            rows_html,
            '打印报表',
            'printReportV1'
        )

    st.markdown("#### show 参考件")
    ref_left, ref_right = st.columns(2)
    with ref_left:
        show_reference_key = "balance_sheet_show_reference" if report_type == "资产负债表" else "profit_statement_show_reference"
        render_file_preview(dataset.resolve_path(manifest[show_reference_key]), allow_expand=True)
    with ref_right:
        st.markdown("#### 官方样例参考")
        reference_key = "balance_sheet_reference" if report_type == "资产负债表" else "profit_statement_reference"
        render_file_preview(dataset.resolve_path(manifest[reference_key]), allow_expand=True)
