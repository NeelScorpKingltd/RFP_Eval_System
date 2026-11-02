# PRD: Agentic RFP Evaluation & Supplier Ranking System

Version 1.0 · Companion docs: [architecture.md](architecture.md) (how) · [AGENTS.md](AGENTS.md) (rules for coding agents)

Priority key: **Must** = mandated by the project brief. **Should** = high-impact extension (`[N]` in the brief) or small gap-filler (`[P]`). **Could** = nice to have.

---

## 1. Summary

Procurement teams compare supplier proposals by hand, which is slow, inconsistent and hard to audit. This product reads several supplier RFP proposals (PDF), has an LLM extract criterion-level scores, evidence and fine-print risks, then ranks suppliers with **deterministic Python** so that every number and every ordering is reproducible and explainable. After the ranking, a human can ask for a negotiation playbook (BAFO) aimed at the winner's weak spots.

The LLM judges content. Code decides arithmetic, benchmarking, tie-breaks and rank.

## 2. Problem and context

- Reading and scoring 4–10 long proposals against a rubric takes days and varies by reviewer.
- LLM-only ranking is unacceptable for sourcing decisions: it is not reproducible, it cannot be audited, and it is vulnerable to injected text inside proposals.
- Buyers rarely use evaluation insight in the negotiation that follows.

This build is a demonstrable, deployable reference application: public URL, runnable by a reviewer with no setup, with at least one successful run and one validation or error case on record.

## 3. Users

| Persona | Needs |
|---|---|
| **Procurement analyst** (primary) | Upload proposals, tune criteria and weights, get a defensible ranking, see evidence and risks, prepare negotiation. |
| **Sourcing lead / approver** | Understand why Rank 1 beat Rank 2, test "what if we weigh price higher", export an auditable record. |
| **Evaluator / instructor** | Try the app instantly with no key, trigger the error paths, check formulas and security behaviour. |
| **Administrator** | Change criteria and weights without code changes; supply BYOK keys or a shared demo key. |

## 4. Goals and non-goals

**Goals**

1. Reproducible ranking: same scores and metadata produce the same ranks and explanations every time.
2. Zero-config demo with the free default model; BYOK for four providers.
3. Resilient pipeline: bad PDFs, malformed LLM output and out-of-range scores never crash a run.
4. Safe against indirect prompt injection in uploaded PDFs.
5. Transparent: evidence, benchmarks, gaps, tie-break explanations and warnings visible in the UI and the export.
6. Cheap: caching avoids repeat LLM calls; negotiation tokens are spent only on request.

**Non-goals (v1)**

- User accounts, roles, multi-tenant storage.
- OCR for scanned or image-only PDFs (they are rejected with a clear message).
- Automatic contract generation or sending anything to suppliers.
- Parallel LLM calls, streaming token display, multi-round negotiation.
- Real supplier data; only synthetic proposals are in scope.

## 5. Success metrics

| Metric | Target |
|---|---|
| Determinism | 100% identical ranking and explanation strings across repeated recomputation of the same stored scores |
| Pipeline robustness | 0 unhandled exceptions on the edge-case PDF suite and fault-injection run |
| Cache effectiveness | Re-running an unchanged batch makes 0 LLM calls; a weight-only change makes 0 LLM calls |
| Time to first result (demo) | Under 90 s for 4 suppliers on a fast model, uncached |
| Recompute latency (What-If) | Under 50 ms for up to 20 suppliers × 10 criteria |
| Test quality | ≥ 95% line coverage on `domain/` and `tools/`; ≥ 85% overall |
| Reviewer success | A new reviewer reaches a ranked leaderboard in under 3 minutes with no key and the demo-suppliers button |

## 6. Scope summary

In scope: five Streamlit screens plus sidebar; SQLite persistence; LangGraph orchestration; PyMuPDF ingestion with sanitisation; BYOK LLM factory; validation and fault demo; deterministic ranking; What-If simulator; Risk Radar; on-demand BAFO playbook; unified JSON export; four synthetic PDFs; Streamlit Community Cloud deployment; README; recorded walkthrough.

