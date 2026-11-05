"""
Comprehensive Held-Out Semantic Relevance Benchmark and Intent Satisfaction Tests.
Validates the research.semantic_relevance capability, precision/recall metrics,
false positive elimination, and end-to-end planner integration.
"""

import pytest
from typing import Any, Dict, List
from backend.iol.agent.planner import AdaptiveCapabilityPlanner
from backend.iol.capabilities.base import ExecutionContext
from backend.iol.capabilities.registry import capability_registry
from backend.iol.capabilities.semantic_relevance import SemanticRelevanceCapability
from backend.iol.core.research_models import (
    IntentConstraints,
    SemanticRelevanceInput,
    SemanticRelevanceOutput,
    VerifiedRecord,
)

# ==============================================================================
# Held-Out Evaluation Dataset (20 Real-World Benchmark Entities)
# ==============================================================================
HELD_OUT_BENCHMARK_DATASET = [
    # --------------------------------------------------------------------------
    # AI Developer Frameworks & Evaluation Tools (Category 1)
    # --------------------------------------------------------------------------
    {
        "id": "tp_1",
        "expected": True,
        "category": "ai_developer_framework",
        "entity_type": "tool",
        "record": {
            "repository_name": "vllm-project/vllm",
            "primary_language": "Python",
            "license": "Apache-2.0",
            "official_repository_url": "https://github.com/vllm-project/vllm",
            "evidence": "A high-throughput and memory-efficient LLM inference and serving engine for language models.",
            "description": "vLLM is a fast and easy-to-use library for LLM inference and serving with PagedAttention.",
        }
    },
    {
        "id": "tp_2",
        "expected": True,
        "category": "ai_developer_framework",
        "entity_type": "tool",
        "record": {
            "repository_name": "stanfordnlp/dspy",
            "primary_language": "Python",
            "license": "MIT",
            "official_repository_url": "https://github.com/stanfordnlp/dspy",
            "evidence": "DSPy: The framework for programming—not prompting—foundation models and optimizing LM pipelines.",
            "description": "DSPy is the open-source framework for compiling declarative language model calls into self-improving pipelines.",
        }
    },
    {
        "id": "tp_3",
        "expected": True,
        "category": "ai_developer_framework",
        "entity_type": "tool",
        "record": {
            "repository_name": "confident-ai/deepeval",
            "primary_language": "Python",
            "license": "Apache-2.0",
            "official_repository_url": "https://github.com/confident-ai/deepeval",
            "evidence": "The Open-Source LLM Evaluation Framework for testing and benchmarking LLM applications and RAG pipelines.",
            "description": "DeepEval is a simple-to-use open-source LLM evaluation tool like PyTest for unit testing LLM apps.",
        }
    },
    {
        "id": "tp_4",
        "expected": True,
        "category": "ai_developer_framework",
        "entity_type": "tool",
        "record": {
            "repository_name": "langchain-ai/langchain",
            "primary_language": "Python",
            "license": "MIT",
            "official_repository_url": "https://github.com/langchain-ai/langchain",
            "evidence": "Building applications with LLMs through composability, agent orchestration, and retrieval pipelines.",
            "description": "LangChain provides an open-source framework and toolkit to orchestrate complex LLM agents and memory.",
        }
    },
    {
        "id": "tp_5",
        "expected": True,
        "category": "ai_developer_framework",
        "entity_type": "tool",
        "record": {
            "repository_name": "ragas-io/ragas",
            "primary_language": "Python",
            "license": "Apache-2.0",
            "official_repository_url": "https://github.com/ragas-io/ragas",
            "evidence": "Supercharging evaluation of Large Language Model and RAG architectures with automated metrics.",
            "description": "Ragas is an evaluation framework for testing Retrieval Augmented Generation pipelines.",
        }
    },
    {
        "id": "fp_1",
        "expected": False,
        "category": "ai_developer_framework",
        "entity_type": "tool",
        "record": {
            "repository_name": "RecruiterRon/Recuiting-Junior-Software-Developers",
            "primary_language": "Markdown",
            "license": "None",
            "official_repository_url": "https://github.com/RecruiterRon/Recuiting-Junior-Software-Developers",
            "evidence": "Hiring pipeline and job search tips for junior software developers in tech.",
            "description": "Talent acquisition guidelines and interview prep questions for hiring junior developers.",
        }
    },
    {
        "id": "fp_2",
        "expected": False,
        "category": "ai_developer_framework",
        "entity_type": "tool",
        "record": {
            "repository_name": "shbnq422/cv",
            "primary_language": "HTML",
            "license": "None",
            "official_repository_url": "https://github.com/shbnq422/cv",
            "evidence": "Personal curriculum vitae and resume portfolio hosting static site.",
            "description": "My CV, skills, education history, and personal portfolio.",
        }
    },
    {
        "id": "fp_3",
        "expected": False,
        "category": "ai_developer_framework",
        "entity_type": "tool",
        "record": {
            "repository_name": "student123/cs101-homework",
            "primary_language": "Python",
            "license": "None",
            "official_repository_url": "https://github.com/student123/cs101-homework",
            "evidence": "Student homework 1 for introductory computer science course.",
            "description": "Class assignment submission for learning basic Python loops and functions.",
        }
    },
    {
        "id": "fp_4",
        "expected": False,
        "category": "ai_developer_framework",
        "entity_type": "tool",
        "record": {
            "repository_name": "candidate-resume/resume.pdf",
            "primary_language": "TeX",
            "license": "None",
            "official_repository_url": "https://github.com/candidate-resume/my-resume",
            "evidence": "My resume and personal portfolio for applying to software engineering roles.",
            "description": "Curriculum vitae and resume repository.",
        }
    },
    {
        "id": "fp_5",
        "expected": False,
        "category": "ai_developer_framework",
        "entity_type": "tool",
        "record": {
            "repository_name": "tech-recruiter/talent-acquisition-portal",
            "primary_language": "JavaScript",
            "license": "MIT",
            "official_repository_url": "https://github.com/tech-recruiter/talent-acquisition-portal",
            "evidence": "Recruitment agency job board for hiring developers and talent acquisition.",
            "description": "Job search portal for recruiting junior and senior developers.",
        }
    },

    # --------------------------------------------------------------------------
    # Academic Faculty & Professors (Category 2)
    # --------------------------------------------------------------------------
    {
        "id": "tp_6",
        "expected": True,
        "category": "academic_faculty",
        "entity_type": "professor",
        "record": {
            "name": "Prof. Chetan Arora",
            "institution": "Indian Institute of Technology Delhi",
            "research_interests": "Computer Vision, Deep Learning, Autonomous Systems",
            "official_profile_url": "https://cse.iitd.ac.in/~chetan",
            "evidence": "Professor in the Department of Computer Science & Engineering at IIT Delhi leading vision and machine learning lab.",
            "bio": "Faculty chair and published author of numerous peer-reviewed papers on AI and vision.",
        }
    },
    {
        "id": "tp_7",
        "expected": True,
        "category": "academic_faculty",
        "entity_type": "professor",
        "record": {
            "name": "Prof. Subhashis Banerjee",
            "institution": "Indian Institute of Technology Delhi",
            "research_interests": "Machine Learning, Embedded AI, Vision Systems",
            "official_profile_url": "https://cse.iitd.ac.in/~suban",
            "evidence": "Faculty professor at IIT Delhi focusing on machine learning algorithms and embedded computing architectures.",
            "bio": "Head of laboratory, university professor with extensive publication and DOI citations.",
        }
    },
    {
        "id": "fp_6",
        "expected": False,
        "category": "academic_faculty",
        "entity_type": "professor",
        "record": {
            "name": "Alex Student",
            "institution": "Unknown",
            "research_interests": "None",
            "official_profile_url": "https://alexblog.com",
            "evidence": "Undergraduate assignment and personal blog about campus life.",
            "bio": "First year undergraduate student sharing homework 1 notes.",
        }
    },
    {
        "id": "fp_7",
        "expected": False,
        "category": "academic_faculty",
        "entity_type": "professor",
        "record": {
            "name": "Casual Blogger",
            "institution": "Self",
            "research_interests": "Tech opinions",
            "official_profile_url": "https://medium.com/@casual",
            "evidence": "Personal blog with random tech essays and opinions.",
            "bio": "Hobbyist writing personal blog posts without academic affiliation or lab.",
        }
    },

    # --------------------------------------------------------------------------
    # Startups & Commercial Companies (Category 3)
    # --------------------------------------------------------------------------
    {
        "id": "tp_8",
        "expected": True,
        "category": "ai_startup",
        "entity_type": "startup",
        "record": {
            "company_name": "CognitiveLab AI",
            "product_focus": "Autonomous Enterprise AI & Multi-Agent Robotics",
            "location": "Gurugram, India",
            "official_website": "https://www.cognitivelab.in",
            "evidence": "Founded in 2022 in Gurugram, India. Venture-backed enterprise AI and robotics startup manufacturing autonomous systems.",
        }
    },
    {
        "id": "tp_9",
        "expected": True,
        "category": "ai_startup",
        "entity_type": "startup",
        "record": {
            "company_name": "DevRev Technologies India",
            "product_focus": "Developer AI & Autonomous Support CRM",
            "location": "Bengaluru, India",
            "official_website": "https://www.devrev.ai",
            "evidence": "Founded in 2021 in Bengaluru, India. Commercial venture and enterprise AI startup building intelligent developer support platforms.",
        }
    },
    {
        "id": "tp_10",
        "expected": True,
        "category": "ai_startup",
        "entity_type": "startup",
        "record": {
            "company_name": "Sarvam AI",
            "product_focus": "Foundational Generative AI for Indian Languages",
            "location": "Bengaluru, India",
            "official_website": "https://www.sarvam.ai",
            "evidence": "Series A funded commercial startup building full-stack GenAI infrastructure and enterprise models.",
        }
    },
    {
        "id": "fp_8",
        "expected": False,
        "category": "ai_startup",
        "entity_type": "startup",
        "record": {
            "company_name": "My Weekend Hobby Group",
            "product_focus": "Weekend gaming",
            "location": "Online",
            "official_website": "https://discord.gg/hobby",
            "evidence": "My hobby project and student club for casual gaming on weekends.",
        }
    },
    {
        "id": "fp_9",
        "expected": False,
        "category": "ai_startup",
        "entity_type": "startup",
        "record": {
            "company_name": "Student Hackathon Club",
            "product_focus": "Organizing student meetups",
            "location": "Campus",
            "official_website": "https://club.edu",
            "evidence": "Student organization and non-commercial discussion group.",
        }
    },
    {
        "id": "fp_10",
        "expected": False,
        "category": "ai_startup",
        "entity_type": "startup",
        "record": {
            "company_name": "Beginner Python Club",
            "product_focus": "Tutorials",
            "location": "Local",
            "official_website": "https://learn.org",
            "evidence": "My hobby project with beginner code tutorials.",
        }
    },

    # --------------------------------------------------------------------------
    # Expanded Difficult & Edge Cases (Implementation Task 005)
    # --------------------------------------------------------------------------
    # Difficult Tools & Frameworks
    {
        "id": "tp_11",
        "expected": True,
        "category": "ai_developer_framework",
        "entity_type": "tool",
        "record": {
            "repository_name": "Arize-ai/phoenix",
            "primary_language": "Python",
            "license": "Apache-2.0",
            "official_repository_url": "https://github.com/Arize-ai/phoenix",
            "evidence": "AI observability and evaluation platform for LLMs, RAG pipelines, and model tracing.",
            "description": "Phoenix provides an open-source evaluation platform and library for testing LLMs.",
        }
    },
    {
        "id": "tp_12",
        "expected": True,
        "category": "ai_developer_framework",
        "entity_type": "tool",
        "record": {
            "repository_name": "cleanlab/cleanlab",
            "primary_language": "Python",
            "license": "AGPL-3.0",
            "official_repository_url": "https://github.com/cleanlab/cleanlab",
            "evidence": "The standard open-source framework for data-centric AI and machine learning evaluation.",
            "description": "Cleanlab is a framework and library for evaluating training dataset quality in machine learning.",
        }
    },
    {
        "id": "fp_11",
        "expected": False,
        "category": "ai_developer_framework",
        "entity_type": "tool",
        "record": {
            "repository_name": "someone/awesome-llm-papers",
            "primary_language": "Markdown",
            "license": "None",
            "official_repository_url": "https://github.com/someone/awesome-llm-papers",
            "evidence": "A curated list of awesome papers and collection of links on large language models.",
            "description": "Awesome list of papers. Not a framework or software tool.",
        }
    },
    {
        "id": "fp_12",
        "expected": False,
        "category": "ai_developer_framework",
        "entity_type": "tool",
        "record": {
            "repository_name": "codecamp/ai-week2",
            "primary_language": "Python",
            "license": "MIT",
            "official_repository_url": "https://github.com/codecamp/ai-week2",
            "evidence": "Class exercises and tutorial week 2 on basic neural networks.",
            "description": "Homework tutorial exercises for bootcamp students.",
        }
    },
    {
        "id": "fp_13",
        "expected": False,
        "category": "ai_developer_framework",
        "entity_type": "tool",
        "record": {
            "repository_name": "user/bash-echo-ai",
            "primary_language": "Shell",
            "license": "MIT",
            "official_repository_url": "https://github.com/user/bash-echo-ai",
            "evidence": "A shell script that echoes input text. Not a framework or library.",
            "description": "Basic script with no AI or evaluation capabilities.",
        }
    },

    # Difficult Academic Faculty Cases
    {
        "id": "tp_13",
        "expected": True,
        "category": "academic_faculty",
        "entity_type": "professor",
        "record": {
            "name": "Prof. Pushpak Bhattacharyya",
            "institution": "Indian Institute of Technology Bombay",
            "research_interests": "Natural Language Processing, Machine Translation, AI",
            "official_profile_url": "https://www.cse.iitb.ac.in/~pb/",
            "evidence": "Professor of Computer Science & Engineering at IIT Bombay leading multilingual NLP lab with extensive publication record.",
            "bio": "Distinguished university professor and chair in AI and NLP.",
        }
    },
    {
        "id": "tp_14",
        "expected": True,
        "category": "academic_faculty",
        "entity_type": "professor",
        "record": {
            "name": "Prof. Andrea Goldsmith",
            "institution": "Princeton University",
            "research_interests": "Wireless Communications, Embedded Systems, Machine Learning",
            "official_profile_url": "https://ece.princeton.edu/people/andrea-goldsmith",
            "evidence": "Dean of Engineering and Professor of Electrical Engineering at Princeton University.",
            "bio": "Faculty dean and professor leading communication lab.",
        }
    },
    {
        "id": "fp_14",
        "expected": False,
        "category": "academic_faculty",
        "entity_type": "professor",
        "record": {
            "name": "Dr. John Doe",
            "institution": "Massachusetts Institute of Technology",
            "research_interests": "Computer Vision",
            "official_profile_url": "https://mit.edu/~johndoe",
            "evidence": "Postdoctoral fellow in Computer Science at MIT researching vision.",
            "bio": "Postdoctoral fellow and research fellow in EECS.",
        }
    },
    {
        "id": "fp_15",
        "expected": False,
        "category": "academic_faculty",
        "entity_type": "professor",
        "record": {
            "name": "Emily Smith",
            "institution": "Stanford University",
            "research_interests": "Robotics",
            "official_profile_url": "https://stanford.edu/~esmith",
            "evidence": "Graduate research assistant and Ph.D. candidate at Stanford University studying robotics.",
            "bio": "Graduate research assistant and student.",
        }
    },
    {
        "id": "fp_16",
        "expected": False,
        "category": "academic_faculty",
        "entity_type": "professor",
        "record": {
            "name": "A. Author",
            "institution": "Unknown",
            "research_interests": "Data Science",
            "official_profile_url": "https://unverified.org/author",
            "evidence": "Research paper author whose institutional affiliation is unconfirmed and unlisted.",
            "bio": "Publication author with unknown affiliation.",
        }
    },

    # Difficult Indian Startup Cases (Geography & Temporal constraints)
    {
        "id": "tp_15",
        "expected": True,
        "category": "ai_startup",
        "entity_type": "startup",
        "record": {
            "company_name": "Krutrim SI Designs",
            "product_focus": "Multilingual AI Foundation Models & Cloud",
            "location": "Bengaluru, India",
            "official_website": "https://www.krutrim.com",
            "evidence": "Founded in 2023 in Bengaluru, India. Full-stack AI startup and commercial enterprise building Indian foundation models.",
        }
    },
    {
        "id": "tp_16",
        "expected": True,
        "category": "ai_startup",
        "entity_type": "startup",
        "record": {
            "company_name": "Genwise AI",
            "product_focus": "Generative AI Platform for Seniors",
            "location": "New Delhi, India",
            "official_website": "https://www.genwise.ai",
            "evidence": "Founded in 2023 in New Delhi, India. Series A funded commercial startup building enterprise AI products.",
        }
    },
    {
        "id": "fp_17",
        "expected": False,
        "category": "ai_startup",
        "entity_type": "startup",
        "record": {
            "company_name": "OldGuard AI Pvt Ltd",
            "product_focus": "Enterprise IT Support",
            "location": "Bengaluru, India",
            "official_website": "https://oldguard.in",
            "evidence": "Founded in 2018 in Bengaluru, India. Commercial IT consultancy.",
        }
    },
    {
        "id": "fp_18",
        "expected": False,
        "category": "ai_startup",
        "entity_type": "startup",
        "record": {
            "company_name": "Stanford AI Marketing LLC",
            "product_focus": "Social media marketing",
            "location": "Wilmington, Delaware, USA",
            "official_website": "https://stanford-marketing.com",
            "evidence": "Marketing agency with university-sounding name in Delaware. Not an Indian company and not doing AI.",
        }
    },
    {
        "id": "fp_19",
        "expected": False,
        "category": "ai_startup",
        "entity_type": "startup",
        "record": {
            "company_name": "AI Visa Consultancy Services",
            "product_focus": "Visa processing automation",
            "location": "Dubai, UAE",
            "official_website": "https://visa-ai.ae",
            "evidence": "Visa processing consultancy located in Dubai. Fails geographic restriction for Indian startups.",
        }
    },
    {
        "id": "fp_20",
        "expected": False,
        "category": "ai_startup",
        "entity_type": "startup",
        "record": {
            "company_name": "Legacy Call Center Solutions",
            "product_focus": "BPO services",
            "location": "Mumbai, India",
            "official_website": "https://legacybpo.in",
            "evidence": "Founded in 2005 in Mumbai, India. Legacy telemarketing call center.",
        }
    },
]


