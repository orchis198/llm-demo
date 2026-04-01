from __future__ import annotations

from dataclasses import asdict, dataclass
from datetime import datetime
from typing import Any

PLACEHOLDER_DEBIT_ACCOUNT = "待人工确认借方科目"
PLACEHOLDER_CREDIT_ACCOUNT = "待人工确认贷方科目"

PURCHASE_KEYWORDS = (
    "材料",
    "原材料",
    "商品",
    "货物",
    "配套产品",
    "零配件",
    "电脑",
    "电源",
    "显示器",
    "服务器",
    "设备",
    "工作站",
    "打印机",
    "家具",
)

EXPENSE_KEYWORDS = (
    "服务",
    "服务费",
    "咨询",
    "维护",
    "维修",
    "培训",
    "差旅",
    "办公",
    "租赁",
    "运输",
    "物流",
    "快递",
    "广告",
    "会议",
    "劳务",
    "技术服务",
    "检测",
)

SALES_KEYWORDS = (
    "销售",
    "销货",
    "收入",
    "结算",
)

FIXED_ASSET_KEYWORDS = (
    "设备",
    "服务器",
    "工作站",
    "电脑",
    "显示器",
    "打印机",
    "家具",
)

MATERIAL_KEYWORDS = (
    "材料",
    "原材料",
    "零配件",
    "配套产品",
    "商品",
    "货物",
    "电源",
)

EXPENSE_ACCOUNT_RULES = (
    (("运输", "物流", "快递"), "销售费用"),
    (("财务", "手续费", "利息"), "财务费用"),
    (("办公", "咨询", "培训", "服务", "维护", "维修", "会议", "租赁", "劳务", "技术服务", "检测"), "管理费用"),
)

PAID_KEYWORDS = (
    "已付款",
    "已支付",
    "已结清",
    "银行付款",
    "现金支付",
    "刷卡",
)


@dataclass(slots=True)
class RecommendationLine:
    summary: str
    account: str
    debit: float | None = None
    credit: float | None = None


@dataclass(slots=True)
class AccountingRecommendation:
    business_type: str
    confidence: str
    voucher_title: str
    voucher_summary: str
    classification_reasons: list[str]
    generation_notes: list[str]
    risk_notes: list[str]
    recommended_entries: list[RecommendationLine]
    requires_human_confirmation: bool

    def to_dict(self) -> dict[str, Any]:
        data = asdict(self)
        data["recommended_entries"] = [asdict(entry) for entry in self.recommended_entries]
        return data


