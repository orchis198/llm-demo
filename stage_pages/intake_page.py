from __future__ import annotations

import copy
from io import BytesIO
from pathlib import Path

import pandas as pd
import streamlit as st

from services.intake_service import (
    FIELD_STATUS_OPTIONS,
    HEADER_FIELDS,
    LINE_ITEM_COLUMNS,
    LINE_ITEM_EDITOR_COLUMNS,
    REVIEW_OWNER_FIELD,
    apply_parsed_invoice,
    build_review_draft,
    collect_field_changes,
    collect_sample_files,
    finalize_review_draft,
    is_sample_source,
    parse_invoice,
    render_pdf_pages,
    validate_submission,
)
from engines.invoice_parser import InvoiceParser
from ui.components.file_preview import render_source_snapshot_preview
from ui.components.status_cards import render_stage_header, render_status_card
from ui.session_state import go_to_stage, normalize_editor_rows


def _render_sample_hint(invoice_data: dict) -> None:
    if not is_sample_source(invoice_data):
        return
    st.markdown(
        """
        <div style="background:#f5f7fb;border:1px dashed #b8c2d9;padding:12px 16px;border-radius:8px;color:#6b7280;">
            <div style="font-size:18px;font-weight:700;letter-spacing:1px;">示例数据</div>
            <div style="font-size:12px;margin-top:4px;">当前页面内容用于演示，颜色已弱化，请勿误认为正式审核结论。</div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def _render_overview(invoice_data: dict) -> None:
    st.subheader("解析结果概览")
    metric_columns = st.columns(4)
    metric_columns[0].metric("来源格式", str(invoice_data.get("source_type") or ""))
    metric_columns[1].metric("发票号码", str(invoice_data.get("invoice_number") or invoice_data.get("invoice_code") or ""))
    metric_columns[2].metric("购方名称", str(invoice_data.get("buyer_name") or ""))
    metric_columns[3].metric("价税合计", str(invoice_data.get("total_amount") or ""))


def _render_submission_summary(validation_result: dict) -> None:
    st.subheader("审核建议")
    conclusion = validation_result.get("conclusion", "待确认")
    if conclusion == "审核通过":
        st.success(f"建议审核结论：{conclusion}。当前硬性字段未发现阻断项，可确认采数结果。")
    elif conclusion == "需补充确认":
        st.warning(f"建议审核结论：{conclusion}。当前仍有硬性字段处于存疑或待补充状态，不能直接确认采数结果。")
    else:
        st.error(f"建议审核结论：{conclusion}。当前存在硬性错误项，已直接拦截。")

    for error in validation_result.get("errors", []):
        st.error(error)
    for message in validation_result.get("critical_messages", []):
        st.warning(message)
    for message in validation_result.get("optional_messages", []):
        st.info(message)


def _render_review_editor(parsed_invoice: dict) -> dict:
    st.subheader("人工审核")
    review_draft = copy.deepcopy(st.session_state.review_draft or build_review_draft(parsed_invoice))
    st.caption("审核值默认带入原解析数据。你可以直接保留、修改、或标记为存疑/有误；系统不会额外乱填。")

    owner_columns = st.columns([1.1, 3.8])
    owner_columns[0].markdown("**审核人**")
    review_draft[REVIEW_OWNER_FIELD] = owner_columns[1].text_input(
        "审核人",
        value=str(review_draft.get(REVIEW_OWNER_FIELD, "") or st.session_state.get("intake_review_owner", "张会计")),
        key="review_owner",
    )
    st.session_state.intake_review_owner = review_draft[REVIEW_OWNER_FIELD]

    for field_key, field_label in HEADER_FIELDS:
        current_value = review_draft["field_values"].get(field_key)
        current_status = review_draft["field_statuses"].get(field_key, "正常")
        field_columns = st.columns([1.1, 2.6, 0.9])
        field_columns[0].markdown(f"**{field_label}**")
        if field_key in {"subtotal_amount", "tax_amount", "total_amount"}:
            review_draft["field_values"][field_key] = field_columns[1].text_input(
                "审核值",
                value="" if current_value is None else str(current_value),
                key=f"review_value_{field_key}",
                label_visibility="collapsed",
            )
        elif field_key == "remarks":
            review_draft["field_values"][field_key] = field_columns[1].text_area(
                "审核值",
                value="" if current_value is None else str(current_value),
                height=88,
                key=f"review_value_{field_key}",
                label_visibility="collapsed",
            )
        else:
            review_draft["field_values"][field_key] = field_columns[1].text_input(
                "审核值",
                value="" if current_value is None else str(current_value),
                key=f"review_value_{field_key}",
                label_visibility="collapsed",
            )
        review_draft["field_statuses"][field_key] = field_columns[2].selectbox(
            "状态",
            FIELD_STATUS_OPTIONS,
            index=FIELD_STATUS_OPTIONS.index(current_status) if current_status in FIELD_STATUS_OPTIONS else 0,
            key=f"review_status_{field_key}",
            label_visibility="collapsed",
        )

    st.markdown("#### 发票明细审核")
    original_line_items = pd.DataFrame(parsed_invoice.get("line_items", []), columns=[column_key for column_key, _ in LINE_ITEM_COLUMNS])
    original_line_items = original_line_items.rename(columns=dict(LINE_ITEM_COLUMNS))
    st.markdown("**原解析明细**")
    if original_line_items.empty:
        st.info("当前未解析出发票明细。")
    else:
        st.dataframe(original_line_items, use_container_width=True, hide_index=True)

    editable_records: list[dict] = []
    for record in review_draft.get("line_items", []):
        row = {column_label: record.get("values", {}).get(column_key, "") for column_key, column_label in LINE_ITEM_COLUMNS}
        row["状态"] = record.get("status", "正常")
        editable_records.append(row)
    editable_frame = pd.DataFrame(
        editable_records or [{column_label: "" for column_label in LINE_ITEM_EDITOR_COLUMNS}],
        columns=LINE_ITEM_EDITOR_COLUMNS,
    )
    edited_frame = st.data_editor(
        editable_frame,
        num_rows="dynamic",
        use_container_width=True,
        hide_index=True,
        column_config={"状态": st.column_config.SelectboxColumn("状态", options=FIELD_STATUS_OPTIONS)},
        key="review_line_items_editor",
    )
    edited_rows = normalize_editor_rows(edited_frame)
    updated_line_items: list[dict] = []
    for row in edited_rows:
        values = {column_key: row.get(column_label, "") for column_key, column_label in LINE_ITEM_COLUMNS}
        updated_line_items.append({"values": values, "status": row.get("状态", "正常")})
    review_draft["line_items"] = updated_line_items
    st.session_state.review_draft = review_draft
    return review_draft


def render_intake_page(base_dir: str) -> None:
    render_stage_header("发票/凭证采数", "恢复旧版采数、原件对照与人工审核体验，并允许确认后进入下一环节。")
    sample_files = collect_sample_files(base_dir)

    source_mode = st.radio(
        "选择导入方式",
        ("示例文件", "上传文件"),
        horizontal=True,
        key="intake_source_mode",
    )
    selected_label = None
    uploaded_file = None

    if source_mode == "示例文件":
        sample_options = list(sample_files.keys())
        default_index = 0
        saved_sample = st.session_state.get("intake_selected_sample")
        if saved_sample in sample_options:
            default_index = sample_options.index(saved_sample)
        if sample_options:
            selected_label = st.selectbox("选择示例文件", sample_options, index=default_index, key="intake_selected_sample")
        else:
            st.info("当前没有可用示例文件，请改用上传文件。")
    else:
        uploaded_file = st.file_uploader("上传待审核文件", type=["pdf", "txt", "docx", "xlsx", "xls"])
        if uploaded_file is not None:
            st.session_state.intake_uploaded_name = uploaded_file.name

    current_source_label = "未选择"
    current_review_owner = st.session_state.get("review_owner") or st.session_state.get("intake_review_owner", "张会计")
    if st.session_state.get("parsed_invoice"):
        current_source_label = st.session_state.parsed_invoice.get("source_file", current_source_label)
    elif selected_label:
        current_source_label = selected_label
    elif uploaded_file is not None:
        current_source_label = uploaded_file.name

    render_status_card(
        "发票/凭证采数",
        current_review_owner,
        st.session_state.get("intake_status", "待审核"),
        st.session_state.get("intake_effect_status", "未确认"),
        current_source_label,
    )

    action_columns = st.columns(4)
    if action_columns[0].button("开始解析", type="primary", use_container_width=True):
        try:
            source_file_bytes = None
            source_page_images: list[bytes] = []
            if selected_label:
                sample_path = sample_files[selected_label]
                parsed_invoice = parse_invoice(selected_label, file_path=sample_path)
                if Path(sample_path).suffix.lower() == ".pdf":
                    source_file_bytes = Path(sample_path).read_bytes()
            elif uploaded_file is not None:
                source_file_bytes = uploaded_file.getvalue()
                parsed_invoice = parse_invoice(uploaded_file.name, file_bytes=source_file_bytes)
            else:
                raise ValueError("请先选择示例文件或上传文件。")

            if source_file_bytes and parsed_invoice.get("source_type") == "pdf":
                source_page_images = render_pdf_pages(source_file_bytes)

            apply_parsed_invoice(parsed_invoice, source_file_bytes, source_page_images)
            st.session_state.intake_status = "待审核"
            st.session_state.intake_effect_status = "未确认"
            st.session_state.intake_invoice_data = None
            st.success("解析完成，已加载原解析数据，等待人工审核。")
        except Exception as exc:
            st.error(f"解析失败：{exc}")

    if action_columns[1].button("重置为原解析结果", use_container_width=True, disabled=st.session_state.get("parsed_invoice") is None):
        parsed_invoice = st.session_state.get("parsed_invoice")
        if parsed_invoice is not None:
            st.session_state.review_draft = build_review_draft(parsed_invoice)
            st.session_state.saved_review = None
            st.session_state.submitted_review = None
            st.session_state.verify_result = None
            st.session_state.preview_page_index = 0
            st.session_state.intake_status = "待审核"
            st.session_state.intake_effect_status = "未确认"
            st.rerun()

    if st.session_state.get("parsed_invoice") is None:
        st.info("请先选择示例文件或上传文件，然后点击“开始解析”。")
        return

    parsed_invoice = st.session_state.parsed_invoice
    render_source_snapshot_preview(st.sidebar, parsed_invoice)
    _render_sample_hint(parsed_invoice)
    _render_overview(parsed_invoice)

    review_draft = _render_review_editor(parsed_invoice)
    finalized_review = finalize_review_draft(review_draft, parsed_invoice)
    validation_result = validate_submission(finalized_review)

    _render_submission_summary(validation_result)

    review_action_columns = st.columns(4)
    if review_action_columns[0].button("保存当前草稿", use_container_width=True):
        st.session_state.saved_review = copy.deepcopy(finalized_review)
        st.success("当前草稿已保存。")
    if review_action_columns[1].button("提交审核结果", use_container_width=True, disabled=not validation_result.get("can_submit", False)):
        submitted_review = copy.deepcopy(finalized_review)
        submitted_review["review_conclusion"] = validation_result["conclusion"]
        st.session_state.submitted_review = submitted_review
        st.session_state.intake_status = validation_result["conclusion"]
        st.session_state.intake_effect_status = "未确认"
        st.success("审核结果已提交。")
    if review_action_columns[2].button(
        "确认采数结果",
        type="primary",
        use_container_width=True,
        disabled=not validation_result.get("can_confirm", False),
    ):
        submitted_review = copy.deepcopy(finalized_review)
        submitted_review["review_conclusion"] = validation_result["conclusion"]
        st.session_state.submitted_review = submitted_review
        st.session_state.intake_invoice_data = copy.deepcopy(finalized_review)
        st.session_state.intake_status = "审核通过"
        st.session_state.intake_effect_status = "已确认"
        st.session_state.matching_result = None
        st.session_state.matching_status = "待审核"
        st.session_state.matching_effect_status = "未确认"
        st.session_state.voucher_draft_v1 = None
        st.session_state.voucher_status_v1 = "待审核"
        st.session_state.tax_draft_v1 = None
        st.session_state.tax_status_v1 = "待审核"
        st.session_state.report_draft_v1 = None
        st.session_state.report_status_v1 = "待审核"
        go_to_stage("三单核对")
    if review_action_columns[3].button(
        "进入下一步：三单核对",
        use_container_width=True,
        disabled=st.session_state.get("intake_status") != "审核通过",
    ):
        go_to_stage("三单核对")

    st.subheader("审核差异")
    changes = collect_field_changes(parsed_invoice, finalized_review)
    if not changes:
        st.info("当前没有修改，也没有存疑/有误标记。")
    else:
        st.dataframe(pd.DataFrame(changes), use_container_width=True, hide_index=True)

    assist_columns = st.columns(2)
    parser = InvoiceParser()
    compliance_result = parser.check_compliance(finalized_review)
    with assist_columns[0]:
        st.subheader("辅助信息")
        issues = compliance_result.get("issues", [])
        suggestions = compliance_result.get("suggestions", [])
        if issues:
            st.markdown("**合规提示**")
            st.dataframe(pd.DataFrame(issues), use_container_width=True, hide_index=True)
        else:
            st.success("当前未发现明显合规问题。")
        if suggestions:
            st.markdown("**建议**")
            for suggestion in suggestions:
                st.write(f"- {suggestion}")
        if st.button("执行发票查验"):
            st.session_state.verify_result = parser.verify_invoice(finalized_review)
        if st.session_state.get("verify_result") is not None:
            st.markdown("**查验结果**")
            st.json(st.session_state.verify_result)
    with assist_columns[1]:
        st.subheader("审核草稿与结果")
        st.caption("调试型 JSON 默认收起，演示时优先查看上方审核建议与差异。")
        with st.expander("查看当前审核草稿", expanded=False):
            st.json(finalized_review)
        if st.session_state.get("saved_review") is not None:
            with st.expander("查看已保存草稿", expanded=False):
                st.json(st.session_state.saved_review)
        if st.session_state.get("submitted_review") is not None:
            with st.expander("查看已提交审核结果", expanded=False):
                st.json(st.session_state.submitted_review)
