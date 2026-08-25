from __future__ import annotations

import json
import os
import subprocess
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any


@dataclass
class V7BridgeRunner:
    scenario_id: str
    arm: str
    benchmark_root: Path
    xspa_root: Path
    database_url: str | None = None
    state: dict[str, Any] = field(default_factory=dict)

    def __call__(self, _plan: Any, step: dict[str, Any], _index: int) -> dict[str, Any]:
        payload = {
            "scenarioId": self.scenario_id,
            "arm": self.arm,
            "step": step,
            "state": self.state,
        }
        env = os.environ.copy()
        env["XSPA_REPO"] = str(self.xspa_root)
        if self.database_url:
            env["V7_DATABASE_URL"] = self.database_url
        bridge = self.benchmark_root / "harness" / "v7_bridge.ts"
        proc = subprocess.run(
            ["pnpm", "exec", "tsx", str(bridge), json.dumps(payload, separators=(",", ":"))],
            cwd=self.xspa_root,
            env=env,
            text=True,
            capture_output=True,
            check=False,
        )
        if proc.returncode != 0:
            detail = proc.stderr.strip() or proc.stdout.strip() or f"exit={proc.returncode}"
            raise RuntimeError(f"v7-bridge:{self.scenario_id}:{self.arm}:{step.get('op')}:{detail}")
        output = json.loads(proc.stdout)
        if not isinstance(output, dict) or not isinstance(output.get("measurement"), dict) or not isinstance(output.get("state"), dict):
            raise RuntimeError("v7-bridge-output-invalid")
        self.state = output["state"]
        return output["measurement"]
