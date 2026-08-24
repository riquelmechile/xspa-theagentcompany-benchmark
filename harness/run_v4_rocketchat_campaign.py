#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import subprocess
from datetime import datetime, timezone
from pathlib import Path

CONDITIONS = [
    "control",
    "lost_ack_after_commit",
    "auth_session_expiry",
    "concurrent_duplicate_intent",
]
ARMS = ["direct", "xanxitospa"]


def run(argv: list[str], *, cwd: Path | None = None, timeout: int = 150) -> subprocess.CompletedProcess[str]:
    proc = subprocess.run(argv, cwd=str(cwd) if cwd else None, text=True, capture_output=True, timeout=timeout)
    if proc.returncode != 0:
        raise RuntimeError(f"command failed {argv}: {proc.stderr[-800:]} {proc.stdout[-800:]}")
    return proc


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--reset-container", required=True)
    parser.add_argument("--xspa-repo", required=True)
    parser.add_argument("--config", required=True)
    parser.add_argument("--output", required=True)
    parser.add_argument("--condition", required=True, choices=CONDITIONS)
    parser.add_argument("--target", default="Sarah Johnson")
    parser.add_argument("--manifest-fingerprint", required=True)
    args = parser.parse_args()

    xspa_repo = Path(args.xspa_repo)
    condition = args.condition
    text = f"XSPA-V4-QA-ESCALATE-{condition.upper()}"
    rows = []
    for arm in ARMS:
        reset = run(["docker", "exec", args.reset_container, "/utils/init.sh"], timeout=150)
        reset_ok = "All services are ready!" in reset.stdout
        if not reset_ok:
            raise RuntimeError(f"reset did not prove ready for {condition}/{arm}")
        proc = run([
            "pnpm", "exec", "tsx", "packages/testing/src/run-tac-rocketchat-fault.ts",
            "--mode", arm,
            "--condition", condition,
            "--config", args.config,
            "--target", args.target,
            "--text", text,
        ], cwd=xspa_repo, timeout=90)
        result = json.loads(proc.stdout)
        rows.append({
            "scenarioId": f"qa-escalate-emergency__{condition}",
            "arm": arm,
            "resetReady": reset_ok,
            "result": result,
        })

    payload = {
        "benchmark": "XanxitoSpA fault-injection v4",
        "version": "v4-stateful-1",
        "manifestFingerprint": args.manifest_fingerprint,
        "taskId": "qa-escalate-emergency",
        "condition": condition,
        "design": "paired-frozen-action-plan-execution-integrity",
        "generatedAt": datetime.now(timezone.utc).isoformat(),
        "runs": rows,
    }
    output = Path(args.output)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(json.dumps(payload, indent=2, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
