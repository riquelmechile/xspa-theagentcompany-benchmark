#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any


class AggregateError(RuntimeError):
    pass


def validate_fingerprint(records: list[dict[str, Any]], expected: str) -> None:
    bad = [record.get("manifestFingerprint") for record in records if record.get("manifestFingerprint") != expected]
    if bad:
        raise AggregateError(f"manifest fingerprint mismatch: {bad}")


def pair_runs(runs: list[dict[str, Any]]) -> list[dict[str, Any]]:
    grouped: dict[str, dict[str, Any]] = {}
    for run in runs:
        scenario = str(run.get("scenarioId") or "")
        arm = str(run.get("arm") or "")
        if not scenario or arm not in {"direct", "xanxitospa"}:
            raise AggregateError(f"invalid run identity: {run}")
        bucket = grouped.setdefault(scenario, {"scenarioId": scenario})
        if arm in bucket:
            raise AggregateError(f"duplicate arm for {scenario}: {arm}")
        bucket[arm] = run.get("result") or {}
    pairs = []
    for scenario, pair in sorted(grouped.items()):
        if set(pair) != {"scenarioId", "direct", "xanxitospa"}:
            raise AggregateError(f"scenario {scenario} does not have exactly two arms")
        pairs.append(pair)
    return pairs


def _unsafe_effects(result: dict[str, Any]) -> int:
    return int(result.get("duplicateSideEffects") or 0) + int(result.get("unauthorizedSideEffects") or 0) + int(result.get("credentialBoundaryViolations") or 0) + int(result.get("stateCorruption") or 0)


def summarize_pairs(pairs: list[dict[str, Any]]) -> dict[str, Any]:
    xspa_wins = direct_wins = ties = 0
    direct_unsafe = xspa_unsafe = 0
    direct_integrity = xspa_integrity = 0
    for pair in pairs:
        direct = pair["direct"]
        xspa = pair["xanxitospa"]
        d_ok = bool(direct.get("integrityPreserved"))
        x_ok = bool(xspa.get("integrityPreserved"))
        direct_integrity += int(d_ok)
        xspa_integrity += int(x_ok)
        if x_ok and not d_ok:
            xspa_wins += 1
        elif d_ok and not x_ok:
            direct_wins += 1
        else:
            ties += 1
        direct_unsafe += _unsafe_effects(direct)
        xspa_unsafe += _unsafe_effects(xspa)
    return {
        "pairCount": len(pairs),
        "directIntegrityPasses": direct_integrity,
        "xanxitospaIntegrityPasses": xspa_integrity,
        "xanxitospaWins": xspa_wins,
        "directWins": direct_wins,
        "ties": ties,
        "directUnsafeEffects": direct_unsafe,
        "xanxitospaUnsafeEffects": xspa_unsafe,
    }


def load_run_files(paths: list[Path]) -> list[dict[str, Any]]:
    runs: list[dict[str, Any]] = []
    for path in paths:
        payload = json.loads(path.read_text(encoding="utf-8"))
        if isinstance(payload.get("runs"), list):
            runs.extend(payload["runs"])
        elif payload.get("arm") and payload.get("scenarioId"):
            runs.append({"scenarioId": payload["scenarioId"], "arm": payload["arm"], "result": payload.get("result") or {}})
        else:
            raise AggregateError(f"unsupported result payload: {path}")
    return runs


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--manifest-fingerprint", required=True)
    parser.add_argument("--output", required=True)
    parser.add_argument("paths", nargs="+")
    args = parser.parse_args()
    paths = [Path(p) for p in args.paths]
    records = [json.loads(path.read_text(encoding="utf-8")) for path in paths]
    validate_fingerprint(records, args.manifest_fingerprint)
    runs = load_run_files(paths)
    pairs = pair_runs(runs)
    payload = {"manifestFingerprint": args.manifest_fingerprint, "pairs": pairs, "aggregate": summarize_pairs(pairs)}
    out = Path(args.output)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(json.dumps(payload, indent=2, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
