# V5 historical deterministic replication report

> **Methodological correction (2026-08-25).** The raw V5 outcomes, preregistration and commit chronology are preserved unchanged, but the former statistical-confirmation interpretation is withdrawn. A code audit found deterministic fixed branches, arm-asymmetric mutation/recovery logic, and two DIRECT cases whose failing integrity outcome is effectively encoded by the implementation. The sign-test values below are historical outputs of the preregistered analysis, **not sampling p-values that quantify evidence for a population effect**. Three identical repetitions demonstrate deterministic replay of the suite, not independent replication. See `V6_DESIGN.md` for the corrected comparison contract.

## Result

Historically, V5 satisfied the criterion frozen before repetitions 2 and 3 were observed. After runner audit, this is retained as a chronology/preregistration fact rather than interpreted as prospective statistical confirmation.

The preregistered **prospective-only analysis historically produced**: across the 20 scenarios, combining only repetitions 2 and 3 gives **8 XANXITOSPA wins, 0 DIRECT wins, and 12 ties**. The exact two-sided sign test over the 8 non-tie scenario outcomes is **p = 0.0078125**, which mechanically satisfied the frozen rule (`p < 0.01` and direction favoring XANXITOSPA).

The preregistered primary all-three-repetition scenario analysis is also **8 / 0 / 12, p = 0.0078125**. Each individual repetition independently produced the same scenario-level split: **8 / 0 / 12**.

The pooled 60-pair result is **descriptive only**, as preregistered: XANXITOSPA preserved integrity in **60/60** pairs versus **36/60** for DIRECT, with **24 XANXITOSPA wins, 0 DIRECT wins, 36 ties**, exact two-sided sign-test **p = 1.1920928955078125e-07**. This pooled p-value is not used as the primary inferential result because repetitions within a scenario are not treated as independent scenarios.

## Preregistration timeline

The V5 manifest was generated and fingerprinted before the first V5 arm, but repetition 1 completed before the preregistration commit. Commit `da81bedbe4df5804925170216f6e762c64015c7a` (`docs: preregister v5 replication criterion`) records that limitation and freezes the success criterion before repetitions 2 and 3 began. Commit `761f75a976c4a1dac80938b5478227138bc48fe5` then pins the V5 runner. The raw V5 outcomes are committed only after the campaign completed, preserving the externally inspectable Git timeline.

`V5_PREREGISTRATION.md` explicitly discloses that V4's manifest/evidence push occurred after V4 execution. That disclosure is retained unchanged; V4 is therefore prior discovery/confirmation evidence, not claimed as an externally preregistered experiment.

## Interpretation

The defensible post-audit interpretation is narrower. V3 detected no directional capability difference in its small matched sample but did not establish equivalence. V4/V5 show deterministic regression differences between the exact scripted arms that were executed. They do not yet establish that the broader XANXITOSPA architecture causally outperforms a competent DIRECT resilience baseline. V6 is designed to test that narrower causal question.

A key limitation is that the DIRECT arm was **not specifically prompted or instrumented to add its own resilience layer**. The comparison therefore estimates the effect of adding the XANXITOSPA execution-integrity substrate to otherwise direct execution under the frozen benchmark protocol; it does not establish that no specially engineered DIRECT resilience strategy could achieve comparable behavior.

## Evidence and reproduction

Canonical artifacts:

- `V5_PREREGISTRATION.md` — preregistration disclosure and frozen analysis plan.
- `manifest/v5-success-criterion.json` — machine-readable frozen success criterion.
- `manifest/fault-injection-v5-replication.json` — frozen V5 scenario/order manifest.
- `results/v5-r*-p*-direct.json` and `results/v5-r*-p*-xanxitospa.json` — raw valid V5 arm outcomes.
- `results/v5-invalid-attempts/` — retained invalid attempt evidence; valid negative outcomes were not retried.
- `results/v5-replication-final.json` — pooled descriptive aggregate.
- `results/v5-preregistered-analysis.json` — scenario-blocked primary and prospective analyses.
- `evidence/local-evidence-sha256-v5.json` — SHA-256 ledger for V5 publication artifacts.

After cloning, reproduce the published analyses with:

```bash
python -m harness.aggregate_v5_replication --require-complete --output /tmp/v5-replication-final.json
python -m harness.report_v5_replication --output /tmp/v5-preregistered-analysis.json
```

Then compare the substantive result fields in those generated files with `results/v5-replication-final.json` and `results/v5-preregistered-analysis.json`. The `generatedAt` field in the pooled aggregate is expected to differ when regenerated.

To verify the preregistration chronology directly:

```bash
git show --stat da81bedbe4df5804925170216f6e762c64015c7a
git log --reverse --format='%H %aI %s'
git log --all -- results/v5-r01-p001-direct.json results/v5-r02-p021-direct.json results/v5-r03-p041-direct.json
```
