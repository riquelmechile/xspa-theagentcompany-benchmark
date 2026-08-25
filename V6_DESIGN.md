# V6 corrected integrity benchmark design

## Purpose

V6 replaces the causal interpretation of the historical v4/v5 scripted comparison. It asks a narrower question: **after DIRECT receives ordinary competent distributed-systems hygiene, which integrity differences remain attributable to XANXITOSPA-specific durable fencing and governance boundaries?**

V6 is a deterministic regression/causal-mechanism suite. It does not manufacture sampling p-values from fixed branches. Results are reported scenario by scenario with measured side effects, final state, recovery state and audit evidence.

## Non-negotiable comparison contract

For every pair, both arms MUST share the same:

1. action-plan fingerprint;
2. external mutation intent;
3. fault-injection fingerprint and timing point;
4. state reset/fingerprint before execution;
5. oracle implementation and integrity predicate;
6. target service/container version;
7. SUT commit SHA and clean-tree assertion for XANXITOSPA code used by either arm.

An outcome MUST be derived from measured observations. Literal arm-specific fields such as `integrityPreserved: false`, synthetic duplicate counts or arm-specific oracle formulas are forbidden.

## Competent DIRECT baseline

DIRECT is intentionally not “naive direct”. It receives ordinary application-level resilience that does not depend on XANXITOSPA:

- retry only when the result is known-not-applied;
- read/probe before retry when an acknowledgement is lost;
- stable idempotency keys when the target API natively supports them;
- bounded restart after process death;
- final-state verification using the common oracle.

DIRECT does **not** receive XANXITOSPA's durable idempotency journal, fencing-token settlement, Company constitution, signed authority mandates, budget adjudication or governed Work lifecycle. Those are the treatment mechanisms V6 is intended to isolate.

## Durable scenarios

Any scenario claiming crash recovery, takeover or stale-writer protection MUST use `PostgresRuntimeStore` (or a future equally durable store), not `InMemoryRuntimeStore`. At least one process must be killed between claim and settlement in recovery scenarios. A fresh process must reconstruct state from PostgreSQL before reconciliation.

## SUT pinning

Every manifest and result records:

- `sut.commitSha` — exact 40-hex Git commit;
- `sut.treeClean` — MUST be true;
- `sut.packageLockSha256`;
- `runtimeStore` — e.g. `postgres`;
- runner commit SHA from this benchmark repo.

The manifest fingerprint includes all of the above. A result whose SUT SHA differs from the frozen manifest is invalid, not retryable evidence.

## Statistics

V6's primary outputs are deterministic scenario outcomes and mechanism traces. No sign-test p-value is used as evidential strength unless a future experiment introduces a genuine randomization/sampling model and preregisters it. Repeated identical deterministic runs are reproducibility checks, not independent observations.

For future model-in-the-loop governance experiments, randomization can come from independently sampled model sessions/prompts/seeds or randomized adversarial perturbations; that design must be preregistered separately.

## Capacity non-regression

V3 is retained as “no directional difference detected”, not equivalence. Any future capability-neutral claim requires a preregistered equivalence margin and an appropriate paired equivalence procedure with adequate power.

## Portability

V6 code MUST use repository-relative paths or explicit environment variables. `/home/...` paths are forbidden in V6 files. Historical v1-v5 evidence is not rewritten.

## Result validity gates

A V6 result is valid only if `harness/v6_contract.py` accepts it. The validator rejects mismatched plan/oracle/fault fingerprints, unpinned SUTs, non-Postgres durability claims, dirty SUT trees and literal outcomes.
