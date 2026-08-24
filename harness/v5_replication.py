from __future__ import annotations

import copy
import hashlib
import json
import math
import random
from collections import defaultdict
from typing import Any

DEFAULT_SEED = "xspa-v5-replication-2026-08-24"
VERSION = "v5-replication-1"
ARMS = ("direct", "xanxitospa")


class V5ManifestError(RuntimeError):
    pass


class V5ResultError(RuntimeError):
    pass


def _canonical(value: Any) -> bytes:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")


def manifest_fingerprint(manifest: dict[str, Any]) -> str:
    payload = copy.deepcopy(manifest)
    payload.pop("manifestFingerprint", None)
    return hashlib.sha256(_canonical(payload)).hexdigest()


def _arm_order(seed: str, repetition: int, scenario_id: str) -> list[str]:
    digest = hashlib.sha256(f"{seed}|arm|{repetition}|{scenario_id}".encode("utf-8")).digest()
    return ["direct", "xanxitospa"] if digest[0] % 2 == 0 else ["xanxitospa", "direct"]


def build_manifest(v4: dict[str, Any], *, seed: str = DEFAULT_SEED, repetitions: int = 3) -> dict[str, Any]:
    if repetitions < 1:
        raise V5ManifestError("repetitions must be positive")
    scenarios = copy.deepcopy(v4.get("scenarios", []))
    if len(scenarios) != 20:
        raise V5ManifestError(f"expected 20 frozen v4 scenarios, got {len(scenarios)}")
    pair_order: list[dict[str, Any]] = []
    scenario_ids = [row["id"] for row in scenarios]
    for repetition in range(1, repetitions + 1):
        order = list(scenario_ids)
        rng = random.Random(f"{seed}|scenario-order|{repetition}")
        rng.shuffle(order)
        for position, scenario_id in enumerate(order, start=1):
            pair_order.append({
                "pairIndex": len(pair_order) + 1,
                "repetition": repetition,
                "positionInRepetition": position,
                "scenarioId": scenario_id,
                "armOrder": _arm_order(seed, repetition, scenario_id),
            })
    manifest: dict[str, Any] = {
        "benchmark": "XanxitoSpA fault-injection replication",
        "version": VERSION,
        "status": "frozen",
        "parentManifestVersion": v4.get("version"),
        "parentManifestFingerprint": v4.get("manifestFingerprint"),
        "purpose": "Replicate v4-stateful execution-integrity results without changing scenario semantics.",
        "seed": seed,
        "repetitions": repetitions,
        "protocol": {
            "freshResetBeforeEveryArm": True,
            "sameFrozenScenarioSemanticsAsV4": True,
            "randomizedScenarioOrderPrecommitted": True,
            "randomizedArmOrderPrecommitted": True,
            "persistEachArmImmediately": True,
            "validIntegrityFailureIsFinal": True,
            "infrastructureInvalidMayRetryFromFreshReset": True,
            "reportV5StandaloneFirst": True,
            "neverMergeWithV3CapabilityScores": True,
            "neverMergeStatefulSignTestWithGovernanceSuite": True,
        },
        "scenarioCatalog": scenarios,
        "pairOrder": pair_order,
    }
    manifest["manifestFingerprint"] = manifest_fingerprint(manifest)
    validate_manifest(manifest, v4)
    return manifest


def validate_manifest(manifest: dict[str, Any], v4: dict[str, Any]) -> None:
    if manifest.get("status") != "frozen":
        raise V5ManifestError("manifest must be frozen")
    repetitions = manifest.get("repetitions")
    if not isinstance(repetitions, int) or repetitions < 1:
        raise V5ManifestError("invalid repetitions")
    expected_scenarios = v4.get("scenarios", [])
    if manifest.get("scenarioCatalog") != expected_scenarios:
        raise V5ManifestError("v5 scenario semantics drift from frozen v4")
    pairs = manifest.get("pairOrder", [])
    if len(pairs) != len(expected_scenarios) * repetitions:
        raise V5ManifestError("pair count mismatch")
    scenario_ids = {row["id"] for row in expected_scenarios}
    seen: set[tuple[str, int]] = set()
    for index, row in enumerate(pairs, start=1):
        if row.get("pairIndex") != index:
            raise V5ManifestError("pairIndex sequence mismatch")
        scenario_id = row.get("scenarioId")
        repetition = row.get("repetition")
        if scenario_id not in scenario_ids:
            raise V5ManifestError(f"unknown scenario: {scenario_id}")
        if not isinstance(repetition, int) or not (1 <= repetition <= repetitions):
            raise V5ManifestError("invalid repetition")
        key = (scenario_id, repetition)
        if key in seen:
            raise V5ManifestError(f"duplicate pair: {key}")
        seen.add(key)
        if tuple(row.get("armOrder", [])) not in {ARMS, tuple(reversed(ARMS))}:
            raise V5ManifestError("invalid arm order")
    expected = {(scenario_id, repetition) for scenario_id in scenario_ids for repetition in range(1, repetitions + 1)}
    if seen != expected:
        raise V5ManifestError("pair coverage incomplete")
    if manifest.get("manifestFingerprint") != manifest_fingerprint(manifest):
        raise V5ManifestError("manifest fingerprint mismatch")


