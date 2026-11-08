"""
Experience Recipe Store and Catalog for IOL v0.6.
Stores reusable presentation recipes for various intent families,
enabling zero-shot adaptation of visual workspaces for similar tasks.
"""

import copy
import uuid
from typing import Any, Dict, List, Optional
from backend.iol.experience.models import ExperienceComponent, ExperienceMode, ExperiencePlan, ExperienceRecipe


class ExperienceRecipeStore:
    """In-memory catalog of reusable experience recipes with matching and adaptation logic."""

    def __init__(self):
        self._recipes: Dict[str, ExperienceRecipe] = {}
        self._seed_default_recipes()

    def register_recipe(self, recipe: ExperienceRecipe) -> None:
        """Register a new experience recipe."""
        self._recipes[recipe.recipe_id] = recipe

    def get_recipe(self, recipe_id: str) -> Optional[ExperienceRecipe]:
        """Fetch recipe by ID."""
        return self._recipes.get(recipe_id)

    def list_recipes(self) -> List[ExperienceRecipe]:
        """Return all registered recipes."""
        return list(self._recipes.values())

    def find_matching_recipe(self, intent: str, entity_type: Optional[str] = None) -> ExperienceRecipe:
        """
        Match an intent to the best reusable ExperienceRecipe.
        Uses intent keywords and entity_type classification.
        """
        intent_lower = intent.lower()

        # 1. Educational simulation matching
        educational_keywords = [
            "teach", "explain", "how a", "learns", "neural network", "simulation",
            "interactive visualization", "step by step", "deep learning", "gradient descent",
            "backpropagation", "neuron", "activation"
        ]
        if any(kw in intent_lower for kw in educational_keywords) or (entity_type and "educational" in entity_type.lower()):
            recipe = self.get_recipe("exp_recipe_educational_simulation")
            if recipe:
                return recipe

        # 2. Comparison analysis matching
        comparison_keywords = ["compare", "versus", "vs", "benchmark", "difference between", "comparison"]
        if any(kw in intent_lower for kw in comparison_keywords) or (entity_type and "comparison" in entity_type.lower()):
            recipe = self.get_recipe("exp_recipe_comparison_analysis")
            if recipe:
                return recipe

        # 3. Browser extraction matching
        if "http://" in intent_lower or "https://" in intent_lower or any(kw in intent_lower for kw in ["browse", "website", "web page", "extract from", "visit"]):
            recipe = self.get_recipe("exp_recipe_browser_extraction")
            if recipe:
                return recipe

        # 4. Form drafting matching
        if any(kw in intent_lower for kw in ["form", "apply", "application", "passport", "visa", "license", "draft form"]):
            recipe = self.get_recipe("exp_recipe_form_draft")
            if recipe:
                return recipe

        # 5. Default: Research Workspace Database recipe
        return self._recipes.get("exp_recipe_research_database") or list(self._recipes.values())[0]

    def adapt_recipe_to_plan(
        self,
        recipe: ExperienceRecipe,
        task_id: str,
        intent: str,
        entity_type: Optional[str] = None,
        custom_columns: Optional[List[Dict[str, Any]]] = None
    ) -> ExperiencePlan:
        """
        Instantiate and adapt a recipe into a concrete ExperiencePlan for a specific task.
        """
        plan_id = f"exp_{uuid.uuid4().hex[:8]}"

        # Derive title and subtitle from intent
        title = recipe.name
        if "teach" in intent.lower() or "neural" in intent.lower():
            title = "Interactive Neural Network Visualizer"
            subtitle = intent
        elif "startup" in intent.lower():
            title = "AI Infrastructure Startups Research Workspace"
            subtitle = intent
        elif "professor" in intent.lower() or "researcher" in intent.lower():
            title = "Faculty & Research Intelligence Workspace"
            subtitle = intent
        else:
            title = f"{entity_type.capitalize() if entity_type else 'Task'} Workspace"
            subtitle = intent

        # Deep copy components so recipes remain immutable templates
        components_data = copy.deepcopy(recipe.default_components)
        components: List[ExperienceComponent] = []

        for comp_dict in components_data:
            # Dynamic adaptation of data_grid columns if provided
            if comp_dict.get("type") == "data_grid" and custom_columns:
                comp_dict["props"]["columns"] = custom_columns
                if entity_type:
                    comp_dict["props"]["title"] = f"Verified {entity_type.replace('_', ' ').capitalize()} Directory"

            components.append(ExperienceComponent(**comp_dict))

        return ExperiencePlan(
            plan_id=plan_id,
            task_id=task_id,
            mode=recipe.layout_mode,
            title=title,
            subtitle=subtitle,
            status="ACTIVE",
            components=components,
            metadata={
                "recipe_id": recipe.recipe_id,
                "recipe_name": recipe.name,
                "target_intent_family": recipe.target_intent_family,
                "data_binding_slots": recipe.data_binding_slots
            }
        )

    def _seed_default_recipes(self) -> None:
        """Seed the built-in foundational experience recipes."""

        # Recipe 1: Research Database Workspace
        self.register_recipe(
            ExperienceRecipe(
                recipe_id="exp_recipe_research_database",
                name="Autonomous Research Workspace",
                target_intent_family="research_database",
                description="Full-screen adaptive workspace for structured intelligence discovery, entity verification, and tabular analysis.",
                compatible_entity_types=["startup", "professor", "repository", "research_paper", "company", "framework"],
                layout_mode=ExperienceMode.FULL_WORKSPACE,
                data_binding_slots={
                    "primary_records": "research_grid_main",
                    "status_metrics": "metric_strip_main"
                },
                default_components=[
                    {
                        "id": "metric_strip_main",
                        "type": "metric_strip",
                        "props": {
                            "metrics": [
                                {"label": "Status", "value": "INITIALIZING", "badge_color": "blue"},
                                {"label": "Execution Mode", "value": "PENDING", "badge_color": "gray"},
                                {"label": "Entities Discovered", "value": 0, "badge_color": "purple"},
                                {"label": "Verified Authentic", "value": 0, "badge_color": "emerald"},
                            ]
                        }
                    },
                    {
                        "id": "research_grid_main",
                        "type": "data_grid",
                        "props": {
                            "title": "Verified Entity Database",
                            "columns": [
                                {"key": "name", "header": "Entity Name", "type": "text"},
                                {"key": "domain", "header": "Domain / Focus", "type": "badge"},
                                {"key": "url", "header": "Verified URL", "type": "link"},
                                {"key": "confidence", "header": "Evidence Confidence", "type": "score"},
                            ],
                            "rows": [],
                            "placeholder_count": 5,
                            "searchable": True,
                            "exportable": True
                        }
                    }
                ]
            )
        )

        # Recipe 2: Educational Simulation & Visual Explanation
        self.register_recipe(
            ExperienceRecipe(
                recipe_id="exp_recipe_educational_simulation",
                name="Interactive Educational Visualizer",
                target_intent_family="educational_simulation",
                description="Interactive 2D node-edge canvas with live forward-propagation and backpropagation simulation controls.",
                compatible_entity_types=["neural_network", "algorithm", "state_machine", "concept"],
                layout_mode=ExperienceMode.FULL_WORKSPACE,
                data_binding_slots={
                    "simulation_state": "neural_canvas_main",
                    "status_metrics": "metric_strip_main"
                },
                default_components=[
                    {
                        "id": "metric_strip_main",
                        "type": "metric_strip",
                        "props": {
                            "metrics": [
                                {"label": "Simulation", "value": "2-Layer Perceptron", "badge_color": "blue"},
                                {"label": "Epoch", "value": "0 / 10", "badge_color": "purple"},
                                {"label": "Loss (MSE)", "value": "0.5000", "badge_color": "amber"},
                                {"label": "Learning Rate", "value": "0.1", "badge_color": "cyan"},
                            ]
                        }
                    },
                    {
                        "id": "neural_canvas_main",
                        "type": "interactive_canvas_2d",
                        "props": {
                            "title": "Interactive 2D Neural Network Learning Simulation",
                            "architecture": {
                                "input_nodes": 2,
                                "hidden_nodes": 2,
                                "output_nodes": 1
                            },
                            "nodes": [
                                {"id": "x1", "label": "Input x₁", "layer": "input", "value": 0.5, "x": 100, "y": 140},
                                {"id": "x2", "label": "Input x₂", "layer": "input", "value": 0.8, "x": 100, "y": 280},
                                {"id": "h1", "label": "Hidden h₁", "layer": "hidden", "value": 0.62, "bias": 0.1, "x": 350, "y": 140},
                                {"id": "h2", "label": "Hidden h₂", "layer": "hidden", "value": 0.48, "bias": -0.2, "x": 350, "y": 280},
                                {"id": "y_out", "label": "Output ŷ", "layer": "output", "value": 0.55, "bias": 0.05, "x": 600, "y": 210},
                            ],
                            "edges": [
                                {"id": "e_x1_h1", "source": "x1", "target": "h1", "weight": 0.45, "gradient": -0.02},
                                {"id": "e_x1_h2", "source": "x1", "target": "h2", "weight": -0.32, "gradient": 0.01},
                                {"id": "e_x2_h1", "source": "x2", "target": "h1", "weight": 0.78, "gradient": -0.04},
                                {"id": "e_x2_h2", "source": "x2", "target": "h2", "weight": 0.15, "gradient": 0.02},
                                {"id": "e_h1_y", "source": "h1", "target": "y_out", "weight": 0.85, "gradient": -0.08},
                                {"id": "e_h2_y", "source": "h2", "target": "y_out", "weight": -0.65, "gradient": 0.05},
                            ],
                            "current_step": 0,
                            "total_steps": 5,
                            "steps_detail": [
                                {
                                    "step_idx": 0,
                                    "phase": "Forward Propagation (Inputs)",
                                    "description": "Feed inputs x₁=0.5 and x₂=0.8 into the network.",
                                    "activations": {"x1": 0.5, "x2": 0.8, "h1": 0.0, "h2": 0.0, "y_out": 0.0},
                                    "active_layer": "input",
                                    "loss": 0.500
                                },
                                {
                                    "step_idx": 1,
                                    "phase": "Hidden Layer Activations",
                                    "description": "Compute linear sum z = W₁x + b₁ and apply Sigmoid activation σ(z) for h₁ and h₂.",
                                    "activations": {"x1": 0.5, "x2": 0.8, "h1": 0.701, "h2": 0.490, "y_out": 0.0},
                                    "active_layer": "hidden",
                                    "loss": 0.500
                                },
                                {
                                    "step_idx": 2,
                                    "phase": "Output Calculation & Loss",
                                    "description": "Compute output ŷ = σ(W₂h + b₂) = 0.570. Compare with target y=1.0 to compute MSE Loss = 0.5 * (1.0 - 0.570)² = 0.0925.",
                                    "activations": {"x1": 0.5, "x2": 0.8, "h1": 0.701, "h2": 0.490, "y_out": 0.570},
                                    "active_layer": "output",
                                    "loss": 0.0925
                                },
                                {
                                    "step_idx": 3,
                                    "phase": "Backpropagation (Gradients)",
                                    "description": "Calculate gradient of loss with respect to each weight using chain rule: ∂Loss/∂W.",
                                    "activations": {"x1": 0.5, "x2": 0.8, "h1": 0.701, "h2": 0.490, "y_out": 0.570},
                                    "active_layer": "backward",
                                    "loss": 0.0925
                                },
                                {
                                    "step_idx": 4,
                                    "phase": "Weight Update (Gradient Descent)",
                                    "description": "Update weights in opposite direction of gradient: W := W - η * (∂Loss/∂W). Loss decreases to 0.0410!",
                                    "activations": {"x1": 0.5, "x2": 0.8, "h1": 0.725, "h2": 0.470, "y_out": 0.710},
                                    "active_layer": "updated",
                                    "loss": 0.0410
                                }
                            ]
                        }
                    }
                ]
            )
        )

        # Recipe 3: Comparison Analysis Workspace
        self.register_recipe(
            ExperienceRecipe(
                recipe_id="exp_recipe_comparison_analysis",
                name="Comparative Analysis Workspace",
                target_intent_family="comparison_analysis",
                description="Side-by-side multi-entity comparative analysis matrix with evidence-grounded benchmarks.",
                compatible_entity_types=["framework", "model", "tool", "candidate"],
                layout_mode=ExperienceMode.FULL_WORKSPACE,
                data_binding_slots={
                    "primary_records": "comparison_matrix_main",
                    "status_metrics": "metric_strip_main"
                },
                default_components=[
                    {
                        "id": "metric_strip_main",
                        "type": "metric_strip",
                        "props": {
                            "metrics": [
                                {"label": "Comparison Target", "value": "AI Frameworks", "badge_color": "blue"},
                                {"label": "Entities Compared", "value": 0, "badge_color": "purple"},
                                {"label": "Criteria Evaluated", "value": 5, "badge_color": "amber"},
                            ]
                        }
                    },
                    {
                        "id": "comparison_matrix_main",
                        "type": "data_grid",
                        "props": {
                            "title": "Comparative Capability Matrix",
                            "columns": [
                                {"key": "feature", "header": "Feature / Dimension", "type": "text"},
                                {"key": "option_a", "header": "Candidate A", "type": "badge"},
                                {"key": "option_b", "header": "Candidate B", "type": "badge"},
                                {"key": "verdict", "header": "Evaluation Verdict", "type": "text"}
                            ],
                            "rows": [],
                            "placeholder_count": 4
                        }
                    }
                ]
            )
        )

        # Recipe 4: Browser Web Extraction Workspace
        self.register_recipe(
            ExperienceRecipe(
                recipe_id="exp_recipe_browser_extraction",
                name="Web Intelligence & Extraction Workspace",
                target_intent_family="browser_extraction",
                description="Live sandboxed browser telemetry, extracted web entities, accessible elements, and DOM facts.",
                compatible_entity_types=["web_page", "document", "site", "portal"],
                layout_mode=ExperienceMode.FULL_WORKSPACE,
                data_binding_slots={
                    "primary_records": "research_grid_main",
                    "status_metrics": "metric_strip_main"
                },
                default_components=[
                    {
                        "id": "metric_strip_main",
                        "type": "metric_strip",
                        "props": {
                            "metrics": [
                                {"label": "Browser Session", "value": "Playwright Chromium", "badge_color": "blue"},
                                {"label": "Security Sandbox", "value": "SSRF Isolated", "badge_color": "emerald"},
                                {"label": "Status", "value": "Navigating", "badge_color": "amber"},
                            ]
                        }
                    },
                    {
                        "id": "research_grid_main",
                        "type": "data_grid",
                        "props": {
                            "title": "Extracted Web Entities & Telemetry",
                            "columns": [
                                {"key": "name", "header": "Entity / Section / Link", "type": "text"},
                                {"key": "type", "header": "Type", "type": "badge"},
                                {"key": "source", "header": "Source URL", "type": "link"},
                                {"key": "status", "header": "Verification", "type": "badge"}
                            ],
                            "rows": [],
                            "placeholder_count": 4
                        }
                    }
                ]
            )
        )

        # Recipe 5: Guided Form Draft & Action Workspace
        self.register_recipe(
            ExperienceRecipe(
                recipe_id="exp_recipe_form_draft",
                name="Guided Form & Application Workspace",
                target_intent_family="form_draft",
                description="Structured form drafting, field validation, and secure operator approval gateway.",
                compatible_entity_types=["form", "application", "submission"],
                layout_mode=ExperienceMode.FULL_WORKSPACE,
                data_binding_slots={
                    "primary_records": "research_grid_main",
                    "status_metrics": "metric_strip_main"
                },
                default_components=[
                    {
                        "id": "metric_strip_main",
                        "type": "metric_strip",
                        "props": {
                            "metrics": [
                                {"label": "Form Category", "value": "Public Application Draft", "badge_color": "purple"},
                                {"label": "Approval Status", "value": "LOCAL_DRAFT", "badge_color": "amber"},
                                {"label": "Submission Gate", "value": "Blocked (Approval Required)", "badge_color": "emerald"},
                            ]
                        }
                    },
                    {
                        "id": "form_draft_main",
                        "type": "form_draft",
                        "props": {
                            "title": "Government / Public Service Application Draft",
                            "service_name": "Passport Seva Kendra",
                            "jurisdiction": "Ministry of External Affairs",
                            "status": "LOCAL_DRAFT",
                            "official_portal_url": "https://passportindia.gov.in",
                            "instructions": "Review the extracted draft fields below. In accordance with safety policies, this form has NOT been submitted to the government agency. You may copy these values directly to the official portal.",
                            "fields": [
                                {"name": "applicant_full_name", "label": "Full Legal Name", "value": "Jane Doe", "required": True, "source_evidence": "User Profile Context"},
                                {"name": "date_of_birth", "label": "Date of Birth (DD/MM/YYYY)", "value": "15/08/1995", "required": True, "source_evidence": "User Profile Context"},
                                {"name": "service_type", "label": "Application Service Type", "value": "Re-issue / Renewal of 36-page Passport", "required": True, "source_evidence": "Intent Specification"},
                                {"name": "jurisdiction_office", "label": "Passport Office (RPO)", "value": "Bengaluru / Regional Office", "required": True, "source_evidence": "Intent Constraints"},
                                {"name": "police_station", "label": "Nearest Police Station", "value": "Indiranagar Police Station", "required": True, "source_evidence": "Address Verification"}
                            ]
                        }
                    },
                    {
                        "id": "research_grid_main",
                        "type": "data_grid",
                        "props": {
                            "title": "Draft Application Fields & Requirements",
                            "columns": [
                                {"key": "field_name", "header": "Form Field / Question", "type": "text"},
                                {"key": "value", "header": "Assisted Draft Value", "type": "text"},
                                {"key": "required", "header": "Required", "type": "badge"},
                                {"key": "status", "header": "Draft Status", "type": "badge"}
                            ],
                            "rows": [
                                {"field_name": "Full Name", "value": "Jane Doe", "required": "Yes", "status": "DRAFTED"},
                                {"field_name": "Contact Email", "value": "user@example.com", "required": "Yes", "status": "VERIFIED"},
                                {"field_name": "Official Portal", "value": "https://passportindia.gov.in", "required": "Yes", "status": "HANDOFF_READY"}
                            ],
                            "placeholder_count": 0
                        }
                    }
                ]
            )
        )


# Global singleton store
experience_recipe_store = ExperienceRecipeStore()