@pytest.fixture
def relevance_cap() -> SemanticRelevanceCapability:
    return SemanticRelevanceCapability()


# ==============================================================================
# 1. Held-Out Precision & Recall Benchmark
# ==============================================================================
@pytest.mark.asyncio
async def test_held_out_benchmark_precision_and_recall(relevance_cap):
    """
    Evaluates the held-out benchmark across tools, professors, and startups.
    Asserts precision >= 80% and recall >= 80%.
    """
    context = ExecutionContext(task_id="bench_001", step_id="step_relevance")

    # Group benchmark by category to test each domain constraint
    categories = ["ai_developer_framework", "academic_faculty", "ai_startup"]

    overall_tp = 0
    overall_fp = 0
    overall_tn = 0
    overall_fn = 0

    for cat in categories:
        samples = [s for s in HELD_OUT_BENCHMARK_DATASET if s["category"] == cat]
        candidates = [s["record"] for s in samples]

        # Setup constraints
        if cat == "ai_developer_framework":
            constraints = IntentConstraints(
                entity_category=cat,
                mandatory_inclusion_criteria=["Corroborated AI/LLM developer framework or evaluation functionality"],
                exclusion_criteria=["Personal CV / Resume", "Recruiting or job search", "Classroom homework"],
                requested_record_count=5
            )
            entity_type = "tool"
        elif cat == "academic_faculty":
            constraints = IntentConstraints(
                entity_category=cat,
                mandatory_inclusion_criteria=["Confirmed academic faculty affiliation or peer-reviewed publication"],
                exclusion_criteria=["Undergraduate homework", "Personal blog"],
                requested_record_count=5
            )
            entity_type = "professor"
        else:
            constraints = IntentConstraints(
                entity_category=cat,
                mandatory_inclusion_criteria=["Confirmed commercial venture or startup enterprise", "Headquartered in India", "Founded in 2021 or later"],
                exclusion_criteria=["Personal hobby project", "Student club", "Founded before 2021", "Outside India"],
                geographic_restrictions={"country": "India"},
                temporal_restrictions={"founded_after": 2021},
                requested_record_count=5
            )
            entity_type = "startup"

        input_data = SemanticRelevanceInput(
            entity_type=entity_type,
            candidates=candidates,
            intent_constraints=constraints,
            task_intent=f"Find benchmark targets in {cat}"
        )

        res = await relevance_cap.execute(input_data, context)
        assert res.success is True

        output = SemanticRelevanceOutput.model_validate(res.data)
        eval_map = {e.identifier: e.is_relevant for e in output.evaluations}

        for s in samples:
            ident = (
                s["record"].get("repository_name")
                or s["record"].get("name")
                or s["record"].get("company_name")
            )
            is_rel = eval_map.get(ident, False)
            expected = s["expected"]

            if expected and is_rel:
                overall_tp += 1
            elif not expected and is_rel:
                overall_fp += 1
            elif not expected and not is_rel:
                overall_tn += 1
            elif expected and not is_rel:
                overall_fn += 1

    total_predicted_positive = overall_tp + overall_fp
    precision = overall_tp / total_predicted_positive if total_predicted_positive > 0 else 0.0

    total_actual_positive = overall_tp + overall_fn
    recall = overall_tp / total_actual_positive if total_actual_positive > 0 else 0.0

    print(f"\nHeld-Out Metrics: TP={overall_tp}, FP={overall_fp}, TN={overall_tn}, FN={overall_fn}")
    print(f"Precision: {precision:.2%}, Recall: {recall:.2%}")

    # Core target: Precision >= 80% on held-out set
    assert precision >= 0.80, f"Precision was {precision:.2%}, expected >= 80%"
    assert recall >= 0.80, f"Recall was {recall:.2%}, expected >= 80%"
    assert overall_fp == 0, "No false positives should bypass the semantic exclusion filters"


