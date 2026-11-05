# Comprehensive Repository Audit: Outreach Intelligence Engine

**Audit Date:** November 2026  
**Audited Repository:** `https://github.com/harsh-bitverse/Outreach-intelligence-engine.git`  
**Inspected Working Copy:** `C:\Workspace\Projects\Outreach Intelligence Engine` (commit `8b779e5`)  
**Associated Artifacts:** `C:\Users\ch1251635.ACAD\antigravity\proud-planck`  

---

## 1. Executive Summary

This audit assesses the architecture, runtime characteristics, security controls, data pipelines, and external integrations of the **International Research Outreach Intelligence Engine**. The objective is to identify genuinely reusable capabilities for the **Intent Operating Layer (IOL)**—a general-purpose intent-to-outcome execution platform—while maintaining strict boundaries and zero disruption to the existing engine.

The Outreach Intelligence Engine is a local-first, highly specialized Python 3.12 application engineered to support high-precision academic outreach. It bridges an authoritative Excel workbook (1,357 faculty prospects across 121 universities) into a transactional SQLite store, generates structured four-paragraph personalized outreach emails grounded in substantiated student credentials, computes destination-local weekday morning dispatch windows across 13 global regional clusters, and enforces a cryptographic human-only permission boundary preventing autonomous email transmission.

All existing automated tests (**41 test cases across 10 test modules**) execute successfully and pass with zero failures (`41 passed in 2.83s`).

---

## 2. Technical Stack and Actual Repository Structure

### 2.1 Languages & Frameworks
- **Primary Language:** Python 3.12 (`>=3.12`)
- **Web API & Framework:** FastAPI (`>=0.110.0`), Starlette, Uvicorn (`>=0.28.0`)
- **Data Validation & Settings:** Pydantic (`>=2.6.0`), Pydantic Settings (`>=2.2.0`)
- **Workbook Processing:** openpyxl (`>=3.1.2`)
- **Timezone Calculations:** Standard library `zoneinfo` with `tzdata` (`>=2024.1`)
- **Credential Storage:** `keyring` (`>=25.0.0`) interfacing Windows Credential Manager / Vault
- **Testing & Quality:** Pytest (`>=8.0.0`), Pytest-Asyncio (`>=0.23.0`), Ruff (`>=0.3.0`), HTTPX (`>=0.27.0`)
- **Operator UI:** Single-page application served via FastAPI StaticFiles (`vanilla HTML5, CSS3, ES6 JavaScript`)

