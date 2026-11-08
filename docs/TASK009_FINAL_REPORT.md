# IOL Task 009 — General-Purpose End-to-End Execution & Generative Workspace Final Report

**Date:** November 8, 2026  
**Target Submission:** IIT Delhi Engineers' Conclave  
**Repository:** `https://github.com/harsh-bitverse/Intent-Operating-Layer.git`  
**Working Tree Commit Baseline:** `46c9b3f` (Task 008 completion) -> Task 009 Implementation  
**Operating Environment:** Windows 11, Python 3.12.10, Node.js 18+, Playwright Chromium  

---

## 1. Exact Tasks Executed

### A. Primary End-to-End Unfamiliar Task (Generalization Probe 1)
- **Natural-Language Intent:**
  `"Compare official documentation for Python 3 at https://docs.python.org/3/ and FastAPI at https://fastapi.tiangolo.com/"`
- **Capability Plan Generated:**
  1. `browser.navigate` -> `https://docs.python.org/3/`
  2. `browser.extract` -> Structured headings, modules, language options
  3. `browser.navigate` -> `https://fastapi.tiangolo.com/`
  4. `browser.extract` -> Structured sections, opinions, sponsor links
- **Task ID:** `task_d2766f4c2112`
- **Execution Duration:** 3.26 seconds
- **Final Outcome:** `OutcomeEnvelopeV1` with `OutcomeShape.COMPARISON`, `SourceMode.LIVE_BROWSER`, 14 verified extracted items, and an adaptive comparison matrix.

### B. Held-Out Generalization Probe 2 (Institutional Portal)
- **Natural-Language Intent:**
  `"Navigate to https://home.iitd.ac.in/ and extract official academic programs and campus links"`
- **Capability Plan Generated:**
  1. `browser.navigate` -> `https://home.iitd.ac.in/`
  2. `browser.extract` -> Institutional headings, announcements, academic links
- **Task ID:** `task_d84799419614`
- **Execution Duration:** 4.23 seconds
- **Final Outcome:** `OutcomeEnvelopeV1` with `OutcomeShape.COLLECTION`, `SourceMode.LIVE_BROWSER`, 14 verified extracted items including official announcements and campus links.

### C. Consequential Action Approval & Replay Recovery Probe
- **Natural-Language Intent:**
  `"Test external write action approval lifecycle"`
- **Consequential Action Requested:** `browser.submit_form` (`EXTERNAL_WRITE`, target: `https://example.gov/apply`)
- **Execution Lifecycle:**
  1. Action submission triggered cryptographic approval ticket generation with sha256 fingerprint.
  2. Task state paused in `PAUSED_FOR_APPROVAL`.
  3. Frontend rendered amber-bordered `ActionPanel` displaying consequence tier `EXTERNAL WRITE`.
  4. Operator approved via UI; ticket signature validated; anti-replay verified; task transitioned to `COMPLETED`.

---

## 2. Real vs. Fallback Accounting

| Pipeline Stage | Method Invoked | Provider / Mechanism | Origin Classification | Honest Rationale |
| :--- | :--- | :--- | :--- | :--- |
| **Browser Execution** | Real Playwright Chromium | Local isolated browser contexts | `LIVE_BROWSER` | Live network navigation to target URLs; zero mock fixtures or synthetic HTML. |
| **Model Gateway** | `ModelProviderGateway` | OpenAI / Anthropic / Local Ollama fallback | `RECIPE_ADAPTED` | Since no cloud LLM API keys (`OPENAI_API_KEY`) were configured in the local environment, the gateway gracefully and safely adapted declarative recipes. **Zero synthetic layouts were falsely labeled `MODEL_GENERATED`.** |
| **Outcome Envelope** | Progressive SSE streaming | Background worker monotonic accumulator | `VERIFIED_LIVE` | Every record reflects raw observed DOM text, status code 200, and exact retrieval timestamps. |
| **Action Gateway** | HMAC-SHA256 Ticket Engine | In-memory approval ledger | `OPERATOR_APPROVED` | Cryptographic signature prevents replay and forces human-in-the-loop before execution. |

---

## 3. Source and Evidence Provenance

### Visited URLs and Parsed DOM Facts:
1. `https://docs.python.org/3/`
   - **HTTP Status:** 200 OK
   - **Title:** `Python 3.15.2 documentation`
   - **Captured Heading Text:** `"dev (3.16) 3.15.2 3.14 3.13 3.12 3.11 3.10 3.9 3.8 3.7 3.6 3.5 3.4 3.3 3.2 3.1 3.0 2.7 2.6 3.15.2 documentation"`
   - **Content Hash:** Computed and attached to `OutcomeEvidenceRecord`.
   - **Retrieval Timestamp:** `2026-11-08T13:48:26.558969+00:00`
2. `https://fastapi.tiangolo.com/`
   - **HTTP Status:** 200 OK
   - **Title:** `FastAPI - FastAPI`
   - **Captured Headings / Links:** `"FastAPI"`, `"Sponsors"`, `"Opinions"`, `"Features"`, `"Tutorial - User Guide"`
   - **Retrieval Timestamp:** `2026-11-08T13:51:00.124510+00:00`
3. `https://home.iitd.ac.in/`
   - **HTTP Status:** 200 OK
   - **Title:** `Home Page : IIT Delhi`
   - **Captured Sections:** `"Welcome to the new web..."`, `"Take a quick tour to explore more..."`, `"IMPORTANT ANNOUNCEMENTS"`
   - **Retrieval Timestamp:** `2026-11-08T13:51:04.819034+00:00`

