"""
Generalized Research Request, Source Acquisition, and Extraction Contracts for IOL.
Provides domain-neutral schemas for live web/API research across academia, startups, and industry.
"""

from datetime import datetime, timezone
from typing import Any, Dict, List, Literal, Optional
from pydantic import BaseModel, Field
from backend.iol.core.models import ExecutionBudget


def utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


# ==============================================================================
# 1. Intent Constraints Contract
# ==============================================================================
class IntentConstraints(BaseModel):
    """Structured intent constraints specifying category, inclusion/exclusion rules, and count."""
    entity_category: str = Field(..., description="Target category, e.g. 'ai_developer_framework', 'ai_startup', 'academic_faculty'")
    mandatory_inclusion_criteria: List[str] = Field(
        default_factory=list,
        description="Conditions that candidate entity MUST satisfy with evidence"
    )
    exclusion_criteria: List[str] = Field(
        default_factory=list,
        description="Conditions that immediately disqualify candidate entity"
    )
    requested_attributes: List[str] = Field(default_factory=list)
    geographic_restrictions: Optional[Dict[str, Any]] = None
    temporal_restrictions: Optional[Dict[str, Any]] = None
    requested_record_count: int = Field(default=5, ge=1, le=50)
    evidence_requirements: Dict[str, Any] = Field(default_factory=dict)


# ==============================================================================
# 2. Generalized Research Request Specification
# ==============================================================================
class ResearchRequest(BaseModel):
    """Declarative specification for an autonomous research mission."""
    entity_type: str = Field(..., description="Target entity type, e.g. 'professor', 'startup', 'tool'")
    goal_and_constraints: str = Field(..., description="Natural language objective and search constraints")
    requested_fields: List[str] = Field(
        ...,
        description="Target attributes to extract into the result table, e.g. ['name', 'institution', 'official_profile_url']"
    )
    intent_constraints: Optional[IntentConstraints] = Field(
        default=None,
        description="Formal semantic constraints, inclusion rules, and exclusion filters"
    )
    source_requirements: Dict[str, Any] = Field(
        default_factory=lambda: {
            "require_live_acquisition": True,
            "preferred_providers": ["openalex", "web", "github"],
            "max_sources": 15
        }
    )
    verification_requirements: Dict[str, Any] = Field(
        default_factory=lambda: {
            "require_evidence_url": True,
            "require_email": False,
            "minimum_confidence": 0.60
        }
    )
    max_records: int = Field(default=10, ge=1, le=50)
    budget: ExecutionBudget = Field(default_factory=ExecutionBudget)
    optional_user_context: Optional[str] = Field(default=None, description="Optional CV, background, or user preferences")
    include_outreach_draft: bool = Field(default=False, description="Whether to compose personalized correspondence")
    include_scheduling: bool = Field(default=False, description="Whether to calculate arrival time windows")


# ==============================================================================
# 3. Live Source Acquisition Models
# ==============================================================================
# 2. Live Source Acquisition Models
# ==============================================================================
class AcquiredSource(BaseModel):
    """An individual source acquired from live external search or HTTP retrieval."""
    source_id: str
    source_url: str
    title: str
    retrieval_timestamp: str = Field(default_factory=utc_now_iso)
    content_snippet: str
    content_hash: str = Field(description="SHA-256 hash of retrieved content for provenance")
    status_code: int = 200
    provider: str
    raw_metadata: Dict[str, Any] = Field(default_factory=dict)


class SourceAcquisitionInput(BaseModel):
    entity_type: str = Field(..., description="Type of entity to acquire sources for")
    query_terms: List[str] = Field(..., description="Search terms and keywords")
    target_locations: Optional[List[str]] = Field(default=None)
    preferred_providers: List[str] = Field(default=["openalex", "github", "web"])
    max_sources: int = Field(default=15, ge=1, le=50)
    timeout_seconds: float = Field(default=10.0)


class SourceAcquisitionOutput(BaseModel):
    entity_type: str
    sources: List[AcquiredSource]
    total_sources: int
    retrieval_latency_ms: float
    provider_used: str
    provenance_log: List[Dict[str, str]] = Field(default_factory=list)


