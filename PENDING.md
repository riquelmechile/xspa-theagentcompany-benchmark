# Pending work

## Current state

- **v1/v2/v3:** historical capability evidence retained unchanged.
- **v4/v5:** complete historical deterministic fault-suite evidence. Raw outputs, preregistration and chronology are preserved, but the former statistical-confirmation interpretation is withdrawn after the arm-symmetry audit.
- **V6:** corrective comparison contract and parent design manifest were frozen before outcomes, but a pre-run audit found that the frozen manifest contains no concrete scenario list/runner mapping. Because the frozen runner SHA cannot be changed after the freeze, V6 is intentionally left with zero outcomes rather than manufacturing a campaign after the fact. A new benchmark version must freeze the executable scenario campaign before its first outcome.
- **Governance model-in-loop:** design specified separately; no outcomes claimed yet.

## Next executable work

1. **DONE / fail-closed:** V6 parent design manifest frozen after `shared-executor-v2`, pinned to exact clean XanxitoSpA SUT commit, lockfile hash and benchmark runner commit; pre-run validation proves it is not an executable campaign because it has no scenarios. Keep V6 at zero outcomes.
2. Create the next benchmark version with a concrete campaign manifest committed before outcomes: ordered scenarios, common action plan, shared executor-authored trace, common mutation intent/fault/oracle/pre-state, explicit runner mapping and PostgreSQL for durability/fencing claims.
3. Run only that newly frozen executable campaign and report deterministic scenario measurements as regression evidence; do not attach sampling p-values without genuine randomization/sampling.
4. Run the separate ChatGPT-hosted MCP governance experiment with independently randomized host sessions for adversarial authority/budget/mandate/tool-metadata conditions.
5. For any future capability-equivalence claim, preregister an equivalence margin and power analysis; v3 currently supports only “no directional difference detected in this sample.”

## Closeout invariants

1. Never rewrite v4/v5 raw outcomes, preregistration commits or historical criterion files to make the corrected interpretation look cleaner.
2. Preserve raw official evaluator scores; annotate defects rather than editing scores.
3. Keep credential-bearing trajectories/live service artifacts out of Git; publish sanitized evidence and hashes.
4. DIRECT in V6 must be competent: bounded retry plus probe/read-before-retry where ordinary engineering would use it.
5. No arm-specific oracle, literal integrity outcome, hidden mutation plan, or arm-authored contract fingerprint is allowed in V6; both arms consume independent deep copies of the same `V6Plan` snapshot, while the shared executor walks the ordered steps and authors the canonical execution trace.
6. Durability/fencing claims require the PostgreSQL runtime, not the in-memory store.
7. Every V6 result must identify the exact SUT commit and dependency lock hash.
