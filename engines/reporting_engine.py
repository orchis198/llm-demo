from __future__ import annotations

from datetime import datetime
from typing import Any

ASSET_BALANCE_SHEET_ITEMS = [
    "银行存款",
    "应收账款",
    "原材料",
    "固定资产",
    "应付账款",
    "应交税费",
    "实收资本",
    "未分配利润",
]

PROFIT_STATEMENT_ITEMS = [
    "主营业务收入",
    "主营业务成本",
    "管理费用",
    "销售费用",
    "财务费用",
    "利润总额",
]

BALANCE_SHEET_LEFT_TEMPLATE = [
    ("流动资产：", "", False),
    ("货币资金", "1", True),
    ("短期投资", "2", True),
    ("应收票据", "3", True),
    ("应收股利", "4", True),
    ("应收利息", "5", True),
    ("应收账款", "6", True),
    ("其他应收款", "7", True),
    ("预付账款", "8", True),
    ("应收补贴款", "9", True),
    ("存货", "10", True),
    ("待摊费用", "11", True),
    ("一年内到期的长期债权投资", "21", True),
    ("其他流动资产", "24", True),
    ("流动资产合计", "31", True),
    ("长期投资：", "", False),
    ("长期股权投资", "32", True),
    ("长期债权投资", "34", True),
    ("长期投资合计", "38", True),
    ("固定资产：", "", False),
    ("固定资产原价", "39", True),
    ("减：累计折旧", "40", True),
    ("固定资产净值", "41", True),
    ("减：固定资产减值准备", "42", True),
    ("固定资产净额", "43", True),
    ("工程物资", "44", True),
    ("在建工程", "45", True),
    ("固定资产清理", "46", True),
    ("固定资产合计", "50", True),
    ("无形资产及其他资产：", "", False),
    ("无形资产", "51", True),
    ("长期待摊费用", "52", True),
    ("其他长期资产", "53", True),
    ("无形资产及其他资产合计", "60", True),
    ("递延税项：", "", False),
    ("递延税款借项", "61", True),
    ("资产合计", "67", True),
]

BALANCE_SHEET_RIGHT_TEMPLATE = [
    ("流动负债：", "", False),
    ("短期借款", "68", True),
    ("应付票据", "69", True),
    ("应付账款", "70", True),
    ("预收账款", "71", True),
    ("应付工资", "72", True),
    ("应付福利费", "73", True),
    ("应付股利", "74", True),
    ("应交税金", "75", True),
    ("其他应交款", "80", True),
    ("其他应付款", "81", True),
    ("预提费用", "82", True),
    ("预计负债", "83", True),
    ("一年内到期的长期负债", "86", True),
    ("其他流动负债", "90", True),
    ("流动负债合计", "100", True),
    ("长期负债：", "", False),
    ("长期借款", "101", True),
    ("应付债券", "102", True),
    ("长期应付款", "103", True),
    ("专项应付款", "106", True),
    ("其他长期负债", "108", True),
    ("长期负债合计", "110", True),
    ("递延税项：", "", False),
    ("递延税款贷项", "111", True),
    ("负债合计", "114", True),
    ("所有者权益（或股东权益）：", "", False),
    ("实收资本(或股本)", "115", True),
    ("减：已归还投资", "116", True),
    ("实收资本(或股本)净额", "117", True),
    ("资本公积", "118", True),
    ("盈余公积", "119", True),
    ("其中：法定公益金", "120", True),
    ("未分配利润", "121", True),
    ("所有者权益（或股东权益）合计", "122", True),
    ("负债和所有者权益（或股东权益）总计", "135", True),
]

PROFIT_STATEMENT_TEMPLATE = [
    ("一、主营业务收入", "1", True),
    ("减：主营业务成本", "4", True),
    ("主营业务税金及附加", "5", True),
    ("二、主营业务利润（亏损以“－”号填列）", "10", True),
    ("加：其他业务利润（亏损以“－”号填列）", "11", True),
    ("减：营业费用", "14", True),
    ("管理费用", "15", True),
    ("财务费用", "16", True),
    ("三、营业利润（亏损以“－”号填列）", "18", True),
    ("加：投资收益（损失以“－”填列）", "19", True),
    ("补贴收入", "22", True),
    ("营业外收入", "23", True),
    ("减：营业外支出", "25", True),
    ("四、利润总额（亏损总额以“－”号填列）", "27", True),
    ("减：所得税", "28", True),
    ("五、净利润（净亏损以“－”号填列）", "30", True),
]