# ==============================================================================
# 2. Rejection Reasons and Exclusion Verification
# ==============================================================================
@pytest.mark.asyncio
async def test_rejection_reasons_explicit_and_actionable(relevance_cap):
    """
    Verifies that rejected false positives have clear, explicit rejection reasons
    referencing violated exclusion rules or unmet inclusion criteria.
    """
    context = ExecutionContext(task_id="bench_002", step_id="step_relevance")

    false_positive_tools = [
        s["record"] for s in HELD_OUT_BENCHMARK_DATASET
        if s["category"] == "ai_developer_framework" and not s["expected"]
    ]

    constraints = IntentConstraints(
        entity_category="ai_developer_framework",
        mandatory_inclusion_criteria=["Corroborated AI/LLM developer framework or evaluation functionality"],
        exclusion_criteria=["Personal CV / Resume", "Recruiting or job search", "Classroom homework"],
        requested_record_count=5
    )

    input_data = SemanticRelevanceInput(
        entity_type="tool",
        candidates=false_positive_tools,
        intent_constraints=constraints,
        task_intent="Find AI developer frameworks"
    )

    res = await relevance_cap.execute(input_data, context)
    output = SemanticRelevanceOutput.model_validate(res.data)

    assert len(output.qualified_candidates) == 0
    assert len(output.rejected_candidates) == len(false_positive_tools)

    # Check that each rejection details why it was disqualified
    for rej in output.rejected_candidates:
        assert len(rej.rejection_reasons) > 0
        assert any("Exclusion:" in r or "Lacks" in r for r in rej.rejection_reasons)


