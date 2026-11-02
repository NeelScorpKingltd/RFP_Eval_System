# AGENTS.md

Operating manual for AI coding agents 
 working on the **Agentic RFP Evaluation & Supplier Ranking System**.

Read this file in full before touching code.

| Companion doc | Use it for |
|---|---|
| [PRD.md](PRD.md) | What and why. Requirement IDs (`FR-*`, `NFR-*`), acceptance criteria, milestones, open decisions. |
| [architecture.md](architecture.md) | How. Module contracts, schemas, formulas, pipeline, security model, ADRs. |


---

## 1. Project in one paragraph

A Streamlit app that evaluates two or more supplier RFP proposals (PDF) against weighted criteria stored in SQLite. An LLM reads each proposal and returns structured criterion scores, evidence, justifications and procurement risks. **All arithmetic, benchmarking, tie-breaking and ranking is deterministic Python.** After ranking, an on-demand negotiation agent drafts a Best-and-Final-Offer (BAFO) playbook for the Rank 1 supplier. Stack: Python 3.11+, Streamlit, SQLite (`sqlite3`), LangGraph, PyMuPDF, Pydantic v2, and a BYOK LLM factory for OpenAI, Gemini, Anthropic and Groq. Deployed on Streamlit Community Cloud, where disk is ephemeral.

---

## 2. Prime directives

Violating any of these is a bug, even if every test passes.

1. **The LLM never decides numbers or order.** It returns per-criterion scores, evidence, justifications and risks. It is never asked for totals, weights, benchmarks, PPI, tie-breaks or rank. Prompts do not contain criterion weights.
2. **One scoring code path.** Formulas live only in `rfp_eval/tools/ranking_tool.py`. The orchestrator, the What-If simulator and the export all call it. Never re-implement a formula in UI code.
3. **PDF text and LLM output are hostile.** Wrap PDF text in `<untrusted_proposal_content>` tags with the sandwich instruction, neutralise any closing tag inside the text, and never pass PDF- or LLM-derived strings to `st.markdown(..., unsafe_allow_html=True)`.
4. **Spec contracts are frozen.** Table and column names, unified-JSON keys, the 4-tier tie-break order, formula definitions, and the exact warning and explanation string formats (architecture.md §10) change only through an ADR plus a PRD update. You may add optional keys or columns; never rename or remove.
5. **Gate before run.** Active weights sum to 100 (`abs(sum - 100.0) < 0.01`), at least 2 valid suppliers, complete metadata. Enforced in the UI and again inside the orchestrator.
6. **Fail soft per supplier, fail loud per run.** One bad PDF or one malformed LLM reply never crashes the batch (zero-fallback plus a warning). A systematic failure such as an invalid API key aborts the run with a clear message and `status = FAILED`.
7. **Secrets stay in memory.** BYOK keys live only in session state or process memory. Never log, persist, export, or echo them in an error message. Use `pydantic.SecretStr` and `security/redaction.py`.
8. **Demo-fault output is never cached.** Results produced with "Simulate Malformed LLM Output" are neither read from nor written to the cache.
9. **Deterministic means reproducible.** Same inputs give byte-identical rankings and explanations. No `random`, no `datetime.now()` inside `tools/` (inject a clock), no reliance on dict or set order, no unstable sorts, no float equality on PPI (see ADR-003).
10. **Tests ship with code.** Nothing in `domain/`, `tools/`, `db/`, `security/` or `llm/` merges without unit tests.

---

## 3. Commands

```bash
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt -r requirements-dev.txt

make setup      # install deps + pre-commit hooks
make initdb     # python scripts/init_db.py  (idempotent create + seed)
make samples    # generate sample_data/proposals/*.pdf and edge_cases/*.pdf
make run        # streamlit run app.py
make test       # pytest -q (no network; fake LLM only)
make lint       # ruff check . && ruff format --check .
make types      # mypy rfp_eval
make check      # lint + types + test  <-- must pass before you finish any task
make live       # pytest -m live_llm  (opt-in, needs real keys in env; never in CI)
```

Run `make check` before declaring any task done. If a command above does not exist yet, creating it is part of milestone M0.

---

## 4. Repository map

Flat package layout (no `src/`) so `streamlit run app.py` and Streamlit Community Cloud resolve `rfp_eval` without an editable install.

