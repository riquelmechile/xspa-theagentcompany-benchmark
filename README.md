# XanxitoSpA × TheAgentCompany benchmark evidence

Private evidence repository for the paired comparison **DIRECT vs XANXITOSPA** on TheAgentCompany 1.0.0.

## Current v3 ChatGPT-hosted MCP result

This is the user-requested architecture where **this ChatGPT session is the agent host** and the PC only supplies benchmark runtimes, services, Docker and evidence. XANXITOSPA adds a bounded read-only `ChatGPT -> Xanxittoo -> xanxitospa` preflight; no Codex CLI or secondary model is spawned.

- Agent model: `gpt-5.6-sol`, reasoning effort `max`.
- Environment/evaluator text model: `xspa-env-qwen3.8-27b`.
- Completed v3 pairs: **16/16** of the previously remaining tasks.
- DIRECT raw official: **69/95 = 72.6316%**.
- XANXITOSPA raw official: **68/95 = 71.5789%**.
- Pair wins / ties / losses for XANXITOSPA: **1 / 14 / 1**.
- Exact two-sided paired sign test on the two discordant pairs: **p = 1.0**. There is **no measurable directional capability difference** in this sample.
- The raw one-checkpoint difference (69 vs 68 of 95) is descriptive noise, not evidence that XANXITOSPA is worse.
- Fixed-evaluator-compatible subset (excluding the two vision-dependent tasks): DIRECT **67/83**, XANXITOSPA **66/83**; the same paired conclusion holds (1 win, 1 loss; two-sided sign-test **p = 1.0**).
- Vision-incompatible tasks: `ds-visualize-data-in-pie-and-bar-chart`, `research-reproduce-figures` (the fixed Qwen evaluator rejects image input with HTTP 500).

**Methodology warning:** v3 arms use fresh task runtime/state and separate trajectories, but they execute sequentially in the same ChatGPT conversation context. This is not fresh-context blind isolation. v3 must not be merged with v2 totals. The absolute percentages are also **not comparable to TheAgentCompany paper results** because this run uses a 16-task subset, a local Qwen environment/evaluator model, and a text-only evaluator that cannot score two vision-dependent tasks. The paired within-run contrast is the valid result.

See `results/results-v3-chatgpt-hosted-mcp.json` for all 16 task-level scores and grader annotations.


## v4 deterministic fault-injection micro-pilot

The v3 paired result is capability-neutral, so the next experiment targets the surfaces XanxitoSpA is actually designed to add: idempotency, recovery, budget boundaries and fencing under controlled failure.

The first v4 micro-pilot uses the **production kernel implementation** (`CapabilityPlane`, `BudgetEnvelope`, durable idempotency journal, reconciliation and monotonic fencing) with the same provider/objective/fault presented to a raw DIRECT path and to the XANXITOSPA governed path. It is an injector/metric validation step, **not yet the final TAC task-level benchmark**.

Pilot scenarios:

| Failure | DIRECT integrity | XANXITOSPA integrity | Key observation |
|---|---:|---:|---|
| lost acknowledgement after mutation | fail | pass | DIRECT blind retry produced 2 effects; XSPA reconciled and replayed with 1 |
| budget overrun | fail | pass | DIRECT executed CLP 60k; XSPA escalated before provider call under CLP 50k cap |
| stale fencing token after takeover | fail | pass | DIRECT stale owner overwrote newer state; XSPA rejected stale settlement |

Aggregate micro-pilot: **DIRECT 0/3 integrity passes, XANXITOSPA 3/3; 3 unsafe effects vs 0**. See `results/fault-injection-v4-pilot.json` and `manifest/fault-injection-v4-pilot.json`. The next stage is to reproduce the same deterministic injection semantics on at least two stateful TAC tasks before freezing the final v4 manifest.

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

The v3 result is a **capability-neutral non-regression result**, not a directional loss: 14/16 pairs tied, one favored XANXITOSPA and one favored DIRECT; the exact paired sign test is **p = 1.0**. Under these capability-matched single-session tasks we did not detect a capability cost from adding the XANXITOSPA preflight/governance layer. This benchmark does **not** exercise the architecture's primary advantages (leases, fencing, authority/budget boundaries, durable recovery, duplicate-side-effect prevention), so the next experiment is a deterministic fault-injection benchmark rather than more baseline TAC tasks.

The single XANXITOSPA loss (`ds-coffee-shop-database-management`) has been autopsied in `evidence/coffee-shop-autopsy-v3.json`: the arm-specific 2-point loss was semantic overreach in planning, not an authority/budget denial or runtime overhead. The actionable guard is to freeze explicit artifact contracts before applying operational heuristics.