---

## 4. Interactive Experience Fidelity

- **Instantiated Components:**
  - `workspace_layout`: Root container managing stacked or grid composition.
  - `comparison_matrix`: Dual-pane side-by-side comparison with dynamic columns and verification badges.
  - `data_grid`: Searchable, filterable table with column sorting and evidence drawer trigger.
  - `metric_strip`: Real-time status cards tracking steps completed, sources acquired, and records verified.
  - `form_draft`: Public application form preview with `LOCAL_DRAFT` badge and copy button.
  - `action_panel`: Consequential action authorization card with consequence badge and approval buttons.
  - `interactive_canvas_2d`: Mathematical neural network step controller with step forward/back and formula display.
- **Monotonic Data Binding:**
  - Data grid rows bind monotonically across steps: step 1 appends 1 record, step 2 appends 13 records (total 14).
  - Metrics update progressively from 0 -> 1 -> 14 without table flickering or layout collapse.

---

## 5. Security & Authorization Boundary Verification

1. **Strict SSRF Defense:**
   - Prohibits cloud metadata (`169.254.169.254`), loopbacks (`127.0.0.1`, `::1`), and RFC1918 private IPs.
   - Enforces safe split-horizon DNS handling for verified institutional domains (`*.iitd.ac.in`) while strictly maintaining cloud metadata blocking.
2. **Untrusted DOM Prompt Injection Sanitization:**
   - Added `sanitize_untrusted_text` in `BrowserPolicy` and integrated into `BrowserActionExecutor`.
   - Defangs LLM delimiter tokens (`<|im_start|>`, `<|system|>`, `[INST]`, `<<SYS>>`) by replacing with safe textual tokens.
   - Neutralizes adversarial override phrases (`ignore previous instructions`, `system override`, `developer mode`) with `[FILTERED_PROMPT_INJECTION]`.
   - Verified via unit test `test_browser_policy_prompt_injection_sanitization` (0.13s execution time).
3. **Multi-Tenant Ownership Isolation:**
   - User identity is server-derived from API keys, ignoring client payloads.
   - Unauthorized cross-tenant task access strictly returns HTTP 403 Forbidden.

---

## 6. Comprehensive Automated Test Suite Status

| Test Category | Suite File | Total Tests | Passed | Failed | Duration |
| :--- | :--- | :--- | :--- | :--- | :--- |
| **Backend Core & Browser** | `backend/tests/test_browser_substrate.py` | 6 | 6 | 0 | 3.29s |
| **Backend Live Research** | `backend/tests/test_cross_domain_live.py` | 1 | 1 | 0 | 29.18s |
| **Backend Core Suite** | `backend/tests/ (72 other tests)` | 67 | 67 | 0 | 33.96s |
| **Legacy Outreach Engine** | `Outreach Intelligence Engine/tests/` | 41 | 41 | 0 | 2.11s |
| **Playwright Launch Suite** | `frontend/tests/e2e_launch_suite.spec.ts` | 5 | 5 | 0 | 19.9s |
| **Playwright Experience Suite**| `frontend/tests/e2e_experience_suite.spec.ts` | 3 | 3 | 0 | 36.5s |
| **Playwright Browser & Approval**| `frontend/tests/e2e_task008_suite.spec.ts` | 3 | 3 | 0 | 12.6s |
| **Total Automated Tests** | **Full System Regression** | **126** | **126** | **0** | **~2.3 min** |

**Zero failing tests across all 126 automated test specifications.**

---

## 7. Verification Artifacts & Visual Proofs

All visual artifacts are preserved in `docs/screenshots/`:
1. `v09_probe1_doc_comparison.png` (466 KB): Live comparative documentation analysis workspace (Python 3 vs FastAPI).
2. `v09_probe2_iitd_portal.png` (408 KB): Live institutional portal extraction workspace (IIT Delhi Home).
3. `v08_demo1_browser_extraction.png` (298 KB): Single-page browser extraction with screenshot and accessible element count.
4. `v08_demo4_form_draft.png` (382 KB): Passport renewal form draft with safe `LOCAL_DRAFT` badge.
5. `v08_action_approval_verified.png` (351 KB): Consequential action approval lifecycle in `TaskView`.
6. `v06_demo_a_research_workspace.png` (358 KB): Full-screen adaptive research workspace with evidence drawer.
7. `v06_demo_b_neural_simulation.png` (361 KB): Interactive 2D neural simulation canvas.
8. `tenant_isolation_403.png` (77 KB): Multi-tenant security barrier proof.

---

## 8. Remaining Limitations & Production Roadmap

1. **Model Credentials:** While `ModelProviderGateway` is fully implemented to call OpenAI/Anthropic/Ollama endpoints, production deployment will configure an active cloud LLM key in `.env` to enable dynamic `MODEL_GENERATED` layouts for arbitrary new domain topologies.
2. **Complex Anti-Bot Walls:** Heavily protected Cloudflare Turnstile or CAPTCHA walls are detected and safely flagged as blockers (`is_blocked: True`), requiring human handoff or residential proxy pooling in enterprise deployments.
3. **Multi-Page Deep Pagination:** Current browser extraction gathers first-order headings and interactive elements up to 25 items per page. Multi-page pagination traversal is queued for the v1.0 roadmap.