```text
rfp-evaluator/
├── app.py                       # thin Streamlit entrypoint: config, CSS, boot, nav, route to screens
├── Makefile
├── pyproject.toml               # ruff, mypy, pytest config
├── requirements.txt             # runtime deps, pinned at M0
├── requirements-dev.txt
├── AGENTS.md  PRD.md  architecture.md  README.md
├── .streamlit/
│   ├── config.toml
│   └── secrets.toml.example     # DEFAULT_LLM_PROVIDER, DEFAULT_LLM_API_KEY (real file is gitignored)
├── data/                        # runtime SQLite file (gitignored, .gitkeep)
├── sample_data/
│   ├── proposals/               # 4 synthetic PDFs (committed)
│   ├── edge_cases/              # too_many_pages.pdf, image_only.pdf, injection_demo.pdf
│   ├── suppliers.json           # demo metadata for the "Load demo suppliers" button
│   └── sample_run.json          # exported unified run JSON (deliverable)
├── scripts/
│   ├── init_db.py
│   ├── generate_synthetic_pdfs.py
│   ├── generate_edge_case_pdfs.py
│   └── export_sample_run.py
├── rfp_eval/
│   ├── config.py                # limits, model IDs, prompt version, precision constants
│   ├── logging_setup.py
│   ├── domain/                  # pure Pydantic models, enums, errors
│   ├── db/                      # connection, schema + init_and_seed_db, repositories
│   ├── security/                # injection_scanner, sandbox (XML wrap + sandwich), redaction
│   ├── tools/                   # document_tool, validation_tool, ranking_tool, weight_gate, cache, rounding
│   ├── llm/                     # base Protocol, factory, providers/, json_retry, prompts, fault_injection, fake
│   ├── agents/                  # evaluation_agent, negotiation_agent
│   ├── orchestration/           # state, nodes, graph, progress (reporter Protocol), runner
│   ├── services/                # sensitivity, export, briefing, run_loader
│   └── ui/                      # state, styles, components, sidebar, readiness, reporter, screens/
└── tests/
    ├── unit/  integration/  ui/  fixtures/
    └── test_architecture.py     # enforces the layering table below
```

Full responsibilities per module are in architecture.md §5.

---

## 5. Layering rules

`tests/test_architecture.py` parses imports with `ast` and fails the build on violations.

| Layer | May import | Must not import |
|---|---|---|
| `domain` | stdlib, pydantic | any other `rfp_eval` package |
| `tools` | `domain`, `config`, `security` | `llm`, `db`, `agents`, `orchestration`, `streamlit` |
| `tools.ranking_tool`, `tools.rounding`, `tools.weight_gate` | `domain`, stdlib only | everything else |
| `db` | `domain`, `config` | `llm`, `tools`, `agents`, `streamlit` |
| `security` | `domain`, `config`, stdlib | `llm`, `db`, `streamlit` |
| `llm` | `domain`, `config`, `security.redaction` | `db`, `tools.ranking_tool`, `streamlit` |
| `agents` | `domain`, `llm`, `security` | `db`, `streamlit` |
| `orchestration` | `domain`, `tools`, `agents`, `db`, `llm`, `security` | `streamlit` |
| `services` | `domain`, `tools`, `db`, `agents` | `streamlit` |
| `ui` | all of the above, via `services` and `orchestration` | (only layer allowed to import `streamlit`) |

Direction of dependency is inward. `domain` is the centre and knows nothing about SQLite, LLMs or Streamlit.

---

## 6. Runtime agent contracts (summary)

The *product's* agents, as opposed to you, the coding agent. Full contracts are in architecture.md §7.

| Component | Kind | Input → Output | Uses LLM | Module |
|---|---|---|---|---|
| Orchestrator | LangGraph controller | `RunRequest` → `RunResult` | no | `orchestration/` |
| Document Tool | deterministic | PDF bytes → `SanitizedDocument` or `DocumentRejected` | no | `tools/document_tool.py` |
| Evaluation Agent | LLM agent | `SanitizedDocument` + criteria → raw JSON payload | yes | `agents/evaluation_agent.py` |
| Validation Tool | deterministic | raw payload + criteria → `ValidatedEvaluation` + warnings | no | `tools/validation_tool.py` |
| Ranking Tool | deterministic | validated scores + metadata + criteria → `RankingResult` | no | `tools/ranking_tool.py` |
| Negotiation Agent | LLM agent, on-demand | Rank 1 gaps + source text → `WinnerNegotiationPlaybook` | yes | `agents/negotiation_agent.py` |

The Negotiation Agent is never part of the batch graph (steps 2–9). It runs only when the user clicks the Screen 5 button.

---

## 7. Coding standards

