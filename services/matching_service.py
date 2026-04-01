from __future__ import annotations

from engines.matching_engine import MatchingEngine
from domain.models import DocumentRecord, DocumentType, ParsedField


def build_document_record(document_id: str, document_type: DocumentType, file_name: str, field_mapping: dict[str, str]) -> DocumentRecord:
    return DocumentRecord(
        document_id=document_id,
        document_type=document_type,
        file_path=file_name,
        file_name=file_name,
        parsed_fields=[
            ParsedField(
                field_name=field_name,
                raw_value=value,
                normalized_value=value,
                confidence=1.0,
                source_ref=file_name,
            )
            for field_name, value in field_mapping.items()
        ],
        raw_text_excerpt=" ".join(field_mapping.values()),
    )


def run_three_way_match(invoice_fields: dict[str, str], contract_fields: dict[str, str], receipt_fields: dict[str, str]):
    engine = MatchingEngine()
    invoice_doc = build_document_record("invoice_show", DocumentType.VAT_SPECIAL_INVOICE, "show_invoice.txt", invoice_fields)
    contract_doc = build_document_record("contract_show", DocumentType.CONTRACT, "show_contract.txt", contract_fields)
    receipt_doc = build_document_record("receipt_show", DocumentType.GOODS_RECEIPT, "show_receipt.txt", receipt_fields)
    return engine.match_three_way(invoice_doc, contract_doc, receipt_doc)