class ReportingEngine:
    def generate_report_recommendation(self, voucher_data: dict[str, Any], report_type: str) -> dict[str, Any]:
        if voucher_data.get("approval_status") != "审核通过":
            return {
                "report_type": report_type,
                "can_generate": False,
                "reasons": ["当前凭证未审核通过，不能生成正式报表初稿。"],
                "risk_notes": ["请先完成凭证审核，再进入报表阶段。"],
                "items": [],
            }

        normalized_type = report_type.strip() or "资产负债表"
        entries = voucher_data.get("entries") or []
        if normalized_type == "利润表":
            items, reasons, risks = self._build_profit_statement(entries)
        else:
            items, reasons, risks = self._build_balance_sheet(entries)

        reasons.insert(0, f"当前报表根据已审核通过凭证 {voucher_data.get('voucher_number', '待补充')} 生成官方主体草稿。")
        return {
            "report_type": normalized_type,
            "can_generate": True,
            "reasons": reasons,
            "risk_notes": risks,
            "items": items,
        }

    def build_report_draft(
        self,
        voucher_data: dict[str, Any],
        recommendation: dict[str, Any],
        review_owner: str = "",
    ) -> dict[str, Any]:
        now_period = datetime.now().strftime("%Y-%m")
        report_type = recommendation.get("report_type") or "资产负债表"
        report_number_prefix = "BS" if report_type == "资产负债表" else "PL"
        voucher_number = str(voucher_data.get("voucher_number") or "0000")
        item_values = {item.get("item_name"): item.get("amount") for item in recommendation.get("items", [])}
        draft = {
            "review_owner": (review_owner or voucher_data.get("review_owner") or "").strip(),
            "report_type": report_type,
            "report_number": f"{report_number_prefix}-{voucher_number}",
            "form_code": "会企01表" if report_type == "资产负债表" else "会企02表",
            "period": voucher_data.get("period") or now_period,
            "company_name": voucher_data.get("buyer_name") or voucher_data.get("company_name") or "",
            "unit_label": "元",
            "source_voucher_number": voucher_number,
            "items": [
                {
                    "item_name": item.get("item_name"),
                    "amount": item.get("amount"),
                    "note": item.get("note", ""),
                }
                for item in recommendation.get("items", [])
            ],
            "approval_comment": "",
            "approval_status": "初稿待修改",
            "effective_status": "未生效",
            "reasons": recommendation.get("reasons", []),
            "risk_notes": recommendation.get("risk_notes", []),
        }
        if report_type == "利润表":
            draft["main_rows"] = self._build_profit_main_rows(item_values)
        else:
            left_rows, right_rows = self._build_balance_main_rows(item_values)
            draft["left_rows"] = left_rows
            draft["right_rows"] = right_rows
        return draft

    def _build_balance_sheet(self, entries: list[dict[str, Any]]) -> tuple[list[dict[str, Any]], list[str], list[str]]:
        amounts = {item: 0.0 for item in ASSET_BALANCE_SHEET_ITEMS}
        reasons: list[str] = []
        risks: list[str] = []

        for entry in entries:
            account = str(entry.get("account") or "").strip()
            debit = self._to_number(entry.get("debit")) or 0.0
            credit = self._to_number(entry.get("credit")) or 0.0

            if account == "银行存款":
                amounts["银行存款"] += debit - credit
                reasons.append("根据凭证中的银行存款分录，提取货币资金变动。")
            elif account == "应收账款":
                amounts["应收账款"] += debit - credit
                reasons.append("根据凭证中的应收账款分录，承接应收项目。")
            elif account == "原材料":
                amounts["原材料"] += debit - credit
                reasons.append("根据凭证中的原材料分录，承接存货项目。")
            elif account == "固定资产":
                amounts["固定资产"] += debit - credit
                reasons.append("根据凭证中的固定资产分录，承接长期资产项目。")
            elif account == "应付账款":
                amounts["应付账款"] += credit - debit
                reasons.append("根据凭证中的应付账款分录，承接负债项目。")
            elif account.startswith("应交税费"):
                amounts["应交税费"] += credit - debit if credit > debit else debit - credit
                reasons.append("根据凭证中的应交税费分录，承接税费项目。")

        if amounts["实收资本"] == 0:
            risks.append("当前凭证未涉及实收资本，资产负债表主体中该项目先保留为空。")
        if amounts["未分配利润"] == 0:
            risks.append("当前凭证未直接形成未分配利润，需后续结合利润表与期初数据人工确认。")

        items = [
            {"item_name": item, "amount": round(amounts[item], 2) if amounts[item] else None, "note": ""}
            for item in ASSET_BALANCE_SHEET_ITEMS
        ]
        if not reasons:
            reasons.append("当前凭证可映射到资产负债表主体的项目较少，其他栏位需人工补充。")
        return items, self._deduplicate(reasons), self._deduplicate(risks)

    def _build_profit_statement(self, entries: list[dict[str, Any]]) -> tuple[list[dict[str, Any]], list[str], list[str]]:
        amounts = {item: 0.0 for item in PROFIT_STATEMENT_ITEMS}
        reasons: list[str] = []
        risks: list[str] = []

        for entry in entries:
            account = str(entry.get("account") or "").strip()
            debit = self._to_number(entry.get("debit")) or 0.0
            credit = self._to_number(entry.get("credit")) or 0.0

            if account == "主营业务收入":
                amounts["主营业务收入"] += credit - debit
                reasons.append("根据主营业务收入分录承接收入项目。")
            elif account == "主营业务成本":
                amounts["主营业务成本"] += debit - credit
                reasons.append("根据主营业务成本分录承接成本项目。")
            elif account == "管理费用":
                amounts["管理费用"] += debit - credit
                reasons.append("根据管理费用分录承接期间费用项目。")
            elif account == "销售费用":
                amounts["销售费用"] += debit - credit
                reasons.append("根据销售费用分录承接期间费用项目。")
            elif account == "财务费用":
                amounts["财务费用"] += debit - credit
                reasons.append("根据财务费用分录承接期间费用项目。")

        amounts["利润总额"] = round(
            amounts["主营业务收入"]
            - amounts["主营业务成本"]
            - amounts["管理费用"]
            - amounts["销售费用"]
            - amounts["财务费用"],
            2,
        )
        reasons.append("利润总额按当前主体结构内的收入、成本和期间费用直接计算。")

        if amounts["主营业务收入"] == 0:
            risks.append("当前凭证未体现主营业务收入，利润表主体可能只展示费用侧结果。")
        items = [
            {"item_name": item, "amount": round(amounts[item], 2) if amounts[item] else None, "note": ""}
            for item in PROFIT_STATEMENT_ITEMS
        ]
        return items, self._deduplicate(reasons), self._deduplicate(risks)

    def _build_balance_main_rows(self, item_values: dict[str, Any]) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
        left_line_values = {
            "1": item_values.get("银行存款"),
            "6": item_values.get("应收账款"),
            "10": item_values.get("原材料"),
            "43": item_values.get("固定资产"),
            "50": item_values.get("固定资产"),
            "67": self._sum_numbers(item_values.get("银行存款"), item_values.get("应收账款"), item_values.get("原材料"), item_values.get("固定资产")),
        }
        right_line_values = {
            "70": item_values.get("应付账款"),
            "75": item_values.get("应交税费"),
            "100": self._sum_numbers(item_values.get("应付账款"), item_values.get("应交税费")),
            "115": item_values.get("实收资本"),
            "121": item_values.get("未分配利润"),
            "122": self._sum_numbers(item_values.get("实收资本"), item_values.get("未分配利润")),
            "135": self._sum_numbers(item_values.get("应付账款"), item_values.get("应交税费"), item_values.get("实收资本"), item_values.get("未分配利润")),
        }
        left_rows = [self._build_main_row(label, line_no, left_line_values.get(line_no), editable) for label, line_no, editable in BALANCE_SHEET_LEFT_TEMPLATE]
        right_rows = [self._build_main_row(label, line_no, right_line_values.get(line_no), editable) for label, line_no, editable in BALANCE_SHEET_RIGHT_TEMPLATE]
        return left_rows, right_rows

    def _build_profit_main_rows(self, item_values: dict[str, Any]) -> list[dict[str, Any]]:
        current_map = {
            "1": item_values.get("主营业务收入"),
            "4": item_values.get("主营业务成本"),
            "15": item_values.get("管理费用"),
            "14": item_values.get("销售费用"),
            "16": item_values.get("财务费用"),
            "27": item_values.get("利润总额"),
            "30": item_values.get("利润总额"),
        }
        rows = []
        for label, line_no, editable in PROFIT_STATEMENT_TEMPLATE:
            value = current_map.get(line_no)
            rows.append(
                {
                    "项目": label,
                    "行次": line_no,
                    "本月数": value,
                    "本年累计数": value,
                    "editable": editable,
                }
            )
        return rows

    def _build_main_row(self, label: str, line_no: str, amount: Any, editable: bool) -> dict[str, Any]:
        return {
            "项目": label,
            "行次": line_no,
            "年初数": None,
            "期末数": amount if amount not in (None, 0.0) else None,
            "editable": editable,
        }

    def _sum_numbers(self, *values: Any) -> float | None:
        total = 0.0
        has_value = False
        for value in values:
            number = self._to_number(value)
            if number is None:
                continue
            total += number
            has_value = True
        return round(total, 2) if has_value else None

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


