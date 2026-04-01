"""发票解析模块。"""

import os
import re
from datetime import datetime

import pdfplumber
import requests

from config.settings import VAT_CERTIFICATION_DAYS

REMARK_REQUIRED_KEYWORDS = (
    "建筑服务",
    "运输服务",
    "货物运输",
    "不动产",
    "劳务派遣",
)

STRUCTURAL_NOISE_LINES = {
    "买",
    "售",
    "方",
    "购",
    "销",
    "信",
    "息",
}

NORMALIZATION_RULES = (
    (r"购买方名称[:：]", "购方名称："),
    (r"销售方名称[:：]", "销方名称："),
    (r"购买方纳税人识别号[:：]", "购方纳税人识别号："),
    (r"销售方纳税人识别号[:：]", "销方纳税人识别号："),
    (r"购买方地址、电话[:：]", "购方地址、电话："),
    (r"销售方地址、电话[:：]", "销方地址、电话："),
    (r"购买方开户行及账号[:：]", "购方开户行及账号："),
    (r"销售方开户行及账号[:：]", "销方开户行及账号："),
    (r"购买方开户地址及账号[:：]", "购方开户行及账号："),
    (r"销售方开户地址及账号[:：]", "销方开户行及账号："),
    (r"购\s*名称[:：]", "购方名称："),
    (r"销\s*名称[:：]", "销方名称："),
    (r"税率/征收率", "税率"),
    (r"\(小写\)", "（小写）"),
    (r"\(大写\)", "（大写）"),
)