## 7. User stories and acceptance criteria

**US-1 Configure criteria.** As an analyst, I can edit criteria and weights so the rubric matches the procurement.
- Given the database is empty, when the app boots, then five default criteria totalling 100% exist and are shown.
- Given I change active weights to total 95, when I view Screen 1 or 2, then a blocking banner appears and **Evaluate** is disabled.
- Given weights total 100 (within 0.01) and I click **Save**, then changes persist across reload without code changes.

**US-2 Upload and sanitise proposals.** As an analyst, I can upload several PDFs with metadata and know immediately which are unusable.
- Given a 12 MB file, a 16-page file, or an image-only PDF, then that file is rejected with a specific message and the others remain usable.
- Given fewer than 2 valid suppliers, or a missing name, invalid date or missing rating, then **Evaluate** is disabled with the reason shown.
- Given a PDF containing "ignore previous instructions", then a security finding is shown and logged; the file is still evaluated safely.

**US-3 Run an evaluation.** As an analyst, I can watch the pipeline run and get a ranked leaderboard.
- Given valid inputs, when I click **Evaluate**, then a live tracker shows sanitise, cache, evaluate, validate, score, benchmark, rank, persist, and completes with one `RFP_RUN_ID`.
- Given an identical batch run again, then no LLM calls occur and results appear immediately.
- Given only weights changed, then no LLM calls occur and scores are recomputed.

**US-4 Understand the ranking.** As an approver, I can see why one supplier beat another.
- The leaderboard shows Rank, Supplier, Absolute Score, PPI, Submission Date, Experience Rating with progress columns.
- Screen 5 lists one explanation per adjacent pair, in the frozen formats, including the tie-break tier used.
- Screen 4 shows per-criterion score, benchmark, gap, relative %, weight, evidence and justification.

**US-5 Test sensitivity.** As an approver, I can move weights and see rank changes without new LLM calls.
- Given I move a slider, then weights renormalise to 100, ranks update instantly, and badges show movements such as "#3 to #1".

**US-6 See hidden risks.** As an analyst, I can see fine-print risks side by side.
- Risk Radar shows severity, category, issue and verbatim excerpt per supplier. The synthetic BrightPath proposal surfaces pass-through travel expenses, capped SLA credits and customer staffing dependencies.

**US-7 Prepare negotiation.** As an analyst, I can generate a BAFO playbook for the winner on demand.
- Given a completed run, when I click **✨ Generate BAFO Negotiation Playbook for {winner}**, then a structured playbook renders, is saved to the Rank 1 row, and can be downloaded as Markdown.
- Given I never click the button, then no negotiation tokens are consumed.
- The playbook never names competitors.

**US-8 Export an audit record.** As an approver, I can download one JSON file for the whole run.
- Export includes run id, criteria, benchmarks, warnings, tie-break explanations, rankings with scorecards, and the playbook when it exists.

**US-9 Try it with no key.** As a reviewer, I can run the app with the free default model.
- Given demo mode is selected and `st.secrets` is configured, then a full run works without entering a key. Given secrets are missing, the option is disabled with an explanation.

**US-10 See the error handling.** As a reviewer, I can trigger the validation paths.
- With **Simulate Malformed LLM Output** on, one supplier receives a score of 14 (max 10) and a missing criterion; the run completes, the score is clipped to 10, the missing criterion is `0`, and both warnings appear on Screen 5. The run does not crash and is not cached.

## 8. Functional requirements

IDs are used in commit messages, test names and the traceability matrix (§18).

### Setup and persistence

| ID | Requirement | Priority |
|---|---|---|
| FR-SETUP-01 | On every boot run `init_and_seed_db()`: create three tables if missing; if `evaluation_criteria` is empty, seed 5 default criteria totalling 100% | Must |
| FR-SETUP-02 | Standalone `scripts/init_db.py` calls the same routine | Must |
| FR-DB-01 | Tables `evaluation_criteria`, `rfp_runs`, `supplier_results` exactly as in the brief | Must |
| FR-DB-02 | Persist a complete run under one `RFP_RUN_ID`, in one transaction, without negotiation text | Must |
| FR-DB-03 | Additive columns `negotiation_playbook_json`, `cache_hash` | Must |
| FR-DB-04 | Index on `cache_hash` | Should |

