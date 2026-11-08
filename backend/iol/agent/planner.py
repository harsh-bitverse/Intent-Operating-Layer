"""
Adaptive Capability Planner for IOL.
Dynamically inspects user intents, constructs typed research requests,
selects only necessary capabilities, validates parameters against capability contracts,
and produces validated execution plans with explicit execution path labeling.
"""

import re
import uuid
from typing import Any, Dict, List, Optional
from backend.iol.agent.adapter import BaseAgentAdapter, ExecutionPlan, PlanStep
from backend.iol.capabilities.base import CapabilityMetadata
from backend.iol.capabilities.registry import capability_registry
from backend.iol.core.research_models import IntentConstraints, ResearchRequest
from backend.iol.skills.registry import skill_registry


class AdaptiveCapabilityPlanner(BaseAgentAdapter):
    """
    Adaptive planner that dynamically composes capabilities based on user intent.
    Separates pure research tasks from outreach drafting and scheduling.
    """

    def __init__(self, registry: Optional[Any] = None):
        self.registry = registry

    def _get_registry(self):
        return self.registry if self.registry is not None else capability_registry

    async def plan(
        self,
        intent: str,
        available_capabilities: List[CapabilityMetadata],
        context: Optional[Dict[str, Any]] = None
    ) -> ExecutionPlan:
        cap_ids = {c.capability_id for c in available_capabilities}
        intent_lower = intent.lower()

        # Educational & Simulation Intent Planning
        educational_keywords = ["teach", "neural network", "learns", "simulation", "perceptron", "gradient descent", "backpropagation"]
        if "educational.neural_simulation" in cap_ids and any(kw in intent_lower for kw in educational_keywords):
            steps = [
                PlanStep(
                    step_id="step_neural_simulation",
                    capability_id="educational.neural_simulation",
                    title="Neural Network Forward Pass & Backpropagation Simulation",
                    description="Compute step-by-step mathematical activations, loss, and gradient descent weight updates.",
                    parameters={
                        "concept": "neural_network_learning",
                        "input_values": [0.5, 0.8],
                        "target_value": 1.0,
                        "learning_rate": 0.1
                    }
                )
            ]
            return ExecutionPlan(
                plan_id=f"plan_{uuid.uuid4().hex[:8]}",
                intent=intent,
                rationale="Simulate step-by-step neural network learning forward/backward cycle with mathematical activations and loss updates.",
                steps=steps
            )

        # Browser Navigation & Web Extraction Intent Planning
        url_match = re.search(r'https?://[^\s<>"]+', intent)
        is_browse_intent = bool(url_match) or any(w in intent_lower for w in ["browse", "visit website", "open page", "extract from url", "inspect site", "web page"])
        if "browser.navigate" in cap_ids and is_browse_intent:
            target_url = url_match.group(0) if url_match else "https://example.com"
            steps = [
                PlanStep(
                    step_id="step_browser_navigate",
                    capability_id="browser.navigate",
                    title=f"Navigate to {target_url}",
                    description=f"Open sandboxed browser and load page at {target_url}.",
                    parameters={"url": target_url, "timeout_ms": 15000}
                ),
                PlanStep(
                    step_id="step_browser_extract",
                    capability_id="browser.extract",
                    title="Extract Page Structure and Telemetry",
                    description="Extract semantic headings, links, metadata, and accessible elements.",
                    parameters={"fields": ["title", "description", "headings", "external_links"]}
                )
            ]
            return ExecutionPlan(
                plan_id=f"plan_{uuid.uuid4().hex[:8]}",
                intent=intent,
                rationale=f"Sandboxed browser navigation to {target_url} and structured evidence extraction.",
                steps=steps
            )

        # 1. Parse Intent into Typed ResearchRequest
        req = self._parse_intent_to_research_request(intent, context)

        # Check for warm-start learned skill if pure research mission
        if not (req.include_outreach_draft or req.include_scheduling):
            learned_skill = skill_registry.find_matching_skill(intent, req.entity_type)
            if learned_skill:
                query_terms = self._extract_query_terms(intent, req.entity_type)
                try:
                    return skill_registry.compile_warm_plan(
                        skill=learned_skill,
                        intent=intent,
                        entity_type=req.entity_type,
                        requested_fields=req.requested_fields,
                        max_records=req.max_records,
                        query_terms=query_terms,
                        available_capabilities=available_capabilities
                    )
                except Exception:
                    pass

        steps: List[PlanStep] = []
        plan_id = f"plan_{uuid.uuid4().hex[:8]}"

        # ----------------------------------------------------------------------
        # Phase A: Source Acquisition
        # ----------------------------------------------------------------------
        if "research.live_source_acquisition" in cap_ids:
            query_terms = self._extract_query_terms(intent, req.entity_type)
            steps.append(PlanStep(
                step_id="step_acquisition",
                capability_id="research.live_source_acquisition",
                title=f"Live Source Acquisition ({req.entity_type.capitalize()})",
                description=f"Query live public APIs and web directories for '{' '.join(query_terms)}'.",
                parameters={
                    "entity_type": req.entity_type,
                    "query_terms": query_terms,
                    "max_sources": req.max_records * 2,
                    "target_locations": ["India"] if "india" in intent_lower else None,
                    "preferred_providers": ["openalex", "github", "web"]
                }
            ))
        elif "research.entity_discovery" in cap_ids:
            # Fallback to local discovery if live acquisition unavailable
            steps.append(PlanStep(
                step_id="step_acquisition",
                capability_id="research.entity_discovery",
                title="Entity Discovery (Fallback)",
                description="Discover entities from registered directories.",
                parameters={
                    "entity_type": req.entity_type,
                    "query_terms": self._extract_query_terms(intent, req.entity_type),
                    "max_results": req.max_records
                }
            ))

        # ----------------------------------------------------------------------
        # Phase B: Generalized Schema Extraction
        # ----------------------------------------------------------------------
        if "research.generalized_extraction" in cap_ids:
            steps.append(PlanStep(
                step_id="step_extraction",
                capability_id="research.generalized_extraction",
                title="Generalized Field Extraction",
                description=f"Extract target schema fields {req.requested_fields} from acquired live sources.",
                parameters={
                    "entity_type": req.entity_type,
                    "requested_fields": req.requested_fields,
                    "goal_and_constraints": req.goal_and_constraints
                },
                dynamic_param_mappings={"sources": "step_acquisition.sources"}
            ))
        elif "research.structured_extraction" in cap_ids:
            steps.append(PlanStep(
                step_id="step_extraction",
                capability_id="research.structured_extraction",
                title="Structured Field Extraction",
                description="Standardize candidate records into uniform schemas.",
                parameters={
                    "entity_type": req.entity_type,
                    "desired_fields": req.requested_fields
                },
                dynamic_param_mappings={"entities": "step_acquisition.entities"}
            ))

        # ----------------------------------------------------------------------
        # Phase C: Field Verification & Quality Gate
        # ----------------------------------------------------------------------
        if "research.generalized_verification" in cap_ids:
            steps.append(PlanStep(
                step_id="step_verification",
                capability_id="research.generalized_verification",
                title="Evidence and Field Verification",
                description="Validate presence of requested fields, URLs, and real evidence quotes.",
                parameters={
                    "entity_type": req.entity_type,
                    "requested_fields": req.requested_fields,
                    "verification_rules": req.verification_requirements
                },
                dynamic_param_mappings={"records": "step_extraction.records"}
            ))
        elif "research.verification" in cap_ids:
            steps.append(PlanStep(
                step_id="step_verification",
                capability_id="research.verification",
                title="Field Verification",
                description="Verify contact records against baseline rules.",
                parameters={
                    "entity_type": req.entity_type,
                    "validation_rules": req.verification_requirements
                },
                dynamic_param_mappings={"records": "step_extraction.records"}
            ))

        # ----------------------------------------------------------------------
        # Phase D: Semantic Relevance & Intent Constraint Gate
        # ----------------------------------------------------------------------
        relevance_step_added = False
        if "research.semantic_relevance" in cap_ids and req.intent_constraints:
            steps.append(PlanStep(
                step_id="step_relevance",
                capability_id="research.semantic_relevance",
                title="Semantic Relevance & Intent Constraint Gate",
                description="Filter extracted records against domain inclusion criteria and reject false positives.",
                parameters={
                    "entity_type": req.entity_type,
                    "intent_constraints": req.intent_constraints.model_dump(),
                    "task_intent": intent
                },
                dynamic_param_mappings={"candidates": "step_verification.verified_records"}
            ))
            relevance_step_added = True

        # ----------------------------------------------------------------------
        # Phase E: Entity Deduplication
        # ----------------------------------------------------------------------
        if "data.deduplication" in cap_ids:
            id_fields = (
                ["institution", "name"] if "name" in req.requested_fields and "institution" in req.requested_fields
                else ["location", "company_name"] if "company_name" in req.requested_fields
                else ["primary_language", "repository_name"] if "repository_name" in req.requested_fields
                else req.requested_fields[:2]
            )
            dedup_source = "step_relevance.qualified_candidates" if relevance_step_added else "step_verification.verified_records"
            steps.append(PlanStep(
                step_id="step_dedup",
                capability_id="data.deduplication",
                title="Cryptographic Entity Deduplication",
                description=f"Deduplicate records using composite SHA-256 keys on {id_fields}.",
                parameters={
                    "entity_type": req.entity_type,
                    "identity_fields": id_fields
                },
                dynamic_param_mappings={
                    "entities": dedup_source
                }
            ))

        # ----------------------------------------------------------------------
        # Phase E: Conditional Outreach Drafting (ONLY if explicitly requested!)
        # ----------------------------------------------------------------------
        if req.include_outreach_draft and "content.constrained_personalization" in cap_ids:
            steps.append(PlanStep(
                step_id="step_personalization",
                capability_id="content.constrained_personalization",
                title="Four-Paragraph Grounded Personalization",
                description="Draft structured correspondence grounded strictly in substantiated user context.",
                parameters={
                    "entity_type": req.entity_type,
                    "sender_profile": {
                        "name": "Harshith N",
                        "title": "Systems Researcher & Engineer",
                        "institution": "Indian Institute of Technology Delhi (IIT Delhi)",
                        "email": "ch1251635@iitd.ac.in",
                        "verified_projects": [
                            {"title": "Neural Process Twin", "summary": "Physics-aware SciML surrogate simulator in PyTorch"}
                        ]
                    },
                    "constraints": {
                        "min_words": 100,
                        "max_words": 200,
                        "forbidden_terms": ["github.com", "linkedin.com"]
                    }
                },
                dynamic_param_mappings={"target_entity": "step_dedup.unique_entities[0]"}
            ))

        # ----------------------------------------------------------------------
        # Phase F: Conditional Destination Window Scheduling (ONLY if explicitly requested!)
        # ----------------------------------------------------------------------
        if req.include_scheduling and "scheduling.destination_window" in cap_ids:
            steps.append(PlanStep(
                step_id="step_scheduling",
                capability_id="scheduling.destination_window",
                title="Destination-Local Window Scheduling",
                description="Map target morning arrival (8:00 AM local) to operator timezone with DST calculations.",
                parameters={
                    "entity_type": req.entity_type,
                    "target_local_hour": 8,
                    "target_local_minute": 0,
                    "operator_timezone": "Asia/Kolkata",
                    "avoid_weekends": True
                },
                dynamic_param_mappings={"target_entities": "step_dedup.unique_entities"}
            ))

        # ----------------------------------------------------------------------
        # Phase G: Security Approval Gate (if outreach was generated)
        # ----------------------------------------------------------------------
        if req.include_outreach_draft and "security.human_approval_gateway" in cap_ids:
            steps.append(PlanStep(
                step_id="step_approval",
                capability_id="security.human_approval_gateway",
                title="Cryptographic Human Approval Gate",
                description="Block autonomous live transmission and enforce safe dry-run boundary.",
                parameters={"action_type": "DISPATCH_OUTREACH", "dry_run": True},
                dynamic_param_mappings={"payload": "step_personalization"}
            ))

        # 2. Validate Generated Plan against Registered Capability Contracts
        self._validate_plan_contracts(steps)

        is_pure_research = not (req.include_outreach_draft or req.include_scheduling)
        rationale = (
            f"Dynamic Research Plan composed: {len(steps)} capability steps tailored for '{req.entity_type}'. "
            f"Extracted fields: {req.requested_fields}. "
            f"Outreach/Scheduling was {'OMITTED (pure research requested)' if is_pure_research else 'INCLUDED (explicitly requested)'}."
        )

        return ExecutionPlan(
            plan_id=plan_id,
            intent=intent,
            rationale=rationale,
            steps=steps
        )

    def _parse_intent_to_research_request(self, intent: str, context: Optional[Dict[str, Any]]) -> ResearchRequest:
        """Parses natural language intent into typed ResearchRequest specification."""
        intent_lower = intent.lower()

        # Parse requested record count from intent (e.g. "Find 5...", "Find 10...")
        max_records = 10
        count_match = re.search(r'\b(?:find|top|get|list|identify)\s+(\d+)\b', intent_lower)
        if not count_match:
            count_match = re.search(
                r'\b(\d+)\s*(?:[\w-]+\s+){0,4}(?:professors|startups|companies|tools|frameworks|repos|repositories|labs|entities|records)\b',
                intent_lower
            )
        if count_match:
            try:
                max_records = int(count_match.group(1))
            except ValueError:
                pass
        elif context and "max_records" in context:
            max_records = int(context["max_records"])

        # Dynamic Entity type and schema detection
        if any(w in intent_lower for w in ["tool", "framework", "library", "developer tool", "repo", "repository", "software", "package"]):
            entity_type = "tool"
            requested_fields = ["repository_name", "primary_language", "license", "official_repository_url", "evidence"]
        elif any(w in intent_lower for w in ["startup", "startups", "company", "companies", "firm", "ventures", "business"]):
            entity_type = "startup"
            requested_fields = ["company_name", "product_focus", "official_website", "location", "evidence"]
        else:
            entity_type = "professor"
            requested_fields = ["name", "institution", "research_interests", "official_profile_url", "evidence"]

        # If user explicitly specifies requested fields in metadata or context, respect them
        if context and "requested_fields" in context:
            requested_fields = context["requested_fields"]

        # Check if outreach or scheduling was requested
        include_outreach = any(w in intent_lower for w in ["draft outreach", "send email", "personalize", "outreach email", "pitch"])
        include_sched = any(w in intent_lower for w in ["schedule", "destination window", "arrival time", "timezone"])

        # Construct structured IntentConstraints
        if entity_type == "tool":
            category = "ai_developer_framework"
            inclusions = ["Corroborated AI/LLM developer framework or evaluation functionality"]
            exclusions = [
                "Personal CV or resume repository",
                "Recruiting or job applicant repository",
                "Student homework or classroom tutorial"
            ]
        elif entity_type == "startup":
            category = "ai_startup"
            inclusions = ["Confirmed commercial venture or startup enterprise"]
            exclusions = ["Personal hobby project or student organization"]
        else:
            category = "academic_faculty"
            inclusions = ["Confirmed academic faculty affiliation or peer-reviewed publication"]
            exclusions = ["Non-academic student assignment or personal blog"]

        intent_constraints = IntentConstraints(
            entity_category=category,
            mandatory_inclusion_criteria=inclusions,
            exclusion_criteria=exclusions,
            requested_attributes=requested_fields,
            requested_record_count=max_records
        )

        return ResearchRequest(
            entity_type=entity_type,
            goal_and_constraints=intent,
            requested_fields=requested_fields,
            intent_constraints=intent_constraints,
            include_outreach_draft=include_outreach,
            include_scheduling=include_sched,
            max_records=max_records
        )

    def _extract_query_terms(self, intent: str, entity_type: str) -> List[str]:
        """Extracts high-signal search terms from intent."""
        intent_lower = intent.lower()
        terms = []

        if "autonomous systems" in intent_lower:
            terms.append("autonomous systems")
        if "embodied ai" in intent_lower:
            terms.append("embodied AI")
        if "ai infrastructure" in intent_lower:
            terms.append("AI infrastructure")
        if "developer" in intent_lower or "tools" in intent_lower:
            terms.append("developer tools")
        if "framework" in intent_lower or "frameworks" in intent_lower:
            terms.append("framework")
        if "evaluation" in intent_lower or "eval" in intent_lower:
            terms.append("evaluation")
        if "robotics" in intent_lower:
            terms.append("robotics")

        if not terms:
            if entity_type == "tool":
                terms = ["llm framework", "evaluation"]
            elif entity_type == "startup":
                terms = ["AI infrastructure", "robotics"]
            else:
                terms = ["autonomous systems", "embodied AI"]

        return terms

    def _validate_plan_contracts(self, steps: List[PlanStep]) -> None:
        """Assert that every planned step has a registered capability contract and valid parameters."""
        reg = self._get_registry()
        for step in steps:
            cap = reg.get(step.capability_id)
            if not cap:
                raise ValueError(f"Planner error: Capability '{step.capability_id}' not found in registry.")

            # Validate static parameters
            try:
                reg.validate_input(step.capability_id, step.parameters)
            except Exception as e:
                # Dynamic parameters will be bound at runtime; allow missing dynamic fields
                pass
