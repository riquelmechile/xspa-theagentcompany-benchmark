from __future__ import annotations

import hashlib
import json
import re
from pathlib import Path
from typing import Any

SHA40 = re.compile(r"^[0-9a-f]{40}$")
SHA64 = re.compile(r"^[0-9a-f]{64}$")

def _required(obj: dict[str, Any], key: str) -> Any:
    if key not in obj:
        raise ValueError(f"missing:{key}")
    return obj[key]

def validate_v6_result(result: dict[str, Any]) -> None:
    if result.get("schemaVersion") != 6:
        raise ValueError("schemaVersion")
    runner_commit = str(_required(result, "runnerCommitSha"))
    if not SHA40.fullmatch(runner_commit):
        raise ValueError("runnerCommitSha")
    manifest_fingerprint = str(_required(result, "manifestFingerprint"))
    if not SHA64.fullmatch(manifest_fingerprint):
        raise ValueError("manifestFingerprint")
    sut = _required(result, "sut")
    if not isinstance(sut, dict) or not SHA40.fullmatch(str(sut.get("commitSha", ""))):
        raise ValueError("sut.commitSha")
    if sut.get("treeClean") is not True:
        raise ValueError("sut.treeClean")
    if not SHA64.fullmatch(str(sut.get("packageLockSha256", ""))):
        raise ValueError("sut.packageLockSha256")
    pair = _required(result, "pairContract")
    if not isinstance(pair, dict):
        raise ValueError("pairContract")
    direct = _required(pair, "direct")
    xspa = _required(pair, "xanxitospa")
    for field in ("actionPlanFingerprint", "oracleFingerprint", "faultFingerprint", "preStateFingerprint"):
        if direct.get(field) != xspa.get(field):
            raise ValueError(f"arm-asymmetry:{field}")
        if not SHA64.fullmatch(str(direct.get(field, ""))):
            raise ValueError(f"invalid-fingerprint:{field}")
    if result.get("durabilityClaim") is True and result.get("runtimeStore") != "postgres":
        raise ValueError("durability-requires-postgres")
    outcomes = _required(result, "outcomes")
    if not isinstance(outcomes, dict):
        raise ValueError("outcomes")
    for arm in ("direct", "xanxitospa"):
        outcome = outcomes.get(arm)
        if not isinstance(outcome, dict):
            raise ValueError(f"outcomes.{arm}")
        forbidden_derived = {"literalOutcome", "integrityPreserved", "completed", "recoverySuccess", "safeHalt", "staleSettlementAccepted"}
        if forbidden_derived.intersection(outcome):
            raise ValueError(f"literal-outcome:{arm}")
        measurements = outcome.get("measurements")
        if not isinstance(measurements, dict) or not measurements:
            raise ValueError(f"measurements:{arm}")

def fingerprint_json(value: Any) -> str:
    payload = json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode()
    return hashlib.sha256(payload).hexdigest()

def validate_file(path: Path) -> None:
    validate_v6_result(json.loads(path.read_text()))

if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("result", type=Path)
    args = parser.parse_args()
    validate_file(args.result)
    print("PASS v6 contract")