### Criteria

| ID | Requirement | Priority |
|---|---|---|
| FR-CRIT-01 | Show active criteria with description, weight, max score from SQLite in `st.data_editor` | Must |
| FR-CRIT-02 | Edit name, description, weight, max score, active flag, persisted without code changes | Must |
| FR-CRIT-03 | 100% weight gate (`abs(sum - 100.0) < 0.01`); blocking banner on Screens 1 and 2; Evaluate disabled | Must |
| FR-CRIT-04 | Reset criteria to the 5 defaults | Could |

### Supplier input and ingestion

| ID | Requirement | Priority |
|---|---|---|
| FR-SUP-01 | Multi-file PDF upload with Supplier Name, Submission Date, Historical Experience Rating per file | Must |
| FR-SUP-02 | Pre-flight sanitisation: size ≤ 10 MB, pages ≤ 15, stripped text length > 100; specific per-file messages | Must |
| FR-SUP-03 | Block run if < 2 valid suppliers, or any supplier lacks name, valid date, or rating (0–5); names unique | Must |
| FR-SUP-04 | Regex injection scan; findings displayed and logged | Must |
| FR-SUP-05 | **Load demo suppliers** button prefilling the four synthetic PDFs and metadata | Should |

### Pipeline and agents

| ID | Requirement | Priority |
|---|---|---|
| FR-PIPE-01 | Orchestrate the 10-step pipeline with LangGraph / Python | Must |
| FR-PIPE-02 | Live step tracker with `st.status` and `st.progress` | Must |
| FR-PIPE-03 | Run lifecycle `IN_PROGRESS` → `COMPLETED` / `FAILED`; ID format `RUN-YYYYMMDD-NNN` | Must |
| FR-PIPE-04 | One supplier's failure never aborts the batch; invalid API key aborts with a clear message | Must |
| FR-PIPE-05 | Re-check weight gate and supplier preconditions inside the orchestrator | Must |

### Cache

| ID | Requirement | Priority |
|---|---|---|
| FR-CACHE-01 | SHA-256 of PDF bytes plus criteria JSON; a hit bypasses the LLM | Must |
| FR-CACHE-02 | Weight-only changes reuse cached evaluations and recompute scores | Must |
| FR-CACHE-03 | Session and SQLite tiers; hits and misses shown in run details | Must |
| FR-CACHE-04 | Fault-mode results are never cached or served from cache | Must |

### LLM layer

| ID | Requirement | Priority |
|---|---|---|
| FR-LLM-01 | `get_llm_client(provider, api_key)` for OpenAI, Gemini, Anthropic, Groq | Must |
| FR-LLM-02 | Sidebar: provider select, masked key input | Must |
| FR-LLM-07 | Check a newly entered provider key with a small request; show live status and gate evaluation on failure | Should |
| FR-LLM-03 | **Use Free Default Demo Model** reading `st.secrets` | Must |
| FR-LLM-04 | Self-healing JSON loop: strip fences, 2 attempts, parser-error feedback, zero-fallback | Must |
| FR-LLM-05 | Evaluation output schema incl. `criteria[]` and `procurement_risks[]` | Must |
| FR-LLM-06 | Model IDs configurable without code change | Should |

### Validation

| ID | Requirement | Priority |
|---|---|---|
| FR-VAL-01 | Check JSON has `supplier_name`, `criteria`, `overall_summary` | Must |
| FR-VAL-02 | Missing active criterion → score 0, fixed justification string, warning | Must |
| FR-VAL-03 | Clip scores to `[0, max_score]` with warning | Must |
| FR-VAL-04 | Sidebar toggle **Simulate Malformed LLM Output** works with a verified BYOK or demo key; injects a 14-on-10 score and an omitted criterion for one supplier | Must |

### Scoring and ranking

