"""
Tests for Workstream A: Evidence Integrity, Field-Level Evidence Metadata, and Regression Tests.
Verifies calibrated confidence semantics, distinction of supported vs derived vs inferred vs unknown,
and prevention of fabricated or unsupported claims.
"""

import pytest
from backend.iol.capabilities.base import ExecutionContext
from backend.iol.capabilities.live_research import (
    GeneralizedVerificationCapability,
)
from backend.iol.core.research_models import (
    FieldEvidence,
    GeneralizedVerificationInput,
    VerifiedRecord,
)


@pytest.mark.asyncio
async def test_field_evidence_schema_and_serialization():
    """Verify FieldEvidence structure has all required metadata fields and validates status types."""
    fe = FieldEvidence(
        field_name="official_website",
        field_value="https://vllm.ai",
        evidence_url="https://vllm.ai",
        source_type="OFFICIAL_WEBSITE",
        relevant_excerpt="High-throughput LLM serving library",
        verification_method="URL_FORMAT_AND_FETCH_CHECK",
        verification_status="DIRECTLY_SUPPORTED",
        confidence=0.85,
    )
    dumped = fe.model_dump()
    assert dumped["field_name"] == "official_website"
    assert dumped["source_type"] == "OFFICIAL_WEBSITE"
    assert dumped["verification_status"] == "DIRECTLY_SUPPORTED"
    assert dumped["confidence"] == 0.85
    assert dumped["retrieval_timestamp"] is not None


@pytest.mark.asyncio
async def test_academic_rank_unverified_flagging():
    """Verify faculty rank is distinguished from researcher identity."""
    cap = GeneralizedVerificationCapability()
    ctx = ExecutionContext(task_id="t_ev_rank", step_id="s_ev_rank")

    # Author without explicit faculty chair or professor title in raw metadata
    params = GeneralizedVerificationInput(
        entity_type="professor",
        records=[
            {
                "name": "Jane Doe",
                "institution": "MIT",
                "research_interests": "Robotics & Embodied AI",
                "official_profile_url": "https://openalex.org/A123456789",
                "evidence": "Author: Jane Doe, Affiliation: MIT. Publication: 'Embodied Learning' (2025).",
                "_raw_metadata": {
                    "author_name": "Jane Doe",
                    "institution": "MIT",
                    "is_explicit_faculty": False,
                },
                "_source_url": "https://openalex.org/A123456789",
            }
        ],
        requested_fields=["name", "institution", "research_interests", "official_profile_url", "evidence"],
    )

    res = await cap.execute(params, ctx)
    assert res.success is True
    rec = res.data["verified_records"][0]

    # Must flag unverified faculty status
    assert "ACADEMIC_RANK_UNVERIFIED" in rec["validation_flags"]
    assert rec["entity_classification"] == "Academic Researcher (Faculty Rank Unverified)"


@pytest.mark.asyncio
async def test_bibliographic_vs_institutional_url_distinction():
    """Verify that OpenAlex/DOI profile links are classified as bibliographic, not institutional."""
    cap = GeneralizedVerificationCapability()
    ctx = ExecutionContext(task_id="t_ev_url", step_id="s_ev_url")

    params = GeneralizedVerificationInput(
        entity_type="professor",
        records=[
            {
                "name": "Prof. Marco Pavone",
                "institution": "Stanford University",
                "research_interests": "Autonomous Systems",
                "official_profile_url": "https://openalex.org/A987654321",
                "evidence": "Author: Prof. Marco Pavone, Affiliation: Stanford University.",
                "_raw_metadata": {
                    "author_name": "Prof. Marco Pavone",
                    "institution": "Stanford University",
                    "is_explicit_faculty": True,
                },
                "_source_url": "https://openalex.org/A987654321",
            },
            {
                "name": "Prof. Marco Pavone",
                "institution": "Stanford University",
                "research_interests": "Autonomous Systems",
                "official_profile_url": "https://asl.stanford.edu/people/marco-pavone",
                "evidence": "Author: Prof. Marco Pavone, Affiliation: Stanford University.",
                "_raw_metadata": {
                    "author_name": "Prof. Marco Pavone",
                    "institution": "Stanford University",
                    "is_explicit_faculty": True,
                },
                "_source_url": "https://asl.stanford.edu",
            },
        ],
        requested_fields=["name", "institution", "official_profile_url"],
    )

    res = await cap.execute(params, ctx)
    records = res.data["verified_records"]

    # Record 0: OpenAlex profile -> INFERRED & flagged
    rec0_fe = records[0]["field_evidence"]["official_profile_url"]
    assert rec0_fe["source_type"] == "BIBLIOGRAPHIC_PROFILE"
    assert rec0_fe["verification_status"] == "INFERRED"
    assert "PROFILE_IS_BIBLIOGRAPHIC_NOT_INSTITUTIONAL" in records[0]["validation_flags"]

    # Record 1: .edu profile -> DIRECTLY_SUPPORTED
    rec1_fe = records[1]["field_evidence"]["official_profile_url"]
    assert rec1_fe["source_type"] == "OFFICIAL_WEBSITE"
    assert rec1_fe["verification_status"] == "DIRECTLY_SUPPORTED"
    assert "PROFILE_IS_BIBLIOGRAPHIC_NOT_INSTITUTIONAL" not in records[1]["validation_flags"]


