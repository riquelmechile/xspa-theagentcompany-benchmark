# Pending work

## Current state

- **v1/v2/v3:** historical capability evidence retained unchanged.
- **v4/v5:** complete historical deterministic fault-suite evidence. Raw outputs, preregistration and chronology are preserved, but the former statistical-confirmation interpretation is withdrawn after the arm-symmetry audit.
- **V6:** corrective comparison contract implemented and tested; execution campaign has not yet been run.
- **Governance model-in-loop:** design specified separately; no outcomes claimed yet.

## Next executable work

1. Freeze the final V6 manifest only after the shared declarative executor (`V6Plan` -> `execute_pair`) is committed; pin the exact clean XanxitoSpA SUT commit, lockfile hash and runner hash. No V6 arm may run from a hand-authored per-arm fingerprint contract.
2. Run only scenarios satisfying the V6 contract: common action plan, shared executor-authored ordered trace, common external mutation intent, common fault injection, common oracle, measured per-step outcomes only, and PostgreSQL for durability/fencing claims.
3. Report deterministic scenario measurements as regression evidence; do not attach sampling p-values unless a genuine randomization/sampling mechanism is introduced.
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