### 2.2 Directory Layout
```text
Outreach Intelligence Engine/
├── pyproject.toml                     # Build definition & pytest/ruff config
├── README.md                          # Comprehensive documentation & run instructions
├── .env.example                       # Environment configuration template (sanitized)
├── .gitignore                         # Strict exclusion of DBs, credentials, and private PDFs
├── config/
│   ├── settings.py                    # Global Pydantic Settings with safety defaults
│   └── university_timezones.json      # IANA timezone mappings for QS Top-120
├── data/
│   ├── outreach_engine.db             # Local SQLite database (WAL mode)
│   ├── knowledge_base/
│   │   ├── student_profile.json       # Structured profile, degree, and milestones
│   │   ├── verified_projects.json     # Substantiated project cards & domain keywords
│   │   ├── outreach_guidelines.md     # Structural and rhetorical guidelines
│   │   └── editable_research_profile.json
│   ├── seed/                          # Verification and mock test fixtures
│   └── private/                       # Excluded local-only documents
├── logs/
│   └── audit_events.jsonl             # Append-only structured audit event log
├── scripts/
│   ├── import_master_workbook.py      # Standalone CLI reconciliation script
│   ├── audit_database.py              # Database integrity verification
│   ├── run_demo.py                    # Local demonstration script
│   ├── run_session02_demo.py          # 8-stage hardened pipeline demo
│   ├── send_session03a_test.py        # Live personalized self-verification script
│   ├── setup_iitd_credentials.py      # Interactive credential configuration via keyring
│   └── verify_iitd_webmail.py         # Read-only diagnostic verification
├── src/
│   ├── database/
│   │   ├── connection.py              # SQLite connection (WAL, foreign keys, suppressions)
│   │   ├── models.py                  # Dataclass entities (Professor, Thread, Draft, etc.)
│   │   ├── repository.py              # CRUD, durable ID hashing, suppression checks
│   │   ├── workbook_sync.py           # Dynamic schema import & atomic sync-back
│   │   └── workbook_audit.py          # Data discrepancy audit
│   ├── intelligence/
│   │   ├── knowledge_base.py          # In-memory knowledge base loader & project router
│   │   ├── personalization.py         # 4-paragraph template personalization & quality gate
│   │   ├── reply_classifier.py        # 10-category multi-pattern regex classifier
│   │   └── reply_drafter.py           # Contextual follow-up and reply draft generator
│   ├── mail/
│   │   ├── credentials.py             # Credential masking & Windows Vault access
│   │   ├── imap_client.py             # Read-only RFC 3501 IMAP inspection (port 993)
│   │   ├── smtp_client.py             # Authenticated SMTP delivery client (port 465)
│   │   ├── thread_matcher.py          # Message-ID, In-Reply-To, References correlation
│   │   └── sending_gateway.py         # Policy-enforced outbound transmission gateway
│   ├── scheduler/
│   │   ├── timezone_engine.py         # IANA zoneinfo & DST target window calculator
│   │   ├── time_blocks.py             # Regional time block aggregator
│   │   └── missed_window_recovery.py  # Expiration detection and next-weekday rollover
│   ├── security/
│   │   ├── permissions.py             # Application-level role permission matrix
│   │   ├── sessions.py                # Operator session store, tokens, content hash verification
│   │   └── audit_logger.py            # Immutable dual-sink audit logging (DB + JSONL)
│   └── web/
│       ├── app.py                     # FastAPI application server
│       ├── routes/api.py              # REST API endpoints
│       └── static/                    # Operator Dashboard SPA
└── tests/                             # 41 automated pytest test cases
```

---

## 3. Core Subsystems and Architecture Analysis

### 3.1 Entry Points
1. **REST API & Web Server:** `src.web.app:app` launched via `uvicorn src.web.app:app --port 8000`. Exposes `/api` routes for authentication, metrics, drafts, scheduling, and operator inbox.
2. **CLI Scripts:**
   - `scripts/import_master_workbook.py`: Imports and synchronizes the authoritative Excel spreadsheet into SQLite.
   - `scripts/run_session02_demo.py`: Runs an 8-stage end-to-end verification pipeline in dry-run mode.
   - `scripts/setup_iitd_credentials.py`: Securely writes institutional email credentials to Windows Credential Manager.

### 3.2 Data Models & Persistence
- **Storage Engines:**
  - **SQLite Database (`data/outreach_engine.db`):** Run in Write-Ahead Logging (`WAL`) mode with `foreign_keys = ON`. Contains 8 core tables: `professors`, `universities`, `outreach_drafts`, `email_threads`, `email_messages`, `reply_classifications`, `reply_drafts`, `followup_drafts`, `suppression_list`, and `event_log`.
  - **Authoritative Excel Workbook:** Read and written via `DynamicWorkbookSync` in `openpyxl`. Uses atomic file locking (`.lock`), pre-sync timestamped backups (`.bak`), and atomic rename of temporary files (`.tmp_<pid>.xlsx`) to prevent corruption.
- **Deterministic Entity Key:**
  Professors are assigned durable, immutable primary keys using SHA-256:
  $$\text{professor\_id} = \text{"prof\_"} + \text{SHA256}(\text{university\_name.strip().lower()} \mathbin{\Vert} \text{full\_name.strip().lower()})[:16]$$
- **Suppression Safeguards:**
  Addresses and domains are checked against `suppression_list` before draft generation and dispatch. Mandatory suppressions include institutional self-domains (`@iitd.ac.in`), previously contacted faculty, and recipients associated with `BOUNCE`, `REJECTION`, or `OPT_OUT`.

