from __future__ import annotations

import hashlib
import subprocess
from pathlib import Path
from typing import Any

from harness.v6_contract import fingerprint_json

def _git(repo: Path, *args: str) -> str:
    completed = subprocess.run(["git", "-C", str(repo), *args], check=True, capture_output=True, text=True)
    return completed.stdout.strip()

def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()

def capture_sut_pin(repo: Path, lockfile: str = "pnpm-lock.yaml") -> dict[str, Any]:
    repo = repo.resolve()
    commit = _git(repo, "rev-parse", "HEAD")
    if len(commit) != 40:
        raise ValueError("sut.commitSha")
    tree_clean = _git(repo, "status", "--porcelain") == ""
    lock_path = repo / lockfile
    if not lock_path.is_file():
        raise ValueError(f"missing-lockfile:{lockfile}")
    return {
        "commitSha": commit,
        "treeClean": tree_clean,
        "packageLockSha256": sha256_file(lock_path),
    }

def capture_runner_commit(repo: Path) -> str:
    commit = _git(repo.resolve(), "rev-parse", "HEAD")
    if len(commit) != 40:
        raise ValueError("runnerCommitSha")
    return commit

def freeze_v6_manifest(base: dict[str, Any], sut: dict[str, Any], runner_commit_sha: str) -> dict[str, Any]:
    if sut.get("treeClean") is not True:
        raise ValueError("dirty-sut")
    manifest = {**base, "sut": dict(sut), "runnerCommitSha": runner_commit_sha}
    without_fingerprint = {k: v for k, v in manifest.items() if k != "manifestFingerprint"}
    manifest["manifestFingerprint"] = fingerprint_json(without_fingerprint)
    return manifest
