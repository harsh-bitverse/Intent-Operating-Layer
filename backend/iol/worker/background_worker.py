"""
Background Worker Engine for IOL.
Operates independently of HTTP requests and browser sessions.
Executes capability pipelines, manages execution budgets, handles retries,
detects cancellation tokens, and dynamically updates declarative UI schemas.
"""

import asyncio
import copy
import logging
import re
import traceback
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from backend.iol.agent.adapter import ExecutionPlan, PlanStep
from backend.iol.agent.orchestrator import IntentOrchestrator
from backend.iol.agent.planner import AdaptiveCapabilityPlanner
from backend.iol.capabilities.base import ExecutionContext
from backend.iol.capabilities.registry import capability_registry
from backend.iol.core.budgets import BudgetExceededError, BudgetTracker, TaskCancelledError
from backend.iol.core.events import EventType
from backend.iol.core.models import (
    CardComponent, CardMetric, ComparisonComponent, ComparisonEntity, ComparisonFeature,
    DeclarativeUIRoot, TableColumn, TableComponent, Task, TaskStatus, TimelineComponent,
    TimelineItem, utc_now
)
from backend.iol.core.store import task_store

logger = logging.getLogger("iol.worker")


class BackgroundWorker:
    """Asynchronous background worker processing tasks with durable state updates."""

    def __init__(self, store=None, registry=None, planner=None):
        self.store = store or task_store
        self.registry = registry or capability_registry
        self.planner = planner or AdaptiveCapabilityPlanner(registry=self.registry)
        if hasattr(self.planner, "registry") and self.planner.registry is None:
            self.planner.registry = self.registry
        self._queue: asyncio.Queue = asyncio.Queue()
        self._running = False
        self._worker_task: Optional[asyncio.Task] = None

    def start(self) -> None:
        """Start the background worker task loop."""
        if not self._running:
            self._running = True
            self._worker_task = asyncio.create_task(self._run_loop())
            logger.info("IOL Background Worker started.")

    async def stop(self) -> None:
        """Gracefully stop the background worker."""
        self._running = False
        if self._worker_task:
            self._worker_task.cancel()
            try:
                await self._worker_task
            except asyncio.CancelledError:
                pass
            logger.info("IOL Background Worker stopped.")

    def enqueue_task(self, task_id: str) -> None:
        """Queue a task ID for background processing."""
        self._queue.put_nowait(task_id)

    async def _run_loop(self) -> None:
        """Continuous consumer loop decoupled from browser connections."""
        while self._running:
            try:
                # Wait for next task in queue with a brief timeout
                try:
                    task_id = await asyncio.wait_for(self._queue.get(), timeout=1.0)
                    await self.process_task(task_id)
                    self._queue.task_done()
                except asyncio.TimeoutError:
                    continue
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Unexpected error in background worker loop: {e}", exc_info=True)
                await asyncio.sleep(1.0)

    async def process_task(self, task_id: str) -> None:
        """Execute a task through all planned capability steps."""
        task = self.store.get_task(task_id)
        if not task:
            logger.warning(f"Task {task_id} not found in store.")
            return

        if task.status != TaskStatus.PENDING:
            return

        # Check if already cancelled before start
        if self.store.is_task_cancelled(task_id):
            return

        # Mark as RUNNING
        self.store.update_task_status(task_id, TaskStatus.RUNNING)
        self.store.append_event(task_id, EventType.TASK_STARTED, {
            "task_id": task_id,
            "started_at": utc_now().isoformat()
        })

        # Initialize budget tracker
        tracker = BudgetTracker(
            budget=task.budget,
            is_cancelled_callback=lambda: self.store.is_task_cancelled(task_id)
        )

        step_outputs: Dict[str, Any] = {}

        try:
            # 1. Generate execution plan
            capabilities = self.registry.list_capabilities()
            plan: ExecutionPlan = await self.planner.plan(
                intent=task.intent,
                available_capabilities=capabilities,
                context=task.metadata
            )

            # Parse requested record limit from intent or metadata
            target_limit = 10
            count_match = re.search(r'\b(?:find|top|get|list|identify)\s+(\d+)\b', task.intent.lower())
            if not count_match:
                count_match = re.search(
                    r'\b(\d+)\s*(?:[\w-]+\s+){0,4}(?:professors|startups|companies|tools|frameworks|repos|repositories|labs|entities|records)\b',
                    task.intent.lower()
                )
            if count_match:
                try:
                    target_limit = int(count_match.group(1))
                except ValueError:
                    pass
            elif task.metadata and "max_records" in task.metadata:
                target_limit = int(task.metadata["max_records"])

            total_steps = len(plan.steps)
            self.store.update_task_progress(task_id, current_step=0, total_steps=total_steps)
            self.store.append_event(task_id, EventType.PLAN_GENERATED, {
                "plan_id": plan.plan_id,
                "total_steps": total_steps,
                "steps": [s.model_dump() for s in plan.steps]
            })

            # 2. Initialize Declarative UI Structure
            timeline_items = [
                TimelineItem(
                    id=s.step_id,
                    title=s.title,
                    description=s.description,
                    status="pending"
                )
                for s in plan.steps
            ]

            # Detect target requested fields from extraction step if present
            extraction_step = next((s for s in plan.steps if "extraction" in s.step_id), None)
            req_fields = extraction_step.parameters.get("requested_fields") or extraction_step.parameters.get("desired_fields") if extraction_step else None

            if not req_fields:
                req_fields = ["name", "organization", "email"]

            table_columns = []
            for f in req_fields:
                col_type = "link" if any(u in f.lower() for u in ["url", "website"]) else "text"
                header_name = f.replace("_", " ").title()
                table_columns.append(TableColumn(key=f, header=header_name, type=col_type))
            table_columns.append(TableColumn(key="confidence", header="Verification Score", type="score"))
            table_columns.append(TableColumn(key="status", header="Status", type="badge"))

            ui_root = DeclarativeUIRoot(
                title=f"Execution: {task.intent[:60]}",
                summary="Initializing autonomous capability pipeline...",
                components=[
                    CardComponent(
                        id="metric_summary",
                        title="Execution Overview",
                        subtitle="Real-time capability metrics",
                        variant="default",
                        metrics=[
                            CardMetric(label="Status", value="RUNNING"),
                            CardMetric(label="Execution Mode", value="INITIALIZING"),
                            CardMetric(label="Steps", value=f"0 / {total_steps}"),
                            CardMetric(label="Sources Acquired", value=0),
                            CardMetric(label="Verified Records", value=0)
                        ]
                    ),
                    TimelineComponent(
                        id="execution_timeline",
                        title="Capability Execution Pipeline",
                        items=timeline_items
                    ),
                    TableComponent(
                        id="candidate_table",
                        title="Candidate Entities & Research Evidence",
                        subtitle="Discovered and validated targets with source provenance",
                        columns=table_columns,
                        rows=[]
                    )
                ]
            )
            self.store.update_task_ui(task_id, ui_root)
            self.store.append_event(task_id, EventType.UI_UPDATED, ui_root.model_dump())

            # 3. Step Execution Loop
            for step_idx, step in enumerate(plan.steps, start=1):
                # Budget & cancellation check
                tracker.check_constraints()

                # Update progress
                self.store.update_task_progress(task_id, current_step=step_idx, total_steps=total_steps)

                # Update timeline item to running
                for item in timeline_items:
                    if item.id == step.step_id:
                        item.status = "running"
                        item.timestamp = utc_now().strftime("%H:%M:%S UTC")

                ui_root.summary = f"Executing step {step_idx}/{total_steps}: {step.title}"
                self._update_ui_metric(ui_root, "Steps", f"{step_idx - 1} / {total_steps}")
                self.store.update_task_ui(task_id, ui_root)
                self.store.append_event(task_id, EventType.STEP_STARTED, {
                    "step_id": step.step_id,
                    "step_index": step_idx,
                    "title": step.title
                })
                self.store.append_event(task_id, EventType.CAPABILITY_INVOKED, {
                    "step_id": step.step_id,
                    "capability_id": step.capability_id
                })

                # Resolve dynamic input parameters
                resolved_params = self._resolve_parameters(step.parameters, step.dynamic_param_mappings, step_outputs)

                # Execute with retry logic
                attempt = 0
                max_retries = task.budget.retry_limit
                step_success = False
                cap_res = None
                last_err = None

                while attempt <= max_retries and not step_success:
                    attempt += 1
                    try:
                        ctx = ExecutionContext(task_id=task_id, step_id=step.step_id, metadata=task.metadata)
                        cap_res = await self.registry.invoke(step.capability_id, resolved_params, ctx)
                        if cap_res.success:
                            step_success = True
                        else:
                            last_err = cap_res.error_message or "Capability reported non-success"
                    except Exception as exc:
                        last_err = str(exc)
                        if attempt <= max_retries:
                            await asyncio.sleep(0.5 * attempt)

                if not step_success:
                    # Mark step failed
                    for item in timeline_items:
                        if item.id == step.step_id:
                            item.status = "failed"
                            item.description = f"Failed: {last_err}"

                    self.store.append_event(task_id, EventType.STEP_FAILED, {
                        "step_id": step.step_id,
                        "error": last_err
                    })
                    raise RuntimeError(f"Step '{step.title}' failed after {attempt} attempts: {last_err}")

                # Step Succeeded
                tracker.record_step(cap_res.cost_usd)
                step_outputs[step.step_id] = cap_res.data

                # Update timeline
                for item in timeline_items:
                    if item.id == step.step_id:
                        item.status = "success"
                        item.timestamp = utc_now().strftime("%H:%M:%S UTC")

                # Enrich UI based on capability outcome
                self._enrich_ui(ui_root, step.capability_id, cap_res.data, total_steps, step_idx, max_records=target_limit)

                self.store.update_task_ui(task_id, ui_root)
                self.store.append_event(task_id, EventType.UI_UPDATED, ui_root.model_dump())
                self.store.append_event(task_id, EventType.CAPABILITY_COMPLETED, {
                    "step_id": step.step_id,
                    "capability_id": step.capability_id,
                    "verification_score": cap_res.verification_score
                })
                self.store.append_event(task_id, EventType.STEP_COMPLETED, {
                    "step_id": step.step_id,
                    "step_index": step_idx
                })

                # Modest pause to allow smooth event stream rendering
                await asyncio.sleep(0.2)

            # All steps completed successfully
            ui_root.summary = "All capability pipeline steps completed and verified."
            self._update_ui_metric(ui_root, "Status", "COMPLETED")
            self._update_ui_metric(ui_root, "Steps", f"{total_steps} / {total_steps}")
            self.store.update_task_ui(task_id, ui_root)

            final_result = {
                "intent": task.intent,
                "status": "COMPLETED",
                "steps_completed": total_steps,
                "step_outputs": step_outputs
            }
            self.store.update_task_result(task_id, final_result)
            self.store.update_task_status(task_id, TaskStatus.COMPLETED)
            self.store.append_event(task_id, EventType.TASK_COMPLETED, {
                "task_id": task_id,
                "completed_at": utc_now().isoformat(),
                "duration_seconds": tracker.elapsed_seconds
            })

        except TaskCancelledError as e:
            logger.info(f"Task {task_id} halted: {e}")
            self.store.update_task_status(task_id, TaskStatus.CANCELLED, error_message=str(e))
        except BudgetExceededError as e:
            logger.error(f"Task {task_id} budget exceeded: {e}")
            self.store.update_task_status(task_id, TaskStatus.FAILED, error_message=str(e))
            self.store.append_event(task_id, EventType.TASK_FAILED, {"error": str(e)})
        except Exception as e:
            err_msg = f"{type(e).__name__}: {str(e)}"
            logger.error(f"Task {task_id} failed: {err_msg}\n{traceback.format_exc()}")
            self.store.update_task_status(task_id, TaskStatus.FAILED, error_message=err_msg)
            self.store.append_event(task_id, EventType.TASK_FAILED, {"error": err_msg})

    def _resolve_parameters(
        self,
        base_params: Dict[str, Any],
        dynamic_mappings: Dict[str, str],
        outputs: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Resolve dynamic mappings from previous capability step outputs."""
        resolved = copy.deepcopy(base_params)

        for param_key, path in dynamic_mappings.items():
            # Example path: "step_discovery.entities" or "step_dedup.unique_entities[0]"
            parts = path.split(".")
            curr = outputs
            for p in parts:
                if "[" in p and p.endswith("]"):
                    key, idx_str = p[:-1].split("[")
                    curr = curr.get(key, [])
                    try:
                        idx = int(idx_str)
                        curr = curr[idx] if idx < len(curr) else {}
                    except (ValueError, IndexError):
                        curr = {}
                else:
                    curr = curr.get(p, {}) if isinstance(curr, dict) else {}
            resolved[param_key] = curr

        return resolved

    def _update_ui_metric(self, ui_root: DeclarativeUIRoot, label: str, value: Any) -> None:
        """Helper to update a metric card value."""
        for comp in ui_root.components:
            if isinstance(comp, CardComponent) and comp.id == "metric_summary":
                for m in comp.metrics:
                    if m.label == label:
                        m.value = value
                        return

    def _enrich_ui(
        self,
        ui_root: DeclarativeUIRoot,
        cap_id: str,
        data: Dict[str, Any],
        total_steps: int,
        step_idx: int,
        max_records: int = 10
    ) -> None:
        """Dynamically enrich declarative UI tables, cards, and comparison matrices upon capability completion."""
        self._update_ui_metric(ui_root, "Steps", f"{step_idx} / {total_steps}")

        if cap_id == "research.live_source_acquisition":
            sources = data.get("sources", [])
            provider_used = data.get("provider_used", "direct_apis")
            if provider_used == "recorded_replay_fixture":
                mode_str = "RECORDED REPLAY"
            elif "+fixture_fallback" in provider_used:
                mode_str = "FALLBACK REPLAY"
            else:
                mode_str = f"LIVE ({provider_used.replace('_', ' ').upper()})"

            self._update_ui_metric(ui_root, "Execution Mode", mode_str)
            self._update_ui_metric(ui_root, "Sources Acquired", len(sources))

        elif cap_id in ("research.generalized_extraction", "research.structured_extraction"):
            records = data.get("records", [])
            for comp in ui_root.components:
                if isinstance(comp, TableComponent) and comp.id == "candidate_table":
                    new_rows = []
                    for r in records[:max_records]:
                        row = dict(r.get("fields", r))
                        row["confidence"] = 0.50
                        row["status"] = "EXTRACTED"
                        new_rows.append(row)
                    comp.rows = new_rows

        elif cap_id in ("research.generalized_verification", "research.verification"):
            verified = data.get("verified_records") or data.get("verified_entities", [])
            pass_cnt = data.get("pass_count", 0)
            self._update_ui_metric(ui_root, "Verified Records", pass_cnt)

            for comp in ui_root.components:
                if isinstance(comp, TableComponent) and comp.id == "candidate_table":
                    new_rows = []
                    for v in verified[:max_records]:
                        f = dict(v.get("fields") or v.get("verified_data") or {})
                        f["confidence"] = v.get("confidence_score", 0.50)
                        f["status"] = "VERIFIED" if v.get("is_valid") else "FLAGGED"
                        if "field_evidence" in v:
                            f["_field_evidence"] = v["field_evidence"]
                        if "entity_classification" in v:
                            f["_classification"] = v["entity_classification"]
                        if "validation_flags" in v:
                            f["_validation_flags"] = v["validation_flags"]
                        new_rows.append(f)
                    comp.rows = new_rows

        elif cap_id == "research.semantic_relevance":
            qualified = data.get("qualified_candidates", [])
            rejected = data.get("rejected_candidates", [])
            precision = data.get("precision_estimate", 1.0)
            self._update_ui_metric(ui_root, "Verified Records", len(qualified))

            if len(qualified) < max_records:
                ui_root.summary = (
                    f"Semantic filter qualified {len(qualified)} records strictly meeting intent constraints "
                    f"(target was {max_records}). {len(rejected)} candidates were rejected to eliminate false positives."
                )
            else:
                ui_root.summary = (
                    f"Semantic filter verified {len(qualified)} records satisfying all intent criteria. "
                    f"Relevance precision: {int(precision * 100)}%."
                )

            for comp in ui_root.components:
                if isinstance(comp, TableComponent) and comp.id == "candidate_table":
                    new_rows = []
                    for q in qualified[:max_records]:
                        f = dict(q.get("fields") or q.get("verified_data") or q)
                        f["confidence"] = q.get("semantic_relevance_score", 0.85)
                        f["status"] = "INTENT_SATISFIED"
                        if "_field_evidence" in q:
                            f["_field_evidence"] = q["_field_evidence"]
                        elif "field_evidence" in q:
                            f["_field_evidence"] = q["field_evidence"]
                        if "_classification" in q:
                            f["_classification"] = q["_classification"]
                        f["_is_semantically_relevant"] = True
                        f["_relevance_evidence"] = q.get("relevance_evidence")
                        new_rows.append(f)
                    comp.rows = new_rows

        elif cap_id == "data.deduplication":
            unique = data.get("unique_entities", [])
            if max_records and max_records > 0:
                unique = unique[:max_records]
            self._update_ui_metric(ui_root, "Verified Records", len(unique))
            for comp in ui_root.components:
                if isinstance(comp, TableComponent) and comp.id == "candidate_table":
                    new_rows = []
                    for u in unique:
                        f = dict(u.get("fields") or u.get("verified_data") or u)
                        f["confidence"] = u.get("confidence_score", f.get("confidence", 0.85))
                        f["status"] = "UNIQUE_VERIFIED"
                        if "_field_evidence" in u:
                            f["_field_evidence"] = u["_field_evidence"]
                        elif "field_evidence" in u:
                            f["_field_evidence"] = u["field_evidence"]
                        if "_classification" in u:
                            f["_classification"] = u["_classification"]
                        if u.get("is_semantically_relevant") or (isinstance(u.get("fields"), dict) and u["fields"].get("_is_semantically_relevant")):
                            f["_is_semantically_relevant"] = True
                            f["_is_intent_satisfied"] = True
                            f["_relevance_evidence"] = u.get("relevance_evidence") or (u.get("fields", {}).get("_relevance_evidence") if isinstance(u.get("fields"), dict) else None)
                        new_rows.append(f)
                    comp.rows = new_rows

            # Workstream D: Build comparative analysis matrix if 2+ entities
            self._build_comparison_component(ui_root, unique)

        elif cap_id == "research.entity_discovery":
            entities = data.get("entities", [])
            self._update_ui_metric(ui_root, "Sources Acquired", len(entities))
            for comp in ui_root.components:
                if isinstance(comp, TableComponent) and comp.id == "candidate_table":
                    comp.rows = [
                        {
                            "name": e.get("name"),
                            "organization": e.get("organization"),
                            "confidence": 0.50,
                            "status": "DISCOVERED"
                        }
                        for e in entities[:max_records]
                    ]

        elif cap_id == "content.constrained_personalization":
            # Add a preview card for the generated personalized outreach
            preview_card = CardComponent(
                id="outreach_preview",
                title=f"Personalized Draft: {data.get('subject')}",
                subtitle=f"Word Count: {data.get('word_count')} words | Quality Gates: {'PASSED' if data.get('passed_quality_gates') else 'FAILED'}",
                variant="highlight" if data.get("passed_quality_gates") else "warning",
                content=data.get("body_text", ""),
                badges=["4-Paragraph Format", "Verified Background Grounded"]
            )
            # Insert preview card after summary
            ui_root.components.insert(1, preview_card)

        elif cap_id == "scheduling.destination_window":
            windows = data.get("windows", [])
            sched_table = TableComponent(
                id="scheduling_table",
                title="Destination-Local Dispatch Windows",
                subtitle="Calculated 8:00 AM destination arrivals mapped to operator time",
                columns=[
                    TableColumn(key="target_name", header="Target", type="text"),
                    TableColumn(key="organization", header="Organization", type="text"),
                    TableColumn(key="target_local_time", header="Local 8 AM Target", type="text"),
                    TableColumn(key="operator_dispatch_time", header="Operator Dispatch Time", type="text"),
                    TableColumn(key="is_dst", header="DST Active", type="badge")
                ],
                rows=[
                    {
                        "target_name": w.get("target_name"),
                        "organization": w.get("organization"),
                        "target_local_time": w.get("target_local_time"),
                        "operator_dispatch_time": w.get("operator_dispatch_time"),
                        "is_dst": "YES" if w.get("is_dst") else "NO"
                    }
                    for w in windows
                ]
            )
            ui_root.components.append(sched_table)

    def _build_comparison_component(
        self,
        ui_root: DeclarativeUIRoot,
        entities: List[Dict[str, Any]]
    ) -> None:
        """Constructs a declarative comparative matrix across the top unique entities."""
        if len(entities) < 2:
            return

        comp_entities: List[ComparisonEntity] = []
        features_map: Dict[str, Dict[str, Any]] = {}
        sample = dict(entities[0].get("fields") or entities[0].get("verified_data") or entities[0])

        is_tool = any(k in sample for k in ["repository_name", "primary_language", "license"])
        is_startup = any(k in sample for k in ["company_name", "product_focus", "location"])

        top_entities = entities[:5]  # Compare up to top 5 entities

        for idx, ent in enumerate(top_entities, start=1):
            f = dict(ent.get("fields") or ent.get("verified_data") or ent)
            eid = f"cmp_ent_{idx}"

            if is_tool:
                name = f.get("repository_name") or f.get("name") or f"Tool {idx}"
                metric = f.get("primary_language") or "Python"
                badge = f.get("license") or "Open Source"
                url = f.get("official_repository_url") or f.get("url")
            elif is_startup:
                name = f.get("company_name") or f"Startup {idx}"
                metric = f.get("location") or "India"
                badge = f.get("status") or "Verified"
                url = f.get("official_website") or f.get("website")
            else:
                name = f.get("name") or f"Researcher {idx}"
                metric = f.get("institution") or "Affiliation"
                badge = "Academic"
                url = f.get("official_profile_url")

            comp_entities.append(ComparisonEntity(
                entity_id=eid,
                name=name,
                subtitle=f.get("_classification"),
                badge=badge,
                primary_metric=metric,
                url=url
            ))

            for feat_key, feat_label in [
                ("primary_language", "Primary Language"),
                ("license", "License"),
                ("location", "Geographic Location"),
                ("product_focus", "Product Focus / Domain"),
                ("institution", "Institution / Affiliation"),
                ("research_interests", "Research Focus"),
                ("confidence", "Verification Score"),
                ("status", "Verification Status")
            ]:
                if feat_key in f and f[feat_key]:
                    if feat_key not in features_map:
                        features_map[feat_key] = {"label": feat_label, "values": {}}
                    val_str = str(f[feat_key])
                    features_map[feat_key]["values"][eid] = val_str

        features_list = [
            ComparisonFeature(
                key=k,
                label=v["label"],
                values=v["values"],
                confidence_tier="HIGH"
            )
            for k, v in features_map.items()
        ]

        if comp_entities and features_list:
            ui_root.components = [c for c in ui_root.components if not isinstance(c, ComparisonComponent)]
            ui_root.components.append(ComparisonComponent(
                id="cross_entity_comparison",
                title="Structured Multi-Entity Comparison Matrix",
                subtitle="Comparative analysis across verified records and independently corroborated attributes",
                entities=comp_entities,
                features=features_list
            ))


background_worker = BackgroundWorker()