### 3.3 Security & Permission Boundary
The architecture enforces strict role separation between `AUTONOMOUS_AI_ENGINE`, `HUMAN_OPERATOR`, and `SYSTEM_CRON`:
- Autonomous AI roles are structurally barred from invoking `SEND_REPLY_TRANSMISSION` or `SEND_FOLLOWUP_TRANSMISSION`.
- Outbound dispatch requires an active `OperatorSession`, authenticated via a server-side passphrase.
- All drafts approved by a human are tagged with a cryptographic SHA-256 hash of the verified text; modifications trigger an `ApprovalTamperingError`.
- Direct SMTP invocation is blocked without a single-use execution ticket issued by the session store.
- Outbound transmission is strictly disabled by default (`GATEWAY_ENABLED=False`, `DRY_RUN=True`).

### 3.4 Destination-Local Scheduler
- Target arrival window: destination-local **8:00 AM – 9:00 AM Monday through Friday**.
- Resolves time zones via IANA `zoneinfo` definitions mapped in `config/university_timezones.json`.
- Dynamically calculates Daylight Saving Time (DST) offsets and converts local target times to operator Indian Standard Time (`Asia/Kolkata`).
- Includes a `MissedWindowRecoveryEngine` that automatically detects when a local morning window has passed and rolls the dispatch to the next business day morning.

---

## 4. Antigravity Integration Audit: APIs vs. IDE Interactions

A thorough investigation of the codebase and workspace revealed the precise nature of Antigravity's role:

| Integration Aspect | Documented Findings | Classification |
| :--- | :--- | :--- |
| **Python Imports / SDKs** | Zero occurrences of `import antigravity`, Google Antigravity SDKs, or external LLM API clients (OpenAI, Anthropic, Gemini) in `src/`. | **No Programmatic API** |
| **Personalization Engine** | Deterministic string interpolation and keyword-based project routing (`personalization.py`). | **Deterministic Local Logic** |
| **Reply Classifier** | Multi-pattern regex matching across 10 categories with rule-based confidence assignment (`reply_classifier.py`). | **Rule-Based Engine** |
| **Master Workbook Origin** | Default path in `config/settings.py` points to `C:\Users\ch1251635\antigravity\proud-planck\Summer_2027_QS_Top_120_Professor_Research_Database.xlsx`. | **IDE Artifact Dependency** |
| **Research Dataset Scripts** | Directory `C:\Users\ch1251635.ACAD\antigravity\proud-planck` contains "Missions 3–14" (`verify_mission14_source_integrity.py`, `verify_actual_source_retrieval.py`, etc.). | **Interactive IDE Agent Tasks** |
| **Interactive CLI Guidance** | `scripts/setup_iitd_credentials.py` prints: `"You may now notify Antigravity that credential setup succeeded."` | **Human-in-the-Loop IDE Instruction** |

### Key Conclusion on Antigravity Integration
The existing engine **does not embed Antigravity programmatically**. Rather:
1. Antigravity acted as the **interactive pairing agent in the Antigravity IDE**, executing iterative web research, directory scraping, data extraction, and verification scripts that created the authoritative database in the IDE artifact folder `proud-planck`.
2. The Outreach Intelligence Engine was subsequently built as a self-contained local service to store, manage, schedule, and safeguard the outreach generated from that research.
3. For IOL, the integration boundary must **formalize** this interaction: instead of relying on manual chat sessions and file copying, IOL must provide a durable **Capability Contract and Registry** where research, extraction, and verification operations can be executed programmatically by any agent adapter.

---

## 5. Identification of Reusable Capabilities

The Outreach Intelligence Engine contains several high-value algorithms and workflows that are currently specialized for professor outreach, but represent general-purpose capabilities:

