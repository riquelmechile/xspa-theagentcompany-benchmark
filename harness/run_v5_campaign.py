#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import subprocess
import time
from datetime import datetime, timezone
from pathlib import Path


def load(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


def result_path(results_dir: Path, entry: dict, arm: str) -> Path:
    return results_dir / f"v5-r{entry['repetition']:02d}-p{entry['pairIndex']:03d}-{arm}.json"


def valid_existing(path: Path, manifest_fp: str, entry: dict, arm: str) -> bool:
    if not path.is_file():
        return False
    try:
        row = load(path)
    except Exception:
        return False
    return (
        row.get("valid") is True
        and row.get("manifestFingerprint") == manifest_fp
        and row.get("pairIndex") == entry["pairIndex"]
        and row.get("repetition") == entry["repetition"]
        and row.get("scenarioId") == entry["scenarioId"]
        and row.get("arm") == arm
    )


def main() -> int:
    ap = argparse.ArgumentParser(description="Execute v5 pairs strictly in precommitted manifest order")
    ap.add_argument("--manifest", default="manifest/fault-injection-v5-replication.json")
    ap.add_argument("--start-pair", type=int, default=1)
    ap.add_argument("--end-pair", type=int)
    ap.add_argument("--results-dir", default="results")
    ap.add_argument("--max-infra-attempts", type=int, default=3)
    ap.add_argument("--retry-delay-seconds", type=float, default=3.0)
    args = ap.parse_args()

    manifest = load(Path(args.manifest))
    results_dir = Path(args.results_dir)
    results_dir.mkdir(parents=True, exist_ok=True)
    invalid_dir = results_dir / "v5-invalid-attempts"
    invalid_dir.mkdir(parents=True, exist_ok=True)

    rows = [row for row in manifest["pairOrder"] if row["pairIndex"] >= args.start_pair]
    if args.end_pair is not None:
        rows = [row for row in rows if row["pairIndex"] <= args.end_pair]

    for entry in rows:
        for arm in entry["armOrder"]:
            out = result_path(results_dir, entry, arm)
            if valid_existing(out, manifest["manifestFingerprint"], entry, arm):
                print(json.dumps({"state": "skip-valid", "pairIndex": entry["pairIndex"], "arm": arm, "output": str(out)}), flush=True)
                continue
            if out.exists():
                raise RuntimeError(f"existing non-valid result blocks execution: {out}")
            success = False
            for attempt in range(1, args.max_infra_attempts + 1):
                argv = [
                    "python", "-m", "harness.run_v5_arm",
                    "--manifest", args.manifest,
                    "--pair-index", str(entry["pairIndex"]),
                    "--arm", arm,
                    "--attempt", str(attempt),
                    "--output", str(out),
                ]
                print(json.dumps({"state": "run", "pairIndex": entry["pairIndex"], "scenarioId": entry["scenarioId"], "arm": arm, "attempt": attempt}), flush=True)
                proc = subprocess.run(argv, text=True, capture_output=True)
                if proc.returncode == 0 and valid_existing(out, manifest["manifestFingerprint"], entry, arm):
                    print(json.dumps({"state": "complete", "pairIndex": entry["pairIndex"], "arm": arm, "attempt": attempt, "output": str(out)}), flush=True)
                    success = True
                    break
                invalid = {
                    "benchmark": manifest["benchmark"],
                    "version": manifest["version"],
                    "manifestFingerprint": manifest["manifestFingerprint"],
                    "pairIndex": entry["pairIndex"],
                    "repetition": entry["repetition"],
                    "scenarioId": entry["scenarioId"],
                    "arm": arm,
                    "attempt": attempt,
                    "valid": False,
                    "classification": "infrastructure-invalid",
                    "generatedAt": datetime.now(timezone.utc).isoformat(),
                    "returnCode": proc.returncode,
                    "stdoutTail": proc.stdout[-3000:],
                    "stderrTail": proc.stderr[-3000:],
                }
                invalid_path = invalid_dir / f"p{entry['pairIndex']:03d}-{arm}-attempt{attempt}.json"
                invalid_path.write_text(json.dumps(invalid, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
                print(json.dumps({"state": "infra-invalid", "pairIndex": entry["pairIndex"], "arm": arm, "attempt": attempt, "evidence": str(invalid_path)}), flush=True)
                if out.exists():
                    raise RuntimeError(f"runner failed but left output; refusing automatic retry: {out}")
                if attempt < args.max_infra_attempts:
                    time.sleep(args.retry_delay_seconds)
            if not success:
                raise RuntimeError(f"exhausted infrastructure retries for pair {entry['pairIndex']} arm {arm}")
    print(json.dumps({"state": "range-complete", "startPair": args.start_pair, "endPair": args.end_pair or manifest["pairOrder"][-1]["pairIndex"]}), flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
