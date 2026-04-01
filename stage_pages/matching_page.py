from __future__ import annotations

import streamlit as st

from services.matching_service import run_three_way_match
from services.show_dataset_service import ShowDatasetService
from ui.components.file_preview import render_file_preview
from ui.components.status_cards import render_stage_header, render_status_card
from ui.session_state import go_to_stage


def render_matching_page(base_dir: str) -> None:
    render_stage_header("三单核对", "这里对 show 的发票、合同、入库单进行正式三单核对。")
    dataset = ShowDatasetService(base_dir)
    manifest = dataset.load_manifest("show")
    review_owner = st.text_input("审核人", value=st.session_state.get("matching_review_owner", "张会计"), key="matching_review_owner")
    render_status_card(
        "三单核对",
        review_owner,
        st.session_state.get("matching_status", "待审核"),
        st.session_state.get("matching_effect_status", "未确认"),
        manifest["business_id"],
    )

    invoice_fields = {
        "amount": "23504.00",
        "tax_rate": "13%",
        "quantity": "6",
        "vendor_name": "苏州启明设备有限公司",
        "invoice_date": "2026-03-25",
    }
    contract_fields = {
        "amount": "23504.00",
        "tax_rate": "13%",
        "quantity": "6",
        "vendor_name": "苏州启明设备有限公司",
        "contract_date": "2026-03-20",
    }
    receipt_fields = {
        "amount": "23504.00",
        "tax_rate": "13%",
        "quantity": "6",
        "vendor_name": "苏州启明设备有限公司",
        "receipt_date": "2026-03-25",
    }
    result = run_three_way_match(invoice_fields, contract_fields, receipt_fields)

    left, right = st.columns([1.0, 1.25])
    with left:
        st.markdown("#### 核对结论")
        st.info(result.summary)
        st.write(f"- 当前状态：{result.status}")
        if result.differences:
            st.dataframe([
                {
                    "字段": item.field_name,
                    "发票": item.invoice_value,
                    "合同": item.contract_value,
                    "入库": item.receipt_value,
                    "说明": item.message,
                }
                for item in result.differences
            ], use_container_width=True, hide_index=True)
        else:
            st.success("三单关键字段完全一致。")

        st.markdown("#### 人工说明")
        matching_note = st.text_area(
            "审核说明",
            value=st.session_state.get("matching_review_note", ""),
            height=120,
            key="matching_review_note",
            placeholder="如存在差异，请填写人工判断依据、补充说明或风险备注。",
        )
        if matching_note:
            st.caption("当前说明将在确认三单核对结果后保留在 session 状态中。")

        st.session_state.matching_result = result
        action_columns = st.columns(2)
        if action_columns[0].button("确认三单核对结果", type="primary", use_container_width=True):
            st.session_state.matching_status = "审核通过"
            st.session_state.matching_effect_status = "已确认"
            go_to_stage("会计凭证")
        if action_columns[1].button("进入下一步：会计凭证", use_container_width=True, disabled=st.session_state.get("matching_status") != "审核通过"):
            go_to_stage("会计凭证")
    with right:
        st.markdown("#### 合同与入库单预览")
        render_file_preview(dataset.resolve_path(manifest["contract_file"]))
        render_file_preview(dataset.resolve_path(manifest["receipt_file"]))