| Capability Domain | Engine Implementation | General-Purpose IOL Capability ID | Reusability Potential |
| :--- | :--- | :--- | :--- |
| **Entity Discovery** | Discovery of university faculty from departmental directories across QS-120. | `research.entity_discovery` | **High**: Can discover founders, researchers, companies, or candidates given directory URLs and search criteria. |
| **Source Retrieval & Provenance** | Crawling and caching directory web pages with SHA-256 provenance hashes (`verify_actual_source_retrieval.py`). | `research.source_retrieval` | **High**: Can fetch and snapshot HTML/documents with cryptographic audit trails. |
| **Structured Extraction** | Extracting names, titles, emails, profile URLs, and research focus into tabular records. | `research.structured_extraction` | **High**: Configurable JSON schema extraction over arbitrary text/HTML. |
| **Verification & Integrity Gate** | Validating email syntax, domain MX/DNS checks, profile URL presence, and evidence links without hallucinations. | `research.verification` | **High**: General fact-checking, URL liveness, and contact validity verification. |
| **Deduplication & Entity Resolution** | Deterministic composite hashing (`prof_` + sha256(domain || name)[:16]) and suppression checks. | `data.deduplication` | **Critical**: Standardized entity deduplication across heterogeneous sources. |
| **Multi-Criteria Ranking** | Scoring candidates by institutional rank (QS), keyword overlap, and evidence confidence score. | `research.ranking_prioritization` | **High**: Weighted scoring and thresholding of discovered leads. |
| **Atomic Persistence** | Dynamic schema import, atomic `.lock` files, pre-write `.bak` copies, and transactional WAL SQLite. | `data.atomic_persistence` | **Critical**: Non-destructive data store synchronization. |
| **Constrained Personalization** | 4-paragraph structured drafting with strict word count boundaries (130-180 words) and negative prompt quality gates (no GitHub/LinkedIn links). | `content.constrained_personalization` | **High**: Parameterized communication drafting adhering to strict policy bounds. |
| **Destination-Local Scheduling** | IANA `zoneinfo` computation targeting local business morning arrival (8-9 AM local), DST adjustment, and weekend rollover. | `scheduling.destination_window` | **High**: General timezone-aware notification or communication delivery. |
| **Cryptographic Human Approval Gateway** | Pre-transmission cryptographic content hashing (SHA-256), session-bound single-use execution tickets, and killswitches. | `security.human_approval_gateway` | **Critical**: General safety barrier for high-consequence agent actions (e.g., payments, email dispatch, external mutations). |

---

## 6. Verification and Existing Test Results

The existing test suite was executed in the environment:
```powershell
python -m pytest
```
**Results:**
- **Status:** 41 passed, 0 failed, 0 errors
- **Execution Time:** 2.83 seconds
- **Platform:** Windows (Python 3.12.10, Pytest 9.1.1)

### Test Suite Coverage Breakdown
- `test_adversarial_security.py`: 7 tests verifying prohibition of autonomous AI role escalation, unauthenticated requests, spoofed operator IDs, content tampering detection, direct SMTP blocking, execution ticket replay prevention, and follow-up session requirements.
- `test_credentials.py`: 4 tests verifying credential masking, environment fallbacks, and Windows Vault/keyring resolution.
- `test_end_to_end.py`: 1 comprehensive test covering the complete engine lifecycle.
- `test_permissions_and_boundary.py`: 4 tests ensuring autonomous AI cannot send replies, dry-run operator permissions, permanent suppression enforcement, and emergency stop killswitch operation.
- `test_personalization.py`: 3 tests checking four-paragraph word count bounds, project domain routing, and quality gate rejection of forbidden links.
- `test_reply_classifier.py`: 10 tests checking all 10 reply categories (interest, rejection, referral, meeting invite, bounce, opt-out, etc.).
- `test_scheduler_and_timezones.py`: 4 tests validating timezone resolution, US Eastern DST transitions, UK DST transitions, and QS rank sorting.
- `test_sending_gateway.py`: 1 test verifying batch dry-run dispatch.
- `test_thread_matcher.py`: 3 tests validating subject normalization and In-Reply-To / References correlation.
- `test_workbook_sync.py`: 4 tests checking durable ID consistency, dynamic schema import, atomic sync-back, and lockfile collision prevention.

---

## 7. Known Risks, Unknowns, and Security Considerations

1. **Hardcoded User Profile in Code & Artifacts:**
   The student identity and credentials (`Harshith N`, IIT Delhi Chemical Engineering) are currently hardcoded in `data/knowledge_base/student_profile.json` and template routines in `personalization.py`.  
   *Risk:* Prevents reuse for other domains or users.  
   *Mitigation:* IOL must abstract personas, profiles, and templates into configurable inputs.