@pytest.mark.asyncio
async def test_india_connection_verification_and_fallback():
    """Verify startup India location is verified separately from search query fallback."""
    cap = GeneralizedVerificationCapability()
    ctx = ExecutionContext(task_id="t_ev_india", step_id="s_ev_india")

    params = GeneralizedVerificationInput(
        entity_type="startup",
        records=[
            {
                "company_name": "Krutrim SI Designs",
                "product_focus": "Indic LLMs and AI Compute Infrastructure",
                "official_website": "https://krutrim.com",
                "location": "Bengaluru, India",
                "evidence": "Company: Krutrim (Location: Bengaluru, India). Website: https://krutrim.com.",
                "_raw_metadata": {
                    "company_name": "Krutrim SI Designs",
                    "location": "Bengaluru, India",
                    "is_india_verified": True,
                },
                "_source_url": "https://krutrim.com",
            },
            {
                "company_name": "Global AI Lab",
                "product_focus": "General AI Models",
                "official_website": "https://globalai.io",
                "location": "India",
                "evidence": "Company: Global AI Lab. Inferred from search query.",
                "_raw_metadata": {
                    "company_name": "Global AI Lab",
                    "location": None,
                    "is_india_verified": False,
                },
                "_source_url": "https://globalai.io",
            },
        ],
        requested_fields=["company_name", "product_focus", "location", "official_website"],
    )

    res = await cap.execute(params, ctx)
    records = res.data["verified_records"]

    # Record 0: Explicit India profile
    assert records[0]["entity_classification"] == "Verified Indian AI Startup"
    assert records[0]["field_evidence"]["location"]["verification_status"] == "DIRECTLY_SUPPORTED"

    # Record 1: Uncorroborated location -> Inferred
    assert records[1]["entity_classification"] == "AI Tech Organization (India Inferred)"
    assert records[1]["field_evidence"]["location"]["verification_status"] == "INFERRED"
    assert "LOCATION_INFERRED_FROM_QUERY" in records[1]["validation_flags"]


@pytest.mark.asyncio
async def test_preservation_of_unknown_and_missing_values():
    """Verify missing values are not defaulted to generic placeholders and are marked UNKNOWN."""
    cap = GeneralizedVerificationCapability()
    ctx = ExecutionContext(task_id="t_ev_missing", step_id="s_ev_missing")

    params = GeneralizedVerificationInput(
        entity_type="professor",
        records=[
            {
                "name": "Dr. Alex Rivera",
                "institution": None,  # Unlisted affiliation
                "research_interests": "Reinforcement Learning",
                "official_profile_url": "https://alexrivera.ai",
                "evidence": "Author: Dr. Alex Rivera, Affiliation: Unlisted.",
                "_raw_metadata": {"author_name": "Dr. Alex Rivera", "institution": None},
                "_source_url": "https://alexrivera.ai",
            }
        ],
        requested_fields=["name", "institution", "research_interests", "official_profile_url"],
    )

    res = await cap.execute(params, ctx)
    rec = res.data["verified_records"][0]

    # Institution must remain None and have UNKNOWN verification status
    inst_fe = rec["field_evidence"]["institution"]
    assert inst_fe["field_value"] is None
    assert inst_fe["verification_status"] == "UNKNOWN"
    assert inst_fe["confidence"] == 0.0
    assert "MISSING_FIELD_INSTITUTION" in rec["validation_flags"]


@pytest.mark.asyncio
async def test_confidence_capping_and_unsupported_rejection():
    """Verify confidence is never 1.00 and records with missing critical identity are rejected."""
    cap = GeneralizedVerificationCapability()
    ctx = ExecutionContext(task_id="t_ev_cap", step_id="s_ev_cap")

    params = GeneralizedVerificationInput(
        entity_type="tool",
        records=[
            {
                "repository_name": "vllm-project/vllm",
                "primary_language": "Python",
                "license": "Apache-2.0",
                "official_repository_url": "https://github.com/vllm-project/vllm",
                "evidence": "Repository: vllm-project/vllm. Primary Language: Python. License: Apache-2.0.",
                "_raw_metadata": {"repository_name": "vllm-project/vllm"},
                "_source_url": "https://github.com/vllm-project/vllm",
            },
            {
                # Plausible-looking but invalid: missing critical repository_name
                "repository_name": "",
                "primary_language": "Python",
                "license": "MIT",
                "official_repository_url": "invalid-protocol-url",
                "evidence": "Short",
                "_raw_metadata": {},
                "_source_url": "",
            },
        ],
        requested_fields=["repository_name", "primary_language", "license", "official_repository_url"],
    )

    res = await cap.execute(params, ctx)
    records = res.data["verified_records"]

    # Record 0: Fully valid, but confidence capped at <= 0.88 (not 1.00)
    assert records[0]["is_valid"] is True
    assert records[0]["confidence_score"] <= 0.88
    assert records[0]["confidence_score"] > 0.70

    # Record 1: Invalid because critical identifier repository_name is missing
    assert records[1]["is_valid"] is False
    assert any("MISSING_FIELD_REPOSITORY_NAME" in f for f in records[1]["validation_flags"])
    assert "NO_VALID_HTTP_URL" in records[1]["validation_flags"]
