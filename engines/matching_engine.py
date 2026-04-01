from domain.models import (
    DocumentRecord,
    MatchDifference,
    MatchDifferenceType,
    ThreeWayMatchResult,
)


class MatchingEngine:
    def match_three_way(
        self,
        invoice_doc: DocumentRecord,
        contract_doc: DocumentRecord,
        receipt_doc: DocumentRecord,
    ) -> ThreeWayMatchResult:
        differences: list[MatchDifference] = []

        for difference in [
            self.compare_amount(invoice_doc, contract_doc, receipt_doc),
            self.compare_tax_rate(invoice_doc, contract_doc, receipt_doc),
            self.compare_quantity(invoice_doc, contract_doc, receipt_doc),
            self.compare_vendor(invoice_doc, contract_doc, receipt_doc),
            self.compare_dates(invoice_doc, contract_doc, receipt_doc),
        ]:
            if difference is not None:
                differences.append(difference)

        return self.build_result(invoice_doc, contract_doc, receipt_doc, differences)

    def compare_amount(
        self,
        invoice_doc: DocumentRecord,
        contract_doc: DocumentRecord,
        receipt_doc: DocumentRecord,
    ) -> MatchDifference | None:
        return self._compare_shared_field(
            invoice_doc,
            contract_doc,
            receipt_doc,
            field_name="amount",
            difference_type=MatchDifferenceType.HARD_MISMATCH,
            message="金额不一致，需要人工审核。",
            can_pass_with_explanation=False,
        )

    def compare_tax_rate(
        self,
        invoice_doc: DocumentRecord,
        contract_doc: DocumentRecord,
        receipt_doc: DocumentRecord,
    ) -> MatchDifference | None:
        return self._compare_shared_field(
            invoice_doc,
            contract_doc,
            receipt_doc,
            field_name="tax_rate",
            difference_type=MatchDifferenceType.HARD_MISMATCH,
            message="税率不一致，需要人工审核。",
            can_pass_with_explanation=False,
        )

    def compare_quantity(
        self,
        invoice_doc: DocumentRecord,
        contract_doc: DocumentRecord,
        receipt_doc: DocumentRecord,
    ) -> MatchDifference | None:
        return self._compare_shared_field(
            invoice_doc,
            contract_doc,
            receipt_doc,
            field_name="quantity",
            difference_type=MatchDifferenceType.HARD_MISMATCH,
            message="数量不一致，需要人工审核。",
            can_pass_with_explanation=False,
        )

    def compare_vendor(
        self,
        invoice_doc: DocumentRecord,
        contract_doc: DocumentRecord,
        receipt_doc: DocumentRecord,
    ) -> MatchDifference | None:
        return self._compare_shared_field(
            invoice_doc,
            contract_doc,
            receipt_doc,
            field_name="vendor_name",
            difference_type=MatchDifferenceType.HARD_MISMATCH,
            message="供应商不一致，需要人工审核。",
            can_pass_with_explanation=False,
        )

    def compare_dates(
        self,
        invoice_doc: DocumentRecord,
        contract_doc: DocumentRecord,
        receipt_doc: DocumentRecord,
    ) -> MatchDifference | None:
        invoice_value = invoice_doc.get_field_value("invoice_date")
        contract_value = contract_doc.get_field_value("contract_date")
        receipt_value = receipt_doc.get_field_value("receipt_date")
        values = [invoice_value, contract_value, receipt_value]

        if not all(values):
            return self.build_difference(
                field_name="date",
                invoice_value=invoice_value,
                contract_value=contract_value,
                receipt_value=receipt_value,
                difference_type=MatchDifferenceType.MISSING_DATA,
                review_comment_required=True,
                can_pass_with_explanation=False,
                message="日期字段缺失，需要人工审核。",
            )

        if len({invoice_value, contract_value, receipt_value}) == 1:
            return None

        return self.build_difference(
            field_name="date",
            invoice_value=invoice_value,
            contract_value=contract_value,
            receipt_value=receipt_value,
            difference_type=MatchDifferenceType.EXPLAINABLE_MISMATCH,
            review_comment_required=True,
            can_pass_with_explanation=True,
            message="日期不一致，需要人工说明后审核通过。",
        )

    def build_difference(
        self,
        field_name: str,
        invoice_value: str,
        contract_value: str,
        receipt_value: str,
        difference_type: MatchDifferenceType,
        review_comment_required: bool,
        can_pass_with_explanation: bool,
        message: str,
    ) -> MatchDifference:
        return MatchDifference(
            field_name=field_name,
            invoice_value=invoice_value,
            contract_value=contract_value,
            receipt_value=receipt_value,
            difference_type=difference_type,
            review_comment_required=review_comment_required,
            can_pass_with_explanation=can_pass_with_explanation,
            message=message,
        )

    def build_result(
        self,
        invoice_doc: DocumentRecord,
        contract_doc: DocumentRecord,
        receipt_doc: DocumentRecord,
        differences: list[MatchDifference],
    ) -> ThreeWayMatchResult:
        if not differences:
            return ThreeWayMatchResult(
                invoice_document_id=invoice_doc.document_id,
                contract_document_id=contract_doc.document_id,
                receipt_document_id=receipt_doc.document_id,
                differences=[],
                is_match_exact=True,
                review_required=False,
                status="matched",
                summary="三单关键字段完全一致。",
            )

        difference_types = {difference.difference_type for difference in differences}
        if MatchDifferenceType.MISSING_DATA in difference_types:
            status = "missing_data_review_required"
            summary = "存在关键字段缺失，必须人工审核。"
        elif MatchDifferenceType.HARD_MISMATCH in difference_types:
            status = "conflicted_review_required"
            summary = "存在关键字段冲突，必须人工审核。"
        else:
            status = "explainable_review_required"
            summary = "存在日期差异，需人工说明后审核。"

        return ThreeWayMatchResult(
            invoice_document_id=invoice_doc.document_id,
            contract_document_id=contract_doc.document_id,
            receipt_document_id=receipt_doc.document_id,
            differences=differences,
            is_match_exact=False,
            review_required=True,
            status=status,
            summary=summary,
        )

    def _compare_shared_field(
        self,
        invoice_doc: DocumentRecord,
        contract_doc: DocumentRecord,
        receipt_doc: DocumentRecord,
        field_name: str,
        difference_type: MatchDifferenceType,
        message: str,
        can_pass_with_explanation: bool,
    ) -> MatchDifference | None:
        invoice_value = invoice_doc.get_field_value(field_name)
        contract_value = contract_doc.get_field_value(field_name)
        receipt_value = receipt_doc.get_field_value(field_name)
        values = [invoice_value, contract_value, receipt_value]

        if not all(values):
            return self.build_difference(
                field_name=field_name,
                invoice_value=invoice_value,
                contract_value=contract_value,
                receipt_value=receipt_value,
                difference_type=MatchDifferenceType.MISSING_DATA,
                review_comment_required=True,
                can_pass_with_explanation=False,
                message=f"字段 {field_name} 缺失，需要人工审核。",
            )

        if len({invoice_value, contract_value, receipt_value}) == 1:
            return None

        return self.build_difference(
            field_name=field_name,
            invoice_value=invoice_value,
            contract_value=contract_value,
            receipt_value=receipt_value,
            difference_type=difference_type,
            review_comment_required=True,
            can_pass_with_explanation=can_pass_with_explanation,
            message=message,
        )
