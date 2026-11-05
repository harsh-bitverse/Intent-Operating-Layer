"""
Intent Orchestrator and Capability Planner for IOL.
Interprets natural language intents and generates multi-step capability execution plans.
Handles dynamic variable piping from previous step outputs to subsequent step inputs.
"""

import re
import uuid
from typing import Any, Dict, List, Optional
from backend.iol.agent.adapter import BaseAgentAdapter, ExecutionPlan, PlanStep
from backend.iol.capabilities.base import CapabilityMetadata


class IntentOrchestrator(BaseAgentAdapter):
    """Deterministic, high-reliability agent planner mapping intent to capability pipelines."""

    async def plan(
        self,
        intent: str,
        available_capabilities: List[CapabilityMetadata],
        context: Optional[Dict[str, Any]] = None
    ) -> ExecutionPlan:
        intent_lower = intent.lower()
        cap_ids = {c.capability_id for c in available_capabilities}

        # Determine target entity type
        if "startup" in intent_lower or "founder" in intent_lower or "company" in intent_lower or "tech" in intent_lower and "professor" not in intent_lower:
            entity_type = "startup"
            org_label = "Tech Startups"
        else:
            entity_type = "faculty"
            org_label = "Top Universities"

        # Extract domain query terms
        query_terms = []
        if "ai" in intent_lower or "artificial intelligence" in intent_lower:
            query_terms.append("ai")
        if "sciml" in intent_lower or "neural process" in intent_lower or "physics" in intent_lower:
            query_terms.append("sciml")
        if "llm" in intent_lower or "inference" in intent_lower or "nlp" in intent_lower:
            query_terms.append("llm")
        if "robot" in intent_lower or "robotics" in intent_lower:
            query_terms.append("robotics")
        if not query_terms:
            query_terms = ["ai", "machine learning"]

        plan_id = f"plan_{uuid.uuid4().hex[:8]}"
        steps: List[PlanStep] = []

        # Step 1: Entity Discovery
        if "research.entity_discovery" in cap_ids:
            steps.append(PlanStep(
                step_id="step_discovery",
                capability_id="research.entity_discovery",
                title=f"Discover {entity_type.capitalize()} Candidates",
                description=f"Identify prospective {entity_type} leads matching terms {query_terms} from verified directories.",
                parameters={
                    "entity_type": entity_type,
                    "query_terms": query_terms,
                    "max_results": 5
                }
            ))

        # Step 2: Structured Field Extraction
        if "research.structured_extraction" in cap_ids:
            steps.append(PlanStep(
                step_id="step_extraction",
                capability_id="research.structured_extraction",
                title="Structured Field Extraction",
                description="Standardize candidate records into uniform schemas with contact and evidence URLs.",
                parameters={
                    "entity_type": entity_type,
                    "desired_fields": ["name", "organization", "email", "role_or_title", "domain_or_department", "source_url", "evidence_url"]
                },
                dynamic_param_mappings={"entities": "step_discovery.entities"}
            ))

        # Step 3: Verification & Quality Gate
        if "research.verification" in cap_ids:
            steps.append(PlanStep(
                step_id="step_verification",
                capability_id="research.verification",
                title="Verify Contacts and Evidence",
                description="Assert email syntax integrity, institutional affiliation, and evidence URL provenance.",
                parameters={
                    "entity_type": entity_type,
                    "validation_rules": {
                        "require_email": True,
                        "check_syntax": True,
                        "require_evidence_url": True,
                        "minimum_confidence": 0.60
                    }
                },
                dynamic_param_mappings={"records": "step_extraction.records"}
            ))

        # Step 4: Deduplication
        if "data.deduplication" in cap_ids:
            steps.append(PlanStep(
                step_id="step_dedup",
                capability_id="data.deduplication",
                title="Entity Deduplication & Key Hashing",
                description="Generate deterministic SHA-256 entity keys and prune redundant leads.",
                parameters={
                    "entity_type": entity_type,
                    "identity_fields": ["organization", "name"]
                },
                dynamic_param_mappings={"entities": "step_verification.verified_entities"}
            ))

        # Step 5: Constrained Personalization (if requested or default)
        if "content.constrained_personalization" in cap_ids and ("personaliz" in intent_lower or "outreach" in intent_lower or "draft" in intent_lower or "email" in intent_lower or True):
            steps.append(PlanStep(
                step_id="step_personalization",
                capability_id="content.constrained_personalization",
                title="Four-Paragraph Grounded Personalization",
                description="Draft structured, 130-180 word correspondence grounded in verified student research.",
                parameters={
                    "entity_type": entity_type,
                    "sender_profile": {
                        "name": "Harshith N",
                        "title": "Undergraduate, Department of Chemical Engineering",
                        "institution": "Indian Institute of Technology Delhi (IIT Delhi)",
                        "email": "ch1251635@iitd.ac.in",
                        "verified_projects": [
                            {"title": "Neural Process Twin", "summary": "Physics-aware SciML surrogate simulator in PyTorch"},
                            {"title": "LLM Inference Intelligence Engine", "summary": "Benchmarking platform profiling latency and memory saturation"}
                        ]
                    },
                    "constraints": {
                        "min_words": 100,
                        "max_words": 200,
                        "forbidden_terms": ["github.com", "linkedin.com"],
                        "purpose": "Summer Research"
                    }
                },
                dynamic_param_mappings={"target_entity": "step_dedup.unique_entities[0]"}
            ))

        # Step 6: Morning Window Destination Scheduling
        if "scheduling.destination_window" in cap_ids and ("schedule" in intent_lower or "window" in intent_lower or "timezone" in intent_lower or True):
            steps.append(PlanStep(
                step_id="step_scheduling",
                capability_id="scheduling.destination_window",
                title="Destination-Local Window Scheduling",
                description="Map target morning arrival (8:00 AM local) to operator timezone with DST calculations.",
                parameters={
                    "entity_type": entity_type,
                    "target_local_hour": 8,
                    "target_local_minute": 0,
                    "operator_timezone": "Asia/Kolkata",
                    "avoid_weekends": True
                },
                dynamic_param_mappings={"target_entities": "step_dedup.unique_entities"}
            ))

        # Step 7: Security Approval Gateway
        if "security.human_approval_gateway" in cap_ids:
            steps.append(PlanStep(
                step_id="step_approval",
                capability_id="security.human_approval_gateway",
                title="Cryptographic Human Approval Gate",
                description="Ensure live transmission remains strictly blocked and verified in safe dry-run mode.",
                parameters={
                    "action_type": "DISPATCH_OUTREACH",
                    "dry_run": True
                },
                dynamic_param_mappings={"payload": "step_personalization"}
            ))

        return ExecutionPlan(
            plan_id=plan_id,
            intent=intent,
            rationale=f"Constructed an end-to-end {entity_type} research & execution workflow with 7 verified capabilities.",
            steps=steps
        )