| ID | Requirement | Priority |
|---|---|---|
| FR-SCORE-01 | Absolute weighted score `Σ (score / max) × weight` | Must |
| FR-SCORE-02 | Criterion benchmark = max valid score across suppliers | Must |
| FR-SCORE-03 | Criterion gap = score − benchmark (0 for leader, negative otherwise) | Must |
| FR-SCORE-04 | Relative performance % with safe zero-division | Must |
| FR-SCORE-05 | PPI = Σ relative % × normalised weight | Must |
| FR-SCORE-06 | 4-tier stable sort: PPI desc, date asc, experience desc, name asc | Must |
| FR-SCORE-07 | `tie_break_explanations` for each adjacent pair, in frozen formats | Must |
| FR-SCORE-08 | Sequential ranks 1..n; LLM never computes or influences them | Must |
| FR-SCORE-09 | What-If simulator: sliders, auto-normalise to 100%, instant recompute, ⬆️/⬇️ deltas, zero LLM calls | Should |

### Security

| ID | Requirement | Priority |
|---|---|---|
| FR-SEC-01 | XML sandbox `<untrusted_proposal_content>` plus sandwich instruction | Must |
| FR-SEC-02 | Neutralise embedded closing tags | Should |
| FR-SEC-03 | Never log, persist or export API keys | Must |
| FR-SEC-04 | LLM- and PDF-derived text is rendered escaped; no `unsafe_allow_html` on it | Must |
| FR-SEC-05 | Parameterised SQL only | Must |
| FR-SEC-06 | Detect hidden (white or tiny) text; strip from LLM input by default | Should |

### UI

| ID | Requirement | Priority |
|---|---|---|
| FR-UI-01 | Sidebar: BYOK, demo-model option, fault toggle | Must |
| FR-UI-02 | Screen 1 Criteria | Must |
| FR-UI-03 | Screen 2 Supplier Input with validation and sanitisation log | Must |
| FR-UI-04 | Screen 3 tracker, leaderboard with `ProgressColumn`, simulator | Must (simulator Should) |
| FR-UI-05 | Screen 4 criteria breakdown with `ProgressColumn`, evidence, justification | Must |
| FR-UI-06 | Screen 4 Procurement Risk Radar grid | Should |
| FR-UI-07 | Screen 5 run details: run id, warnings, tie-break explanations, cache stats, JSON download | Must |
| FR-UI-08 | Custom CSS: `fadeInSlide`, `softPulse`, `.animated-card`, `.winner-banner` | Should |
| FR-UI-09 | Winner banner; values HTML-escaped | Should |
| FR-UI-10 | Gated stage progression with a session-only Cancel run action | Must |
| FR-UI-11 | Sidebar Previous runs screen reloads completed SQLite results without an LLM call | Must |

### Negotiation

| ID | Requirement | Priority |
|---|---|---|
| FR-NEG-01 | On-demand button on Screen 5: `✨ Generate BAFO Negotiation Playbook for [Winner]` | Should |
| FR-NEG-02 | Decoupled from steps 1–9; no tokens spent unless clicked | Should |
| FR-NEG-03 | Output validated as `WinnerNegotiationPlaybook` (Pydantic) | Should |
| FR-NEG-04 | Persist to `supplier_results.negotiation_playbook_json` for the Rank 1 row | Should |
| FR-NEG-05 | Rendered matrix and Markdown briefing download | Should |
| FR-NEG-06 | Prompt grounded in the winner's negative gaps and proposal excerpts; no competitor names | Should |

### Export and deliverables

| ID | Requirement | Priority |
|---|---|---|
| FR-EXP-01 | Unified run JSON per the brief's schema, downloadable | Must |
| FR-EXP-02 | Sample export from a completed 4-supplier run committed to the repo | Must |
| FR-DEL-01 | Modular source with BYOK factory and `requirements.txt` | Must |
| FR-DEL-02 | DB creation and seed script plus boot routine | Must |
| FR-DEL-03 | Four synthetic PDFs (`Apex_Systems.pdf`, `BrightPath_Tech.pdf`, `NexaWorks.pdf`, `Orbit_Digital.pdf`) | Must |
| FR-DEL-04 | Public Streamlit Community Cloud deployment with `st.secrets` configured | Must |
| FR-DEL-05 | README: setup, architecture diagram, formulas, BYOK, security, assumptions, screenshots | Must |
| FR-DEL-06 | Walkthrough covering one successful run and at least one error case | Must |