# ==============================================================================
# 3. Four-Tier State Distinction
# ==============================================================================
def test_four_tier_state_distinction():
    """
    Verifies the four-tier semantic distinction on VerifiedRecord:
    1. is_source_verified (Valid reachable domain / API source)
    2. is_field_verified (Extracted attributes meet structural schema)
    3. is_semantically_relevant (Satisfies mandatory category & intent constraints)
    4. is_intent_satisfied (Meets end-to-end user goal)
    """
    # A source can be verified, fields verified, but NOT semantically relevant (e.g., CV repo)
    rec_cv = VerifiedRecord(
        record_id="rec_cv_01",
        is_valid=True,
        confidence_score=0.85,
        confidence_tier="HIGH",
        fields={"repository_name": "shbnq422/cv", "primary_language": "HTML"},
        is_source_verified=True,      # GitHub API returned 200 OK
        is_field_verified=True,       # fields extracted cleanly
        is_semantically_relevant=False, # Personal CV is NOT an AI developer framework
        is_intent_satisfied=False,    # Fails user intent
        semantic_relevance_score=0.20
    )
    assert rec_cv.is_source_verified is True
    assert rec_cv.is_field_verified is True
    assert rec_cv.is_semantically_relevant is False
    assert rec_cv.is_intent_satisfied is False

    # A genuine LLM framework satisfies all four tiers
    rec_vllm = VerifiedRecord(
        record_id="rec_vllm_01",
        is_valid=True,
        confidence_score=0.88,
        confidence_tier="HIGH",
        fields={"repository_name": "vllm-project/vllm", "primary_language": "Python"},
        is_source_verified=True,
        is_field_verified=True,
        is_semantically_relevant=True,
        is_intent_satisfied=True,
        semantic_relevance_score=0.85,
        relevance_evidence="Corroborated AI/LLM developer framework"
    )
    assert rec_vllm.is_source_verified is True
    assert rec_vllm.is_field_verified is True
    assert rec_vllm.is_semantically_relevant is True
    assert rec_vllm.is_intent_satisfied is True


