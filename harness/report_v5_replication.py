#!/usr/bin/env python3
from __future__ import annotations

import argparse
import glob
import json
import math
from collections import defaultdict
from pathlib import Path
from typing import Any


def load(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def exact_two_sided_sign_p(wins: int, losses: int) -> float:
    n = wins + losses
    if n == 0:
        return 1.0
    k = min(wins, losses)
    tail = sum(math.comb(n, i) for i in range(k + 1)) / (2**n)
    return min(1.0, 2.0 * tail)


def sign(direct: dict[str, Any], xspa: dict[str, Any]) -> int:
    d = bool(direct["result"]["integrityPreserved"])
    x = bool(xspa["result"]["integrityPreserved"])
    return 1 if x and not d else -1 if d and not x else 0


def summarize_signs(values: list[int]) -> dict[str, Any]:
    wins = sum(v > 0 for v in values)
    losses = sum(v < 0 for v in values)
    ties = sum(v == 0 for v in values)
    return {
        "xanxitospaWins": wins,
        "directWins": losses,
        "ties": ties,
        "nonTies": wins + losses,
        "exactTwoSidedSignP": exact_two_sided_sign_p(wins, losses),
    }


def main() -> int:
    ap = argparse.ArgumentParser(description="Report preregistered V5 scenario-blocked analyses")
    ap.add_argument("--results-glob", default="results/v5-r*-p*.json")
    ap.add_argument("--criterion", default="manifest/v5-success-criterion.json")
    ap.add_argument("--output", default="results/v5-preregistered-analysis.json")
    args = ap.parse_args()

    criterion = load(Path(args.criterion))
    runs: dict[tuple[str, int, str], dict[str, Any]] = {}
    for name in sorted(glob.glob(args.results_glob)):
        path = Path(name)
        if path.name.endswith(".launch.json") or path.name.endswith(".runner.log"):
            continue
        row = load(path)
        if row.get("version") != "v5-replication-1" or not row.get("valid", False):
            continue
        runs[(row["scenarioId"], int(row["repetition"]), row["arm"])] = row

    scenario_reps: dict[str, dict[int, int]] = defaultdict(dict)
    for scenario in sorted({k[0] for k in runs}):
        for rep in (1, 2, 3):
            d = runs.get((scenario, rep, "direct"))
            x = runs.get((scenario, rep, "xanxitospa"))
            if d is None or x is None:
                raise SystemExit(f"incomplete scenario/repetition: {scenario} rep{rep}")
            if d["manifestFingerprint"] != x["manifestFingerprint"]:
                raise SystemExit(f"fingerprint mismatch: {scenario} rep{rep}")
            scenario_reps[scenario][rep] = sign(d, x)

    if len(scenario_reps) != 20:
        raise SystemExit(f"expected 20 scenarios, got {len(scenario_reps)}")

    per_rep = {str(rep): summarize_signs([reps[rep] for reps in scenario_reps.values()]) for rep in (1, 2, 3)}

    primary_signs = []
    prospective_signs = []
    scenario_rows = []
    for scenario, reps in sorted(scenario_reps.items()):
        votes = [reps[1], reps[2], reps[3]]
        total = sum(votes)
        primary = 1 if total > 0 else -1 if total < 0 else 0
        future_total = reps[2] + reps[3]
        prospective = 1 if future_total > 0 else -1 if future_total < 0 else 0
        primary_signs.append(primary)
        prospective_signs.append(prospective)
        scenario_rows.append({
            "scenarioId": scenario,
            "rep1": reps[1],
            "rep2": reps[2],
            "rep3": reps[3],
            "primaryScenarioSign": primary,
            "prospectiveRep2Rep3Sign": prospective,
        })

    primary = summarize_signs(primary_signs)
    prospective = summarize_signs(prospective_signs)
    pooled = summarize_signs([reps[rep] for reps in scenario_reps.values() for rep in (1, 2, 3)])

    primary_met = (
        primary["exactTwoSidedSignP"] < 0.01
        and primary["xanxitospaWins"] > primary["directWins"]
    )
    prospective_met = (
        prospective["exactTwoSidedSignP"] < 0.01
        and prospective["xanxitospaWins"] > prospective["directWins"]
    )

    payload = {
        "analysis": "preregistered-v5-scenario-blocked",
        "criterionFile": args.criterion,
        "criterionFreezeRule": criterion["freezeRule"],
        "repetitionScenarioSummaries": per_rep,
        "primaryAllThreeRepetitions": {**primary, "criterionMet": primary_met},
        "prospectiveOnlyRep2Rep3": {**prospective, "strongProspectiveConfirmationMet": prospective_met},
        "pooled60PairsDescriptiveOnly": pooled,
        "scenarios": scenario_rows,
    }
    Path(args.output).write_text(json.dumps(payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(json.dumps(payload, indent=2, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
