"""
Typed Pydantic Schemas for Reusable Outreach Engine Capabilities.
Provides domain-independent schemas for entity discovery, structured extraction,
verification, deduplication, constrained personalization, and destination-local scheduling.
"""

from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field


# ------------------------------------------------------------------------------
# 1. Entity Discovery Schema
# ------------------------------------------------------------------------------
class EntityDiscoveryInput(BaseModel):
    entity_type: str = Field(..., description="Type of entity, e.g. 'faculty', 'startup', 'researcher'")
    query_terms: List[str] = Field(..., description="Keywords or topic filters, e.g. ['Artificial Intelligence', 'Robotics']")
    target_organizations: Optional[List[str]] = Field(default=None, description="Target institutions or companies")
    target_locations: Optional[List[str]] = Field(default=None, description="Target countries or cities")
    max_results: int = Field(default=10, ge=1, le=100)
    seed_data_reference: Optional[str] = Field(default=None, description="Optional path to authoritative seed data")


class DiscoveredEntity(BaseModel):
    entity_id: str
    entity_type: str
    name: str
    organization: str
    role_or_title: str
    domain_or_department: str
    source_url: str
    country: str = "United States"
    evidence_url: Optional[str] = None
    raw_metadata: Dict[str, Any] = Field(default_factory=dict)


class EntityDiscoveryOutput(BaseModel):
    entity_type: str
    entities: List[DiscoveredEntity]
    total_discovered: int


# ------------------------------------------------------------------------------
# 2. Structured Extraction Schema
# ------------------------------------------------------------------------------
class StructuredExtractionInput(BaseModel):
    entity_type: str
    entities: List[Dict[str, Any]]
    desired_fields: List[str] = Field(
        default=["name", "organization", "email", "role_or_title", "domain_or_department", "source_url"],
        description="Fields required to be extracted into standard form"
    )


class ExtractedRecord(BaseModel):
    entity_id: str
    fields: Dict[str, Any]
    extraction_confidence: float = 1.0


class StructuredExtractionOutput(BaseModel):
    entity_type: str
    records: List[ExtractedRecord]
    fields_extracted: List[str]
    total_extracted: int


# ------------------------------------------------------------------------------
# 3. Verification Schema
# ------------------------------------------------------------------------------
class VerificationInput(BaseModel):
    entity_type: str
    records: List[Dict[str, Any]]
    validation_rules: Dict[str, Any] = Field(
        default_factory=lambda: {
            "require_email": True,
            "check_syntax": True,
            "require_evidence_url": True,
            "minimum_confidence": 0.60
        }
    )


class VerifiedEntity(BaseModel):
    entity_id: str
    is_valid: bool
    confidence_score: float = Field(..., ge=0.0, le=1.0)
    confidence_tier: str = Field(..., description="HIGH, MEDIUM, LOW")
    validation_flags: List[str] = Field(default_factory=list)
    verified_data: Dict[str, Any]


class VerificationOutput(BaseModel):
    entity_type: str
    verified_entities: List[VerifiedEntity]
    pass_count: int
    flagged_count: int


# ------------------------------------------------------------------------------
# 4. Deduplication Schema
# ------------------------------------------------------------------------------
class DeduplicationInput(BaseModel):
    entity_type: str
    entities: List[Dict[str, Any]]
    identity_fields: List[str] = Field(
        default=["organization", "name"],
        description="Fields used to construct the immutable deterministic key"
    )


class DeduplicatedOutput(BaseModel):
    entity_type: str
    unique_entities: List[Dict[str, Any]]
    duplicates_detected: int
    dedup_keys: List[str]


# ------------------------------------------------------------------------------
# 5. Constrained Personalization Schema
# ------------------------------------------------------------------------------
class PersonalizationInput(BaseModel):
    entity_type: str
    target_entity: Dict[str, Any]
    sender_profile: Dict[str, Any] = Field(
        description="Substantiated sender information (name, degree, institution, verified projects)"
    )
    constraints: Dict[str, Any] = Field(
        default_factory=lambda: {
            "min_words": 130,
            "max_words": 180,
            "forbidden_terms": ["github.com", "linkedin.com"],
            "purpose": "Summer Research"
        }
    )


class PersonalizationOutput(BaseModel):
    entity_id: str
    subject: str
    body_text: str
    word_count: int
    grounded_facts: List[str]
    passed_quality_gates: bool
    quality_gate_violations: List[str] = Field(default_factory=list)


# ------------------------------------------------------------------------------
# 6. Destination-Local Scheduling Schema
# ------------------------------------------------------------------------------
class SchedulingInput(BaseModel):
    entity_type: str
    target_entities: List[Dict[str, Any]]
    target_local_hour: int = Field(default=8, ge=0, le=23)
    target_local_minute: int = Field(default=0, ge=0, le=59)
    operator_timezone: str = Field(default="Asia/Kolkata")
    avoid_weekends: bool = True


class ScheduledEntityWindow(BaseModel):
    entity_id: str
    target_name: str
    organization: str
    timezone_iana: str
    target_local_time: str
    operator_dispatch_time: str
    is_dst: bool
    day_of_week: str


class SchedulingOutput(BaseModel):
    windows: List[ScheduledEntityWindow]
    operator_timezone: str
    total_scheduled: int


# ------------------------------------------------------------------------------
# 7. Human Approval Gateway Schema
# ------------------------------------------------------------------------------
class ApprovalGatewayInput(BaseModel):
    action_type: str = Field(default="DISPATCH_OUTREACH")
    payload: Dict[str, Any]
    operator_session_token: Optional[str] = None
    content_hash: Optional[str] = None
    dry_run: bool = True


class ApprovalGatewayOutput(BaseModel):
    allowed: bool
    execution_status: str
    dry_run: bool
    message: str
    verified_hash: Optional[str] = None
