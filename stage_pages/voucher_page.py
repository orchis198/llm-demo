from __future__ import annotations

import copy

import pandas as pd
import streamlit as st

from engines.accounting_engine import validate_voucher_draft
from services.show_dataset_service import ShowDatasetService
from services.voucher_service import build_voucher_from_invoice
from ui.components.file_preview import render_file_preview
from ui.components.print_views import render_print_shell
from ui.components.status_cards import render_kv_table, render_stage_header, render_status_card
from ui.session_state import go_to_stage, normalize_editor_rows


def _invoice_fingerprint(invoice_data: dict) -> tuple:
    return (
        invoice_data.get("invoice_number"),
        invoice_data.get("issue_date"),
        invoice_data.get("total_amount"),
        invoice_data.get("buyer_name"),
        invoice_data.get("seller_name"),
    )


def render_voucher_page(base_dir: str) -> None:
    render_stage_header("会计凭证", "这里根据已确认采数结果生成会计凭证初稿，并允许人工修改后审核通过。")
    intake_invoice = st.session_state.get("intake_invoice_data")
    if intake_invoice is None:
        st.warning("请先完成发票/凭证采数。")
        return

    dataset = ShowDatasetService(base_dir)
    manifest = dataset.load_manifest("show")
    current_review_owner = st.session_state.get("voucher_review_owner_v1", "张会计")
    review_owner = st.text_input("审核人", value=current_review_owner, key="voucher_review_owner_v1")

    recommendation, generated_draft = build_voucher_from_invoice(intake_invoice, review_owner)
    current_fingerprint = _invoice_fingerprint(intake_invoice)
    working_draft = st.session_state.get("voucher_draft_v1")
    if working_draft is None or working_draft.get("source_invoice_fingerprint") != current_fingerprint:
        working_draft = copy.deepcopy(generated_draft)
        working_draft["source_invoice_fingerprint"] = current_fingerprint
        st.session_state.voucher_draft_v1 = working_draft

    working_draft["review_owner"] = review_owner
    render_status_card(
        "会计凭证",
        review_owner,
        working_draft.get("approval_status", "待审核"),
        working_draft.get("posting_status", "未入账"),
        working_draft.get("source_invoice_number", manifest["invoice_number"]),
    )

    left, right = st.columns([1.0, 1.2])
    with left:
        st.markdown("#### 推荐分录")
        st.dataframe(recommendation.get("recommended_entries", []), use_container_width=True, hide_index=True)

        st.markdown("#### 推荐依据")
        basis_reasons = [item for item in recommendation.get("classification_reasons", []) if item]
        if basis_reasons:
            for reason in basis_reasons:
                st.write(f"- {reason}")
        else:
            st.info("当前未返回明确推荐依据，建议人工复核。")

        st.markdown("#### 智能体任务卡")
        llm_meta = recommendation.get("llm_meta", {}) or {}
        task_columns = st.columns(3)
        task_columns[0].metric("当前任务", "正在生成凭证建议")
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
        st.markdown("#### 人工审核与凭证编辑")
        st.caption("先修改分录，再查看校验摘要；审核通过后才能进入税表或会计报表。")
        edited = st.data_editor(
            working_draft.get("entries", []),
            num_rows="dynamic",
            use_container_width=True,
            hide_index=True,
            key="voucher_editor_v1",
        )
        working_draft["entries"] = normalize_editor_rows(edited)
        working_draft["review_owner"] = review_owner
        st.session_state.voucher_draft_v1 = working_draft

        validation = validate_voucher_draft(working_draft)
        totals = validation.get("totals") or {"debit": 0.0, "credit": 0.0}
        debit_total = totals.get("debit") or 0.0
        credit_total = totals.get("credit") or 0.0

        summary_columns = st.columns(3)
        summary_columns[0].metric("有效分录数", str(validation.get("entry_count", 0)))
        summary_columns[1].metric("借方合计", f"{debit_total:.2f}")
        summary_columns[2].metric("贷方合计", f"{credit_total:.2f}")

        st.markdown("**审核校验**")
        if validation["errors"]:
            st.warning("当前不可审核通过，请先处理以下问题。")
            for error in validation["errors"]:
                st.error(error)
        else:
            st.success("当前校验已通过，可执行审核通过。")

        st.markdown("**审核操作**")
        action_columns = st.columns(4)
        if action_columns[0].button("保存草稿", use_container_width=True):
            st.session_state.voucher_draft_v1 = copy.deepcopy(working_draft)
            st.success("凭证草稿已保存。")
        if action_columns[1].button("审核通过（并入账）", type="primary", use_container_width=True, disabled=not validation["can_post"]):
            working_draft["approval_status"] = "审核通过"
            working_draft["posting_status"] = "可进入总账"
            st.session_state.voucher_draft_v1 = working_draft
            st.session_state.voucher_status_v1 = "审核通过"
            st.success("会计凭证已审核通过，可进入后续环节。")
        if action_columns[2].button("下一步：纳税申报表", use_container_width=True, disabled=st.session_state.get("voucher_status_v1") != "审核通过"):
            go_to_stage("纳税申报表")
        if action_columns[3].button("下一步：会计报表", use_container_width=True, disabled=st.session_state.get("voucher_status_v1") != "审核通过"):
            go_to_stage("会计报表")

        st.markdown("#### 打印预览")
        business_id = manifest.get("business_id", "")
        voucher_number = working_draft.get("voucher_number") or manifest.get("voucher_number", "")
        voucher_summary = working_draft.get("voucher_summary") or ""
        rows_html = ''.join(
            f"<tr><td style='padding:8px 10px;text-align:center;'>{index}</td><td style='padding:8px 10px;'>{row.get('summary','')}</td><td style='padding:8px 10px;'>{row.get('account','')}</td><td style='padding:8px 10px;text-align:right;'>{row.get('debit') or ''}</td><td style='padding:8px 10px;text-align:right;'>{row.get('credit') or ''}</td></tr>"
            for index, row in enumerate(working_draft.get('entries', []), start=1)
        )
        rows_html += f"<tr><td colspan='3' style='padding:8px 10px;text-align:right;font-weight:800;'>合计</td><td style='padding:8px 10px;text-align:right;font-weight:800;'>{debit_total:.2f}</td><td style='padding:8px 10px;text-align:right;font-weight:800;'>{credit_total:.2f}</td></tr>"
        render_print_shell(
            '记账凭证',
            [
                f"业务编号：{business_id}",
                f"凭证编号：{voucher_number}",
                f"审核人：{review_owner}",
                f"会计期间：{working_draft.get('period','')}",
                f"摘要：{voucher_summary}",
                f"来源发票：{working_draft.get('source_invoice_number','')}",
            ],
            ['序号','摘要','会计科目','借方','贷方'],
            rows_html,
            '打印凭证',
            'printVoucherV1'
        )

    st.markdown("#### show 参考件")
    ref_left, ref_right = st.columns(2)
    with ref_left:
        render_file_preview(dataset.resolve_path(manifest["voucher_show_reference"]))
    with ref_right:
        st.markdown("#### 官方样例参考")
        render_file_preview(dataset.resolve_path(manifest["voucher_reference"]))