- **Python 3.11+**, full type hints, `from __future__ import annotations`. `mypy --strict` on `domain/`, `tools/`, `security/`, `db/`; plain `mypy` elsewhere.
- **Pydantic v2** for every structure that crosses a module boundary. No bare dicts between layers; dicts are allowed only at JSON edges (LLM reply, DB column, export).
- **Pure functions first.** Side effects (DB, network, clock, randomness, Streamlit) enter through injected dependencies (`Deps` in `orchestration/runner.py`).
- **Small modules, one job.** Aim for under 300 lines per file and under 40 per function. Split before you exceed them.
- **Errors:** raise typed exceptions from `domain/errors.py` (`DocumentRejected`, `GateViolation`, `LLMAuthError`, `LLMTransportError`, `LLMOutputError`, `ConfigError`). Catch them only at boundaries: the per-supplier loop in nodes, and the UI. Never `except Exception: pass`.
- **Logging:** stdlib `logging` via `logging_setup.py`, with `run_id` in context. No `print`. No keys, no full proposal text in logs.
- **SQL:** parameterised queries only; one connection per operation via a context manager; `PRAGMA foreign_keys = ON`. SQL lives only in `db/`.
- **Numbers:** round only at the persistence and presentation edges, using `tools/rounding.round_half_up`. Never compare floats with `==`.
- **Docstrings:** every public function states purpose, args, returns, raises. Formula functions quote the formula from architecture.md §10.
- **UI strings** that come from PDFs, the LLM or user metadata are rendered with `st.text`, `st.caption`, `st.code`, or `html.escape` first.
- **Style:** `ruff` (rules E, F, I, B, UP, SIM, S, PL, RUF) plus `ruff format`. Imports sorted. No wildcard imports. No commented-out code.
- **Dependencies:** adding one needs a reason in the PR description. Prefer stdlib or what is already pinned (PyMuPDF can also generate the synthetic PDFs, so no ReportLab).

---

## 8. Testing rules

| Marker | Scope | Network | Runs in `make test` |
|---|---|---|---|
| `unit` | single module, pure | no | yes |
| `integration` | orchestrator + SQLite (temp file) + `FakeLLMClient` | no | yes |
| `ui` | `streamlit.testing.v1.AppTest` smoke flows | no | yes |
| `live_llm` | real provider smoke | yes | no (opt-in via `make live`) |

Minimum test set per component:

- **ranking_tool:** golden vector from architecture.md §10.5; each tier of the tie-break; zero-benchmark division; permutation invariance (shuffle inputs, same ranks); ranks are exactly `1..n`; explanation strings match the templates byte for byte.
- **validation_tool:** missing criterion → `0` with the exact justification string; `14 → 10` clip with the exact warning; negative → `0`; non-numeric score → `0`; unknown criterion id ignored with warning; duplicate ids; unparseable payload → all-zero fallback.
- **weight_gate:** boundary cases `99.99`, `100.0`, `100.009`, `100.011`; decimal-style weights; no active criteria.
- **document_tool:** oversize, 16 pages, image-only, encrypted, non-PDF bytes, empty text, injection phrase detected, closing-tag breakout neutralised.
- **cache:** hash is stable across criterion order; changes when description or `max_score` changes; does **not** change when only weight changes; fault-mode runs neither read nor write.
- **json_retry:** fenced JSON, prose around JSON, trailing comma → retry succeeds, two failures → fallback.
- **sensitivity:** result equals `ranking_tool` output for the same weights (identity test, not a reimplementation).
- **negotiation_agent:** prompt contains no competitor names; invalid JSON handled; playbook persisted to the Rank 1 row only.
- **ui:** AppTest covers gate banner, disabled Evaluate button, supplier validation messages, leaderboard render from a fixture `RunResult`.

CI never touches the network. All LLM behaviour in tests comes from `llm/fake.py`.

---

## 9. How to work

1. **Locate the requirement.** Find the `FR-*` IDs in PRD.md for your task. Put them in commit messages and test names (`test_fr_score_06_tier2_earlier_date_wins`).
2. **Read the contract.** Open the matching section of architecture.md. If it is ambiguous, check the ADR list (§16) before deciding.
3. **Tests first** for anything in `tools/`, `db/`, `security/`, `llm/json_retry`.
4. **Smallest vertical slice.** Make it pass, then refactor.
5. **`make check`.** Fix everything it reports.
6. **Update docs** if you changed a contract, added an ADR, or resolved an open decision.
7. **Commit** using Conventional Commits: `feat(ranking): tier-3 tie-break [FR-SCORE-06]`. One logical change per commit.

### Build order (do not skip ahead; each milestone ends green)

| M | Deliverable | Depends on |
|---|---|---|
| M0 | Scaffold, tooling, Makefile, CI, `test_architecture.py` | none |
| M1 | `domain/` models and errors, `db/` schema + `init_and_seed_db`, repositories, `weight_gate` | M0 |
| M2 | `ranking_tool`, `validation_tool`, `rounding`, `services/sensitivity` | M1 |
| M3 | `document_tool`, `security/`, synthetic and edge-case PDF generators | M1 |
| M4 | `llm/` (Protocol, factory, providers, `json_retry`, prompts, fault injection, fake) | M1 |
| M5 | `evaluation_agent`, `cache` | M2, M3, M4 |
| M6 | `orchestration/` graph, runner, persistence, `services/export` | M2–M5 |
| M7 | Streamlit UI: sidebar, Screens 1–5, CSS, live tracker | M6 (stub with fixtures earlier) |
| M8 | `negotiation_agent`, playbook UI, Markdown briefing download | M6 |
| M9 | Hardening, README, sample run JSON, deployment, walkthrough | all |

