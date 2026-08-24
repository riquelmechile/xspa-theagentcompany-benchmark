#!/usr/bin/env python3
from __future__ import annotations

import argparse
import fcntl
import json
import subprocess
from datetime import datetime, timezone
from pathlib import Path

from harness.reset_controller import reset_gitlab

CONDITIONS = ["control", "lost_ack_after_commit", "credential_expiry", "service_restart_after_commit"]
ARMS = ["direct", "xanxitospa"]
EXPECTED_FINGERPRINT = "c6f7c55f354a8af2e230f7efd48d8151589a75ed5d03a712874188e15f283275"


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
    parser.add_argument("--renew-script", required=True)
    parser.add_argument("--output", required=True)
    parser.add_argument("--project", default="root/api-server")
    parser.add_argument("--gitlab-container", default="gitlab-benchmark-canonical")
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

    baseline = reset_gitlab()
    if baseline.get("fingerprint") != EXPECTED_FINGERPRINT:
        raise RuntimeError(f"unexpected GitLab baseline: {baseline.get('fingerprint')}")

    remote_script = "/tmp/xspa-v4-renew-token.rb"
    run(["docker", "cp", args.renew_script, f"{args.gitlab_container}:{remote_script}"], timeout=30)
    renewed = run(["docker", "exec", args.gitlab_container, "gitlab-rails", "runner", remote_script], timeout=90).stdout.strip()
    if not renewed:
        raise RuntimeError("fixture token renewal returned empty evidence")

    title = f"XSPA-V4-GITLAB-{args.condition.upper()}"
    proc = run([
        "pnpm", "exec", "tsx", "packages/testing/src/run-tac-gitlab-fault.ts",
        "--mode", args.arm,
        "--condition", args.condition,
        "--config", args.config,
        "--project", args.project,
        "--title", title,
        "--description", "XSPA v4 frozen execution-integrity campaign",
        "--gitlab-container", args.gitlab_container,
    ], cwd=Path(args.xspa_repo), timeout=360 if args.condition == "service_restart_after_commit" else 180)
    result = json.loads(proc.stdout)
    payload = {
        "benchmark": "XanxitoSpA fault-injection v4",
        "version": "v4-stateful-1",
        "manifestFingerprint": args.manifest_fingerprint,
        "taskId": "pm-ask-for-issue-and-create-in-gitlab",
        "scenarioId": f"pm-ask-for-issue-and-create-in-gitlab__{args.condition}",
        "arm": args.arm,
        "condition": args.condition,
        "generatedAt": datetime.now(timezone.utc).isoformat(),
        "reset": {
            "fingerprint": baseline["fingerprint"],
            "projectCount": baseline["project_count"],
            "imageIdentity": baseline["image_identity"],
        },
        "fixtureCredentialRenewed": True,
        "result": result,
    }
    output.write_text(json.dumps(payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(json.dumps(payload, indent=2, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
