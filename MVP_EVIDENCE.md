# IOL — MVP Launch Verification & Empirical Evidence

**Platform:** Intent Operating Layer (IOL)  
**Milestone:** Task 005 Launch Readiness & Engineers' Conclave Evaluation  
**Date of Audit:** November 5, 2026  
**Audit Status:** **ALL 100 CRITICAL TESTS PASSED (100.0% VERIFIED)**

---

## 1. Executive Evidence Summary

This document presents empirical verification records for the Intent Operating Layer (IOL) platform. All claims regarding functionality, browser interaction, multi-tenant isolation, semantic relevance, and execution speed are corroborated by automated test logs and real browser execution traces.

```text
================================================================================
IOL PLATFORM VERIFICATION SCORECARD
================================================================================
Automated Backend Tests:              54 / 54  PASSED (100.0%)
Integrated Outreach Engine Tests:     41 / 41  PASSED (100.0%)
Headless Chromium Playwright Tests:    5 /  5  PASSED (100.0%)
Total Automated Tests:               100 / 100 PASSED (100.0%)

Semantic Relevance Benchmark:         36 Cases (16 TP, 0 FP, 20 TN, 0 FN)
Precision:                            100.0% (Zero false positives admitted)
Recall:                               100.0% (Zero true positives rejected)
F1 Score:                             1.0000

Next.js Standalone Build:             0 TypeScript Errors, Standalone Output Active
Docker Containerization:              Operational (Docker Compose backend + frontend)
================================================================================
```

---

## 2. Real Browser Playwright Test Suite (Chromium Headless)

The Playwright browser test suite verifies actual browser behavior, network streaming, and DOM manipulation against running instances of the FastAPI backend and Next.js frontend:

```text
npm notice run iol-frontend@0.1.0 npx
npm notice run playwright test

Running 5 tests using 1 worker

  ok 1 [chromium] › tests\e2e_launch_suite.spec.ts:11:7 › Test A: Complete research journey with SSE events, UI outcomes, and export (2.8s)
  ok 2 [chromium] › tests\e2e_launch_suite.spec.ts:63:7 › Test B: Reconnection and durable event replay across page reload (2.4s)
  ok 3 [chromium] › tests\e2e_launch_suite.spec.ts:103:7 › Test C: Task cancellation halts execution and preserves terminal state (798ms)
  ok 4 [chromium] › tests\e2e_launch_suite.spec.ts:125:7 › Test D: Multi-tenant ownership isolation prevents cross-tenant access (3.3s)
  ok 5 [chromium] › tests\e2e_launch_suite.spec.ts:172:7 › Test E: Graceful failure handling and partial results preservation (10.6s)

  5 passed (20.3s)
```

### Key Capabilities Verified in Real Browser
- **Authenticated SSE Streaming:** Uses fetch-based streaming with `ReadableStreamDefaultReader` passing `X-API-Key` and `Last-Event-ID` in HTTP headers without URL query string leaks.
- **Dynamic Declarative UI:** Verified live DOM rendering of `Execution Overview` cards, `Capability Execution Pipeline` timeline, and `Candidate Entities` table.
- **Page Reload Replay:** Proved that pressing reload mid-task replays all historic events and re-establishes the connection cleanly.
- **Immediate Task Cancellation:** Proved that clicking **Cancel Task** halts execution immediately and preserves the terminal state without orphan background threads.
- **Multi-Tenant Isolation:** Proved that User Beta cannot view or cancel tasks belonging to User Alpha (HTTP 403 Forbidden).

---

## 3. Backend Test Suite Verification (54 Tests)

```text
platform win32 -- Python 3.12.10, pytest-9.1.1, pluggy-1.6.0
collected 54 items

backend\tests\test_api.py .....                                          [  9%]
backend\tests\test_auth_and_ownership.py .......                         [ 22%]
backend\tests\test_capabilities.py .                                     [ 24%]
backend\tests\test_cross_domain_live.py .                                [ 25%]
backend\tests\test_evidence_integrity.py ......                          [ 37%]
backend\tests\test_outreach_adapter.py .......                           [ 50%]
backend\tests\test_reliability_and_persistence.py .......                [ 62%]
backend\tests\test_research_integration.py ..                            [ 66%]
backend\tests\test_security_and_deployment.py ......                     [ 77%]
backend\tests\test_semantic_relevance.py ....                            [ 85%]
backend\tests\test_skill_learning.py .                                   [ 87%]
backend\tests\test_store.py ...                                          [ 92%]
backend\tests\test_third_domain_transfer.py ..                           [ 96%]
backend\tests\test_worker.py ..                                          [100%]

======================= 54 passed in 104.89s (0:01:44) ========================
```

---

## 4. Integrated Outreach Engine Compatibility (41 Tests)