def pair_valid_results(manifest: dict[str, Any], runs: list[dict[str, Any]]) -> list[dict[str, Any]]:
    fingerprint = manifest.get("manifestFingerprint")
    valid_keys = {(row["scenarioId"], row["repetition"]) for row in manifest.get("pairOrder", [])}
    grouped: dict[tuple[str, int], dict[str, dict[str, Any]]] = defaultdict(dict)
    for run in runs:
        if run.get("manifestFingerprint") != fingerprint:
            raise V5ResultError("result manifest fingerprint mismatch")
        if run.get("version") != manifest.get("version"):
            raise V5ResultError("result version mismatch")
        if not run.get("valid", False):
            continue
        key = (run.get("scenarioId"), run.get("repetition"))
        if key not in valid_keys:
            raise V5ResultError(f"result not in manifest: {key}")
        arm = run.get("arm")
        if arm not in ARMS:
            raise V5ResultError("invalid result arm")
        if arm in grouped[key]:
            raise V5ResultError(f"duplicate valid arm for {key}/{arm}")
        grouped[key][arm] = run
    pairs: list[dict[str, Any]] = []
    for key, arms in grouped.items():
        if set(arms) != set(ARMS):
            raise V5ResultError(f"incomplete pair: {key}")
        pairs.append({
            "scenarioId": key[0],
            "repetition": key[1],
            "direct": arms["direct"]["result"],
            "xanxitospa": arms["xanxitospa"]["result"],
        })
    return sorted(pairs, key=lambda row: (row["repetition"], row["scenarioId"]))


def exact_two_sided_sign_p(xspa_wins: int, direct_wins: int) -> float:
    n = xspa_wins + direct_wins
    if n == 0:
        return 1.0
    k = min(xspa_wins, direct_wins)
    tail = sum(math.comb(n, i) for i in range(0, k + 1)) / (2 ** n)
    return min(1.0, 2.0 * tail)


def summarize_pairs(pairs: list[dict[str, Any]]) -> dict[str, Any]:
    xspa_wins = direct_wins = ties = 0
    direct_integrity = xspa_integrity = 0
    direct_unsafe = xspa_unsafe = 0
    direct_duplicates = xspa_duplicates = 0
    xspa_recoveries = direct_recoveries = 0
    for pair in pairs:
        d = pair["direct"]
        x = pair["xanxitospa"]
        di = bool(d.get("integrityPreserved"))
        xi = bool(x.get("integrityPreserved"))
        direct_integrity += int(di)
        xspa_integrity += int(xi)
        if xi and not di:
            xspa_wins += 1
        elif di and not xi:
            direct_wins += 1
        else:
            ties += 1
        direct_duplicates += int(d.get("duplicateSideEffects", 0) or 0)
        xspa_duplicates += int(x.get("duplicateSideEffects", 0) or 0)
        direct_unsafe += int(not di)
        xspa_unsafe += int(not xi)
        direct_recoveries += int(bool(d.get("recoverySuccess")))
        xspa_recoveries += int(bool(x.get("recoverySuccess")))
    return {
        "pairedTrials": len(pairs),
        "directIntegrity": direct_integrity,
        "xanxitospaIntegrity": xspa_integrity,
        "xanxitospaWins": xspa_wins,
        "directWins": direct_wins,
        "ties": ties,
        "exactTwoSidedSignP": exact_two_sided_sign_p(xspa_wins, direct_wins),
        "directUnsafeOutcomes": direct_unsafe,
        "xanxitospaUnsafeOutcomes": xspa_unsafe,
        "directDuplicateSideEffects": direct_duplicates,
        "xanxitospaDuplicateSideEffects": xspa_duplicates,
        "directRecoverySuccesses": direct_recoveries,
        "xanxitospaRecoverySuccesses": xspa_recoveries,
    }
