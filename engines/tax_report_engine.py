from __future__ import annotations

from datetime import datetime
from typing import Any

VAT_RETURN_ITEMS = [
    "按适用税率计税销售额",
    "销项税额",
    "进项税额",
    "进项税额转出",
    "应纳税额",
    "期末留抵税额",
]

TAX_MAIN_SHEET_TEMPLATE = [
    {"项目": "销售额", "栏次": ""},
    {"项目": "（一）按适用税率计税销售额", "栏次": "1"},
    {"项目": "其中：应税货物销售额", "栏次": "2"},
    {"项目": "应税劳务销售额", "栏次": "3"},
    {"项目": "纳税检查调整的销售额", "栏次": "4"},
    {"项目": "（二）按简易办法计税销售额", "栏次": "5"},
    {"项目": "其中：纳税检查调整的销售额", "栏次": "6"},
    {"项目": "（三）免、抵、退办法出口销售额", "栏次": "7"},
    {"项目": "（四）免税销售额", "栏次": "8"},
    {"项目": "其中：免税货物销售额", "栏次": "9"},
    {"项目": "免税劳务销售额", "栏次": "10"},
    {"项目": "税款计算", "栏次": ""},
    {"项目": "销项税额", "栏次": "11"},
    {"项目": "进项税额", "栏次": "12"},
    {"项目": "上期留抵税额", "栏次": "13"},
    {"项目": "进项税额转出", "栏次": "14"},
    {"项目": "免、抵、退应退税额", "栏次": "15"},
    {"项目": "按适用税率计算的纳税检查应补缴税额", "栏次": "16"},
    {"项目": "应抵扣税额合计", "栏次": "17"},
    {"项目": "实际抵扣税额", "栏次": "18"},
    {"项目": "应纳税额", "栏次": "19"},
    {"项目": "期末留抵税额", "栏次": "20"},
    {"项目": "简易计税办法计算的应纳税额", "栏次": "21"},
    {"项目": "按简易计税办法计算的纳税检查应补缴税额", "栏次": "22"},
    {"项目": "应纳税额减征额", "栏次": "23"},
    {"项目": "应纳税额合计", "栏次": "24"},
    {"项目": "税款缴纳", "栏次": ""},
    {"项目": "期初未缴税额（多缴为负数）", "栏次": "25"},
    {"项目": "实收出口开具专用缴款书退税额", "栏次": "26"},
    {"项目": "本期已缴税额", "栏次": "27"},
    {"项目": "①分次预缴税额", "栏次": "28"},
    {"项目": "②出口开具专用缴款书预缴税额", "栏次": "29"},
    {"项目": "③本期缴纳上期应纳税额", "栏次": "30"},
    {"项目": "④本期缴纳欠缴税额", "栏次": "31"},
    {"项目": "期末未缴税额（多缴为负数）", "栏次": "32"},
    {"项目": "其中：欠缴税额（≥0）", "栏次": "33"},
    {"项目": "本期应补(退)税额", "栏次": "34"},
    {"项目": "即征即退实际退税额", "栏次": "35"},
]


