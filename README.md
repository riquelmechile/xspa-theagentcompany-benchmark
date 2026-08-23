# XanxitoSpA × TheAgentCompany benchmark evidence

Private evidence repository for the paired comparison **DIRECT vs XANXITOSPA** on TheAgentCompany 1.0.0.

## Current clean v2 result

- Agent model: `gpt-5.6-sol`, reasoning effort `max` in both arms.
- Environment/evaluator text model: `xspa-env-qwen3.8-27b`.
- Completed hard-isolation pairs: **7**.
- DIRECT: **13/30 = 43.3333%**.
- XANXITOSPA: **13/30 = 43.3333%**.
- Delta: **0.0 percentage points**.
- Pair wins / ties / losses for XANXITOSPA: **0 / 7 / 0**.
- Annotated broken/literal graders: **4**.
- Safety-excluded task: `hr-resume-screening` (not scored).

| Task | DIRECT | XANXITOSPA | Status |
|---|---:|---:|---|
| `finance-invoice-matching` | 4/5 | 4/5 | `valid-paired-v2` |
| `finance-find-signatories` | 4/5 | 4/5 | `valid-paired-v2` |
| `hr-check-attendance-multiple-days-department-with-chat` | 1/4 | 1/4 | `broken-grader` |
| `hr-salary-analysis` | 0/2 | 0/2 | `valid-paired-with-literal-grader-defect` |
| `pm-ask-for-issue-and-create-in-gitlab` | 2/5 | 2/5 | `valid-paired-v2-with-documented-gitlab-recovery` |
| `pm-copy-plane-issues-to-gitlab` | 1/4 | 1/4 | `broken-grader-and-plane-baseline-mismatch` |
| `pm-check-backlog-update-issues` | 1/5 | 1/5 | `broken-npc-and-grader` |

## What is actually comparable

The **v2 hard-isolation** ledger is the current final-quality dataset. The older v1 file is retained only as pilot/debug evidence and must **not** be combined with v2 totals.

DIRECT has Apps/MCP/plugins/browser/computer-use disabled and solves through local shell/filesystem plus benchmark services. XANXITOSPA uses the same model and benchmark environment, with one bounded **read-only** `@Xanxito -> xanxitospa` task-aware preflight; HostOps, other downstream MCPs and writes are forbidden.

Fresh benchmark state is required before each arm. Raw evaluator scores are never manually overridden. Known benchmark/evaluator defects are annotated while preserving the official raw score.

## Evidence publication policy

Raw `trajectory.jsonl` files and live service artifacts are **not committed** because they can contain benchmark session cookies, CSRF values, Plane API tokens and other ephemeral authentication material. `evidence/local-evidence-sha256.json` records SHA-256 hashes and byte sizes for the local evidence, so the exact local runs can still be integrity-checked without publishing secrets.

The repository includes:

- `results/results-v2-hard-isolation.json` — canonical clean v2 ledger.
- `results/results-v1-pilot.json` — non-final prompt-isolated pilot results.
- `manifest/subset-v1.json` — frozen 24-task order.
- `evidence/pair-summaries.json` — ledger-derived task summaries.
- `evidence/raw-evals-available.json` — raw evaluator JSON where it was safely persisted as JSON.
- `evidence/local-evidence-sha256.json` — integrity hashes for local pair evidence.
- `PROTOCOL.md` — isolation and scoring rules.
- `PENDING.md` — exact remaining work.

## Current interpretation

At **7 clean paired tasks**, XANXITOSPA has changed planning/process in several runs but has **not yet changed the aggregate official score**: the current observed delta is 0 pp. This sample is too small and too grader-defect-heavy for a strong product claim; the frozen subset should be completed before drawing a conclusion.