M2, M3 and M4 are independent and can run in parallel.

### Definition of done (per task)

- Requirement IDs addressed are listed in the PR description.
- `make check` is green; new code has tests; coverage is not lower (target ≥95% on `tools/` and `domain/`).
- No prime directive is weakened. No new `# type: ignore` or `# noqa` without a reason on the same line.
- Docs updated where contracts moved.

---

## 10. Parallel work lanes (for subagents or Antigravity's agent manager)

Contract-first: freeze `domain/models.py` and the `run_evaluation` signature in M1 so lanes do not block each other. A lane edits only the files it owns; changes to another lane's files go through that lane or a small, separate PR.

| Lane | Owns | Starts with |
|---|---|---|
| A. Core math | `domain/`, `tools/ranking_tool.py`, `tools/validation_tool.py`, `tools/weight_gate.py`, `tools/rounding.py`, `services/sensitivity.py` | golden vector tests |
| B. Data | `db/`, `services/export.py`, `services/run_loader.py` | schema + seed test |
| C. Ingestion & security | `tools/document_tool.py`, `security/`, `scripts/generate_*` | edge-case PDFs |
| D. LLM | `llm/`, `agents/`, `tools/cache.py` | `FakeLLMClient`, `json_retry` |
| E. Orchestration | `orchestration/` | graph over fakes |
| F. UI | `ui/`, `app.py`, `.streamlit/` | screens against a fixture `RunResult` |
| G. QA & docs | `tests/integration`, `tests/ui`, `README.md`, `sample_data/sample_run.json` | end-to-end fake run |

---

## 11. Ask first

Stop and ask the human before you:

- change a frozen contract (prime directive 4), the SQLite schema, or the unified JSON export keys;
- add or upgrade a dependency, or change a model ID in `config.py`;
- add any network call to a test, or any code path that sends proposal text somewhere other than the selected LLM provider;
- delete or rewrite files you did not create;
- resolve an item in PRD.md §17 (Open decisions) yourself.

## 12. Never

- Never ask the LLM to compute, rank, sum, or compare suppliers.
- Never put weights, other suppliers' text, or other suppliers' scores in an evaluation prompt.
- Never embed an API key in code, tests, fixtures, logs, `result_json`, or the export.
- Never write raw PDF- or LLM-derived text into HTML.
- Never block the batch on a single supplier failure, or silently swallow an error without a warning.
- Never commit `data/*.db`, `.streamlit/secrets.toml`, or real supplier data.

---

## 13. Common recipes

**Add an LLM provider.** Create `llm/providers/<name>_client.py` implementing `LLMClient`; register it in `llm/factory.py` and `domain/enums.Provider`; add its default model ID to `config.py`; add a factory unit test with a stubbed SDK; add it to the sidebar options. Do not touch agents.

**Add a criterion field.** Additive column in `db/schema.py` with a migration guard (`ALTER TABLE ... ADD COLUMN` inside `init_and_seed_db`), model field with a default, include it in the cache projection only if the LLM sees it, update the editor in `ui/screens/criteria.py`, add tests.

**Change a tie-break or formula.** Not allowed without an ADR and PRD change. If approved: update architecture.md §10 first, then golden tests, then code.

**Add a screen.** New module in `ui/screens/` exposing `render(ctx: ScreenContext) -> None`; register it in `app.py` navigation; no business logic inside, only calls to `services` and `orchestration`.

---

## 14. Streamlit and deployment gotchas

- The script reruns top to bottom on every interaction. Keep expensive work behind `st.cache_resource` (DB init) or an explicit button; keep results in `st.session_state` via the typed accessors in `ui/state.py`.
- `st.data_editor` returns an edited frame; persist only on an explicit **Save** after validation. Do not write to SQLite on every rerun.
- Uploaded files: read once with `getvalue()` into bytes and store bytes, not file objects, in session state.
- Call `st.status`, `st.progress` and other `st.*` only from the main script thread. Keep the pipeline sequential in v1; a worker thread must never touch `st.*`.
- Streamlit Community Cloud disk is ephemeral: `init_and_seed_db()` runs on every boot, idempotently, and the app must work from an empty database. Export the run JSON before the app sleeps.
- Read secrets with `st.secrets.get(...)`; a missing secret disables the demo-model option with an explanation rather than raising.
- Model IDs named in the spec (for example `gemini-1.5-flash`, `claude-3-5-sonnet`) may have been retired by providers. They live in `config.py` and are overridable by env var. Verify availability before deploying.

