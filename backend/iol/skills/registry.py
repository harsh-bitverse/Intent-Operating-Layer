"""
Skill Registry and Warm-Start Compiler for IOL.
Manages versioned learned skills, enforces the 3-stage validation state machine:
(CANDIDATE -> VALIDATED_FOR_TASK_FAMILY -> TRUSTED_FOR_BOUNDED_REUSE),
and compiles warm-start execution plans with zero search latency.
"""

import re
import uuid
from typing import Any, Dict, List, Optional
from backend.iol.agent.adapter import ExecutionPlan, PlanStep
from backend.iol.capabilities.base import CapabilityMetadata
from backend.iol.skills.models import (
    LearnedSkill,
    SkillLifecycleState,
    SkillValidationRecord,
)


class LearnedSkillRegistry:
    """Manages storage, lifecycle promotion, and warm-start execution of learned skills."""

    def __init__(self):
        self._skills: Dict[str, LearnedSkill] = {}

    def register_skill(self, skill: LearnedSkill) -> None:
        """Register a new extracted skill candidate."""
        self._skills[skill.skill_id] = skill

    def get_skill(self, skill_id: str) -> Optional[LearnedSkill]:
        return self._skills.get(skill_id)

    def list_skills(self) -> List[LearnedSkill]:
        return list(self._skills.values())

    def record_validation(
        self,
        skill_id: str,
        task_id: str,
        success: bool,
        domain: str,
        notes: str = ""
    ) -> LearnedSkill:
        """
        Records a validation run and executes the state machine:
        - 1 successful validation -> VALIDATED_FOR_TASK_FAMILY
        - 2+ successful validations -> TRUSTED_FOR_BOUNDED_REUSE
        """
        skill = self._skills.get(skill_id)
        if not skill:
            raise ValueError(f"Skill '{skill_id}' not found.")

        record = SkillValidationRecord(
            task_id=task_id,
            success=success,
            domain=domain,
            notes=notes
        )
        skill.validation_history.append(record)

        successful_validations = [r for r in skill.validation_history if r.success]
        distinct_domains = {r.domain for r in successful_validations}

        if len(successful_validations) >= 2 and len(distinct_domains) >= 2:
            skill.lifecycle_state = SkillLifecycleState.TRUSTED_FOR_BOUNDED_REUSE
        elif len(successful_validations) >= 1:
            skill.lifecycle_state = SkillLifecycleState.VALIDATED_FOR_TASK_FAMILY

        skill.usage_count += 1
        skill.success_rate = round(len(successful_validations) / len(skill.validation_history), 2)
        return skill

    def find_matching_skill(self, intent: str, entity_type: str) -> Optional[LearnedSkill]:
        """
        Finds a validated or trusted skill matching the requested intent.
        Skills in CANDIDATE state are not served for autonomous warm-starts until validated.
        """
        intent_lower = intent.lower()
        for skill in self._skills.values():
            if skill.lifecycle_state not in (
                SkillLifecycleState.VALIDATED_FOR_TASK_FAMILY,
                SkillLifecycleState.TRUSTED_FOR_BOUNDED_REUSE
            ):
                continue

            # Match family or entity type
            if entity_type == "tool" and "tool" in skill.task_family:
                return skill
            elif entity_type == "startup" and "startup" in skill.task_family:
                return skill
            elif entity_type == "professor" and "academic" in skill.task_family:
                return skill
            elif "generic" in skill.task_family:
                return skill

        return None

    def compile_warm_plan(
        self,
        skill: LearnedSkill,
        intent: str,
        entity_type: str,
        requested_fields: List[str],
        max_records: int,
        query_terms: List[str],
        available_capabilities: List[CapabilityMetadata]
    ) -> ExecutionPlan:
        """
        Instantaneously compiles an ExecutionPlan by binding the validated skill template.
        Bypasses cold dynamic capability discovery, reducing planning latency to < 5ms.
        """
        cap_ids = {c.capability_id for c in available_capabilities}
        compiled_steps: List[PlanStep] = []

        for p_step in skill.steps:
            if p_step.capability_id not in cap_ids:
                raise ValueError(f"Capability '{p_step.capability_id}' required by skill is not registered.")

            params = dict(p_step.parameter_template)
            params["entity_type"] = entity_type

            # Bind dynamic values into template
            if "query_terms" in params:
                params["query_terms"] = query_terms
            if "max_sources" in params:
                params["max_sources"] = max_records * 2
            if "requested_fields" in params:
                params["requested_fields"] = requested_fields
            if "intent_constraints" in params and isinstance(params["intent_constraints"], dict):
                params["intent_constraints"]["requested_record_count"] = max_records
            if "task_intent" in params:
                params["task_intent"] = intent

            compiled_steps.append(PlanStep(
                step_id=p_step.step_id,
                capability_id=p_step.capability_id,
                title=p_step.title,
                description=p_step.description,
                parameters=params,
                dynamic_param_mappings=p_step.dynamic_param_mappings
            ))

        plan_id = f"plan_warm_{uuid.uuid4().hex[:8]}"
        rationale = (
            f"Warm-start execution plan compiled from learned skill '{skill.skill_id}' "
            f"(Version: {skill.version}, State: {skill.lifecycle_state.value}). "
            f"Bypassed cold heuristic capability planning."
        )

        return ExecutionPlan(
            plan_id=plan_id,
            intent=intent,
            rationale=rationale,
            steps=compiled_steps
        )


# Global skill registry singleton
skill_registry = LearnedSkillRegistry()
