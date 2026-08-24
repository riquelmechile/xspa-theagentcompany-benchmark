#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import subprocess
from datetime import datetime, timezone
from pathlib import Path

CONDITIONS = ["control", "lost_ack_after_commit", "auth_session_expiry", "concurrent_duplicate_intent"]
ARMS = ["direct", "xanxitospa"]


def run(argv: list[str], *, cwd: Path | None = None, timeout: int = 150) -> subprocess.CompletedProcess[str]:
    proc = subprocess.run(argv, cwd=str(cwd) if cwd else None, text=True, capture_output=True, timeout=timeout)
    if proc.returncode != 0:
        raise RuntimeError(f"command failed {argv}: {proc.stderr[-1000:]} {proc.stdout[-1000:]}")
    return proc


def main() -> int:
    parser = argparse.ArgumentParser(description="Run one RocketChat fault-injection arm with a fresh task reset")
    parser.add_argument("--arm", choices=ARMS, required=True)
    parser.add_argument("--condition", choices=CONDITIONS, required=True)
    parser.add_argument("--reset-container", required=True)
    parser.add_argument("--xspa-repo", required=True)
    parser.add_argument("--config", required=True)
    parser.add_argument("--target", default="Sarah Johnson")
    parser.add_argument("--text", required=True)
    parser.add_argument("--output", required=True)
    parser.add_argument("--manifest-fingerprint", required=True)
    args = parser.parse_args()

    reset = run(["docker", "exec", args.reset_container, "/utils/init.sh"], timeout=180)
    reset_ok = "All services are ready!" in reset.stdout
    if not reset_ok:
        raise RuntimeError("RocketChat reset did not prove service readiness")

    proc = run([
        "pnpm", "exec", "tsx", "packages/testing/src/run-tac-rocketchat-fault.ts",
        "--mode", args.arm,
        "--condition", args.condition,
        "--config", args.config,
        "--target", args.target,
        "--text", args.text,
    ], cwd=Path(args.xspa_repo), timeout=120)
    result = json.loads(proc.stdout)
    payload = {
        "benchmark": "XanxitoSpA stateful surface runner",
        "manifestFingerprint": args.manifest_fingerprint,
        "taskId": "qa-escalate-emergency",
        "scenarioId": f"qa-escalate-emergency__{args.condition}",
        "arm": args.arm,
        "condition": args.condition,
        "generatedAt": datetime.now(timezone.utc).isoformat(),
        "reset": {"service": "rocketchat", "resetReady": True, "resetContainer": args.reset_container},
        "result": result,
    }
    output = Path(args.output)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(json.dumps(payload, indent=2, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