## 9. Non-functional requirements

| ID | Requirement |
|---|---|
| NFR-DET-01 | Ranking and explanation output is deterministic and independent of input order |
| NFR-PERF-01 | Cache-hit re-run for 4 suppliers completes in under 3 s excluding UI render |
| NFR-PERF-02 | Uncached 4-supplier run under 90 s with a fast model; PDF limits bound input size |
| NFR-PERF-03 | What-If recompute under 50 ms for up to 20 suppliers × 10 criteria |
| NFR-REL-01 | No unhandled exception or traceback reaches the user |
| NFR-REL-02 | App starts from an empty or missing database (ephemeral storage) |
| NFR-SEC-01 | Prime directives in AGENTS.md §2 hold; keys never leave memory |
| NFR-PRIV-01 | Proposal text is sent only to the provider the user selected; stated in README |
| NFR-MAINT-01 | Layering enforced by `tests/test_architecture.py`; `ruff`, `mypy` clean |
| NFR-TEST-01 | Coverage targets in §5; CI has no network access |
| NFR-COST-01 | Negotiation LLM calls occur only on explicit click |
| NFR-PORT-01 | Runs locally and on Streamlit Community Cloud without code changes |

## 10. Screens (summary)

Layout and component detail are in architecture.md §12.

1. **Criteria:** editable table, gate banner.
2. **Supplier Input:** uploader, metadata, sanitisation log, security findings, demo-load button.
3. **Run & Leaderboard:** Evaluate, live tracker, leaderboard, What-If simulator.
4. **Scorecard & Risk Radar:** per-supplier breakdown and risk grid.
5. **Playbook & Run Details:** winner banner, BAFO button and matrix, run metadata, JSON and Markdown downloads.

Global sidebar: provider, masked key, demo-model option, fault-demo toggle.

## 11. Synthetic data requirements

Four fictional proposals, 2–4 pages each, generated by `scripts/generate_synthetic_pdfs.py` (PyMuPDF) and committed. Each contains all six sections: executive summary and requirement understanding; proposed solution and approach; timeline, team and milestones; price table with assumptions; security, compliance and risk controls; support model, experience and references.

Intended signal strengths (design intent for authors and manual review; automated tests do not assert LLM scores):

| Supplier | Technical | Implementation | Commercial | Security | Support | Notes |
|---|---|---|---|---|---|---|
| Apex Systems | High | Medium | Low–Medium | High | Medium–High | Enterprise design, higher price, moderate schedule |
| BrightPath Tech | Medium | Medium–High | High | Low | Low | Lowest price, fast timeline, weak compliance detail, limited experience; buried caveats: pass-through travel expenses, capped SLA credits, customer staffing dependencies |
| NexaWorks | Medium–High | High | Medium–High | Medium | High | Balanced; strongest implementation plan and support model |
| Orbit Digital | Low–Medium | Medium | Medium | Medium | High | Strong experience and references; vague integration plan |

Suggested demo metadata (`sample_data/suppliers.json`): Apex 2026-10-10 / 4.8; NexaWorks 2026-10-12 / 4.5; BrightPath 2026-10-14 / 3.4; Orbit 2026-10-15 / 4.6.

Edge-case PDFs for the error demo (generated, not hand-made): 16-page file, image-only file, a file containing an injection phrase, and an oversize file produced on demand into a temp directory (not committed).

## 12. Demonstration script (acceptance walkthrough)

**Success path**
1. Open the app, select **Use Free Default Demo Model**.
2. Screen 1: confirm 5 criteria, 100%.
3. Screen 2: **Load demo suppliers**; show sanitisation results.
4. Screen 3: **Evaluate**; show the live tracker; show the leaderboard with progress columns; move a What-If slider and show rank deltas.
5. Screen 4: open a scorecard (evidence, gaps) and the Risk Radar (BrightPath caveats).
6. Screen 5: read tie-break explanations; click **✨ Generate BAFO Negotiation Playbook**; download the Markdown briefing and the Unified Run JSON.
7. Re-run unchanged: show cache hits and zero LLM calls.

