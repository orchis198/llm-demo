import unittest

from engines.accounting_engine import AccountingEngine, validate_voucher_draft


class AccountingEngineTestCase(unittest.TestCase):
    def setUp(self) -> None:
        self.engine = AccountingEngine()

    def test_generate_purchase_recommendation_with_reasons(self) -> None:
        invoice_data = {
            "invoice_number": "12345678",
            "buyer_name": "华东演示科技有限公司",
            "seller_name": "深圳万达凯旋科技有限公司",
            "subtotal_amount": 9400.0,
            "tax_amount": 1222.0,
            "total_amount": 10622.0,
            "line_items": [
                {"item_name": "*计算机配套产品*台式工作站"},
                {"item_name": "*计算机配套产品*显示器"},
            ],
        }

        recommendation = self.engine.generate_ai_recommendation(invoice_data)

        self.assertEqual(recommendation["business_type"], "采购类")
        self.assertTrue(recommendation["classification_reasons"])
        self.assertEqual(recommendation["recommended_entries"][0]["account"], "固定资产")
        self.assertEqual(recommendation["recommended_entries"][-1]["account"], "应付账款")

    def test_generate_expense_recommendation_with_reasons(self) -> None:
        invoice_data = {
            "invoice_number": "22345678",
            "buyer_name": "华东演示科技有限公司",
            "seller_name": "上海云策咨询有限公司",
            "subtotal_amount": 1000.0,
            "tax_amount": 60.0,
            "total_amount": 1060.0,
            "line_items": [{"item_name": "技术服务费"}],
            "remarks": "企业管理咨询服务",
        }

        recommendation = self.engine.generate_ai_recommendation(invoice_data)

        self.assertEqual(recommendation["business_type"], "费用类")
        self.assertIn("费用关键词", recommendation["classification_reasons"][0])
        self.assertEqual(recommendation["recommended_entries"][0]["account"], "管理费用")

    def test_missing_amount_requires_human_confirmation(self) -> None:
        invoice_data = {
            "invoice_number": "32345678",
            "buyer_name": "华东演示科技有限公司",
            "seller_name": "待确认供应商",
            "line_items": [{"item_name": "未知业务"}],
        }

        recommendation = self.engine.generate_ai_recommendation(invoice_data)

        self.assertTrue(recommendation["requires_human_confirmation"])
        self.assertTrue(recommendation["risk_notes"])

    def test_validate_voucher_rejects_empty_reviewer(self) -> None:
        voucher_draft = {
            "review_owner": "",
            "entries": [
                {"summary": "测试", "account": "管理费用", "debit": 100.0, "credit": None},
                {"summary": "测试", "account": "应付账款", "debit": None, "credit": 100.0},
            ],
        }

        validation = validate_voucher_draft(voucher_draft)

        self.assertIn("审核人不能为空。", validation["errors"])
        self.assertFalse(validation["can_post"])

    def test_validate_voucher_rejects_unbalanced_entries(self) -> None:
        voucher_draft = {
            "review_owner": "张会计",
            "entries": [
                {"summary": "测试", "account": "管理费用", "debit": 100.0, "credit": None},
                {"summary": "测试", "account": "应付账款", "debit": None, "credit": 99.0},
            ],
        }

        validation = validate_voucher_draft(voucher_draft)

        self.assertIn("凭证借贷不平，不能审核通过。", validation["errors"])
        self.assertFalse(validation["can_post"])

    def test_validate_voucher_rejects_placeholder_account(self) -> None:
        voucher_draft = {
            "review_owner": "张会计",
            "entries": [
                {"summary": "测试", "account": "待人工确认借方科目", "debit": 100.0, "credit": None},
                {"summary": "测试", "account": "应付账款", "debit": None, "credit": 100.0},
            ],
        }

        validation = validate_voucher_draft(voucher_draft)

        self.assertTrue(any("占位科目" in message for message in validation["errors"]))
        self.assertFalse(validation["can_post"])

    def test_validate_voucher_passes_when_balanced(self) -> None:
        voucher_draft = {
            "review_owner": "张会计",
            "entries": [
                {"summary": "测试", "account": "管理费用", "debit": 100.0, "credit": None},
                {"summary": "测试", "account": "应付账款", "debit": None, "credit": 100.0},
            ],
        }

        validation = validate_voucher_draft(voucher_draft)

        self.assertEqual(validation["errors"], [])
        self.assertTrue(validation["can_post"])


if __name__ == "__main__":
    unittest.main()