class AccountingEngine:
    def generate_ai_recommendation(self, invoice_data: dict[str, Any]) -> dict[str, Any]:
        signals = self._collect_signals(invoice_data)
        business_type, confidence, classification_reasons = self._classify_business_type(signals)
        voucher_summary = self._build_voucher_summary(invoice_data, business_type, signals)
        recommended_entries, generation_notes, risk_notes, requires_human_confirmation = self._build_entries(
            invoice_data,
            business_type,
            voucher_summary,
            signals,
        )
        recommendation = AccountingRecommendation(
            business_type=business_type,
            confidence=confidence,
            voucher_title="记账凭证",
            voucher_summary=voucher_summary,
            classification_reasons=classification_reasons,
            generation_notes=generation_notes,
            risk_notes=risk_notes,
            recommended_entries=recommended_entries,
            requires_human_confirmation=requires_human_confirmation,
        )
        return recommendation.to_dict()

    def build_voucher_draft(
        self,
        invoice_data: dict[str, Any],
        recommendation: dict[str, Any],
        review_owner: str = "",
    ) -> dict[str, Any]:
        issue_date = str(invoice_data.get("issue_date") or "")
        period = issue_date[:7] if len(issue_date) >= 7 else datetime.now().strftime("%Y-%m")
        invoice_number = str(invoice_data.get("invoice_number") or invoice_data.get("invoice_code") or "待补充")
        voucher_number = f"AI-{period.replace('-', '')}-{invoice_number[-4:] if invoice_number else '0000'}"
        entries = [
            {
                "summary": str(entry.get("summary") or recommendation.get("voucher_summary") or ""),
                "account": str(entry.get("account") or ""),
                "debit": entry.get("debit"),
                "credit": entry.get("credit"),
            }
            for entry in recommendation.get("recommended_entries", [])
        ]
        if not entries:
            entries = [
                {"summary": recommendation.get("voucher_summary") or "", "account": "", "debit": None, "credit": None},
                {"summary": recommendation.get("voucher_summary") or "", "account": "", "debit": None, "credit": None},
            ]
        return {
            "review_owner": (review_owner or invoice_data.get("review_owner") or "").strip(),
            "source_invoice_number": invoice_number,
            "source_buyer_name": str(invoice_data.get("buyer_name") or ""),
            "source_seller_name": str(invoice_data.get("seller_name") or ""),
            "voucher_title": recommendation.get("voucher_title") or "记账凭证",
            "voucher_number": voucher_number,
            "period": period,
            "business_type": recommendation.get("business_type") or "待人工确认",
            "voucher_summary": recommendation.get("voucher_summary") or "",
            "entries": entries,
            "approval_comment": "",
            "approval_status": "初稿待修改" if recommendation.get("requires_human_confirmation") else "待审核确认",
            "posting_status": "未入账",
            "classification_reasons": recommendation.get("classification_reasons", []),
            "generation_notes": recommendation.get("generation_notes", []),
            "risk_notes": recommendation.get("risk_notes", []),
        }

    def _collect_signals(self, invoice_data: dict[str, Any]) -> dict[str, Any]:
        line_items = invoice_data.get("line_items") or []
        item_names = [str(item.get("item_name") or "").strip() for item in line_items if str(item.get("item_name") or "").strip()]
        normalized_text = " ".join(
            [
                str(invoice_data.get("invoice_title") or ""),
                str(invoice_data.get("invoice_type") or ""),
                str(invoice_data.get("remarks") or ""),
                " ".join(item_names),
            ]
        )
        return {
            "normalized_text": normalized_text,
            "item_names": item_names,
            "first_item": item_names[0] if item_names else "",
            "seller_name": str(invoice_data.get("seller_name") or "").strip(),
            "buyer_name": str(invoice_data.get("buyer_name") or "").strip(),
        }

    def _classify_business_type(self, signals: dict[str, Any]) -> tuple[str, str, list[str]]:
        text = signals["normalized_text"]
        purchase_matches = [keyword for keyword in PURCHASE_KEYWORDS if keyword in text]
        expense_matches = [keyword for keyword in EXPENSE_KEYWORDS if keyword in text]
        sales_matches = [keyword for keyword in SALES_KEYWORDS if keyword in text]

        if sales_matches and len(sales_matches) >= max(len(purchase_matches), len(expense_matches)):
            reasons = [f"识别到销售关键词：{'、'.join(sales_matches[:3])}。"]
            reasons.append("当前单据更接近收入确认场景，先按销售类推荐。")
            return "销售类", self._build_confidence(sales_matches), reasons

        if expense_matches and len(expense_matches) > len(purchase_matches):
            reasons = [f"识别到费用关键词：{'、'.join(expense_matches[:3])}。"]
            reasons.append("当前单据更接近费用报销或服务采购场景。")
            return "费用类", self._build_confidence(expense_matches), reasons

        if purchase_matches:
            reasons = [f"识别到采购关键词：{'、'.join(purchase_matches[:3])}。"]
            reasons.append("当前单据更接近货物、材料或设备采购场景。")
            return "采购类", self._build_confidence(purchase_matches), reasons

        reasons = ["未识别到稳定的采购、费用或销售关键词。"]
        reasons.append("当前仅能给出可编辑凭证草稿，业务分类需人工确认。")
        return "待人工确认", "低", reasons

    def _build_voucher_summary(
        self,
        invoice_data: dict[str, Any],
        business_type: str,
        signals: dict[str, Any],
    ) -> str:
        seller_name = signals["seller_name"] or "供应商"
        buyer_name = signals["buyer_name"] or "客户"
        first_item = signals["first_item"] or "相关业务"
        if business_type == "采购类":
            return f"收到{seller_name}开具的{first_item}采购发票"
        if business_type == "费用类":
            return f"确认{seller_name}相关费用"
        if business_type == "销售类":
            return f"向{buyer_name}确认{first_item}销售收入"
        return f"{seller_name or buyer_name}相关业务待人工确认"

    def _build_entries(
        self,
        invoice_data: dict[str, Any],
        business_type: str,
        voucher_summary: str,
        signals: dict[str, Any],
    ) -> tuple[list[RecommendationLine], list[str], list[str], bool]:
        subtotal_amount = self._to_number(invoice_data.get("subtotal_amount"))
        tax_amount = self._to_number(invoice_data.get("tax_amount"))
        total_amount = self._to_number(invoice_data.get("total_amount"))
        if total_amount is None and subtotal_amount is not None and tax_amount is not None:
            total_amount = round(subtotal_amount + tax_amount, 2)

        generation_notes: list[str] = []
        risk_notes: list[str] = []
        requires_human_confirmation = business_type == "待人工确认"

        if total_amount is None:
            risk_notes.append("金额缺失，AI 仅生成可编辑占位凭证，人工补充金额后才能审核通过。")
            requires_human_confirmation = True
        if tax_amount is None:
            risk_notes.append("税额缺失，当前不拆税额分录，凭证先按总额建议。")
            requires_human_confirmation = True

        if business_type == "采购类":
            debit_account = self._choose_purchase_account(signals["normalized_text"])
            credit_account = self._choose_credit_account(invoice_data)
            generation_notes.append(f"按采购类先推荐借记“{debit_account}”，贷记“{credit_account}”。")
            return (
                self._build_purchase_or_expense_entries(
                    voucher_summary,
                    debit_account,
                    credit_account,
                    subtotal_amount,
                    tax_amount,
                    total_amount,
                ),
                generation_notes,
                risk_notes,
                requires_human_confirmation,
            )

        if business_type == "费用类":
            debit_account = self._choose_expense_account(signals["normalized_text"])
            credit_account = self._choose_credit_account(invoice_data)
            generation_notes.append(f"按费用类先推荐借记“{debit_account}”，贷记“{credit_account}”。")
            return (
                self._build_purchase_or_expense_entries(
                    voucher_summary,
                    debit_account,
                    credit_account,
                    subtotal_amount,
                    tax_amount,
                    total_amount,
                ),
                generation_notes,
                risk_notes,
                requires_human_confirmation,
            )

        if business_type == "销售类":
            generation_notes.append("按销售类先推荐收入确认分录，税额存在时拆分销项税额。")
            return (
                self._build_sales_entries(voucher_summary, subtotal_amount, tax_amount, total_amount),
                generation_notes,
                risk_notes,
                requires_human_confirmation,
            )

        generation_notes.append("当前分类不明确，只生成可编辑占位凭证，等待人工改写。")
        return (
            self._build_uncertain_entries(voucher_summary, total_amount),
            generation_notes,
            risk_notes,
            True,
        )

    def _build_purchase_or_expense_entries(
        self,
        voucher_summary: str,
        debit_account: str,
        credit_account: str,
        subtotal_amount: float | None,
        tax_amount: float | None,
        total_amount: float | None,
    ) -> list[RecommendationLine]:
        if total_amount is None:
            return [
                RecommendationLine(summary=voucher_summary, account=debit_account, debit=None, credit=None),
                RecommendationLine(summary=voucher_summary, account=credit_account, debit=None, credit=None),
            ]

        if subtotal_amount is not None and tax_amount is not None:
            return [
                RecommendationLine(summary=voucher_summary, account=debit_account, debit=subtotal_amount, credit=None),
                RecommendationLine(summary=voucher_summary, account="应交税费-应交增值税（进项税额）", debit=tax_amount, credit=None),
                RecommendationLine(summary=voucher_summary, account=credit_account, debit=None, credit=total_amount),
            ]

        return [
            RecommendationLine(summary=voucher_summary, account=debit_account, debit=total_amount, credit=None),
            RecommendationLine(summary=voucher_summary, account=credit_account, debit=None, credit=total_amount),
        ]

    def _build_sales_entries(
        self,
        voucher_summary: str,
        subtotal_amount: float | None,
        tax_amount: float | None,
        total_amount: float | None,
    ) -> list[RecommendationLine]:
        if total_amount is None:
            return [
                RecommendationLine(summary=voucher_summary, account="应收账款", debit=None, credit=None),
                RecommendationLine(summary=voucher_summary, account="主营业务收入", debit=None, credit=None),
            ]

        if subtotal_amount is not None and tax_amount is not None:
            return [
                RecommendationLine(summary=voucher_summary, account="应收账款", debit=total_amount, credit=None),
                RecommendationLine(summary=voucher_summary, account="主营业务收入", debit=None, credit=subtotal_amount),
                RecommendationLine(summary=voucher_summary, account="应交税费-应交增值税（销项税额）", debit=None, credit=tax_amount),
            ]

        return [
            RecommendationLine(summary=voucher_summary, account="应收账款", debit=total_amount, credit=None),
            RecommendationLine(summary=voucher_summary, account="主营业务收入", debit=None, credit=total_amount),
        ]

    def _build_uncertain_entries(self, voucher_summary: str, total_amount: float | None) -> list[RecommendationLine]:
        return [
            RecommendationLine(summary=voucher_summary, account=PLACEHOLDER_DEBIT_ACCOUNT, debit=total_amount, credit=None),
            RecommendationLine(summary=voucher_summary, account=PLACEHOLDER_CREDIT_ACCOUNT, debit=None, credit=total_amount),
        ]

    def _choose_purchase_account(self, text: str) -> str:
        if any(keyword in text for keyword in FIXED_ASSET_KEYWORDS):
            return "固定资产"
        if any(keyword in text for keyword in MATERIAL_KEYWORDS):
            return "原材料"
        return "原材料"

    def _choose_expense_account(self, text: str) -> str:
        for keywords, account in EXPENSE_ACCOUNT_RULES:
            if any(keyword in text for keyword in keywords):
                return account
        return "管理费用"

    def _choose_credit_account(self, invoice_data: dict[str, Any]) -> str:
        remarks = str(invoice_data.get("remarks") or "")
        if any(keyword in remarks for keyword in PAID_KEYWORDS):
            return "银行存款"
        return "应付账款"

    def _build_confidence(self, matches: list[str]) -> str:
        if len(matches) >= 2:
            return "高"
        if matches:
            return "中"
        return "低"

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


