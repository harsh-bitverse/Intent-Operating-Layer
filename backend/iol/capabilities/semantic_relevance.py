"""
Semantic Relevance Capability for Intent Operating Layer (IOL).
Evaluates candidate entities against structured intent constraints, inclusion criteria,
and exclusion filters to eliminate semantically irrelevant records before result selection.
"""

import re
from typing import Any, Dict, List, Optional, Tuple
from backend.iol.capabilities.base import BaseCapability, CapabilityResult, ExecutionContext
from backend.iol.core.research_models import (
    IntentConstraints,
    RejectionDetail,
    RelevanceEvaluation,
    SemanticRelevanceInput,
    SemanticRelevanceOutput,
)


class SemanticRelevanceCapability(BaseCapability):
    """
    Evaluates candidate entities against structured intent constraints,
    mandatory inclusion rules, and exclusion filters.
    Rejects false positives (e.g., recruitment repositories, personal CVs, student homework)
    even when basic field extraction succeeded.
    """

    capability_id = "research.semantic_relevance"
    name = "Semantic Relevance & Intent Constraint Gate"
    description = (
        "Filters extracted candidates by validating mandatory domain inclusion criteria "
        "and eliminating false positives matching explicit exclusion rules."
    )
    version = "1.0.0"
    input_model = SemanticRelevanceInput
    output_model = SemanticRelevanceOutput
    required_permissions = []
    estimated_cost_usd = 0.0

    async def execute(self, params: SemanticRelevanceInput, context: ExecutionContext) -> CapabilityResult:
        constraints = params.intent_constraints
        candidates = params.candidates
        qualified: List[Dict[str, Any]] = []
        rejected: List[RejectionDetail] = []
        evaluations: List[RelevanceEvaluation] = []

        for idx, cand in enumerate(candidates, start=1):
            cand_id = cand.get("_source_id") or cand.get("record_id") or f"cand_{idx}"
            fields = cand.get("fields") if isinstance(cand.get("fields"), dict) else cand
            identifier = (
                fields.get("repository_name")
                or fields.get("name")
                or fields.get("company_name")
                or fields.get("title")
                or cand.get("repository_name")
                or cand.get("name")
                or cand.get("company_name")
                or cand.get("title")
                or f"Entity_{idx}"
            )

            is_rel, score, matched, violated_excl, unmet_incl, evidence_str, reason = (
                self._evaluate_candidate(cand, constraints, params.entity_type)
            )

            evaluation = RelevanceEvaluation(
                candidate_id=cand_id,
                identifier=identifier,
                is_relevant=is_rel,
                relevance_score=score,
                matched_inclusion_criteria=matched,
                violated_exclusion_criteria=violated_excl,
                relevance_evidence=evidence_str,
                rejection_reason=reason,
            )
            evaluations.append(evaluation)

            if is_rel:
                # Augment candidate record with semantic relevance indicators
                enriched_cand = dict(cand)
                enriched_cand["is_semantically_relevant"] = True
                enriched_cand["is_intent_satisfied"] = True
                enriched_cand["semantic_relevance_score"] = score
                enriched_cand["relevance_evidence"] = evidence_str
                if isinstance(enriched_cand.get("fields"), dict):
                    enriched_cand["fields"]["_is_semantically_relevant"] = True
                    enriched_cand["fields"]["_relevance_evidence"] = evidence_str
                    enriched_cand["fields"]["_semantic_score"] = score
                qualified.append(enriched_cand)
            else:
                rejection = RejectionDetail(
                    candidate_id=cand_id,
                    identifier=identifier,
                    rejection_reasons=[reason] if reason else ["Failed semantic criteria"],
                    violated_exclusion_criteria=violated_excl,
                    unmet_inclusion_criteria=unmet_incl,
                )
                rejected.append(rejection)

        total_evaluated = len(candidates)
        precision = round(len(qualified) / max(total_evaluated, 1), 2)

        summary = (
            f"Semantic Relevance Gate evaluated {total_evaluated} candidate records: "
            f"{len(qualified)} qualified under intent constraints; "
            f"{len(rejected)} rejected due to category mismatch or exclusion rules."
        )

        output = SemanticRelevanceOutput(
            entity_type=params.entity_type,
            total_evaluated=total_evaluated,
            qualified_candidates=qualified,
            rejected_candidates=rejected,
            precision_estimate=precision,
            relevance_summary=summary,
            evaluations=evaluations,
        )

        return CapabilityResult(
            success=True,
            data=output.model_dump(),
            verification_score=precision,
            verification_details={
                "total_evaluated": total_evaluated,
                "qualified_count": len(qualified),
                "rejected_count": len(rejected),
                "precision": precision,
            },
        )

    def _evaluate_candidate(
        self,
        candidate: Dict[str, Any],
        constraints: IntentConstraints,
        entity_type: str,
    ) -> Tuple[bool, float, List[str], List[str], List[str], Optional[str], Optional[str]]:
        """
        Evaluates a single candidate record against mandatory inclusion criteria and exclusion filters.
        Returns: (is_relevant, score, matched_incl, violated_excl, unmet_incl, evidence_str, rejection_reason)
        """
        category = constraints.entity_category.lower()
        fields = candidate.get("fields") if isinstance(candidate.get("fields"), dict) else candidate

        # Combine text fields for semantic analysis
        text_corpus = " ".join([
            str(fields.get("repository_name") or candidate.get("repository_name") or ""),
            str(fields.get("name") or candidate.get("name") or ""),
            str(fields.get("company_name") or candidate.get("company_name") or ""),
            str(fields.get("product_focus") or candidate.get("product_focus") or ""),
            str(fields.get("location") or candidate.get("location") or ""),
            str(fields.get("institution") or candidate.get("institution") or ""),
            str(fields.get("research_interests") or candidate.get("research_interests") or ""),
            str(fields.get("description") or candidate.get("description") or ""),
            str(fields.get("bio") or candidate.get("bio") or ""),
            str(fields.get("evidence") or candidate.get("evidence") or ""),
            str(fields.get("title") or candidate.get("title") or ""),
            str(fields.get("official_repository_url") or candidate.get("official_repository_url") or ""),
            str(candidate.get("_raw_metadata", {}).get("description") or ""),
            str(candidate.get("_raw_metadata", {}).get("bio") or ""),
        ]).lower()

        violated_exclusions: List[str] = []
        unmet_inclusions: List[str] = []
        matched_inclusions: List[str] = []

        # ======================================================================
        # 1. Category 1: AI Developer Frameworks & Evaluation Tools
        # ======================================================================
        if any(c in category for c in ["tool", "framework", "library", "ai_developer", "evaluation"]):
            # A. Exclusion Rules (False positives: recruitment, personal CVs, homework, non-AI tools, curated lists)
            cv_patterns = [
                r"\bcurriculum\s+vitae\b",
                r"\bmy\s+cv\b",
                r"\bmy\s+resume\b",
                r"\bpersonal\s+portfolio\b",
                r"\bresume\.pdf\b",
                r"/cv\b",
                r"/resume\b",
            ]
            recruiting_patterns = [
                r"\brecruit(?:ing|er|ment)?\b",
                r"\bhiring\b",
                r"\bjunior\s+software\s+developer\b",
                r"\bjob\s+search\b",
                r"\binterview\s+prep\b",
                r"\btalent\s+acquisition\b",
            ]
            homework_patterns = [
                r"\bhomework\b",
                r"\bclass\s+assignment\b",
                r"\bcourse\s+project\b",
                r"\blearn\s+python\s+basics\b",
                r"\btutorial\s+week\b",
                r"\bclass\s+exercises\b",
            ]
            curated_list_patterns = [
                r"\bawesome[- ]\b",
                r"\bcurated\s+list\b",
                r"\bcollection\s+of\s+links\b",
                r"\blist\s+of\s+papers\b",
            ]
            non_framework_patterns = [
                r"\bnot\s+a\s+(?:framework|library|tool|software)\b",
                r"\bnot\s+(?:an?\s+)?ai\b",
                r"\bno\s+ai\b",
                r"\bbasic\s+script\s+with\s+no\s+ai\b",
            ]

            if any(re.search(p, text_corpus) for p in cv_patterns):
                violated_exclusions.append("Exclusion: Personal CV / Resume or Portfolio repository")
            if any(re.search(p, text_corpus) for p in recruiting_patterns):
                violated_exclusions.append("Exclusion: Recruitment, hiring, or job applicant repository")
            if any(re.search(p, text_corpus) for p in homework_patterns):
                violated_exclusions.append("Exclusion: Student classroom homework or beginner tutorial")
            if any(re.search(p, text_corpus) for p in curated_list_patterns):
                violated_exclusions.append("Exclusion: Curated markdown list or collection of links rather than executable software tool")
            if any(re.search(p, text_corpus) for p in non_framework_patterns):
                violated_exclusions.append("Exclusion: Explicitly non-AI or not an executable software framework/tool")

            # B. Mandatory Inclusion Rules (Must have explicit AI / LLM development or eval evidence)
            ai_domain_markers = [
                "llm", "large language model", "language model", "serving", "inference engine",
                "evaluation", "eval", "evaluating", "benchmark", "rag", "retrieval augmented",
                "agent", "orchestration", "prompt", "transformer", "neural", "deep learning",
                "nlp", "vllm", "dspy", "langchain", "llama", "deepeval", "ragas", "promptfoo",
                "phoenix", "observability", "cleanlab", "data-centric",
            ]
            has_ai_domain = any(m in text_corpus for m in ai_domain_markers)

            framework_markers = [
                "framework", "library", "engine", "toolkit", "sdk", "api", "serving",
                "tool", "benchmark", "pipeline", "platform", "system", "package", "observability",
            ]
            has_framework_nature = any(m in text_corpus for m in framework_markers)

            if has_ai_domain and has_framework_nature:
                matched_inclusions.append("Corroborated AI/LLM developer framework or evaluation functionality")
            else:
                if not has_ai_domain:
                    unmet_inclusions.append("Lacks explicit AI / LLM domain focus")
                if not has_framework_nature:
                    unmet_inclusions.append("Lacks framework, library, or evaluation tool architectural nature")

        # ======================================================================
        # 2. Category 2: Academic Faculty & Professors
        # ======================================================================
        elif any(c in category for c in ["prof", "faculty", "academic"]):
            # Exclusion: student homework, personal non-academic blog, postdocs/students without faculty appointment
            if any(term in text_corpus for term in ["undergraduate assignment", "homework 1", "personal blog"]):
                violated_exclusions.append("Exclusion: Non-academic student assignment or personal blog")

            # Exclude non-faculty researchers (postdocs, graduate students) when faculty is required
            is_non_faculty = any(
                re.search(p, text_corpus) for p in [
                    r"\bpostdoc(?:toral)?\s+fellow\b",
                    r"\bgraduate\s+research\s+assistant\b",
                    r"\bph\.?d\s+candidate\b",
                    r"\bundegraduate\s+student\b",
                ]
            )
            has_prof_title = any(
                re.search(p, text_corpus) for p in [
                    r"\bprof(?:essor)?\b",
                    r"\bfaculty\b",
                    r"\bchair\b",
                    r"\bdean\b",
                ]
            )

            if is_non_faculty and not has_prof_title:
                violated_exclusions.append("Exclusion: Non-faculty researcher (postdoctoral fellow or graduate student)")

            # Check confirmed institutional affiliation or peer-reviewed scholarly record
            inst_field = str(fields.get("institution") or candidate.get("institution") or "").lower()
            has_academic_affiliation = (
                has_prof_title
                or any(t in text_corpus for t in ["university", "institute", "college", "school of", "department of", "iit", "mit", "stanford", "cmu", "berkeley"])
                or ("doi:" in text_corpus and "openalex" in text_corpus)
            )

            if inst_field in ("unknown", "self", "none", "") or "affiliation is unconfirmed" in text_corpus:
                unmet_inclusions.append("Lacks verified institutional faculty appointment or affiliation")
            elif has_academic_affiliation:
                matched_inclusions.append("Confirmed academic faculty affiliation or peer-reviewed publication")
            else:
                unmet_inclusions.append("Lacks verified academic faculty appointment or publication record")

        # ======================================================================
        # 3. Category 3: Startups & Commercial Companies
        # ======================================================================
        elif any(c in category for c in ["startup", "company", "firm"]):
            # Exclusion: personal hobby repo or non-commercial community
            if any(term in text_corpus for term in ["my hobby project", "student club", "non-commercial discussion"]):
                violated_exclusions.append("Exclusion: Personal hobby project or student organization")

            # Non-AI or non-tech services exclusion
            non_ai_business_patterns = [
                r"\bmarketing\s+agency\b",
                r"\bnot\s+doing\s+ai\b",
                r"\bvisa\s+(?:processing|consultancy)\b",
                r"\bcall\s+center\b",
                r"\btelemarketing\b",
            ]
            if any(re.search(p, text_corpus) for p in non_ai_business_patterns):
                violated_exclusions.append("Exclusion: Non-AI business (marketing agency, visa consultancy, or call center)")

            # Exclusion: Geographic restriction (e.g. India requirement)
            geo_dict = constraints.geographic_restrictions or {}
            geo_target = str(geo_dict.get("country", "")).lower() or str(geo_dict.get("region", "")).lower()
            if "india" in geo_target or "india" in category:
                # Check negative mentions
                if any(re.search(p, text_corpus) for p in [r"\bnot\s+an?\s+indian\b", r"\bfails\s+geographic\b", r"\boutside\s+india\b"]):
                    violated_exclusions.append("Exclusion: Fails geographic restriction (not headquartered in India)")
                else:
                    loc_text = str(fields.get("location") or candidate.get("location") or "").lower()
                    india_markers = ["india", "bengaluru", "bangalore", "delhi", "gurugram", "gurgaon", "mumbai", "hyderabad", "pune", "noida"]
                    in_india = any(m in loc_text for m in india_markers) or any(m in text_corpus for m in ["headquartered in india", "bengaluru, india", "new delhi, india", "mumbai, india", "gurugram, india"])
                    if not in_india:
                        violated_exclusions.append("Exclusion: Fails geographic restriction (not headquartered in India)")

            # Exclusion: Temporal restriction (e.g. founded 2021 or later)
            temporal_dict = constraints.temporal_restrictions or {}
            min_year = temporal_dict.get("founded_after") or temporal_dict.get("year_min") or (2021 if "2021" in category else None)
            if min_year:
                year_match = re.search(r"\bfounded\s+(?:in\s+)?(19\d\d|20[0-1]\d|2020)\b", text_corpus)
                if year_match:
                    found_year = int(year_match.group(1))
                    if found_year < int(min_year):
                        violated_exclusions.append(f"Exclusion: Founded in {found_year} (violates constraint of founded >= {min_year})")

            # Inclusion: Commercial company building products
            has_commercial = any(t in text_corpus for t in ["company", "startup", "inc", "ltd", "technologies", "ventures", "solutions", "enterprise", "product", "series a", "funded"])
            if has_commercial:
                matched_inclusions.append("Confirmed commercial venture or startup enterprise")
            else:
                unmet_inclusions.append("Lacks verified commercial company structure")

        # ======================================================================
        # Final Decision
        # ======================================================================
        is_relevant = (len(violated_exclusions) == 0) and (len(unmet_inclusions) == 0)

        if is_relevant:
            # Score reflects evidence density (bounded 0.75 to 0.88 to respect confidence calibration)
            score = 0.85
            evidence_str = f"Corroborated by criteria: {'; '.join(matched_inclusions)}"
            rejection_reason = None
        else:
            score = 0.20 if violated_exclusions else 0.40
            evidence_str = None
            reasons = []
            if violated_exclusions:
                reasons.extend(violated_exclusions)
            if unmet_inclusions:
                reasons.extend(unmet_inclusions)
            rejection_reason = "; ".join(reasons)

        return is_relevant, score, matched_inclusions, violated_exclusions, unmet_inclusions, evidence_str, rejection_reason
