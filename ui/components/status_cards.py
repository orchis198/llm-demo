from __future__ import annotations

from typing import Any

import streamlit as st


def render_stage_header(title: str, subtitle: str) -> None:
    st.subheader(title)
    st.caption(subtitle)


def render_status_card(title: str, review_owner: str, status: str, effect_status: str, source_label: str) -> None:
    columns = st.columns(4)
    columns[0].metric("当前环节", title)
    columns[1].metric("审核人", review_owner or "待填写")
    columns[2].metric("状态", status)
    columns[3].metric("生效/入账", effect_status)
    st.caption(f"来源：{source_label}")


def render_kv_table(rows: list[dict[str, Any]], *, height: int = 220) -> None:
    import pandas as pd

    st.dataframe(pd.DataFrame(rows), use_container_width=True, hide_index=True, height=height)


def render_agent_task_card(
    *,
    task_type: str,
    llm_meta: dict[str, Any] | None,
    prompt_summary: str = "",
    basis_reasons: list[str] | None = None,
    risk_notes: list[str] | None = None,
    task_label: str | None = None,
    subject_label: str | None = None,
    subject_value: str | None = None,
    status_label: str = "已完成",
    extra_summary: str | None = None,
) -> None:
    task_defaults = {
        "voucher": {
            "task_label": "正在生成凭证建议",
            "subject_label": "业务类型",
            "default_summary": "当前使用结构化推荐提示词生成凭证建议。",
            "success_message": "当前凭证推荐由 LLM 参与生成，可用于展示智能体能力。",
            "fallback_message": "当前凭证推荐已回退到规则引擎，用于保证演示链路稳定。",
        },
        "tax": {
            "task_label": "正在生成纳税申报建议",
            "subject_label": "报表名称",
            "default_summary": "当前使用结构化推荐提示词生成税表建议。",
            "success_message": "当前税表推荐由 LLM 参与生成，可用于展示智能体能力。",
            "fallback_message": "当前税表推荐已回退到规则引擎，用于保证演示链路稳定。",
        },
        "report": {
            "task_label": "正在生成会计报表建议",
            "subject_label": "报表类型",
            "default_summary": "当前使用结构化推荐提示词生成会计报表建议。",
            "success_message": "当前会计报表推荐由 LLM 参与生成，可用于展示智能体能力。",
            "fallback_message": "当前会计报表推荐已回退到规则引擎，用于保证演示链路稳定。",
        },
    }

    llm_meta = llm_meta or {}
    basis_reasons = [item for item in (basis_reasons or []) if item]
    risk_notes = [item for item in (risk_notes or []) if item]
    config = task_defaults.get(task_type, task_defaults["voucher"])
    fallback = bool(llm_meta.get("fallback"))
    resolved_task_label = task_label or config["task_label"]
    resolved_subject_label = subject_label or config["subject_label"]
    resolved_prompt_summary = prompt_summary or config["default_summary"]
    resolved_status_label = "规则回退" if fallback else status_label

    st.markdown("#### 智能体任务卡")
    if fallback:
        st.caption("AI 智能体已切换到规则回退模式，以保证当前流程可继续演示。")
    else:
        st.caption("AI 智能体已完成本轮推荐生成，可继续人工复核。")

    top_cols = st.columns(3)
    top_cols[0].metric("当前任务", resolved_task_label)
    top_cols[1].metric("Agent 状态", resolved_status_label)
    top_cols[2].metric("推荐来源", llm_meta.get("source", "未知"))

    if fallback:
        st.warning(config["fallback_message"])
    else:
        st.success(config["success_message"])

    if llm_meta.get("reason"):
        st.info(f"回退原因：{llm_meta.get('reason')}")

    summary_parts: list[str] = []
    if subject_value:
        summary_parts.append(f"{resolved_subject_label}：{subject_value}")
    if extra_summary:
        summary_parts.append(extra_summary)
    if resolved_prompt_summary:
        summary_parts.append(f"提示词摘要：{resolved_prompt_summary}")
    if summary_parts:
        st.info("；".join(summary_parts))

    st.markdown("**推荐依据**")
    if basis_reasons:
        for reason in basis_reasons[:4]:
            st.write(f"- {reason}")
    else:
        st.write("- 当前未返回明确依据，建议人工复核后确认。")

    if risk_notes:
        st.markdown("**风险提示**")
        for risk in risk_notes:
            st.warning(risk)

    st.markdown("**LLM / AI 元数据**")
    render_kv_table([
        {"字段": "推荐来源", "内容": llm_meta.get("source", "未知")},
        {"字段": "Provider", "内容": llm_meta.get("provider", "未配置")},
        {"字段": "Model", "内容": llm_meta.get("model", "未配置")},
        {"字段": "API Base", "内容": llm_meta.get("api_base", "未配置")},
        {"字段": "Fallback", "内容": "是" if llm_meta.get("fallback") else "否"},
    ], height=180)