# ==============================================================================
# 3. Generalized Structured Extraction Models
# ==============================================================================
class GeneralizedExtractionInput(BaseModel):
    entity_type: str
    sources: List[Dict[str, Any]]
    requested_fields: List[str]
    goal_and_constraints: Optional[str] = None


class GeneralizedExtractionOutput(BaseModel):
    entity_type: str
    records: List[Dict[str, Any]]
    fields_extracted: List[str]
    total_extracted: int
    provenance_metadata: Dict[str, Any] = Field(default_factory=dict)


# ==============================================================================
# 4. Generalized Verification & Field-Level Evidence Models
# ==============================================================================

class FieldEvidence(BaseModel):
    """Field-level evidence metadata detailing provenance, support status, and confidence."""
    field_name: str
    field_value: Any
    evidence_url: Optional[str] = None
    source_type: Literal[
        "DIRECT_API_FIELD",
        "BIBLIOGRAPHIC_PROFILE",
        "OFFICIAL_WEBSITE",
        "HTML_TITLE",
        "DOM_SNIPPET",
        "INFERRED_CONTEXT",
        "UNKNOWN"
    ] = "DIRECT_API_FIELD"
    relevant_excerpt: Optional[str] = None
    retrieval_timestamp: str = Field(default_factory=utc_now_iso)
    verification_method: str = "FIELD_EXTRACTION_CHECK"
    verification_status: Literal["DIRECTLY_SUPPORTED", "DERIVED", "INFERRED", "UNKNOWN", "UNSUPPORTED"] = "DIRECTLY_SUPPORTED"
    confidence: float = Field(default=0.85, ge=0.0, le=1.0)


class GeneralizedVerificationInput(BaseModel):
    entity_type: str
    records: List[Dict[str, Any]]
    requested_fields: List[str]
    verification_rules: Dict[str, Any] = Field(
        default_factory=lambda: {
            "require_evidence_url": True,
            "require_email": False,
            "minimum_confidence": 0.60
        }
    )


class VerifiedRecord(BaseModel):
    record_id: str
    is_valid: bool
    confidence_score: float = Field(..., ge=0.0, le=1.0)
    confidence_tier: Literal["HIGH", "MEDIUM", "LOW"]
    validation_flags: List[str] = Field(default_factory=list)
    fields: Dict[str, Any]
    field_evidence: Dict[str, FieldEvidence] = Field(default_factory=dict)
    entity_classification: Optional[str] = None
    source_url: Optional[str] = None
    retrieval_timestamp: Optional[str] = None
    # Four-Tier State Distinction
    is_source_verified: bool = True
    is_field_verified: bool = True
    is_semantically_relevant: bool = True
    is_intent_satisfied: bool = True
    semantic_relevance_score: float = 0.85
    relevance_evidence: Optional[str] = None


class GeneralizedVerificationOutput(BaseModel):
    entity_type: str
    verified_records: List[VerifiedRecord]
    pass_count: int
    flagged_count: int
    average_confidence: float


# ==============================================================================
# 5. Semantic Relevance & Intent Satisfaction Models
# ==============================================================================

class RejectionDetail(BaseModel):
    candidate_id: str
    identifier: str
    rejection_reasons: List[str]
    violated_exclusion_criteria: List[str] = Field(default_factory=list)
    unmet_inclusion_criteria: List[str] = Field(default_factory=list)


class RelevanceEvaluation(BaseModel):
    candidate_id: str
    identifier: str
    is_relevant: bool
    relevance_score: float = Field(..., ge=0.0, le=1.0)
    matched_inclusion_criteria: List[str] = Field(default_factory=list)
    violated_exclusion_criteria: List[str] = Field(default_factory=list)
    relevance_evidence: Optional[str] = None
    rejection_reason: Optional[str] = None


class SemanticRelevanceInput(BaseModel):
    entity_type: str
    candidates: List[Dict[str, Any]]
    intent_constraints: IntentConstraints
    task_intent: Optional[str] = None


class SemanticRelevanceOutput(BaseModel):
    entity_type: str
    total_evaluated: int
    qualified_candidates: List[Dict[str, Any]]
    rejected_candidates: List[RejectionDetail]
    precision_estimate: float
    relevance_summary: str
    evaluations: List[RelevanceEvaluation] = Field(default_factory=list)

