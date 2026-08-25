#!/usr/bin/env python3
from __future__ import annotations

import argparse
import hashlib
import json
import os
import subprocess
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_MANIFEST = REPO_ROOT / "manifest" / "fault-injection-v4-pilot.json"
DEFAULT_XSPA_REPO = Path(os.environ.get("XSPA_SUT_DIR", REPO_ROOT.parent / "xanxitospa"))
DEFAULT_OUTPUT = REPO_ROOT / "results" / "fault-injection-v4-pilot.json"


class PilotValidationError(RuntimeError):
    pass


def load_manifest(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if value.get("version") != "v4-pilot-1":
        raise PilotValidationError("unexpected v4 pilot manifest version")
    scenarios = value.get("scenarios")
    if not isinstance(scenarios, list) or not scenarios:
        raise PilotValidationError("manifest requires scenarios")
    ids = [scenario.get("id") for scenario in scenarios if isinstance(scenario, dict)]
    if len(ids) != len(scenarios) or any(not isinstance(item, str) or not item for item in ids):
        raise PilotValidationError("every scenario requires a non-empty id")
    if len(ids) != len(set(ids)):
        raise PilotValidationError("scenario ids must be unique")
    return value


def _manifest_fingerprint(manifest: dict[str, Any]) -> str:
    encoded = json.dumps(manifest, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode()
    return hashlib.sha256(encoded).hexdigest()


def validate_result(manifest: dict[str, Any], result: dict[str, Any]) -> dict[str, Any]:
    if result.get("version") != manifest.get("version"):
        raise PilotValidationError("result version does not match manifest")
    scenarios = result.get("scenarios")
    if not isinstance(scenarios, list):
        raise PilotValidationError("result scenarios missing")
    expected_ids = [scenario["id"] for scenario in manifest["scenarios"]]
    actual_ids = [scenario.get("id") for scenario in scenarios if isinstance(scenario, dict)]
    if actual_ids != expected_ids:
        raise PilotValidationError(f"scenario order mismatch: expected={expected_ids} actual={actual_ids}")
    required_arm_fields = {"completed", "integrityPreserved"}
    for scenario in scenarios:
        for arm in ("direct", "xanxitospa"):
            value = scenario.get(arm)
            if not isinstance(value, dict) or not required_arm_fields.issubset(value):
                raise PilotValidationError(f"scenario {scenario.get('id')} missing required {arm} metrics")
    aggregate = result.get("aggregate")
    if not isinstance(aggregate, dict):
        raise PilotValidationError("aggregate missing")
    for key in ("directIntegrityPasses", "xanxitospaIntegrityPasses", "directUnsafeEffects", "xanxitospaUnsafeEffects", "xanxitospaRecoverySuccesses"):
        if not isinstance(aggregate.get(key), int) or aggregate[key] < 0:
            raise PilotValidationError(f"invalid aggregate field: {key}")
    return result


def run_production_pilot(manifest: dict[str, Any], xspa_repo: Path = DEFAULT_XSPA_REPO) -> dict[str, Any]:
    ids = [scenario["id"] for scenario in manifest["scenarios"]]
    runner = xspa_repo / "packages" / "testing" / "src" / "run-fault-injection-pilot.ts"
    tsx_cli = xspa_repo / "node_modules" / "tsx" / "dist" / "cli.mjs"
    if not runner.is_file() or not tsx_cli.is_file():
        raise PilotValidationError("XanxitoSpA fault-injection runner or tsx runtime is missing")
    proc = subprocess.run(
        ["node", str(tsx_cli), str(runner), *ids],
        cwd=xspa_repo,
        text=True,
        capture_output=True,
        timeout=120,
        check=False,
    )
    if proc.returncode != 0:
        raise PilotValidationError(f"production pilot failed ({proc.returncode}): {proc.stderr.strip()}")
    try:
        result = json.loads(proc.stdout)
    except json.JSONDecodeError as exc:
        raise PilotValidationError(f"production pilot returned invalid JSON: {exc}") from exc
    return validate_result(manifest, result)


def write_publishable_result(manifest: dict[str, Any], raw: dict[str, Any], output: Path) -> dict[str, Any]:
    validated = validate_result(manifest, raw)
    value = {
        "benchmark": manifest["benchmark"],
        "version": manifest["version"],
        "finalBenchmark": False,
        "methodologyBoundary": "This is a production-kernel micro-pilot for deterministic fault injection. It validates the injector and governance metrics; it is not yet the final TheAgentCompany task-level v4 benchmark.",
        "manifestFingerprint": _manifest_fingerprint(manifest),
        "design": manifest["design"],
        "primaryMetrics": manifest["primaryMetrics"],
        "productionSurfaces": validated.get("productionSurfaces", []),
        "scenarios": validated["scenarios"],
        "aggregate": validated["aggregate"],
        "nextStage": manifest["nextStage"],
    }
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(value, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    return value


def main() -> int:
    parser = argparse.ArgumentParser(description="Run the XanxitoSpA v4 deterministic fault-injection micro-pilot")
    parser.add_argument("command", choices=["check", "run"], nargs="?", default="run")
    parser.add_argument("--manifest", type=Path, default=DEFAULT_MANIFEST)
    parser.add_argument("--xspa-repo", type=Path, default=DEFAULT_XSPA_REPO)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    args = parser.parse_args()
    try:
        manifest = load_manifest(args.manifest)
        if args.command == "check":
            print(json.dumps({"ok": True, "version": manifest["version"], "scenarioIds": [s["id"] for s in manifest["scenarios"]], "manifestFingerprint": _manifest_fingerprint(manifest)}, indent=2))
            return 0
        raw = run_production_pilot(manifest, args.xspa_repo)
        result = write_publishable_result(manifest, raw, args.output)
        print(json.dumps(result, indent=2, ensure_ascii=False))
        return 0
    except Exception as exc:
        print(json.dumps({"ok": False, "error": f"{type(exc).__name__}: {exc}"}, ensure_ascii=False))
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
