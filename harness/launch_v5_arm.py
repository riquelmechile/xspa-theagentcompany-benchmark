#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path


def main() -> int:
    parser = argparse.ArgumentParser(description="Launch one v5 arm detached from chat/tool timeouts")
    parser.add_argument("--pair-index", type=int, required=True)
    parser.add_argument("--arm", choices=["direct", "xanxitospa"], required=True)
    parser.add_argument("--attempt", type=int, default=1)
    parser.add_argument("--output", required=True)
    parser.add_argument("--manifest", default="manifest/fault-injection-v5-replication.json")
    parser.add_argument("--xspa-repo", default="/home/sebastian/workspace/xanxitospa")
    args = parser.parse_args()

    output = Path(args.output)
    output.parent.mkdir(parents=True, exist_ok=True)
    if output.exists():
        print(json.dumps({"ok": True, "state": "already-complete", "output": str(output)}))
        return 0
    state = output.with_suffix(output.suffix + ".launch.json")
    if state.exists():
        try:
            prior = json.loads(state.read_text(encoding="utf-8"))
            pid = int(prior.get("pid") or 0)
            if pid > 0:
                try:
                    os.kill(pid, 0)
                    print(json.dumps({"ok": True, "state": "already-running", **prior}))
                    return 0
                except ProcessLookupError:
                    pass
        except Exception:
            pass

    log_path = output.with_suffix(output.suffix + ".runner.log")
    handle = log_path.open("ab", buffering=0)
    argv = [
        sys.executable, "-m", "harness.run_v5_arm",
        "--manifest", args.manifest,
        "--pair-index", str(args.pair_index),
        "--arm", args.arm,
        "--attempt", str(args.attempt),
        "--output", str(output),
        "--xspa-repo", args.xspa_repo,
    ]
    proc = subprocess.Popen(
        argv,
        cwd=str(Path(__file__).resolve().parents[1]),
        stdin=subprocess.DEVNULL,
        stdout=handle,
        stderr=subprocess.STDOUT,
        start_new_session=True,
        close_fds=True,
    )
    handle.close()
    payload = {
        "ok": True,
        "state": "launched",
        "pid": proc.pid,
        "output": str(output),
        "log": str(log_path),
        "launchedAt": datetime.now(timezone.utc).isoformat(),
    }
    state.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(payload))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