**Error and validation paths (at least one required; show all three)**
- Set a weight so the total is 95: banner appears, Evaluate disabled.
- Upload the 16-page and image-only PDFs: specific rejection messages; the rest remain usable.
- Enable **Simulate Malformed LLM Output**: run completes; clipped score and filled criterion appear as warnings on Screen 5.

## 13. Assumptions and constraints

- Python 3.11+, Streamlit, SQLite, LangGraph, PyMuPDF are fixed by the brief.
- Weights are stored as percentages; the absolute score is 0–100 (ADR-001).
- Experience rating is a number from 0.0 to 5.0.
- Criterion IDs are stable; criteria are deactivated, not deleted, in v1.
- The shared demo key is low-limit and revocable; BYOK keys live in the browser session only.
- A single user per session; concurrent sessions share one SQLite file on the host.
- Provider model IDs are configuration and must be verified against current provider availability before deployment; deployment defaults are recorded in architecture.md ADR-009 and can be overridden through environment variables.

## 14. Risks and mitigations

| Risk | Impact | Mitigation |
|---|---|---|
| Indirect prompt injection in proposals | Inflated scores | Sandbox, sandwich, scanner, hidden-text stripping, no weights in prompt, deterministic scoring, scores clipped |
| LLM returns malformed or partial JSON | Crash or silent bad scores | Self-healing retry, validation normalisation, warnings, zero-fallback |
| Provider model retired or renamed | Runs fail at deployment | Config-driven IDs, env override, verify at M9, clear auth and model errors |
| Shared demo key abused or exhausted | Demo fails for reviewers | Low-limit key, rate-limit error message, BYOK fallback, cache |
| Ephemeral Streamlit storage wipes history | Lost runs | Boot-time init, sample data in repo, export prompt, committed sample JSON |
| Float rounding creates false ties or false separation | Wrong rank explanations | Round half-up at 2 decimals before sorting (ADR-003); boundary tests |
| LLM scores vary run to run | Perceived inconsistency | Temperature 0, cache by content hash, scores persisted, deterministic downstream |
| Long PDFs exceed context window | Truncation or errors | 15-page cap; extracted text capped per prompt; rejection messages |
| Proposal data sent to third-party LLM | Privacy concern | Synthetic data only; README states data flow; user chooses provider |
| Streamlit rerun quirks lose state | Broken UX | Typed `session_state` accessors, keyed widgets, radio navigation, AppTest coverage |

## 15. Milestones

| M | Scope | Exit criteria |
|---|---|---|
| M0 | Scaffold, tooling, CI, architecture test | `make check` green on empty skeleton |
| M1 | Domain models, errors, DB schema and seed, repositories, weight gate | FR-SETUP-*, FR-DB-*, FR-CRIT-03 logic tested; boot from empty DB works |
| M2 | Ranking tool, validation tool, rounding, sensitivity service | Golden vector passes; all FR-SCORE-*, FR-VAL-01..03 tests green |
| M3 | Document tool, security helpers, PDF generators | FR-SUP-02/04, FR-SEC-01/02/06 tests green; 4 + edge PDFs generated |
| M4 | LLM Protocol, factory, providers, JSON retry, prompts, fault injection, fake client | FR-LLM-*, FR-VAL-04 tests green with fakes |
| M5 | Evaluation agent, cache | FR-CACHE-* tests green, including weight-only and fault-mode cases |
| M6 | LangGraph orchestrator, persistence, export | End-to-end integration test with fake LLM; FR-PIPE-*, FR-DB-02, FR-EXP-01 |
| M7 | Streamlit UI, tracker, simulator, Risk Radar, CSS | AppTest flows green; manual run of success path on fake and real model |
| M8 | Negotiation agent, playbook UI, briefing download | FR-NEG-* tests green; playbook persisted to Rank 1 row |
| M9 | Hardening, README, sample JSON, deployment, walkthrough | FR-DEL-* complete; walkthrough recorded; public URL verified from a clean browser |

