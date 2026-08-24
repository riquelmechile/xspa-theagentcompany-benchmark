#!/usr/bin/env python3
from __future__ import annotations

import argparse
import glob
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from harness.v5_replication import pair_valid_results, summarize_pairs, validate_manifest


def _load(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def main() -> int:
    parser = argparse.ArgumentParser(description="Aggregate valid v5 replication pairs")
    parser.add_argument("--manifest", default="manifest/fault-injection-v5-replication.json")
    parser.add_argument("--v4-manifest", default="manifest/fault-injection-v4-stateful.json")
    parser.add_argument("--results-glob", default="results/v5-r*-p*.json")
    parser.add_argument("--output")
    parser.add_argument("--require-complete", action="store_true")
    args = parser.parse_args()

    manifest = _load(Path(args.manifest))
    v4 = _load(Path(args.v4_manifest))
    validate_manifest(manifest, v4)
    runs = []
    for name in sorted(glob.glob(args.results_glob)):
        path = Path(name)
        if path.name.endswith(".launch.json") or path.name.endswith(".runner.log"):
            continue
        value = _load(path)
        if value.get("version") == manifest["version"]:
            runs.append(value)
    pairs = pair_valid_results(manifest, runs) if runs else []
    completed_keys = {(p["scenarioId"], p["repetition"]) for p in pairs}
    pending = [
        {"pairIndex": row["pairIndex"], "repetition": row["repetition"], "scenarioId": row["scenarioId"], "armOrder": row["armOrder"]}
        for row in manifest["pairOrder"]
        if (row["scenarioId"], row["repetition"]) not in completed_keys
    ]
    if args.require_complete and pending:
        raise SystemExit(f"v5 incomplete: {len(pending)} pairs pending")
    payload = {
        "benchmark": manifest["benchmark"],
        "version": manifest["version"],
        "manifestFingerprint": manifest["manifestFingerprint"],
        "generatedAt": datetime.now(timezone.utc).isoformat(),
        "status": "complete" if not pending else "partial",
        "completedPairs": len(pairs),
        "pendingPairs": len(pending),
        "summary": summarize_pairs(pairs),
        "pending": pending,
    }
    if args.output:
        Path(args.output).write_text(json.dumps(payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(json.dumps(payload, indent=2, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
