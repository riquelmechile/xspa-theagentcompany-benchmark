# XanxitoSpA × TheAgentCompany benchmark evidence

Public evidence repository for the paired comparison **DIRECT vs XANXITOSPA** on TheAgentCompany 1.0.0.

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


## V5 prospective replication — primary result

The V5 replication re-runs the frozen 20-scenario v4 stateful fault-injection design three times per scenario. Because repetition 1 completed before the preregistration commit, the **headline inferential result uses only repetitions 2 and 3**, exactly as frozen in `V5_PREREGISTRATION.md` and `manifest/v5-success-criterion.json`.

- Preregistration commit: `da81bedbe4df5804925170216f6e762c64015c7a`.
- Prospective-only rep2+rep3 scenario result: **8 XANXITOSPA wins / 0 DIRECT wins / 12 ties**.
- Exact two-sided sign test over the 8 non-tie scenario outcomes: **p = 0.0078125**.
- Frozen strong prospective confirmation criterion: **met**.
- Primary all-three-repetition scenario result: **8 / 0 / 12, p = 0.0078125**.
- Each individual repetition: **8 / 0 / 12**.
- Pooled 60-pair result, **descriptive only**: XANXITOSPA **60/60 integrity**, DIRECT **36/60**; **24 / 0 / 36**, `p = 1.1920928955078125e-07`.

The result supports the combined interpretation that v3 is capability-neutral in this sample while v4/v5 show an execution-integrity advantage under the frozen deterministic faults. **Limitation:** DIRECT was not specifically prompted or instrumented to add its own resilience layer, so the benchmark does not establish that a separately engineered DIRECT resilience strategy could not match the behavior.

See `V5_REPORT.md`, `results/v5-preregistered-analysis.json`, and `results/v5-replication-final.json`.

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

## v4 stateful fault-injection result

The frozen stateful campaign is complete. It uses **paired frozen action plans** rather than another reasoning benchmark: DIRECT and XANXITOSPA execute the same designated mutation, against a fresh reset state, and differ only in whether the production XSPA execution-integrity substrate is present. The frozen manifest contains **5 stateful TAC surfaces × 4 conditions = 20 pairs / 40 arms**.

- Manifest fingerprint: `25d2991fe2171591b349864ea2a230ff68268ba90fc7b2e1495b9e6bce168a75`.
- DIRECT integrity passes: **12/20 = 60%**.
- XANXITOSPA integrity passes: **20/20 = 100%**.
- Paired wins / ties / losses for XANXITOSPA: **8 / 12 / 0**.
- Exact two-sided sign test over the 8 discordant pairs: **p = 0.0078125**.
- DIRECT unsafe effects recorded by the frozen metrics: **8**. XANXITOSPA: **0**.

The eight integrity wins are concentrated exactly where the kernel is intended to help: acknowledgement loss after commit, duplicate intent, service restart after commit, stale writer settlement, conflicting object revisions, and process death before health verification. Control cases and naturally fail-closed credential/port cases tied. OwnCloud lost-ACK also tied on final-state integrity because repeated identical PUTs are naturally idempotent, although DIRECT performed two writes and XANXITOSPA one reconciled write.

This result is **not combined with v2/v3 TAC capability scores**. It measures execution integrity under deterministic faults, not baseline task-solving capability. See `results/v4-stateful-final.json`.

### Separate governance boundary suite

Four governance semantics that do not map naturally onto every TAC task were tested separately and are not included in the 20-pair sign test: budget overrun, authority denial, poisoned MCP tool metadata, and stale fencing. DIRECT-without-governance preserved integrity in **0/4**; production XANXITOSPA boundaries preserved integrity in **4/4**, with **4 unsafe effects vs 0**. See `results/v4-governance-boundary.json`.

### Infrastructure hardening discovered during v4

Repeated GitLab resets exposed a benchmark-infrastructure leak: anonymous GitLab data volumes (~9 GB each) accumulated until `/data` reached 100%. The reset controller was hardened to capture only the previous canonical GitLab container's anonymous volumes and remove them **after** the replacement passes health and structural fingerprint validation and only when they are no longer referenced. No global `docker volume prune` is used. Two deterministic reset cycles retained the canonical GitLab/Plane fingerprints without ~9 GB/cycle growth.

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

The repository contains four intentionally separate evidence layers: **v2 hard isolation** (Codex-hosted capability pairs), **v3 ChatGPT-hosted MCP** (capability non-regression), **v4 stateful fault injection** (execution integrity discovery/confirmation under deterministic faults), and **v5 prospective replication** (scenario-blocked replication with rep2+rep3 frozen as the prospective-only confirmation). They answer different questions and must not be combined into one score. The older v1 file remains pilot/debug evidence only.

DIRECT has Apps/MCP/plugins/browser/computer-use disabled and solves through local shell/filesystem plus benchmark services. XANXITOSPA uses the same model and benchmark environment, with one bounded **read-only** `@Xanxito -> xanxitospa` task-aware preflight; HostOps, other downstream MCPs and writes are forbidden.

Fresh benchmark state is required before each arm. Raw evaluator scores are never manually overridden. Known benchmark/evaluator defects are annotated while preserving the official raw score.

## Evidence publication policy

Raw `trajectory.jsonl` files and live service artifacts are **not committed** because they can contain benchmark session cookies, CSRF values, Plane API tokens and other ephemeral authentication material. `evidence/local-evidence-sha256.json` records SHA-256 hashes and byte sizes for the local evidence, so the exact local runs can still be integrity-checked without publishing secrets.

The repository includes:

- `V5_REPORT.md` — final prospective replication report and reproduction commands.
- `results/v5-preregistered-analysis.json` — preregistered scenario-blocked V5 analyses.
- `results/v5-replication-final.json` — pooled 60-pair descriptive V5 aggregate.
- `evidence/local-evidence-sha256-v5.json` — SHA-256 ledger for V5 publication artifacts.
- `results/results-v3-chatgpt-hosted-mcp.json` — complete 16-pair ChatGPT-hosted MCP ledger.
- `results/v4-stateful-final.json` — canonical 20-pair stateful fault-injection aggregate.
- `results/v4-governance-boundary.json` — separate four-case governance boundary suite.
- `evidence/local-evidence-sha256-v4.json` — integrity hashes for published v4 summary evidence.
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
