# V7 executable integrity campaign — final report

V7 is the first post-audit executable comparison whose complete campaign was frozen before outcomes.

## Frozen campaign

- Campaign fingerprint: `a693e1020baf3a15689b635eeabedf1f3ba6c03d3105d191b994c723633abfbd`
- XanxitoSpA SUT: `92ac8a12babb8245c4cfd621ecaac487e904409d`
- `pnpm-lock.yaml` SHA-256: `820d1292c52f7f97ebcff0ce97f9bfae6d694ca5d5970320aa72e9c91daa100a`
- Runner commit: `64f23e51807e4c07945e8826f383b4cc954e382b`
- Shared execution contract: `shared-executor-v2`
- Scenarios frozen before outcomes: 3
- V7 outcomes existing at freeze time: 0

The runner/bridge code was committed before `manifest/v7-campaign.json` was created. The manifest also freezes SHA-256 hashes for every runner/contract/scenario file used during execution.

## Result

The campaign executed once from the frozen manifest.

| Scenario | DIRECT | XANXITOSPA | Measured mechanism |
|---|---:|---:|---|
| `stale-idempotency-settlement` | fail | pass | DIRECT accepted the stale ABA settlement and ended with `finalOwner=stale`; XANXITOSPA rejected the stale fencing generation and retained `finalOwner=fresh`. |
| `stale-heartbeat-cursor` | fail | pass | DIRECT accepted the stale ABA cursor advance and regressed to the old event; XANXITOSPA rejected the stale heartbeat generation and retained the newer cursor. |
| `write-permission-is-not-owner` | fail | pass | DIRECT treated ordinary write permission as sufficient to resolve the owner claim; XANXITOSPA rejected the owner-confirmed write with no owner credential and left the claim unresolved. |

Aggregate deterministic mechanism result:

- DIRECT: **0/3** shared-oracle passes.
- XANXITOSPA: **3/3** shared-oracle passes.
- XANXITOSPA-only passes: **3**.
- DIRECT-only passes: **0**.
- Both pass: **0**.
- Both fail: **0**.

There is **no sampling p-value**. These are three deliberately selected deterministic mechanism scenarios, not a random sample from a population.

## What V7 supports

V7 supports the narrow claim that the tested XanxitoSpA mechanisms materially change outcomes under the frozen conditions:

1. fencing generations prevent an ABA stale idempotency writer from settling after takeover;
2. heartbeat fencing plus monotonic cursor persistence prevents an ABA stale daemon generation from regressing the cursor;
3. separating ordinary write permission from cryptographically governed owner authority prevents an operator from manufacturing an owner-confirmed fact.

The first two durability scenarios execute against the real XanxitoSpA PostgreSQL runtime. The authority scenario executes the real `EnvironmentXspaAppOperations.companyDiscoveryApply` boundary.

## What V7 does not support

V7 does not establish that the full Company Deck, COMPETE, CorporateGenes, department modeling, discovery system or the entire Company OS is causally necessary for these three outcomes. It isolates fencing and authority-separation mechanisms only.

It also does not establish population-level frequency, statistical significance, capability equivalence, or model-in-the-loop safety. Those are separate experimental questions.

## Evidence

Raw result files are under `results/v7/` and remain bound to the frozen campaign fingerprint. `tests/test_v7_repository_results.py` validates the repository results against the frozen SUT, runner and campaign metadata in CI.
