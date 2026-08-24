# Protocol v2 — hard capability isolation

## Common controls

- Same TheAgentCompany 1.0.0 task image and task text.
- Same `gpt-5.6-sol` agent model with `model_reasoning_effort=max`.
- Same benchmark services and local environment/evaluator model.
- Fresh task state before each arm.
- Evaluator/checkpoint/grader implementation unavailable to the agent while solving.
- No internet answer lookup and no reuse of opposite-arm artifacts.
- Official raw evaluator scores are retained exactly; defects are annotations, not manual score overrides.

## DIRECT arm

Codex runs with Apps/MCP/plugins/remote-plugin/browser/computer-use disabled. It can use only the local task container shell/filesystem and the benchmark services required by the task.

## XANXITOSPA arm

Same model/container/service access as DIRECT. After reading `task.md`, it may perform a bounded task-aware read-only preflight through `@Xanxito` to downstream `xanxitospa`. Allowed calls are discovery/read operations such as `xspa_status`, `xspa_company_status`, `xspa_skills_search`, `xspa_skill_get`, and related read-only company/skill guidance.

Forbidden in the benchmark arm: HostOps, browser/computer-use, memory/SDD/review assistance, other downstream MCPs, external connectors, and MCP writes. A run that crosses that gate is invalid and excluded.

## Non-standard infrastructure recovery

Infrastructure recovery is allowed only to restore the intended official baseline, never to inject task answers. The canonical ledger documents the observed GitLab Docker-name/storage failure and Plane backup/DNS/startup races. Both arms must begin from equivalent recovered state.

## Reporting

- v1 is pilot/debug evidence only.
- v2 is the capability-isolated comparison.
- Broken graders remain in the raw score and are separately tagged.
- Safety-excluded tasks do not enter the denominator.
- Visual evaluator incompatibility with the fixed text-only environment model is execution-only/unscorable rather than silently scored as failure.


# Protocol v3 addendum — ChatGPT-hosted MCP

v3 is a separate experiment from v2. The agent host is the current ChatGPT session (`gpt-5.6-sol`, max reasoning). The PC is runtime infrastructure only: Docker, benchmark task containers, benchmark services, local environment/evaluator model, and evidence storage. No Codex CLI or secondary agent model is spawned.

## v3 DIRECT

ChatGPT reads the task through the hosted lifecycle and operates only the task runtime plus benchmark services. No XanxitoSpA preflight is permitted. Any MCP event in a DIRECT trajectory invalidates the arm.

## v3 XANXITOSPA

The same ChatGPT model/runtime is used. After reading `task.md`, the arm must first perform downstream discovery for `xanxitospa` and at least one bounded read-only `mcp_read` preflight. Material task execution starts only after that preflight. MCP writes, HostOps as task assistance, other downstream MCPs, browser/computer-use, memory/SDD/review assistance, or hidden grader access invalidate the arm.

## v3 lifecycle and evidence

- Fresh benchmark task state before each arm.
- Separate task containers, output directories and trajectories for DIRECT and XANXITOSPA.
- Opposite-arm output artifacts are not reused.
- Official evaluator source remains unopened until both arms of a pair are complete.
- Invalid/contaminated attempts are aborted and archived before evaluation; they do not enter the ledger.
- Raw scores are never edited after evaluator inspection.
- Raw trajectories remain local; only sanitized ledgers and SHA-256 evidence manifests are committed.

## v3 methodology limitation

DIRECT and XANXITOSPA execute sequentially inside the same ChatGPT conversation context. Runtime/evidence state is isolated, but model conversation context is not freshly reset between arms. Therefore v3 is **not fresh-context blind isolation**. Its totals must not be merged with v2 and should not be presented as a replacement for the v2 hard-isolation result.

## fixed evaluator compatibility

The fixed `xspa-env-qwen3.8-27b` evaluator is text-only. Tasks whose official checkpoints require image input retain their raw official score but are additionally reported in an evaluator-compatible subset that excludes those tasks. For v3 these are `ds-visualize-data-in-pie-and-bar-chart` and `research-reproduce-figures`.


### Contract-preservation guard learned from v3

The coffee-shop autopsy identified one real XANXITOSPA regression mechanism: process planning broadened an explicitly specified `v_short_stock` contract by mixing it with a separate seven-day forecast question. Future preflights must **freeze explicit artifact/schema/view contracts before applying skills or operational heuristics**. Derived analyses may consume those artifacts but must not silently redefine them. This guard addresses semantic planning drift; it is unrelated to authority or budget denials.


## v4 fault-injection protocol (pilot stage)

v4 changes the research question from baseline capability to integrity under deterministic failure. The first stage is a production-kernel micro-pilot; it must not be reported as a final TheAgentCompany score.

For each scenario, DIRECT and XANXITOSPA receive the same objective, provider behavior and injected fault. DIRECT has no authority/budget/idempotency/fencing/reconciliation guard for the tested operation. XANXITOSPA executes through the corresponding production kernel surface. Primary outcomes are completion **and** integrity: duplicate side effects, state corruption, budget violations, safe halt, reconciliation success and audit events.

A scenario only graduates into the final TAC-integrated v4 manifest after the fault trigger and externally visible fault effect can be shown equivalent across both arms. Final v4 must use stateful TAC services/tasks and preserve fresh task state between arms. The micro-pilot manifest is therefore marked `pilot-not-final`.


## v4 stateful fault-injection addendum

v4 is a separate execution-integrity experiment. It does not reuse TAC evaluator scores and is not merged with v2/v3. The frozen manifest fingerprint is `25d2991fe2171591b349864ea2a230ff68268ba90fc7b2e1495b9e6bce168a75`.

Each stateful scenario freezes one action plan and one fault trigger. DIRECT and XANXITOSPA receive the same intended mutation and fresh service/task state. The comparison changes only the execution substrate. Primary paired oracle is `integrityPreserved`; secondary metrics include duplicate/unsafe effects, recovery success, reconciliation requirement, safe halt and fencing evidence. Infrastructure-invalid attempts are excluded before observing/scoring an arm and are never substituted with reconstructed results.

The stateful campaign contains 20 pairs across RocketChat, GitLab, Plane, OwnCloud and a local server runtime. Exact paired sign testing is applied only to discordant stateful integrity outcomes. The separate governance boundary suite (budget, authority, poisoned metadata, stale fencing) is reported descriptively and is not included in that sign test.

Runtime credentials, lock files, launch metadata and invalid-attempt artifacts remain local. Published evidence contains sanitized result JSON plus SHA-256 manifests.
