#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import subprocess
import tempfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from harness.v5_replication import validate_manifest

V4_MANIFEST = Path("manifest/fault-injection-v4-stateful.json")
RUNTIME = Path("/home/sebastian/workspace/xspa-benchmark/runtime")
BACKUP_DIR = Path("/home/sebastian/workspace/xspa-benchmark/infra-backups/plane-20241031-0351")
ROCKETCHAT_RESET_CONTAINER = "tac-v4-rc-direct-cal"
PLANE_PROJECT = "73cb74f7-a7ac-4292-a915-e2f59a09a703"
PLANE_ISSUE = "5d1c8695-acfd-44c2-8d2d-e41c67cdd8c0"
PLANE_TARGET_STATE = "In Progress"


def _load(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _pair_entry(manifest: dict[str, Any], pair_index: int) -> dict[str, Any]:
    rows = [row for row in manifest["pairOrder"] if row["pairIndex"] == pair_index]
    if len(rows) != 1:
        raise RuntimeError(f"pairIndex not unique: {pair_index}")
    return rows[0]


def _scenario(manifest: dict[str, Any], scenario_id: str) -> dict[str, Any]:
    rows = [row for row in manifest["scenarioCatalog"] if row["id"] == scenario_id]
    if len(rows) != 1:
        raise RuntimeError(f"scenario not unique: {scenario_id}")
    return rows[0]


def _condition_for(task_id: str, scenario_id: str) -> str:
    prefix = task_id + "__"
    if not scenario_id.startswith(prefix):
        raise RuntimeError("scenario/task mismatch")
    return scenario_id[len(prefix):]


def _runner_argv(task_id: str, condition: str, arm: str, raw_path: Path, manifest: dict[str, Any], entry: dict[str, Any], xspa_repo: str) -> tuple[list[str], int]:
    common = ["--arm", arm, "--condition", condition, "--xspa-repo", xspa_repo]
    fp = ["--manifest-fingerprint", manifest["manifestFingerprint"]]
    if task_id == "sde-debug-crashed-server":
        return ([
            "python", "-m", "harness.run_v4_local_runtime_arm",
            *common,
            "--config", str(RUNTIME / "tac-local-runtime-fixture.json"),
            "--output", str(raw_path),
            *fp,
        ], 300)
    if task_id == "qa-escalate-emergency":
        text = f"XSPA-V5-R{entry['repetition']}-P{entry['pairIndex']}-{condition.upper()}"
        return ([
            "python", "-m", "harness.run_surface_rocketchat_arm",
            *common,
            "--reset-container", ROCKETCHAT_RESET_CONTAINER,
            "--config", str(RUNTIME / "tac-rocketchat-fixture.json"),
            "--target", "Sarah Johnson",
            "--text", text,
            "--output", str(raw_path),
            *fp,
        ], 300)
    if task_id == "admin-employee-info-reconciliation":
        path = f"/Documents/xspa-v5-r{entry['repetition']}-p{entry['pairIndex']}.csv"
        return ([
            "python", "-m", "harness.run_v4_owncloud_arm",
            *common,
            "--config", str(RUNTIME / "tac-owncloud-fixture.json"),
            "--path", path,
            "--output", str(raw_path),
            *fp,
        ], 300)
    if task_id == "qa-update-issue-status-according-to-colleagues":
        return ([
            "python", "-m", "harness.run_v4_plane_arm",
            *common,
            "--config", str(RUNTIME / "tac-plane-fixture.json"),
            "--backup-dir", str(BACKUP_DIR),
            "--project", PLANE_PROJECT,
            "--issue", PLANE_ISSUE,
            "--target-state", PLANE_TARGET_STATE,
            "--output", str(raw_path),
            *fp,
        ], 300)
    if task_id == "pm-ask-for-issue-and-create-in-gitlab":
        return ([
            "python", "-m", "harness.run_v4_gitlab_arm",
            *common,
            "--config", str(RUNTIME / "tac-gitlab-fixture.json"),
            "--renew-script", str(RUNTIME / "renew_gitlab_fixture_token.rb"),
            "--output", str(raw_path),
            *fp,
        ], 600)
    raise RuntimeError(f"unsupported v5 task: {task_id}")


def main() -> int:
    parser = argparse.ArgumentParser(description="Run one precommitted v5 replication arm using frozen v4 surface semantics")
    parser.add_argument("--manifest", default="manifest/fault-injection-v5-replication.json")
    parser.add_argument("--pair-index", type=int, required=True)
    parser.add_argument("--arm", choices=["direct", "xanxitospa"], required=True)
    parser.add_argument("--attempt", type=int, default=1)
    parser.add_argument("--output", required=True)
    parser.add_argument("--xspa-repo", default="/home/sebastian/workspace/xanxitospa")
    args = parser.parse_args()

    manifest = _load(Path(args.manifest))
    v4 = _load(V4_MANIFEST)
    validate_manifest(manifest, v4)
    entry = _pair_entry(manifest, args.pair_index)
    scenario = _scenario(manifest, entry["scenarioId"])
    task_id = scenario["taskId"]
    condition = _condition_for(task_id, scenario["id"])

    output = Path(args.output)
    if output.exists():
        raise RuntimeError(f"refusing to overwrite v5 result: {output}")
    output.parent.mkdir(parents=True, exist_ok=True)

    with tempfile.TemporaryDirectory(prefix="xspa-v5-raw-") as td:
        raw_path = Path(td) / "raw.json"
        argv, timeout = _runner_argv(task_id, condition, args.arm, raw_path, manifest, entry, args.xspa_repo)
        proc = subprocess.run(argv, text=True, capture_output=True, timeout=timeout)
        if proc.returncode != 0 or not raw_path.is_file():
            raise RuntimeError(f"surface runner failed rc={proc.returncode}: {proc.stderr[-1800:]} {proc.stdout[-1800:]}")
        raw = _load(raw_path)

    payload = {
        "benchmark": "XanxitoSpA fault-injection replication",
        "version": manifest["version"],
        "manifestFingerprint": manifest["manifestFingerprint"],
        "parentManifestVersion": manifest["parentManifestVersion"],
        "pairIndex": entry["pairIndex"],
        "repetition": entry["repetition"],
        "scenarioId": entry["scenarioId"],
        "armOrder": entry["armOrder"],
        "arm": args.arm,
        "attempt": args.attempt,
        "valid": True,
        "generatedAt": datetime.now(timezone.utc).isoformat(),
        "sourceRunner": argv[2] if len(argv) > 2 else argv[0],
        "reset": raw.get("reset"),
        "result": raw.get("result"),
    }
    output.write_text(json.dumps(payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(json.dumps(payload, indent=2, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