def calculate_voucher_totals(entries: list[dict[str, Any]]) -> dict[str, float]:
    total_debit = 0.0
    total_credit = 0.0
    for entry in entries:
        debit = _to_number(entry.get("debit")) or 0.0
        credit = _to_number(entry.get("credit")) or 0.0
        total_debit += debit
        total_credit += credit
    return {
        "debit": round(total_debit, 2),
        "credit": round(total_credit, 2),
    }


def validate_voucher_draft(voucher_draft: dict[str, Any]) -> dict[str, Any]:
    errors: list[str] = []
    entries = voucher_draft.get("entries") or []
    review_owner = str(voucher_draft.get("review_owner") or "").strip()
    if not review_owner:
        errors.append("审核人不能为空。")

    meaningful_entries = []
    placeholder_accounts = {PLACEHOLDER_DEBIT_ACCOUNT, PLACEHOLDER_CREDIT_ACCOUNT}
    for index, entry in enumerate(entries, start=1):
        account = str(entry.get("account") or "").strip()
        summary = str(entry.get("summary") or "").strip()
        debit = _to_number(entry.get("debit"))
        credit = _to_number(entry.get("credit"))
        has_value = any([account, summary, debit is not None, credit is not None])
        if not has_value:
            continue
        meaningful_entries.append(entry)

        if debit is not None and credit is not None:
            errors.append(f"第{index}行不能同时填写借方和贷方金额。")
        if debit is None and credit is None:
            errors.append(f"第{index}行必须填写借方或贷方金额。")
        if (debit or 0) < 0 or (credit or 0) < 0:
            errors.append(f"第{index}行金额不能为负数。")
        if (debit or 0) > 0 or (credit or 0) > 0:
            if not account:
                errors.append(f"第{index}行缺少会计科目。")
            elif account in placeholder_accounts:
                errors.append(f"第{index}行仍为占位科目，请人工改成正式会计科目后再审核。")

    if not meaningful_entries:
        errors.append("凭证至少需要一条有效分录。")

    totals = calculate_voucher_totals(meaningful_entries)
    if totals["debit"] <= 0 and totals["credit"] <= 0:
        errors.append("凭证金额不能为空。")
    if abs(totals["debit"] - totals["credit"]) > 0.005:
        errors.append("凭证借贷不平，不能审核通过。")

    return {
        "errors": errors,
        "totals": totals,
        "entry_count": len(meaningful_entries),
        "can_post": not errors,
    }


def _to_number(value: Any) -> float | None:
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