class TaxReportEngine:
    def generate_tax_report_recommendation(self, voucher_data: dict[str, Any]) -> dict[str, Any]:
        if voucher_data.get("approval_status") != "审核通过":
            return {
                "report_name": "增值税及附加税费申报表",
                "can_generate": False,
                "reasons": ["当前凭证未审核通过，不能生成正式纳税申报表初稿。"],
                "risk_notes": ["请先完成记账凭证审核，再进入纳税申报阶段。"],
                "items": [],
            }

        entries = voucher_data.get("entries") or []
        output_vat = 0.0
        input_vat = 0.0
        sales_amount = 0.0
        input_transfer_out = 0.0
        reasons: list[str] = []
        risks: list[str] = []

        for entry in entries:
            account = str(entry.get("account") or "").strip()
            debit = self._to_number(entry.get("debit")) or 0.0
            credit = self._to_number(entry.get("credit")) or 0.0

            if account == "主营业务收入":
                sales_amount += credit - debit
                reasons.append("根据主营业务收入分录提取销售额。")
            elif account.startswith("应交税费-应交增值税（销项税额）"):
                output_vat += credit - debit
                reasons.append("根据销项税额分录提取销项税。")
            elif account.startswith("应交税费-应交增值税（进项税额）"):
                input_vat += debit - credit
                reasons.append("根据进项税额分录提取进项税。")
            elif "进项税额转出" in account:
                input_transfer_out += credit - debit
                reasons.append("根据进项税额转出分录提取转出税额。")

        deductible_total = round(max(input_vat - input_transfer_out, 0.0), 2)
        actual_deductible = round(min(output_vat, deductible_total), 2)
        tax_payable = round(max(output_vat - actual_deductible, 0.0), 2)
        retained_credit = round(max(deductible_total - actual_deductible, 0.0), 2)
        tax_total = tax_payable

        if sales_amount == 0:
            risks.append("当前凭证未体现销售收入，主表销售额栏位可能仍为空。")
        if input_vat == 0 and output_vat == 0:
            risks.append("当前凭证未提取到明显增值税分录，主表多数字段需人工补充。")
        if retained_credit > 0:
            risks.append("当前按主表规则计算后存在期末留抵税额。")

        items = [
            {"item_name": "按适用税率计税销售额", "amount": round(sales_amount, 2) if sales_amount else None, "note": ""},
            {"item_name": "销项税额", "amount": round(output_vat, 2) if output_vat else None, "note": ""},
            {"item_name": "进项税额", "amount": round(input_vat, 2) if input_vat else None, "note": ""},
            {"item_name": "进项税额转出", "amount": round(input_transfer_out, 2) if input_transfer_out else None, "note": ""},
            {"item_name": "应纳税额", "amount": round(tax_payable, 2) if tax_payable else None, "note": ""},
            {"item_name": "期末留抵税额", "amount": round(retained_credit, 2) if retained_credit else None, "note": ""},
        ]
        if not reasons:
            reasons.append("当前凭证可映射到税表主表的字段较少，其他栏位需人工补充。")
        reasons.insert(0, f"当前税表根据已审核通过凭证 {voucher_data.get('voucher_number', '待补充')} 生成官方主表草稿。")
        return {
            "report_name": "增值税及附加税费申报表",
            "can_generate": True,
            "reasons": self._deduplicate(reasons),
            "risk_notes": self._deduplicate(risks),
            "items": items,
        }

    def build_tax_report_draft(
        self,
        voucher_data: dict[str, Any],
        recommendation: dict[str, Any],
        review_owner: str = "",
    ) -> dict[str, Any]:
        voucher_number = str(voucher_data.get("voucher_number") or "0000")
        item_values = {item.get("item_name"): item.get("amount") for item in recommendation.get("items", [])}
        main_sheet_rows = self._build_main_sheet_rows(item_values)
        return {
            "review_owner": (review_owner or voucher_data.get("review_owner") or "").strip(),
            "report_name": recommendation.get("report_name") or "增值税及附加税费申报表",
            "form_code": "附件1",
            "report_number": f"VAT-{voucher_number}",
            "period": voucher_data.get("period") or datetime.now().strftime("%Y-%m"),
            "company_name": voucher_data.get("buyer_name") or voucher_data.get("company_name") or "",
            "unit_label": "元（列至角分）",
            "source_voucher_number": voucher_number,
            "items": [
                {
                    "item_name": item.get("item_name"),
                    "amount": item.get("amount"),
                    "note": item.get("note", ""),
                }
                for item in recommendation.get("items", [])
            ],
            "main_sheet_rows": main_sheet_rows,
            "approval_comment": "",
            "approval_status": "初稿待修改",
            "effective_status": "未生效",
            "reasons": recommendation.get("reasons", []),
            "risk_notes": recommendation.get("risk_notes", []),
        }

    def _build_main_sheet_rows(self, item_values: dict[str, Any]) -> list[dict[str, Any]]:
        sales_amount = self._to_number(item_values.get("按适用税率计税销售额")) or 0.0
        output_vat = self._to_number(item_values.get("销项税额")) or 0.0
        input_vat = self._to_number(item_values.get("进项税额")) or 0.0
        input_transfer_out = self._to_number(item_values.get("进项税额转出")) or 0.0
        deductible_total = round(max(input_vat - input_transfer_out, 0.0), 2)
        actual_deductible = round(min(output_vat, deductible_total), 2)
        tax_payable = round(max(output_vat - actual_deductible, 0.0), 2)
        retained_credit = round(max(deductible_total - actual_deductible, 0.0), 2)
        tax_total = tax_payable

        line_values = {
            "1": sales_amount,
            "11": output_vat,
            "12": input_vat,
            "14": input_transfer_out,
            "17": deductible_total,
            "18": actual_deductible,
            "19": tax_payable,
            "20": retained_credit,
            "24": tax_total,
        }

        rows: list[dict[str, Any]] = []
        for template in TAX_MAIN_SHEET_TEMPLATE:
            line_no = template["栏次"]
            amount = line_values.get(line_no)
            rows.append(
                {
                    "项目": template["项目"],
                    "栏次": line_no,
                    "一般项目本月数": amount if amount not in (None, 0.0) else None,
                    "一般项目本年累计": amount if amount not in (None, 0.0) else None,
                    "即征即退项目本月数": None,
                    "即征即退项目本年累计": None,
                }
            )
        return rows

    def _deduplicate(self, messages: list[str]) -> list[str]:
        result: list[str] = []
        for message in messages:
            if message and message not in result:
                result.append(message)
        return result

    def _to_number(self, value: Any) -> float | None:
        if value in (None, ""):
            return None
        if isinstance(value, (int, float)):
            return round(float(value), 2)
        text = str(value).replace(",", "").strip()
        if not text:
            return None
        try:
            return round(float(text), 2)
        except ValueError:
            return None


def validate_tax_report_draft(report_draft: dict[str, Any]) -> dict[str, Any]:
    errors: list[str] = []
    review_owner = str(report_draft.get("review_owner") or "").strip()
    if not review_owner:
        errors.append("审核人不能为空。")

    main_sheet_rows = report_draft.get("main_sheet_rows") or []
    if main_sheet_rows:
        amount_keys = ["一般项目本月数", "一般项目本年累计", "即征即退项目本月数", "即征即退项目本年累计"]
        non_empty_amount_count = 0
        for row in main_sheet_rows:
            if any(row.get(key) not in (None, "") for key in amount_keys):
                non_empty_amount_count += 1
        if non_empty_amount_count == 0:
            errors.append("纳税申报表主表金额全部为空，至少需保留一项主表金额后再审核。")
        return {
            "errors": errors,
            "item_count": len(main_sheet_rows),
            "can_effective": not errors,
        }

    items = report_draft.get("items") or []
    meaningful_items = []
    non_empty_amount_count = 0
    for item in items:
        item_name = str(item.get("item_name") or "").strip()
        amount = item.get("amount")
        if not item_name:
            continue
        meaningful_items.append(item)
        if amount not in (None, ""):
            non_empty_amount_count += 1

    if not meaningful_items:
        errors.append("申报表至少需要一项有效内容。")
    if meaningful_items and non_empty_amount_count == 0:
        errors.append("申报表金额全部为空，至少需保留一项金额或补充人工调整后再审核。")

    return {
        "errors": errors,
        "item_count": len(meaningful_items),
        "can_effective": not errors,
    }
