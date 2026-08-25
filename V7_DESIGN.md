# V7 executable integrity campaign

V7 replaces the incomplete V6 campaign freeze. V6 remains preserved exactly as historical design evidence and is not executed.

## Question

V7 asks a narrow deterministic mechanism question: with the **same declarative action plan, fault, pre-state and shared oracle**, does XanxitoSpA preserve integrity in cases where an otherwise ordinary DIRECT integration lacks the specific treatment mechanism?

V7 does not use sampling p-values. Each scenario is a deterministic regression/mechanism test.

## Structural contract

Every scenario is frozen before outcomes with:

- the exact clean XanxitoSpA SUT commit and `pnpm-lock.yaml` SHA-256;
- the exact benchmark runner commit;
- SHA-256 for every executable runner/contract/scenario file;
- a non-empty ordered `actionPlan.steps` list;
- one common `oracle`, `fault` and `preState` object;
- explicit identical runner mapping through `v7_bridge` for DIRECT and XANXITOSPA;
- PostgreSQL for every durability claim;
- one campaign fingerprint covering the complete executable campaign.

`shared-executor-v2` walks every action step itself. Arm runners return measurements only. The shared oracle is applied after both arms complete; no arm may author `integrityPreserved`, `staleSettlementAccepted`, `completed`, `safeHalt` or related verdict fields.

## Frozen initial scenarios

The initial campaign contains exactly three mechanisms:

1. `stale-idempotency-settlement` — an ABA stale writer and its replacement share the same logical worker identity. DIRECT uses owner-only settlement; XANXITOSPA uses the real PostgreSQL idempotency journal and fencing token. The common oracle requires the fresh reconciliation result to survive and the stale settlement to be rejected.
2. `stale-heartbeat-cursor` — an expired heartbeat owner is reacquired under the same logical daemon identity. DIRECT uses owner-only lease checking; XANXITOSPA uses the real fenced PostgreSQL heartbeat cursor. The common oracle requires monotonic final cursor state and rejection of the stale generation.
3. `write-permission-is-not-owner` — an authenticated operator with write permission but no owner credential attempts to create an owner-confirmed discovery fact. DIRECT models ordinary write permission without a separate constitutional credential. XANXITOSPA executes the real runtime discovery boundary. The common oracle requires the owner-only claim to remain unresolved.

These scenarios intentionally isolate **fencing and authority separation**. They do not claim that every part of the broader Company OS is causally necessary.

## Execution law

After `manifest/v7-campaign.json` is frozen, runner files, SUT commit, dependency lock, scenario list, plan, faults, oracles and pre-state are immutable for V7. Any required methodological change creates a later benchmark version.

Valid negative outcomes are never retried. Existing result files are never overwritten. A campaign run aborts if the SUT is dirty, the SUT/lock pin drifts, any runner file hash drifts, the runner commit is not an ancestor, a PostgreSQL durability scenario lacks a database, or any result fails the V7 validator.