# ==============================================================================
# 4. Adaptive Planner Integration with Semantic Relevance Gate
# ==============================================================================
@pytest.mark.asyncio
async def test_adaptive_planner_inserts_semantic_relevance_gate():
    """
    Verifies that the AdaptiveCapabilityPlanner includes 'step_relevance'
    and wires its qualified_candidates into 'step_dedup'.
    """
    from backend.iol.adapters.outreach.adapter import register_outreach_capabilities
    from backend.iol.capabilities.live_research import register_live_research_capabilities
    from backend.iol.capabilities.registry import CapabilityRegistry

    registry = CapabilityRegistry()
    register_outreach_capabilities(registry)
    register_live_research_capabilities(registry)

    planner = AdaptiveCapabilityPlanner(registry=registry)
    caps = registry.list_capabilities()

    # Plan for AI developer frameworks
    intent = "Find 5 open-source AI developer frameworks or evaluation tools"
    plan = await planner.plan(intent, caps)

    step_ids = [s.step_id for s in plan.steps]
    assert "step_acquisition" in step_ids
    assert "step_extraction" in step_ids
    assert "step_verification" in step_ids
    assert "step_relevance" in step_ids
    assert "step_dedup" in step_ids

    # Step relevance comes immediately after verification and before deduplication
    rel_idx = step_ids.index("step_relevance")
    ver_idx = step_ids.index("step_verification")
    dedup_idx = step_ids.index("step_dedup")
    assert ver_idx < rel_idx < dedup_idx

    # Deduplication dynamically depends on step_relevance.qualified_candidates
    dedup_step = next(s for s in plan.steps if s.step_id == "step_dedup")
    assert dedup_step.dynamic_param_mappings.get("entities") == "step_relevance.qualified_candidates"
