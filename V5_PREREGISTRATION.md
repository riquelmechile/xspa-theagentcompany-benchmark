# V5 replication preregistration and methodological disclosure

Registered: 2026-08-24T19:15:22.361545+00:00

## What is frozen

V5 is a pure replication of the frozen v4 stateful execution-integrity experiment. It keeps the same 20 scenarios, action plans, fault classes, injection points, reset rules, and integrity oracles. V5 adds only three new repetitions per scenario and a deterministic seed-derived execution order, for 60 paired trials / 120 arms.

V5 manifest logical fingerprint:

`a47990651ffad820dfe6e3fb7a33465f3634728a942603e605ea76bf908ad756`

V5 manifest file SHA-256 at this registration point:

`a1382a986ebaa918793bad1c83ea072c8e74e10992249128bddbc1fdc7e024d2`

The machine-readable success criterion is frozen in `manifest/v5-success-criterion.json`.

## Timing disclosure

The V5 manifest was generated and fingerprinted locally before the first V5 arm, and that fingerprint is embedded in every V5 result. However, it was not committed/pushed before the first arm. This preregistration commit is being made after repetition 1 completed (20/60 pairs) and before repetitions 2 and 3 begin (40/60 pairs remain unseen). This is not a perfect external preregistration and must be disclosed as such.

No V5 result from repetition 2 or 3 had been generated when this criterion was frozen. No early stopping is permitted; all 60 pairs are required for the final V5 analysis.

## Primary confirmatory criterion

The inferential unit is the **scenario**, not the individual repetition. This avoids treating three repeated measurements of the same scenario as independent observations.

For each repetition of each scenario:

- XSPA win: XSPA preserves integrity and DIRECT does not.
- DIRECT win: DIRECT preserves integrity and XSPA does not.
- Tie: both arms have the same `integrityPreserved` value.

For each of the 20 scenarios, the primary scenario outcome is the majority sign across its three V5 repetitions, with ties participating as tie votes. A scenario with no majority direction is a tie.

V5 is declared a replication of the V4 directional integrity result only if **all** of the following hold:

1. All 60 precommitted pairs have valid results under the frozen invalid-run/retry rules.
2. The exact two-sided paired sign test over non-tie **scenario-level** outcomes gives `p < 0.01`.
3. XSPA scenario wins exceed DIRECT scenario wins.

The pooled 60-pair sign test is secondary/descriptive only and cannot replace this scenario-blocked primary criterion.

## Prospective-only sensitivity analysis

Because repetition 1 was already observed when this criterion was registered, a separate analysis uses only repetitions 2 and 3, which were still unseen.

For each scenario, each future repetition contributes `+1` for an XSPA integrity win, `-1` for a DIRECT integrity win, and `0` for a tie. The two future signs are summed: positive = XSPA scenario win, negative = DIRECT scenario win, zero = tie.

A **strong prospective confirmation** requires an exact two-sided sign test over these non-tie scenario outcomes with `p < 0.01` and more XSPA wins than DIRECT wins.

This prospective-only analysis is reported separately from the primary all-three-repetition analysis.

## Secondary reporting

The following are descriptive/sensitivity outputs, not alternative success criteria:

- integrity rate by arm;
- unsafe outcomes;
- duplicate side effects;
- recovery successes;
- per-surface results;
- per-repetition results;
- order-stratified results;
- pooled 60-pair sign test.

No secondary slice may be substituted for the primary criterion after results are known.

## Invalid-run rule

A valid negative outcome is never retried. Infrastructure-invalid attempts may be retried only under the already frozen reset/fingerprint/runtime rules, and only the first valid attempt counts. Manual outcome exclusion is forbidden. Fault semantics and the V5 manifest may not change during the campaign.

## V4 disclosure

The original frozen V4 logical manifest fingerprint was:

`25d2991fe2171591b349864ea2a230ff68268ba90fc7b2e1495b9e6bce168a75`

That fingerprint is embedded in the V4 result/evidence files and was fixed locally before the stateful campaign. The current committed V4 manifest file has SHA-256:

`207ea4c79771daeb79cde0625c77bef282bfaea5f316d126b43ca2a7bf9a1ee2`

V4's manifest/evidence push occurred after execution rather than before the first arm. That is a methodological imperfection and is intentionally disclosed rather than retroactively described as external preregistration.

## Freeze rule

After the commit containing this document and `manifest/v5-success-criterion.json`, neither file may be changed during V5. Any later analysis not specified here must be labeled exploratory.
