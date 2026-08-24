#!/usr/bin/env python3
from __future__ import annotations

import argparse
import fcntl
import json
import subprocess
from datetime import datetime, timezone
from pathlib import Path

from harness.reset_controller import reset_plane, validate_backup_set

CONDITIONS = ["control", "lost_ack_after_patch", "auth_session_expiry", "stale_writer_after_takeover"]
ARMS = ["direct", "xanxitospa"]
EXPECTED_FINGERPRINT = "8b6d75852ac9fbb2632b7f644b2c1277650a92d97925f0e0b4a1a569faa24627"


def run(argv: list[str], *, cwd: Path | None = None, timeout: int = 180) -> subprocess.CompletedProcess[str]:
    proc = subprocess.run(argv, cwd=str(cwd) if cwd else None, text=True, capture_output=True, timeout=timeout)
    if proc.returncode != 0:
        raise RuntimeError(f"command failed {argv}: {proc.stderr[-1000:]} {proc.stdout[-1000:]}")
    return proc


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--arm", required=True, choices=ARMS)
    parser.add_argument("--condition", required=True, choices=CONDITIONS)
    parser.add_argument("--xspa-repo", required=True)
    parser.add_argument("--config", required=True)
    parser.add_argument("--backup-dir", required=True)
    parser.add_argument("--output", required=True)
    parser.add_argument("--project", required=True)
    parser.add_argument("--issue", required=True)
    parser.add_argument("--target-state", required=True)
    parser.add_argument("--manifest-fingerprint", required=True)
    args = parser.parse_args()

    output = Path(args.output)
    output.parent.mkdir(parents=True, exist_ok=True)
    lock_handle = (output.parent / (output.name + ".lock")).open("a+")
    try:
        fcntl.flock(lock_handle.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
    except BlockingIOError:
        print(json.dumps({"ok": False, "duplicateSuppressed": True, "output": str(output)}))
        return 75

    backup_hashes = validate_backup_set(Path(args.backup_dir))
    baseline = reset_plane(backup_hashes)
    if baseline.get("fingerprint") != EXPECTED_FINGERPRINT:
        raise RuntimeError(f"unexpected Plane baseline: {baseline.get('fingerprint')}")

    proc = run([
        "pnpm", "exec", "tsx", "packages/testing/src/run-tac-plane-fault.ts",
        "--mode", args.arm,
        "--condition", args.condition,
        "--config", args.config,
        "--project", args.project,
        "--issue", args.issue,
        "--target-state", args.target_state,
    ], cwd=Path(args.xspa_repo), timeout=120)
    result = json.loads(proc.stdout)
    payload = {
        "benchmark": "XanxitoSpA fault-injection v4",
        "version": "v4-stateful-1",
        "manifestFingerprint": args.manifest_fingerprint,
        "taskId": "qa-update-issue-status-according-to-colleagues",
        "scenarioId": f"qa-update-issue-status-according-to-colleagues__{args.condition}",
        "arm": args.arm,
        "condition": args.condition,
        "generatedAt": datetime.now(timezone.utc).isoformat(),
        "reset": {
            "fingerprint": baseline["fingerprint"],
            "counts": baseline["counts"],
            "backupSha256": baseline["backup_sha256"],
        },
        "result": result,
    }
    output.write_text(json.dumps(payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(json.dumps(payload, indent=2, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