2. **Windows Path Variance:**
   The default workbook path in `config/settings.py` points to `C:\Users\ch1251635\antigravity\...`, but on active Windows domain accounts the user directory is `C:\Users\ch1251635.ACAD\...`.  
   *Mitigation:* IOL path configurations must resolve paths relative to application roots or environment variables (`IOL_DATA_DIR`).

3. **PostgreSQL vs. SQLite Operational Availability:**
   While PostgreSQL is installed as a Windows service on the host, it requires authentication credentials that may not be configured in the user environment without interactive input.  
   *Mitigation:* The IOL durable task store must support PostgreSQL via standard `DATABASE_URL` connections, while seamlessly defaulting to a high-concurrency SQLite WAL engine when PostgreSQL credentials are not provided.

4. **Zero Live Sending Safeguard:**
   Live outreach transmission in Outreach Engine is blocked by multiple hard guards: `GATEWAY_ENABLED=False`, `DRY_RUN=True`, `CAMPAIGN_AUTHORIZED=False`, and `IITD_CSC_APPROVED=False`.  
   *Mitigation:* IOL must respect this constraint. Outreach transmission capabilities must remain strictly simulation/dry-run unless an explicit, authenticated human approval mechanism is triggered.

---

## 8. Recommended Integration Boundary for IOL

The recommended integration boundary between **IOL (Intent Operating Layer)** and the **Outreach Intelligence Engine** is an **Adapter Pattern** with clean decoupling:

```text
┌────────────────────────────────────────────────────────────────────────┐
│                   IOL Core Execution Engine                            │
│  - Intent Parser & Agent Adapter (Provider-Independent)               │
│  - Durable Task Store & State Machine (PostgreSQL / SQLite WAL)       │
│  - Asynchronous Background Worker & Execution Budgets                  │
│  - Server-Sent Events (SSE) Stream with Replay & Reconnection          │
│  - Declarative UI Schema Renderer (Tables, Cards, Timelines)           │
└───────────────────────────────────┬────────────────────────────────────┘
                                    │ Calls via Typed Interface
                                    ▼
┌────────────────────────────────────────────────────────────────────────┐
│                 IOL Capability Contract & Registry                     │
│  - Typed Inputs (Pydantic / JSON Schema)                               │
│  - Typed Outputs & Verification Metadata                               │
│  - Required Permissions & Security Boundary Policy                     │
└───────────────────────────────────┬────────────────────────────────────┘
                                    │ Implements
                                    ▼
┌────────────────────────────────────────────────────────────────────────┐
│             Outreach Engine Domain Adapter (IOL Adapter)               │
│  - `research.entity_discovery`        (Professors, Startups, Founders) │
│  - `research.structured_extraction`   (Extracts schema from raw data)  │
│  - `research.verification`            (Email & evidence validation)    │
│  - `data.deduplication`               (Domain-agnostic hash resolution)│
│  - `content.constrained_personalize`  (Configurable criteria & words)  │
│  - `scheduling.destination_window`    (Timezone & morning arrival)     │
│  - `security.human_approval_gateway`  (Cryptographic transmission gate)│
└───────────────────────────────────┬────────────────────────────────────┘
                                    │ Safely Invokes (Read/Dry-Run)
                                    ▼
┌────────────────────────────────────────────────────────────────────────┐
│           Existing Outreach Intelligence Engine (Unmodified)           │
│  `src.scheduler.timezone_engine`  •  `src.database.repository`         │
│  `src.intelligence.reply_classifier`  •  `src.database.workbook_sync`  │
└────────────────────────────────────────────────────────────────────────┘
```

By establishing this boundary:
1. **Existing Engine Preservation:** The existing codebase in `C:\Workspace\Projects\Outreach Intelligence Engine` remains 100% untouched and uncorrupted.
2. **True Generalization:** Capabilities are expressed as domain-neutral operations parameterized by target entity type (`professor`, `startup`, etc.), validation rules, and schemas.
3. **Safety Guarantee:** Live email sending remains permanently disabled behind the IOL security approval gateway.