def validate_report_draft(report_draft: dict[str, Any]) -> dict[str, Any]:
    errors: list[str] = []
    review_owner = str(report_draft.get("review_owner") or "").strip()
    if not review_owner:
        errors.append("审核人不能为空。")

    if report_draft.get("report_type") == "利润表" and report_draft.get("main_rows"):
        rows = report_draft.get("main_rows") or []
        non_empty_amount_count = 0
        for row in rows:
            if row.get("本月数") not in (None, "") or row.get("本年累计数") not in (None, ""):
                non_empty_amount_count += 1
        if non_empty_amount_count == 0:
            errors.append("利润表主体金额全部为空，至少需保留一项金额后再审核。")
        return {
            "errors": errors,
            "item_count": len(rows),
            "can_effective": not errors,
        }

    if report_draft.get("report_type") == "资产负债表" and report_draft.get("left_rows") and report_draft.get("right_rows"):
        rows = (report_draft.get("left_rows") or []) + (report_draft.get("right_rows") or [])
        non_empty_amount_count = 0
        for row in rows:
            if row.get("年初数") not in (None, "") or row.get("期末数") not in (None, ""):
                non_empty_amount_count += 1
        if non_empty_amount_count == 0:
            errors.append("资产负债表主体金额全部为空，至少需保留一项金额后再审核。")
        return {
            "errors": errors,
            "item_count": len(rows),
            "can_effective": not errors,
        }

    items = report_draft.get("items") or []
    meaningful_items = []
    non_empty_amount_count = 0
    for item in items:
        item_name = str(item.get("item_name") or "").strip()
        amount = item.get("amount")
        note = str(item.get("note") or "").strip()
        if not item_name:
            continue
        meaningful_items.append(item)
        if amount not in (None, ""):
            non_empty_amount_count += 1
        if isinstance(amount, (int, float)) and amount < 0 and not note:
            errors.append(f"报表项目“{item_name}”为负数时，需填写说明后再审核。")

    if not meaningful_items:
        errors.append("报表至少需要一项有效内容。")
    if meaningful_items and non_empty_amount_count == 0:
        errors.append("报表金额全部为空，至少需保留一项金额或补充人工调整后再审核。")

    return {
        "errors": errors,
        "item_count": len(meaningful_items),
        "can_effective": not errors,
    }