M2, M3 and M4 can proceed in parallel after M1.

## 16. Test and acceptance plan

- **Unit:** every requirement in §8 with a test named by its ID.
- **Golden:** ranking vectors from architecture.md §10.5 plus zero-benchmark, Tier 3, Tier 4 and rounding-edge vectors.
- **Integration:** real graph, temp SQLite, `FakeLLMClient` scenarios (clean, fenced, retry-then-valid, always malformed, out-of-range, missing criterion, auth error); persistence and export assertions; weight-only change causes zero LLM calls.
- **UI:** AppTest for the gate banner, disabled Evaluate, supplier validation, leaderboard from a fixture run.
- **Live (opt-in):** one smoke run per configured provider; soft expectations only (for example Apex leads on Security; BrightPath lowest on Security).
- **Acceptance:** the walkthrough in §12 passes on the deployed URL.

## 17. Open decisions

These need an owner's answer; coding agents must not resolve them unilaterally (AGENTS.md §11). Defaults in brackets are what the architecture currently assumes.

| # | Question | Default |
|---|---|---|
| Q1 | Should the cache key also include provider and model, so scores from different models are not mixed? | [No, per the brief's `(pdf_bytes + criteria)`; model recorded in `meta`] |
| Q2 | Is "tied on PPI" defined at 2-decimal precision? | [Yes, ADR-003] |
| Q3 | Strip hidden or white text before sending to the LLM, or only flag it? | [Strip and flag] |
| Q4 | Allow adding or deleting criteria in the UI, or only edit and deactivate? | [Edit and deactivate only] |
| Q5 | Which exact model IDs per provider at deployment? | [Spec IDs as defaults; verify at M9] |
| Q6 | Pinned Python and Streamlit versions for Community Cloud? | [Python 3.11, latest stable Streamlit at M0, pinned] |

## 18. Traceability matrix

| Brief section | Requirements | Modules (architecture.md) | Primary tests |
|---|---|---|---|
| 1 Stack | FR-DEL-01, NFR-PORT-01 | all | architecture test, deployment check |
| 2–3 Components, pipeline | FR-PIPE-01..05 | `orchestration/` | integration graph tests |
| 4 SQLite, criteria, gate | FR-SETUP-*, FR-DB-*, FR-CRIT-* | `db/`, `tools/weight_gate` | schema/seed, gate boundary tests |
| 5 Scoring, ranking, simulator | FR-SCORE-01..09 | `tools/ranking_tool`, `services/sensitivity` | golden vectors, permutation, identity-with-simulator |
| 6 Synthetic PDFs | FR-DEL-03, §11 | `scripts/generate_*` | page-count, section-heading checks |
| 7 LLM, security, validation, export | FR-LLM-*, FR-SEC-*, FR-VAL-*, FR-CACHE-*, FR-EXP-* | `llm/`, `security/`, `tools/validation_tool`, `tools/cache`, `services/export` | fake-LLM scenarios, injection tests, export schema test |
| 7.6 Negotiation | FR-NEG-* | `agents/negotiation_agent`, `services/briefing` | prompt-content, persistence tests |
| 8 UI | FR-UI-*, FR-SUP-* | `ui/` | AppTest flows |
| 9 Deliverables | FR-DEL-*, FR-EXP-02 | repo root, `sample_data/` | release checklist |

## 19. Glossary

- **BAFO:** Best and Final Offer; the closing round of supplier negotiation.
- **BYOK:** Bring Your Own Key; the user supplies an LLM API key.
- **PPI (Peer Performance Index):** weighted average of a supplier's per-criterion score relative to the best peer on that criterion, as a percentage.
- **Benchmark:** the highest valid score on a criterion across all suppliers in the run.
- **Gap:** a supplier's score minus the benchmark for a criterion.
- **Sandwich defense:** instructions placed both before and after untrusted content so the model keeps treating it as data.
- **HITL:** human in the loop; here, the negotiation playbook runs only when a person asks.

