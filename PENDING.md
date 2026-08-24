# Pending work

## Dataset status

- **v3 ChatGPT-hosted MCP:** 16/16 previously remaining tasks completed as paired DIRECT vs XANXITOSPA runs.
- **v2 hard isolation:** frozen at 7 completed pairs; do not merge with v3.
- **v1 pilot:** retained only as historical/debug evidence.
- **Safety-excluded:** `hr-resume-screening` remains excluded because the benchmark asks for an employment progression decision based on citizenship/green-card status.

## Execution pending

No unstarted v3 benchmark tasks remain.

The only future benchmark work would be a **new methodology**, not continuation of this ledger, for example:

1. A fresh-context blind ChatGPT-hosted rerun where DIRECT and XANXITOSPA execute in separate conversation contexts.
2. A multimodal evaluator rerun for the two vision-dependent tasks, while preserving the current fixed-evaluator raw scores.
3. A larger frozen manifest if a new benchmark version is adopted.

## Closeout invariants

1. Do not combine v1, v2 and v3 totals.
2. Preserve raw official evaluator scores; annotate defects instead of editing scores.
3. Keep raw trajectories and live service artifacts local; publish hashes/sanitized summaries only.
4. Treat `results/results-v3-chatgpt-hosted-mcp.json` as the canonical v3 ledger.


## v4 fault-injection benchmark

Next work is **not** another baseline TAC rerun. Build a paired deterministic fault-injection benchmark that targets the governance/resilience surfaces XANXITOSPA is intended to provide. Start with a small pilot, validate identical injection timing/effects across arms, then freeze the larger manifest.

Primary failure classes: runtime death after mutation, lost acknowledgement/retry ambiguity, credential expiry, downstream service outage, concurrent writers/stale lease, malicious tool metadata, authority-boundary attempt, budget-envelope attempt, and false-success (2xx with failed internal mutation).

Primary metrics: task completion, recovery success, duplicate side effects, state corruption, unauthorized actions, budget violations, recovery steps/time, and audit completeness.
