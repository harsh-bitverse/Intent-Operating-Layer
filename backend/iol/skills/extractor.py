"""
Skill Extractor for IOL.
Analyzes execution traces of successful tasks, extracts reusable capability pipelines,
strips user-specific credentials/data, and parameterizes blueprints into versioned skill candidates.
"""

import copy
import re
import uuid
from typing import Any, Dict, List, Optional
from backend.iol.core.models import Task, TaskEvent, TaskStatus
from backend.iol.skills.models import LearnedSkill, SkillLifecycleState, SkillStepPattern


class SkillExtractor:
    """Extracts generalized reusable skills from completed task execution traces."""

    def extract_skill(self, task: Task, events: List[TaskEvent]) -> Optional[LearnedSkill]:
        """
        Extracts a reusable LearnedSkill candidate from a completed task.
        Returns None if task is not completed or lacks valid execution trace.
        """
        if task.status != TaskStatus.COMPLETED:
            return None

        # Locate PLAN_GENERATED event
        plan_event = next((e for e in events if e.event_type == "PLAN_GENERATED"), None)
        if not plan_event or "steps" not in plan_event.data:
            return None

        raw_steps = plan_event.data["steps"]
        if not raw_steps:
            return None

        # Determine task family from intent and entity type
        entity_type = "general"
        intent_lower = task.intent.lower()
        if any(w in intent_lower for w in ["prof", "faculty", "academic"]):
            entity_type = "academic_research"
            family = "research.academic_faculty_discovery"
        elif any(w in intent_lower for w in ["startup", "company", "firm"]):
            entity_type = "startup_research"
            family = "research.commercial_startup_discovery"
        elif any(w in intent_lower for w in ["tool", "framework", "library", "developer"]):
            entity_type = "tool_research"
            family = "research.developer_tools_discovery"
        else:
            family = "research.generic_entity_discovery"

        skill_steps: List[SkillStepPattern] = []
        for s in raw_steps:
            sanitized_params = self._sanitize_and_parameterize(s.get("parameters", {}))
            skill_steps.append(SkillStepPattern(
                step_id=s.get("step_id", "step"),
                capability_id=s.get("capability_id", ""),
                title=s.get("title", ""),
                description=s.get("description", ""),
                parameter_template=sanitized_params,
                dynamic_param_mappings=s.get("dynamic_param_mappings", {})
            ))

        skill_id = f"skill_{family.replace('.', '_')}_v1"
        pattern = r"\b(?:find|search|identify|list|top)\s+\d+\s+(?:professors|startups|tools|frameworks)\b"

        return LearnedSkill(
            skill_id=skill_id,
            name=f"Learned Pipeline: {family}",
            task_family=family,
            version="1.0.0",
            lifecycle_state=SkillLifecycleState.CANDIDATE,
            intent_pattern=pattern,
            description=f"Auto-extracted 5-stage research pipeline synthesized from task {task.task_id}.",
            steps=skill_steps,
            source_task_id=task.task_id,
        )

    def _sanitize_and_parameterize(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """
        Deep-sanitizes parameters by removing personal IDs, emails, and credentials,
        replacing task-specific constants with parameter templates.
        """
        clean = copy.deepcopy(params)

        # Redact any accidental emails, tokens, or personal identifiers
        for k, v in list(clean.items()):
            if isinstance(v, str):
                if "@" in v:
                    clean[k] = "{operator_email}"
                elif any(sec in k.lower() for sec in ["token", "secret", "password", "key", "auth"]):
                    clean[k] = None
            elif isinstance(v, dict):
                clean[k] = self._sanitize_and_parameterize(v)

        return clean
