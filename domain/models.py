from dataclasses import dataclass, field
from enum import Enum


class DocumentType(str, Enum):
    VAT_SPECIAL_INVOICE = "vat_special_invoice"
    VAT_NORMAL_INVOICE = "vat_normal_invoice"
    CONTRACT = "contract"
    GOODS_RECEIPT = "goods_receipt"
    VOUCHER = "voucher"
    TAX_FORM_MAIN = "tax_form_main"
    TAX_FORM_ATTACHMENT = "tax_form_attachment"
    OTHER = "other"


class TemplateScope(str, Enum):
    STATUTORY = "statutory"
    SYSTEM = "system"
    ENTERPRISE = "enterprise"
    CANDIDATE = "candidate"


class TemplateMatchStatus(str, Enum):
    MATCHED = "matched"
    MATCHED_WITH_REVIEW = "matched_with_review"
    TEMPLATE_MISSING = "template_missing"
    SUSPECTED_NEW_OFFICIAL_LAYOUT = "suspected_new_official_layout"
    CONFLICTED = "conflicted"


class RuleSeverity(str, Enum):
    HARD_BLOCK = "hard_block"
    WARNING = "warning"
    REVIEW_REQUIRED = "review_required"
    KNOWLEDGE_GAP = "knowledge_gap"


class RiskLevel(str, Enum):
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"


class KnowledgeSourceType(str, Enum):
    OFFICIAL_REGULATION = "official_regulation"
    OFFICIAL_GUIDANCE = "official_guidance"
    COMPANY_POLICY = "company_policy"
    SEARCH_CANDIDATE = "search_candidate"


class MatchDifferenceType(str, Enum):
    HARD_MISMATCH = "hard_mismatch"
    EXPLAINABLE_MISMATCH = "explainable_mismatch"
    MISSING_DATA = "missing_data"


class ReviewStatus(str, Enum):
    PENDING = "pending"
    CONFIRMED = "confirmed"
    REJECTED = "rejected"
    MANUAL_ADJUSTED = "manual_adjusted"


@dataclass(slots=True)
class ParsedField:
    field_name: str
    raw_value: str
    normalized_value: str
    confidence: float
    source_ref: str
    is_missing: bool = False


@dataclass(slots=True)
class DocumentRecord:
    document_id: str
    document_type: DocumentType
    file_path: str
    file_name: str
    template_id: str | None = None
    template_match_status: TemplateMatchStatus | None = None
    parsed_fields: list[ParsedField] = field(default_factory=list)
    raw_text_excerpt: str = ""
    needs_manual_completion: bool = False

    def get_field_value(self, field_name: str) -> str:
        for parsed_field in self.parsed_fields:
            if parsed_field.field_name == field_name:
                return parsed_field.normalized_value or parsed_field.raw_value
        return ""


@dataclass(slots=True)
class TemplateDefinition:
    template_id: str
    template_name: str
    document_type: DocumentType
    scope: TemplateScope
    is_statutory: bool
    version: str
    is_active: bool
    field_mapping: dict[str, str] = field(default_factory=dict)
    match_keywords: list[str] = field(default_factory=list)
    description: str = ""


@dataclass(slots=True)
class KnowledgeDocument:
    document_id: str
    title: str
    source_type: KnowledgeSourceType
    issuing_authority: str
    publish_date: str
    effective_date: str
    summary: str
    storage_path: str
    is_approved: bool


@dataclass(slots=True)
class SearchCandidate:
    candidate_id: str
    title: str
    url: str
    source_site: str
    snippet: str
    topic: str
    candidate_type: KnowledgeSourceType
    is_official_site: bool = False
    official_reason: str = ""
    original_rank: int = 0
    is_approved: bool = False


@dataclass(slots=True)
class TemplateMatchResult:
    template_id: str | None
    status: TemplateMatchStatus
    reason: str
    requires_review: bool
    requires_admin_review: bool


@dataclass(slots=True)
class ComplianceIssue:
    rule_id: str
    rule_name: str
    severity: RuleSeverity
    message: str
    related_fields: list[str] = field(default_factory=list)
    knowledge_document_id: str | None = None
    review_required: bool = False


@dataclass(slots=True)
class MatchDifference:
    field_name: str
    invoice_value: str
    contract_value: str
    receipt_value: str
    difference_type: MatchDifferenceType
    review_comment_required: bool
    can_pass_with_explanation: bool
    message: str


@dataclass(slots=True)
class ThreeWayMatchResult:
    invoice_document_id: str
    contract_document_id: str
    receipt_document_id: str
    differences: list[MatchDifference] = field(default_factory=list)
    is_match_exact: bool = False
    review_required: bool = True
    status: str = "missing_data_review_required"
    summary: str = ""
