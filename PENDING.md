# Pending work

## Dataset status

- **v3 ChatGPT-hosted MCP:** 16/16 previously remaining tasks completed as paired DIRECT vs XANXITOSPA runs.
- **v2 hard isolation:** frozen at 7 completed pairs; do not merge with v3.
- **v1 pilot:** retained only as historical/debug evidence.
- **v4 stateful fault injection:** 20/20 paired scenarios complete; governance boundary suite 4/4 complete.
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

Execution is complete. Canonical stateful result: **12/20 DIRECT integrity vs 20/20 XANXITOSPA**, with **8 XSPA wins, 12 ties, 0 losses** and exact two-sided paired sign-test **p=0.0078125**. Governance boundary suite is reported separately (**0/4 DIRECT vs 4/4 XANXITOSPA**) and must not be folded into the stateful p-value.

Remaining work is closeout/publication only: preserve hashes, keep runtime credentials/locks local, and treat any future campaign as a new frozen methodology/version.