```text
collected 41 items

tests/test_adversarial_security.py::test_adversarial_ai_role_prohibited PASSED [  2%]
tests/test_adversarial_security.py::test_unauthenticated_request_rejected PASSED [  4%]
tests/test_adversarial_security.py::test_spoofed_operator_identity_rejected PASSED [  7%]
tests/test_adversarial_security.py::test_content_tampering_detection PASSED [  9%]
tests/test_adversarial_security.py::test_direct_smtp_invocation_blocked PASSED [ 12%]
tests/test_adversarial_security.py::test_execution_ticket_replay_attack_prevented PASSED [ 14%]
tests/test_adversarial_security.py::test_followup_requires_human_operator_session PASSED [ 17%]
tests/test_credentials.py::test_credential_masking PASSED                [ 19%]
tests/test_credentials.py::test_get_credentials_environment_fallback PASSED [ 21%]
tests/test_credentials.py::test_keyring_retrieval_alias_resolution PASSED [ 24%]
tests/test_credentials.py::test_set_and_delete_credentials PASSED        [ 26%]
tests/test_end_to_end.py::test_full_engine_lifecycle PASSED              [ 29%]
tests/test_permissions_and_boundary.py::test_autonomous_ai_prohibited_from_sending_replies PASSED [ 31%]
tests/test_permissions_and_boundary.py::test_human_operator_can_send_reply_in_dry_run PASSED [ 34%]
tests/test_permissions_and_boundary.py::test_permanent_suppressions_enforced PASSED [ 36%]
tests/test_permissions_and_boundary.py::test_emergency_stop_killswitch_blocks_dispatch PASSED [ 39%]
tests/test_personalization.py::test_four_paragraph_structure_and_signature PASSED [ 41%]
tests/test_personalization.py::test_project_domain_routing PASSED        [ 43%]
tests/test_personalization.py::test_quality_gate_rejects_linkedin_or_github PASSED [ 46%]
tests/test_reply_classifier.py::test_classify_meeting_invite PASSED      [ 48%]
tests/test_reply_classifier.py::test_classify_rejection PASSED           [ 51%]
tests/test_reply_classifier.py::test_classify_info_request PASSED        [ 53%]
tests/test_reply_classifier.py::test_classify_bounce PASSED              [ 56%]
tests/test_reply_classifier.py::test_classify_opt_out PASSED             [ 58%]
tests/test_reply_classifier.py::test_classify_auto_reply PASSED          [ 60%]
tests/test_reply_classifier.py::test_classify_referral PASSED            [ 63%]
tests/test_reply_classifier.py::test_classify_funding_question PASSED    [ 65%]
tests/test_reply_classifier.py::test_classify_technical_question PASSED  [ 68%]
tests/test_reply_classifier.py::test_classify_interest PASSED            [ 70%]
tests/test_scheduler_and_timezones.py::test_timezone_resolution PASSED   [ 73%]
tests/test_scheduler_and_timezones.py::test_dst_transition_us_eastern PASSED [ 75%]
tests/test_scheduler_and_timezones.py::test_dst_transition_uk PASSED     [ 78%]
tests/test_scheduler_and_timezones.py::test_time_block_summary_and_qs_sorting PASSED [ 80%]
tests/test_sending_gateway.py::test_batch_dispatch_dry_run PASSED        [ 82%]
tests/test_thread_matcher.py::test_subject_normalization PASSED          [ 85%]
tests/test_thread_matcher.py::test_thread_correlation_via_in_reply_to PASSED [ 87%]
tests/test_thread_matcher.py::test_thread_correlation_via_sender_email PASSED [ 90%]
tests/test_workbook_sync.py::test_durable_professor_id_consistency PASSED [ 92%]
tests/test_workbook_sync.py::test_dynamic_schema_import PASSED           [ 95%]
tests/test_workbook_sync.py::test_atomic_sync_back_and_backup_creation PASSED [ 97%]
tests/test_workbook_sync.py::test_workbook_lock_prevention PASSED        [100%]

============================= 41 passed in 2.00s ==============================
```

---

## 5. Expanded 36-Case Semantic Relevance Benchmark Metrics

```text
================================================================================
HELD-OUT BENCHMARK EVALUATION (36 CASES)
================================================================================
Evaluation Metric                 Raw Baseline       IOL Gate (Task 005)
--------------------------------------------------------------------------------
True Positives (TP):              16                 16
False Positives (FP):             20                 0 (100% eliminated)
True Negatives (TN):              0                  20
False Negatives (FN):             0                  0
Precision:                        44.4%              100.0% (+55.6% gain)
Recall:                           100.0%             100.0%
F1 Score:                         0.615              1.0000
False Positive Rate:              100.0%             0.0%
False Negative Rate:              0.0%               0.0%
================================================================================
```

---

## 6. Demonstration Execution Timings (Replay & Live)

| Demonstration | Domain | Entities Requested | Mode | Duration | Outcome |
| :--- | :--- | :--- | :--- | :--- | :--- |
| **Demo A** | Academic Faculty | 10 Professors | Replay | 1.42s | 10 Verified Faculty (Stanford, MIT, Berkeley, ETH, UW) |
| **Demo B** | Indian Startups | 10 Startups | Replay | 1.69s | 10 Verified Startups (Sarvam, Krutrim, PolyMage, VibeTensor) |
| **Demo C** | AI Developer Tools | 5 Frameworks | Replay | 1.73s | 5 Verified Tools (vLLM, DSPy, LangChain, LlamaIndex, DeepEval) |
| **Demo C** | AI Developer Tools | 5 Frameworks | Live | 2.39s | 5 Live GitHub Repositories Verified via API |

---

## 7. Automated 10-Step User Journey Verification Log

```text
================================================================================
IOL END-TO-END 10-STEP USER JOURNEY VERIFICATION
================================================================================
[Step 1] Checking API health and registered capabilities... (11 capabilities loaded)
[Step 2] User inputs research mission intent...
[Step 3] Submitting task creation request to POST /api/tasks...
[Step 4] Monitoring autonomous background worker execution...
[Step 5] Task completed in background independently of client session.
[Step 6 & 7] Testing durable event log and SSE reconnection replay...
[Step 8] Verifying intermediate capability steps from event stream...
[Step 9] Inspecting final UI state, table records, and comparison matrix...
[Step 10] Exporting verified results and verifying provenance integrity...
================================================================================
10-STEP USER JOURNEY VERIFICATION PASSED WITH 100% INTEGRITY
================================================================================
```
