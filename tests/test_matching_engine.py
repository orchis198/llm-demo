import unittest

from domain.models import DocumentRecord, DocumentType, ParsedField
from engines.matching_engine import MatchingEngine


def build_doc(document_id: str, document_type: DocumentType, mapping: dict[str, str]) -> DocumentRecord:
    return DocumentRecord(
        document_id=document_id,
        document_type=document_type,
        file_path=document_id,
        file_name=document_id,
        parsed_fields=[
            ParsedField(
                field_name=key,
                raw_value=value,
                normalized_value=value,
                confidence=1.0,
                source_ref=document_id,
            )
            for key, value in mapping.items()
        ],
        raw_text_excerpt=" ".join(mapping.values()),
    )


class MatchingEngineTestCase(unittest.TestCase):
    def setUp(self) -> None:
        self.engine = MatchingEngine()

    def test_match_three_way_exact(self) -> None:
        invoice = build_doc("invoice", DocumentType.VAT_SPECIAL_INVOICE, {
            "amount": "23504.00",
            "tax_rate": "13%",
            "quantity": "6",
            "vendor_name": "苏州启明设备有限公司",
            "invoice_date": "2026-03-25",
        })
        contract = build_doc("contract", DocumentType.CONTRACT, {
            "amount": "23504.00",
            "tax_rate": "13%",
            "quantity": "6",
            "vendor_name": "苏州启明设备有限公司",
            "contract_date": "2026-03-25",
        })
        receipt = build_doc("receipt", DocumentType.GOODS_RECEIPT, {
            "amount": "23504.00",
            "tax_rate": "13%",
            "quantity": "6",
            "vendor_name": "苏州启明设备有限公司",
            "receipt_date": "2026-03-25",
        })

        result = self.engine.match_three_way(invoice, contract, receipt)

        self.assertEqual(result.status, "matched")
        self.assertFalse(result.review_required)

    def test_match_three_way_explainable_date_difference(self) -> None:
        invoice = build_doc("invoice", DocumentType.VAT_SPECIAL_INVOICE, {
            "amount": "23504.00",
            "tax_rate": "13%",
            "quantity": "6",
            "vendor_name": "苏州启明设备有限公司",
            "invoice_date": "2026-03-25",
        })
        contract = build_doc("contract", DocumentType.CONTRACT, {
            "amount": "23504.00",
            "tax_rate": "13%",
            "quantity": "6",
            "vendor_name": "苏州启明设备有限公司",
            "contract_date": "2026-03-20",
        })
        receipt = build_doc("receipt", DocumentType.GOODS_RECEIPT, {
            "amount": "23504.00",
            "tax_rate": "13%",
            "quantity": "6",
            "vendor_name": "苏州启明设备有限公司",
            "receipt_date": "2026-03-25",
        })

        result = self.engine.match_three_way(invoice, contract, receipt)

        self.assertEqual(result.status, "explainable_review_required")
        self.assertTrue(result.review_required)

    def test_match_three_way_hard_mismatch(self) -> None:
        invoice = build_doc("invoice", DocumentType.VAT_SPECIAL_INVOICE, {
            "amount": "23504.00",
            "tax_rate": "13%",
            "quantity": "6",
            "vendor_name": "苏州启明设备有限公司",
            "invoice_date": "2026-03-25",
        })
        contract = build_doc("contract", DocumentType.CONTRACT, {
            "amount": "99999.00",
            "tax_rate": "13%",
            "quantity": "6",
            "vendor_name": "苏州启明设备有限公司",
            "contract_date": "2026-03-25",
        })
        receipt = build_doc("receipt", DocumentType.GOODS_RECEIPT, {
            "amount": "23504.00",
            "tax_rate": "13%",
            "quantity": "6",
            "vendor_name": "苏州启明设备有限公司",
            "receipt_date": "2026-03-25",
        })

        result = self.engine.match_three_way(invoice, contract, receipt)

        self.assertEqual(result.status, "conflicted_review_required")
        self.assertTrue(result.review_required)


if __name__ == "__main__":
    unittest.main()
