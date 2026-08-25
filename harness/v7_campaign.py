from __future__ import annotations

import hashlib
import json
import re
import subprocess
from pathlib import Path
from typing import Any

from .v6_contract import fingerprint_json

SHA40 = re.compile(r"^[0-9a-f]{40}$")
SHA64 = re.compile(r"^[0-9a-f]{64}$")
RUNNER_FILES = [
    "harness/v6_executor.py",
    "harness/v7_bridge.ts",
    "harness/v7_runner.py",
    "harness/v7_scenarios.py",
    "harness/v7_contract.py",
    "harness/v7_campaign.py",
    "harness/run_v7_campaign.py",
]


def sha256_file(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def runner_file_hashes(repo: Path) -> dict[str, str]:
    return {name: sha256_file(repo / name) for name in RUNNER_FILES}


def git_head(repo: Path) -> str:
    return subprocess.run(["git", "-C", str(repo), "rev-parse", "HEAD"], check=True, text=True, capture_output=True).stdout.strip()


def git_clean(repo: Path) -> bool:
    return subprocess.run(["git", "-C", str(repo), "status", "--porcelain"], check=True, text=True, capture_output=True).stdout.strip() == ""


def validate_v7_campaign(campaign: dict[str, Any]) -> None:
    if campaign.get("schemaVersion") != 7:
        raise ValueError("campaign.schemaVersion")
    if campaign.get("status") != "frozen-before-outcomes":
        raise ValueError("campaign.status")
    if campaign.get("executionContractSource") != "shared-executor-v2":
        raise ValueError("campaign.executionContractSource")
    sut = campaign.get("sut")
    if not isinstance(sut, dict) or not SHA40.fullmatch(str(sut.get("commitSha", ""))) or sut.get("treeClean") is not True or not SHA64.fullmatch(str(sut.get("packageLockSha256", ""))):
        raise ValueError("campaign.sut")
    if not SHA40.fullmatch(str(campaign.get("runnerCommitSha", ""))):
        raise ValueError("campaign.runnerCommitSha")
    hashes = campaign.get("runnerFilesSha256")
    if not isinstance(hashes, dict) or set(hashes) != set(RUNNER_FILES) or any(not SHA64.fullmatch(str(hashes.get(name, ""))) for name in RUNNER_FILES):
        raise ValueError("campaign.runnerFilesSha256")
    scenarios = campaign.get("scenarios")
    if not isinstance(scenarios, list) or not scenarios:
        raise ValueError("campaign.scenarios")
    ids: set[str] = set()
    for index, scenario in enumerate(scenarios):
        if not isinstance(scenario, dict):
            raise ValueError(f"campaign.scenario:{index}")
        for key in ("id", "actionPlan", "oracle", "fault", "preState", "runtimeStore", "durabilityClaim", "runnerMapping"):
            if key not in scenario:
                raise ValueError(f"campaign.scenario-missing:{index}:{key}")
        sid = str(scenario["id"])
        if not sid or sid in ids:
            raise ValueError(f"campaign.scenario-id:{index}")
        ids.add(sid)
        if scenario["runnerMapping"] != {"direct": "v7_bridge:direct", "xanxitospa": "v7_bridge:xanxitospa"}:
            raise ValueError(f"campaign.runner-mapping:{sid}")
        if scenario.get("durabilityClaim") is True and scenario.get("runtimeStore") != "postgres":
            raise ValueError(f"campaign.durability-requires-postgres:{sid}")
        steps = scenario.get("actionPlan", {}).get("steps") if isinstance(scenario.get("actionPlan"), dict) else None
        if not isinstance(steps, list) or not steps:
            raise ValueError(f"campaign.action-steps:{sid}")
    supplied = campaign.get("campaignFingerprint")
    if not SHA64.fullmatch(str(supplied or "")):
        raise ValueError("campaign.campaignFingerprint")
    expected = fingerprint_json({k: v for k, v in campaign.items() if k != "campaignFingerprint"})
    if supplied != expected:
        raise ValueError("campaign.fingerprint-drift")


def verify_execution_environment(campaign: dict[str, Any], benchmark_repo: Path, xspa_repo: Path) -> None:
    validate_v7_campaign(campaign)
    if not git_clean(benchmark_repo):
        raise ValueError("dirty-benchmark-runner")
    if not git_clean(xspa_repo):
        raise ValueError("dirty-sut")
    if git_head(xspa_repo) != campaign["sut"]["commitSha"]:
        raise ValueError("sut-commit-drift")
    lock_hash = sha256_file(xspa_repo / "pnpm-lock.yaml")
    if lock_hash != campaign["sut"]["packageLockSha256"]:
        raise ValueError("sut-lock-drift")
    current_hashes = runner_file_hashes(benchmark_repo)
    if current_hashes != campaign["runnerFilesSha256"]:
        raise ValueError("runner-file-drift")
    # The benchmark repo may contain the later freeze commit, so HEAD need not equal
    # runnerCommitSha. The pinned runner commit must however be an ancestor.
    ancestor = subprocess.run(["git", "-C", str(benchmark_repo), "merge-base", "--is-ancestor", campaign["runnerCommitSha"], "HEAD"], check=False).returncode == 0
    if not ancestor:
        raise ValueError("runner-commit-not-ancestor")


def load_campaign(path: Path) -> dict[str, Any]:
    campaign = json.loads(path.read_text())
    validate_v7_campaign(campaign)
    return campaign
