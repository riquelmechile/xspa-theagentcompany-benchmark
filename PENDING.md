# Pending work

## Current state

- **v1/v2/v3:** historical capability evidence retained unchanged.
- **v4/v5:** complete historical deterministic fault-suite evidence. Raw outputs, preregistration and chronology are preserved, but the former statistical-confirmation interpretation is withdrawn after the arm-symmetry audit.
- **V6:** corrective comparison contract and parent design manifest were frozen before outcomes, but a pre-run audit found that the frozen manifest contains no concrete scenario list/runner mapping. Because the frozen runner SHA cannot be changed after the freeze, V6 is intentionally left with zero outcomes rather than manufacturing a campaign after the fact. A new benchmark version must freeze the executable scenario campaign before its first outcome.
- **V7:** executable three-scenario campaign is now frozen before outcomes against the exact clean XanxitoSpA SUT, lock hash, runner commit and runner-file hashes; zero V7 outcomes exist at freeze time.
- **Governance model-in-loop:** design specified separately; no outcomes claimed yet.

## Next executable work

1. **DONE / fail-closed:** V6 parent design manifest frozen after `shared-executor-v2`, pinned to exact clean XanxitoSpA SUT commit, lockfile hash and benchmark runner commit; pre-run validation proves it is not an executable campaign because it has no scenarios. Keep V6 at zero outcomes.
2. **DONE:** V7 runner code committed first, then `manifest/v7-campaign.json` frozen with all three ordered scenarios, common plans/faults/oracles/pre-state, explicit runner mapping, exact SUT/lock/runner pins and runner-file hashes.
3. Run V7 exactly once from that frozen manifest. Preserve valid negative outcomes and never overwrite result files. Report deterministic mechanism measurements only; no sampling p-values.
4. Run the separate ChatGPT-hosted MCP governance experiment with independently randomized host sessions for adversarial authority/budget/mandate/tool-metadata conditions.
5. For any future capability-equivalence claim, preregister an equivalence margin and power analysis; v3 currently supports only “no directional difference detected in this sample.”

## Closeout invariants

1. Never rewrite v4/v5 raw outcomes, preregistration commits or historical criterion files to make the corrected interpretation look cleaner.
2. Preserve raw official evaluator scores; annotate defects rather than editing scores.
3. Keep credential-bearing trajectories/live service artifacts out of Git; publish sanitized evidence and hashes.
4. DIRECT in V7 must be competent outside the treatment mechanism being isolated; no arm-specific hidden fault/oracle or literal verdict is allowed.
5. No arm-specific oracle, literal integrity outcome, hidden mutation plan, or arm-authored contract fingerprint is allowed in V7; both arms consume independent deep copies of the same shared plan while `shared-executor-v2` walks the ordered steps and authors the canonical trace.
6. Durability/fencing claims require the PostgreSQL runtime, not the in-memory store.
7. Every V7 result must identify the exact frozen campaign fingerprint, SUT commit, dependency lock hash and runner commit.