class InvoiceParser:
    def parse_pdf(self, file_path: str) -> dict:
        with pdfplumber.open(file_path) as pdf:
            page_texts = [(page.extract_text() or "").strip() for page in pdf.pages]

        invoice_data = self.parse_text("\n".join(text for text in page_texts if text))
        invoice_data["source_type"] = "pdf"
        invoice_data["source_file"] = file_path
        invoice_data["page_count"] = len(page_texts)
        return invoice_data

    def parse_text(self, text: str) -> dict:
        normalized_text = self._normalize_text(text)
        normalized_lines = self._normalize_lines(text)
        vertical_party_fields = self._extract_vertical_party_fields(normalized_lines)
        buyer_name = self._extract_labeled_line_value(normalized_lines, "购方名称") or vertical_party_fields["buyer"]["name"]
        seller_name = self._extract_labeled_line_value(normalized_lines, "销方名称") or vertical_party_fields["seller"]["name"]
        buyer_tax_id = self._extract_labeled_line_value(normalized_lines, "购方纳税人识别号") or vertical_party_fields["buyer"]["tax_id"]
        seller_tax_id = self._extract_labeled_line_value(normalized_lines, "销方纳税人识别号") or vertical_party_fields["seller"]["tax_id"]
        if not buyer_tax_id or not seller_tax_id:
            fallback_buyer_tax_id, fallback_seller_tax_id = self._extract_party_tax_ids(normalized_text)
            buyer_tax_id = buyer_tax_id or fallback_buyer_tax_id
            seller_tax_id = seller_tax_id or fallback_seller_tax_id
        buyer_address_phone = self._extract_labeled_line_value(normalized_lines, "购方地址、电话") or vertical_party_fields["buyer"]["address_phone"]
        seller_address_phone = self._extract_labeled_line_value(normalized_lines, "销方地址、电话") or vertical_party_fields["seller"]["address_phone"]
        buyer_bank_account = self._extract_labeled_line_value(normalized_lines, "购方开户行及账号") or vertical_party_fields["buyer"]["bank_account"]
        seller_bank_account = self._extract_labeled_line_value(normalized_lines, "销方开户行及账号") or vertical_party_fields["seller"]["bank_account"]
        subtotal_amount, tax_amount = self._extract_amount_summary(normalized_text)
        total_amount = self._extract_money_field(
            normalized_text,
            [
                r"价税合计（大写）.*?（小写）[¥￥]?\s*([0-9,.-]+)",
                r"价税合计.*?[（(]小写[）)]?[¥￥]?\s*([0-9,.-]+)",
            ],
        )
        if total_amount is None and subtotal_amount is not None and tax_amount is not None:
            total_amount = round(subtotal_amount + tax_amount, 2)

        line_items = self._extract_line_items(normalized_lines)
        tax_rates = [item["tax_rate"] for item in line_items if item.get("tax_rate")]
        original_invoice_code = self._extract_text_field(
            normalized_text,
            [r"原发票代码[:：]\s*([0-9A-Z]+)"],
        )
        original_invoice_number = self._extract_text_field(
            normalized_text,
            [r"原发票号码[:：]\s*([0-9A-Z]+)"],
        )

        invoice_data = {
            "source_type": "text",
            "source_file": "",
            "page_count": 0,
            "invoice_title": self._extract_invoice_title(normalized_lines),
            "invoice_type": self._extract_text_field(
                normalized_text,
                [r"发票类型[:：]\s*([^\s]+)"],
            )
            or self._extract_invoice_title(normalized_lines),
            "invoice_code": self._extract_text_field(
                normalized_text,
                [r"发票代码[:：]\s*([0-9A-Z]+)"],
            ),
            "invoice_number": self._extract_text_field(
                normalized_text,
                [r"发票号码[:：]\s*([0-9A-Z]+)"],
            ),
            "issue_date": self._extract_issue_date(normalized_text),
            "check_code": self._extract_text_field(
                normalized_text,
                [r"校验码[:：]\s*([0-9\s]+)"],
            ).replace(" ", ""),
            "machine_number": self._extract_text_field(
                normalized_text,
                [r"机器编号[:：]\s*([0-9A-Z]+)"],
            ),
            "buyer_name": self._clean_party_value(buyer_name),
            "buyer_tax_id": buyer_tax_id,
            "buyer_address_phone": buyer_address_phone,
            "buyer_bank_account": buyer_bank_account,
            "seller_name": self._clean_party_value(seller_name),
            "seller_tax_id": seller_tax_id,
            "seller_address_phone": seller_address_phone,
            "seller_bank_account": seller_bank_account,
            "subtotal_amount": subtotal_amount,
            "tax_amount": tax_amount,
            "total_amount": total_amount,
            "total_amount_chinese": self._extract_text_field(
                normalized_text,
                [r"价税合计（大写）\s*(.*?)\s*（小写）"],
            ),
            "tax_rates": sorted(set(tax_rates)),
            "tax_classification_code": self._extract_text_field(
                normalized_text,
                [r"税收分类编码[:：]\s*([0-9A-Z]+)"],
            ),
            "remarks": self._extract_remarks(normalized_text, normalized_lines),
            "payee": self._extract_text_field(
                normalized_text,
                [r"收款人[:：]\s*([^\s]+)"],
            ),
            "reviewer": self._extract_text_field(
                normalized_text,
                [r"复核[:：]\s*([^\s]+)"],
            ),
            "issuer": self._extract_text_field(
                normalized_text,
                [r"开票人[:：]\s*([^\s]+)"],
            ),
            "invoice_status": self._detect_invoice_status(
                normalized_text,
                total_amount,
                original_invoice_code,
                original_invoice_number,
            ),
            "is_void": "作废" in normalized_text,
            "is_red_correction": self._is_red_correction(
                normalized_text,
                total_amount,
                original_invoice_code,
                original_invoice_number,
            ),
            "original_invoice_code": original_invoice_code,
            "original_invoice_number": original_invoice_number,
            "line_item_count": len(line_items),
            "line_items": line_items,
            "raw_text": text.strip(),
        }
        return invoice_data

    def verify_invoice(self, invoice_data: dict) -> dict:
        api_url = os.getenv("INVOICE_VERIFY_API_URL", "").strip()
        api_key = os.getenv("INVOICE_VERIFY_API_KEY", "").strip()
        payload = {
            "invoice_code": invoice_data.get("invoice_code", ""),
            "invoice_number": invoice_data.get("invoice_number", ""),
            "issue_date": invoice_data.get("issue_date", ""),
            "total_amount": invoice_data.get("total_amount"),
            "check_code": invoice_data.get("check_code", ""),
        }
        if not api_url:
            return {
                "enabled": False,
                "verified": False,
                "message": "未配置发票查验接口。",
                "payload": payload,
            }

        headers = {"Content-Type": "application/json"}
        if api_key:
            headers["X-API-Key"] = api_key

        try:
            response = requests.post(api_url, json=payload, headers=headers, timeout=10)
            response.raise_for_status()
        except requests.RequestException as exc:
            return {
                "enabled": True,
                "verified": False,
                "message": f"查验请求失败：{exc}",
                "payload": payload,
            }

        try:
            result = response.json()
        except ValueError:
            return {
                "enabled": True,
                "verified": False,
                "message": "查验接口返回内容不是 JSON。",
                "payload": payload,
                "status_code": response.status_code,
            }

        return {
            "enabled": True,
            "verified": bool(result.get("verified", result.get("success", False))),
            "message": result.get("message", "查验完成。"),
            "payload": payload,
            "result": result,
        }

    def check_compliance(self, invoice_data: dict) -> dict:
        issues: list[dict] = []
        suggestions: list[str] = []

        def add_issue(field: str, level: str, message: str, suggestion: str) -> None:
            issues.append({
                "field": field,
                "level": level,
                "message": message,
            })
            if suggestion and suggestion not in suggestions:
                suggestions.append(suggestion)

        for field_name, field_label in [
            ("invoice_number", "发票号码"),
            ("issue_date", "开票日期"),
            ("buyer_name", "购方名称"),
            ("buyer_tax_id", "购方纳税人识别号"),
            ("seller_name", "销方名称"),
            ("seller_tax_id", "销方纳税人识别号"),
            ("subtotal_amount", "金额合计"),
            ("tax_amount", "税额合计"),
            ("total_amount", "价税合计"),
        ]:
            if invoice_data.get(field_name) in (None, "", []):
                add_issue(field_name, "error", f"缺少{field_label}。", f"补充并核对{field_label}。")

        for field_name, field_label in [
            ("buyer_tax_id", "购方纳税人识别号"),
            ("seller_tax_id", "销方纳税人识别号"),
        ]:
            tax_id = str(invoice_data.get(field_name, "")).strip().upper()
            if tax_id and not re.fullmatch(r"[0-9A-Z]{15,18}", tax_id):
                add_issue(
                    field_name,
                    "error",
                    f"{field_label}格式不正确，应为15到18位数字或大写字母。",
                    f"按营业执照或税务登记信息核对{field_label}。",
                )

        issue_date = invoice_data.get("issue_date", "")
        issue_datetime = None
        if issue_date:
            try:
                issue_datetime = datetime.strptime(issue_date, "%Y-%m-%d")
            except ValueError:
                add_issue(
                    "issue_date",
                    "error",
                    "开票日期格式不正确。",
                    "将开票日期规范为 YYYY-MM-DD。",
                )

        if issue_datetime is not None:
            now = datetime.now()
            if issue_datetime.year != now.year:
                add_issue(
                    "issue_date",
                    "warning",
                    f"当前发票为跨年发票：{issue_datetime.year}年。",
                    "报销入账时确认所属期间与跨年政策。",
                )
            invoice_type = str(invoice_data.get("invoice_type", ""))
            if "专用" in invoice_type:
                elapsed_days = (now - issue_datetime).days
                if elapsed_days > VAT_CERTIFICATION_DAYS:
                    add_issue(
                        "issue_date",
                        "warning",
                        f"增值税专用发票已超过{VAT_CERTIFICATION_DAYS}天认证期限。",
                        "确认是否仍可抵扣或按制度走进项税额转出流程。",
                    )

        remarks = str(invoice_data.get("remarks", "")).strip()
        line_items = invoice_data.get("line_items", [])
        item_names = " ".join(item.get("item_name", "") for item in line_items)
        if any(keyword in f"{remarks} {item_names}" for keyword in REMARK_REQUIRED_KEYWORDS) and not remarks:
            add_issue(
                "remarks",
                "error",
                "当前业务场景通常要求备注栏填写补充信息，但备注为空。",
                "补充备注栏中的项目地点、运输起止地或其他必填说明。",
            )

        if invoice_data.get("is_void"):
            add_issue(
                "invoice_status",
                "warning",
                "当前发票已标记为作废。",
                "停止报销或入账，改用有效发票重提流程。",
            )

        if invoice_data.get("is_red_correction") and not (
            invoice_data.get("original_invoice_code") and invoice_data.get("original_invoice_number")
        ):
            add_issue(
                "original_invoice_number",
                "warning",
                "红冲发票缺少原发票代码或号码。",
                "补充原蓝字发票代码和号码后再继续处理。",
            )

        return {
            "is_compliant": not any(issue["level"] == "error" for issue in issues),
            "issues": issues,
            "suggestions": suggestions,
        }

    def _extract_invoice_title(self, lines: list[str]) -> str:
        for line in lines:
            if "发票" in line:
                return line
        return ""

    def _normalize_text(self, text: str) -> str:
        normalized_text = text.replace("\u3000", " ").replace("\xa0", " ")
        for pattern, replacement in NORMALIZATION_RULES:
            normalized_text = re.sub(pattern, replacement, normalized_text)
        normalized_text = re.sub(r"\s+", " ", normalized_text)
        return normalized_text.strip()

    def _normalize_lines(self, text: str) -> list[str]:
        normalized_lines: list[str] = []
        for raw_line in text.splitlines():
            line = raw_line.replace("\u3000", " ").replace("\xa0", " ")
            for pattern, replacement in NORMALIZATION_RULES:
                line = re.sub(pattern, replacement, line)
            line = re.sub(r"\s+", " ", line).strip()
            if line:
                normalized_lines.append(line)
        return normalized_lines

    def _extract_text_field(self, text: str, patterns: list[str]) -> str:
        for pattern in patterns:
            match = re.search(pattern, text, re.S)
            if match:
                return self._clean_text_value(match.group(1))
        return ""

    def _extract_money_field(self, text: str, patterns: list[str]) -> float | None:
        value = self._extract_text_field(text, patterns)
        return self._to_number(value)

    def _extract_remarks(self, text: str, lines: list[str]) -> str:
        for line in lines:
            stripped_line = line.strip()
            if not stripped_line:
                continue
            if stripped_line in {"备", "注", "备注"}:
                return ""
            if stripped_line.startswith("备注：") or stripped_line.startswith("备注:"):
                return self._clean_text_value(stripped_line.split("：", 1)[1] if "：" in stripped_line else stripped_line.split(":", 1)[1])

        return self._extract_text_field(
            text,
            [r"备\s*注[:：]\s*(.*?)(?=\s+(?:收款人|复核|开票人)[:：]|$)"],
        )

    def _extract_issue_date(self, text: str) -> str:
        raw_date = self._extract_text_field(
            text,
            [
                r"开票日期[:：]\s*([0-9]{4}年[0-9]{1,2}月[0-9]{1,2}日)",
                r"开票日期[:：]\s*([0-9]{4}-[0-9]{1,2}-[0-9]{1,2})",
                r"开票日期[:：]\s*([0-9]{4}/[0-9]{1,2}/[0-9]{1,2})",
            ],
        )
        if not raw_date:
            return ""
        for input_format in ("%Y年%m月%d日", "%Y-%m-%d", "%Y/%m/%d"):
            try:
                return datetime.strptime(raw_date, input_format).strftime("%Y-%m-%d")
            except ValueError:
                continue
        return raw_date

    def _extract_party_names(self, text: str) -> tuple[str, str]:
        pair_match = re.search(
            r"购方名称[:：]\s*(.*?)\s+销方名称[:：]\s*(.*?)(?=\s+(?:买|购方纳税人识别号|销方纳税人识别号|统一社会信用代码/纳税人识别号|项目名称|合计|备注|收款人|复核|开票人))",
            text,
            re.S,
        )
        if pair_match:
            return (
                self._clean_party_value(pair_match.group(1)),
                self._clean_party_value(pair_match.group(2)),
            )

        buyer_name = self._extract_text_field(
            text,
            [
                r"购方名称[:：]\s*(.*?)(?=\s+购方纳税人识别号[:：]|\s+购方地址、电话[:：]|\s+购方开户行及账号[:：]|\s+销方名称[:：]|\s+项目名称|\s+合计)",
            ],
        )
        seller_name = self._extract_text_field(
            text,
            [
                r"销方名称[:：]\s*(.*?)(?=\s+销方纳税人识别号[:：]|\s+销方地址、电话[:：]|\s+销方开户行及账号[:：]|\s+项目名称|\s+合计|\s+备注|\s+收款人|\s+复核|\s+开票人|\s+买)",
            ],
        )
        return buyer_name, seller_name

    def _extract_labeled_line_value(self, lines: list[str], label: str) -> str:
        normalized_label = f"{label}："
        known_labels = [
            "购方名称",
            "销方名称",
            "购方纳税人识别号",
            "销方纳税人识别号",
            "购方地址、电话",
            "销方地址、电话",
            "购方开户行及账号",
            "销方开户行及账号",
            "统一社会信用代码/纳税人识别号",
            "纳税人识别号",
            "项目名称",
            "合计",
            "价税合计",
            "备注",
            "收款人",
            "复核",
            "开票人",
        ]
        next_labels = [
            f"{known_label}：" for known_label in known_labels if known_label != label
        ]

        for line in lines:
            compact_line = line.replace(" ", "")
            if compact_line in STRUCTURAL_NOISE_LINES:
                continue
            start_index = line.find(normalized_label)
            if start_index == -1:
                continue
            value_start = start_index + len(normalized_label)
            value_end = len(line)
            for next_label in next_labels:
                candidate_index = line.find(next_label, value_start)
                if candidate_index != -1:
                    value_end = min(value_end, candidate_index)
            return self._clean_text_value(line[value_start:value_end])
        return ""

    def _extract_party_tax_ids(self, text: str) -> tuple[str, str]:
        buyer_tax_id = self._extract_text_field(
            text,
            [r"购方纳税人识别号[:：]\s*([0-9A-Z]{15,20})"],
        )
        seller_tax_id = self._extract_text_field(
            text,
            [r"销方纳税人识别号[:：]\s*([0-9A-Z]{15,20})"],
        )

        labeled_tax_ids = re.findall(
            r"(?:统一社会信用代码/纳税人识别号|纳税人识别号)[:：]\s*([0-9A-Z]{15,20})",
            text,
        )
        if not buyer_tax_id and labeled_tax_ids:
            buyer_tax_id = labeled_tax_ids[0]
        if not seller_tax_id and len(labeled_tax_ids) > 1:
            seller_tax_id = labeled_tax_ids[1]
        return buyer_tax_id, seller_tax_id

    def _extract_vertical_party_fields(self, lines: list[str]) -> dict[str, dict[str, str]]:
        party_fields = {
            "buyer": {"name": "", "tax_id": "", "address_phone": "", "bank_account": ""},
            "seller": {"name": "", "tax_id": "", "address_phone": "", "bank_account": ""},
        }
        current_party = ""
        index = 0
        while index < len(lines):
            compact_line = lines[index].replace(" ", "")
            vertical_marker = self._detect_vertical_party_marker(lines, index)
            if vertical_marker:
                current_party = vertical_marker
                index += 5
                continue
            if compact_line.startswith(("项目名称", "合计", "价税合计", "备注", "收款人", "复核", "开票人")):
                break
            if not current_party:
                index += 1
                continue
            stripped_line = lines[index].strip()
            if stripped_line.startswith("名称："):
                party_fields[current_party]["name"] = self._clean_party_value(stripped_line.split("：", 1)[1])
            elif stripped_line.startswith(("统一社会信用代码/纳税人识别号：", "纳税人识别号：")):
                party_fields[current_party]["tax_id"] = self._clean_text_value(stripped_line.split("：", 1)[1])
            elif stripped_line.startswith("地址、电话："):
                party_fields[current_party]["address_phone"] = self._clean_text_value(stripped_line.split("：", 1)[1])
            elif stripped_line.startswith("开户行及账号："):
                party_fields[current_party]["bank_account"] = self._clean_text_value(stripped_line.split("：", 1)[1])
            index += 1
        return party_fields

    def _detect_vertical_party_marker(self, lines: list[str], start_index: int) -> str:
        if start_index + 4 >= len(lines):
            return ""
        marker = "".join(lines[start_index + offset].replace(" ", "") for offset in range(5))
        if marker == "购买方信息":
            return "buyer"
        if marker == "销售方信息":
            return "seller"
        return ""

    def _extract_party_address_phones(self, text: str) -> tuple[str, str]:
        buyer_address_phone = self._extract_text_field(
            text,
            [
                r"购方地址、电话[:：]\s*(.*?)(?=\s+销方地址、电话[:：]|\s+购方开户行及账号[:：]|\s+项目名称|\s+合计)",
            ],
        )
        seller_address_phone = self._extract_text_field(
            text,
            [
                r"销方地址、电话[:：]\s*(.*?)(?=\s+销方开户行及账号[:：]|\s+项目名称|\s+合计|\s+备注|\s+收款人|\s+复核|\s+开票人)",
            ],
        )
        return buyer_address_phone, seller_address_phone

    def _extract_party_bank_accounts(self, text: str) -> tuple[str, str]:
        buyer_bank_account = self._extract_text_field(
            text,
            [
                r"购方开户行及账号[:：]\s*(.*?)(?=\s+销方开户行及账号[:：]|\s+项目名称|\s+合计)",
            ],
        )
        seller_bank_account = self._extract_text_field(
            text,
            [
                r"销方开户行及账号[:：]\s*(.*?)(?=\s+项目名称|\s+合计|\s+备注|\s+收款人|\s+复核|\s+开票人)",
            ],
        )
        return buyer_bank_account, seller_bank_account

    def _extract_amount_summary(self, text: str) -> tuple[float | None, float | None]:
        match = re.search(r"合\s*计\s*[¥￥]?\s*([0-9,.-]+)\s*[¥￥]?\s*([0-9,.-]+)", text)
        if not match:
            return None, None
        return self._to_number(match.group(1)), self._to_number(match.group(2))

    def _extract_line_items(self, lines: list[str]) -> list[dict]:
        line_items: list[dict] = []
        start_index = None
        for index, line in enumerate(lines):
            compact_line = line.replace(" ", "")
            if "项目名称" in compact_line and "税额" in compact_line:
                start_index = index + 1
                break
        if start_index is None:
            return line_items

        for offset, line in enumerate(lines[start_index:], start=start_index):
            compact_line = line.replace(" ", "")
            if compact_line in STRUCTURAL_NOISE_LINES:
                continue
            if compact_line.startswith(("合计", "价税合计", "备注", "收款人", "复核", "开票人")):
                break
            matched_item = re.search(
                r"(?P<prefix>.+?)\s+(?P<unit>[^\s]+)\s+(?P<quantity>-?[0-9]+(?:\.[0-9]+)?)\s+(?P<unit_price>-?[0-9]+(?:\.[0-9]+)?)\s+(?P<amount>-?[0-9]+(?:\.[0-9]+)?)\s+(?P<tax_rate>[0-9]+(?:\.[0-9]+)?%|免税|不征税|0%)\s+(?P<tax_amount>-?[0-9]+(?:\.[0-9]+)?)$",
                line,
            )
            if matched_item:
                prefix_parts = matched_item.group("prefix").split()
                if len(prefix_parts) >= 2:
                    spec_model = prefix_parts[-1]
                    item_name = " ".join(prefix_parts[:-1])
                else:
                    spec_model = ""
                    item_name = matched_item.group("prefix")
                line_items.append(
                    {
                        "item_name": self._clean_text_value(item_name),
                        "spec_model": self._clean_text_value(spec_model),
                        "unit": matched_item.group("unit"),
                        "quantity": self._to_number(matched_item.group("quantity")),
                        "unit_price": self._to_number(matched_item.group("unit_price")),
                        "amount": self._to_number(matched_item.group("amount")),
                        "tax_rate": matched_item.group("tax_rate"),
                        "tax_amount": self._to_number(matched_item.group("tax_amount")),
                    }
                )
                continue

            if line_items and self._looks_like_item_continuation(line):
                line_items[-1]["item_name"] = (
                    f"{line_items[-1]['item_name']}{self._clean_text_value(line)}"
                )
                continue

            merged_line = self._merge_split_item_line(lines, offset)
            if not merged_line:
                continue
            matched_item = re.search(
                r"(?P<prefix>.+?)\s+(?P<unit>[^\s]+)\s+(?P<quantity>-?[0-9]+(?:\.[0-9]+)?)\s+(?P<unit_price>-?[0-9]+(?:\.[0-9]+)?)\s+(?P<amount>-?[0-9]+(?:\.[0-9]+)?)\s+(?P<tax_rate>[0-9]+(?:\.[0-9]+)?%|免税|不征税|0%)\s+(?P<tax_amount>-?[0-9]+(?:\.[0-9]+)?)$",
                merged_line,
            )
            if matched_item:
                prefix_parts = matched_item.group("prefix").split()
                if len(prefix_parts) >= 2:
                    spec_model = prefix_parts[-1]
                    item_name = " ".join(prefix_parts[:-1])
                else:
                    spec_model = ""
                    item_name = matched_item.group("prefix")
                line_items.append(
                    {
                        "item_name": self._clean_text_value(item_name),
                        "spec_model": self._clean_text_value(spec_model),
                        "unit": matched_item.group("unit"),
                        "quantity": self._to_number(matched_item.group("quantity")),
                        "unit_price": self._to_number(matched_item.group("unit_price")),
                        "amount": self._to_number(matched_item.group("amount")),
                        "tax_rate": matched_item.group("tax_rate"),
                        "tax_amount": self._to_number(matched_item.group("tax_amount")),
                    }
                )
        return line_items

    def _merge_split_item_line(self, lines: list[str], current_index: int) -> str:
        current_line = lines[current_index].strip()
        if not current_line:
            return ""
        if current_index + 1 >= len(lines):
            return ""
        next_line = lines[current_index + 1].strip()
        next_compact = next_line.replace(" ", "")
        if not next_line or next_compact in STRUCTURAL_NOISE_LINES:
            return ""
        if any(token in next_compact for token in ("：", ":", "合计", "价税合计", "备注", "收款人", "复核", "开票人")):
            return ""
        if re.search(r"[0-9%¥￥]", next_compact):
            return ""
        return f"{current_line}{next_line}"

    def _looks_like_item_continuation(self, line: str) -> bool:
        compact_line = line.replace(" ", "")
        if compact_line in STRUCTURAL_NOISE_LINES:
            return False
        if any(token in compact_line for token in ("：", ":", "合计", "价税合计", "备注", "收款人", "复核", "开票人")):
            return False
        if re.search(r"[0-9%¥￥]", compact_line):
            return False
        return len(compact_line) <= 12

    def _detect_invoice_status(
        self,
        text: str,
        total_amount: float | None,
        original_invoice_code: str,
        original_invoice_number: str,
    ) -> str:
        if "作废" in text:
            return "作废"
        if self._is_red_correction(text, total_amount, original_invoice_code, original_invoice_number):
            return "红冲"
        return "正常"

    def _is_red_correction(
        self,
        text: str,
        total_amount: float | None,
        original_invoice_code: str,
        original_invoice_number: str,
    ) -> bool:
        return any(
            [
                "红字" in text,
                "红冲" in text,
                "负数" in text,
                bool(original_invoice_code),
                bool(original_invoice_number),
                total_amount is not None and total_amount < 0,
            ]
        )

    def _clean_text_value(self, value: str) -> str:
        return re.sub(r"\s+", " ", value or "").strip()

    def _clean_party_value(self, value: str) -> str:
        cleaned_value = self._clean_text_value(value)
        for marker in ("买", "售", "方", "信", "息"):
            if cleaned_value.endswith(marker):
                cleaned_value = cleaned_value[:-1].strip()
        return cleaned_value

    def _to_number(self, value: str | None) -> float | None:
        if value in (None, ""):
            return None
        normalized_value = str(value).replace(",", "").replace("¥", "").replace("￥", "")
        try:
            return round(float(normalized_value), 2)
        except ValueError:
            return None
