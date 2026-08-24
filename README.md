# XanxitoSpA × TheAgentCompany benchmark evidence

Private evidence repository for the paired comparison **DIRECT vs XANXITOSPA** on TheAgentCompany 1.0.0.

## Current v3 ChatGPT-hosted MCP result

This is the user-requested architecture where **this ChatGPT session is the agent host** and the PC only supplies benchmark runtimes, services, Docker and evidence. XANXITOSPA adds a bounded read-only `ChatGPT -> Xanxittoo -> xanxitospa` preflight; no Codex CLI or secondary model is spawned.

- Agent model: `gpt-5.6-sol`, reasoning effort `max`.
- Environment/evaluator text model: `xspa-env-qwen3.8-27b`.
- Completed v3 pairs: **16/16** of the previously remaining tasks.
- DIRECT raw official: **69/95 = 72.6316%**.
- XANXITOSPA raw official: **68/95 = 71.5789%**.
- Raw delta: **-1.0526 percentage points**.
- Pair wins / ties / losses for XANXITOSPA: **1 / 14 / 1**.
- Fixed-evaluator-compatible subset (excluding the two vision-dependent tasks): DIRECT **67/83 = 80.7229%**, XANXITOSPA **66/83 = 79.5181%**, delta **-1.2048 pp**.
- Vision-incompatible tasks: `ds-visualize-data-in-pie-and-bar-chart`, `research-reproduce-figures` (the fixed Qwen evaluator rejects image input with HTTP 500).

**Methodology warning:** v3 arms use fresh task runtime/state and separate trajectories, but they execute sequentially in the same ChatGPT conversation context. This is not fresh-context blind isolation. v3 must not be merged with v2 totals.

See `results/results-v3-chatgpt-hosted-mcp.json` for all 16 task-level scores and grader annotations.

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

The repository now contains two intentionally separate final datasets: **v2 hard isolation** (Codex-hosted, 7 pairs) and **v3 ChatGPT-hosted MCP** (16 pairs). They answer different methodological questions and must not be combined. The older v1 file remains pilot/debug evidence only.

DIRECT has Apps/MCP/plugins/browser/computer-use disabled and solves through local shell/filesystem plus benchmark services. XANXITOSPA uses the same model and benchmark environment, with one bounded **read-only** `@Xanxito -> xanxitospa` task-aware preflight; HostOps, other downstream MCPs and writes are forbidden.

Fresh benchmark state is required before each arm. Raw evaluator scores are never manually overridden. Known benchmark/evaluator defects are annotated while preserving the official raw score.

## Evidence publication policy

Raw `trajectory.jsonl` files and live service artifacts are **not committed** because they can contain benchmark session cookies, CSRF values, Plane API tokens and other ephemeral authentication material. `evidence/local-evidence-sha256.json` records SHA-256 hashes and byte sizes for the local evidence, so the exact local runs can still be integrity-checked without publishing secrets.

The repository includes:

- `results/results-v3-chatgpt-hosted-mcp.json` — complete 16-pair ChatGPT-hosted MCP ledger.
- `results/results-v2-hard-isolation.json` — frozen 7-pair hard-isolation v2 ledger.
- `results/results-v1-pilot.json` — non-final prompt-isolated pilot results.
- `manifest/subset-v1.json` — frozen 24-task order.
- `evidence/pair-summaries.json` — ledger-derived task summaries.
- `evidence/raw-evals-available.json` — raw evaluator JSON where it was safely persisted as JSON.
- `evidence/local-evidence-sha256-v3.json` — integrity hashes for local v3 pair evidence.
- `evidence/local-evidence-sha256.json` — integrity hashes for local v2 pair evidence.
- `PROTOCOL.md` — isolation and scoring rules.
- `PENDING.md` — exact remaining work.

## Current interpretation

At **7 clean paired tasks**, XANXITOSPA has changed planning/process in several runs but has **not yet changed the aggregate official score**: the current observed delta is 0 pp. This sample is too small and too grader-defect-heavy for a strong product claim; the frozen subset should be completed before drawing a conclusion.
