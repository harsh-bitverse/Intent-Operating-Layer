# IOL — Evidence Integrity Report (Implementation Task 003)

## 1. Executive Summary

In Implementation Task 002, the Intent Operating Layer (IOL) achieved autonomous cross-domain execution across academia and commercial startups. However, an audit of the resulting records in `cross_domain_results.json` revealed several critical evidence integrity vulnerabilities:
1. **Bibliographic Confusions:** OpenAlex author IDs (`https://openalex.org/A...`) and paper DOIs were assigned to `official_profile_url` without distinguishing them from official university faculty profiles (`.edu` / `.ac.uk`).
2. **Unverified Academic Ranks:** Every co-author on retrieved publications was classified as a "Professor" without verifying whether they held a faculty appointment, postdoc, or graduate student status.
3. **Inferred Geographic Connections:** In startup research, organizations returned by GitHub search filters (`location:India`) were labeled as Indian entities even when their public bio, domain, or registry records lacked independent corroboration.
4. **Unsupported Certainty (`1.00` Confidence Scores):** All verified records received an uncalibrated confidence score of `1.00`, ignoring the probabilistic nature of heuristic extraction and web scraping.
5. **Requested Count Violations:** When the intent specified "Find 10 professors", the system returned 20 records because source acquisition was hardcoded to fetch 20 sources without downstream result slicing.

To address these vulnerabilities, IOL v0.3.0 implements field-level evidence provenance, conservative confidence semantics, separate identity/rank validation gates, and strict count enforcement.

---

## 2. Audit of Task 002 Outputs (`cross_domain_results.json`)

| Field / Claim in Task 002 | Ground Truth in Source | Integrity Gap Identified | Remediated Status in Task 003 |
| :--- | :--- | :--- | :--- |
| `official_profile_url: https://openalex.org/A5081407249` | Author bibliographic node in OpenAlex database | Bibliographic identifier passed off as official university profile | Categorized as `BIBLIOGRAPHIC_PROFILE` with status `INFERRED` and flagged with `PROFILE_IS_BIBLIOGRAPHIC_NOT_INSTITUTIONAL` |
| `name: Muhammad Sajid Shafique` (classified as Professor) | First author on IEEE SOCC paper; affiliation NYU Abu Dhabi | Co-author status does not imply academic faculty rank | Flagged with `ACADEMIC_RANK_UNVERIFIED` and categorized as "Academic Researcher (Faculty Rank Unverified)" unless explicit faculty chair is confirmed |
| `location: India` | Matched GitHub user search query `location:India` | Bio omitted geographic presence; query bias mistaken for proof | Categorized as `INFERRED_CONTEXT` with status `INFERRED`, tagged with `LOCATION_INFERRED_FROM_QUERY`, and confidence reduced |
| `confidence: 1.0` | Heuristic extraction from API title and snippet | Overconfident 1.0 certainty without ground-truth verification | Calibrated field-by-field; capped at `0.88` maximum to reflect residual uncertainty |
| `records_count: 20` | Intent requested: "Find 10 professors..." | Execution pipeline ignored user-requested record count | Intent parser extracts requested count (`max_records=10`); deduplication slices output to exact limit |

---

## 3. Four-Tier Evidence Integrity Hierarchy

In IOL v0.3.0, every extracted attribute is backed by an explicit `FieldEvidence` metadata block conforming to four canonical support tiers:

### Tier 1: Directly Supported (`DIRECTLY_SUPPORTED`)
- **Definition:** The attribute value is explicitly present in the source DOM, official company website, institutional `.edu` directory, or structured API field.
- **Examples:** Repository name on GitHub (`vllm-project/vllm`), SPDX license in repo metadata (`Apache-2.0`), institutional faculty URL (`https://asl.stanford.edu`).
- **Baseline Confidence:** `0.85`

### Tier 2: Derived (`DERIVED`)
- **Definition:** The attribute value is synthesized or summarized from explicitly documented source content (e.g., research focus extracted from paper titles or repository READMEs).
- **Examples:** Research interests derived from recent publication titles (`Adversarial and Backdoor Threats in Autonomous-Vehicle and Embodied-AI Systems`).
- **Baseline Confidence:** `0.75`

### Tier 3: Inferred (`INFERRED`)
- **Definition:** The attribute is inferred from query context, external link structure, or search heuristics, but not corroborated in the entity's own profile.
- **Examples:** OpenAlex bibliographic URL used as surrogate profile URL; Indian location inferred from GitHub search query without profile bio match.
- **Baseline Confidence:** `0.55 - 0.60`
- **Validation Action:** Flagged with explicit caveat tags (`PROFILE_IS_BIBLIOGRAPHIC_NOT_INSTITUTIONAL`, `LOCATION_INFERRED_FROM_QUERY`).

### Tier 4: Unknown / Unsupported (`UNKNOWN` / `UNSUPPORTED`)
- **Definition:** Attribute is absent from sources, invalid (e.g. malformed URL protocol), or unsupported by factual evidence.
- **Rule:** Missing values **must not be filled with generic fabricated placeholders**. They remain `None` / `Unknown` with status `UNKNOWN` and confidence `0.0`.
- **Validation Action:** If a critical identifier (name, company name, repo name) is missing, `is_valid` is set to `False` and the record is flagged.

---

## 4. Calibrated Confidence Semantics

Rather than assigning an arbitrary `1.00`, IOL calculates an aggregate confidence score for each record based on its individual field confidences:

$$\text{Aggregated Score} = \min\left(0.88, \frac{1}{N} \sum_{i=1}^{N} \text{Confidence}(\text{Field}_i)\right)$$

### Confidence Tiers:
- **`HIGH`** ($\ge 0.75$): All critical and secondary fields directly supported by official sources.
- **`MEDIUM`** ($0.55 - 0.74$): Core attributes confirmed, but secondary fields inferred (e.g. bibliographic profile or query-inferred location).
- **`LOW`** ($< 0.55$): Partial evidence, multiple missing fields, or uncorroborated claims.

Records with missing critical identity fields or average confidence below threshold ($\text{min\_conf} = 0.60$) are categorized as `FLAGGED` and excluded from verified outcomes.

---

## 5. Automated Verification & Regression Tests

Automated regression tests in [`backend/tests/test_evidence_integrity.py`](file:///c:/Workspace/Products/Intent%20Operating%20Layer/backend/tests/test_evidence_integrity.py) verify that:
1. `FieldEvidence` schema round-trips with full serialization.
2. Unverified academic rank emits `ACADEMIC_RANK_UNVERIFIED` and sets classification to "Academic Researcher (Faculty Rank Unverified)".
3. OpenAlex/DOI profile links emit `PROFILE_IS_BIBLIOGRAPHIC_NOT_INSTITUTIONAL` and are labeled `BIBLIOGRAPHIC_PROFILE`.
4. Startup locations lacking bio corroboration emit `LOCATION_INFERRED_FROM_QUERY` and are labeled `INFERRED_CONTEXT`.
5. Missing or unlisted attributes remain `None` and are labeled `UNKNOWN` with `confidence=0.0`.
6. Fabricated or invalid records lacking critical entity names are rejected with `is_valid=False`.
7. Maximum confidence across all verified records is strictly bounded at $\le 0.88$.
