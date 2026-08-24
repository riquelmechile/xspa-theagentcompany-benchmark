#!/usr/bin/env python3
from __future__ import annotations

import argparse
import hashlib
import json
import subprocess
import time
import urllib.error
import urllib.request
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

OFFICIAL_GITLAB_IMAGE = "ghcr.io/theagentcompany/servers-gitlab:1.0.0"
GITLAB_RUNTIME_NAME = "gitlab-benchmark-canonical"
DEFAULT_BACKUP_DIR = Path("/home/sebastian/workspace/xspa-benchmark/infra-backups/plane-20241031-0351")
PLANE_BACKUP_VOLUME = "xspa-plane-official-backup"
REQUIRED_BACKUPS = ("pgdata.tar.gz", "redisdata.tar.gz", "uploads.tar.gz")
BENCHMARK_GITLAB_PORTS = ("8929", "8930", "2424")
EXPECTED_GITLAB_PROJECT_COUNT = 13
EXPECTED_PLANE_COUNTS = {"workspaces_tac": 1, "projects_tac": 10, "issues_tac": 31}
GITLAB_VOLUME_DESTINATIONS = {"/etc/gitlab", "/var/log/gitlab", "/var/opt/gitlab"}
API_BASE = "http://127.0.0.1:2999"


class ResetError(RuntimeError):
    pass


def _canonical_hash(payload: Any) -> str:
    encoded = json.dumps(payload, sort_keys=True, separators=(",", ":")).encode()
    return hashlib.sha256(encoded).hexdigest()


def _sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as fh:
        for chunk in iter(lambda: fh.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def validate_backup_set(backup_dir: Path) -> dict[str, str]:
    result: dict[str, str] = {}
    for name in REQUIRED_BACKUPS:
        path = backup_dir / name
        if not path.is_file() or path.stat().st_size < 1000:
            raise ResetError(f"missing/invalid official Plane backup artifact: {path}")
        result[name] = _sha256_file(path)
    return result


def plan_gitlab_cleanup(containers: list[dict[str, str]]) -> list[str]:
    removals: list[str] = []
    for item in containers:
        name = item.get("Names", "")
        image = item.get("Image", "")
        ports = item.get("Ports", "")
        labels = item.get("Labels", "")
        binds_benchmark_port = any(port in ports for port in BENCHMARK_GITLAB_PORTS)
        canonical_name = name == "gitlab"
        compose_owned = "com.docker.compose.service=gitlab" in labels and "com.docker.compose.project=theagentcompany" in labels

        if canonical_name and image != OFFICIAL_GITLAB_IMAGE:
            raise ResetError(f"canonical gitlab container uses unexpected image: {image}")
        if binds_benchmark_port and image != OFFICIAL_GITLAB_IMAGE:
            raise ResetError(f"unexpected container {name!r} owns a benchmark GitLab port: {image}")
        if image == OFFICIAL_GITLAB_IMAGE and binds_benchmark_port:
            if compose_owned:
                continue
            removals.append(name)
        elif canonical_name and not compose_owned:
            removals.append(name)
    return sorted(set(removals))


def select_stale_gitlab_volumes(previous_mounts: list[dict[str, Any]], current_mounts: list[dict[str, Any]]) -> list[str]:
    current_names = {str(item.get("name") or "") for item in current_mounts if item.get("name")}
    selected: set[str] = set()
    for item in previous_mounts:
        name = str(item.get("name") or "")
        destination = str(item.get("destination") or "")
        if not name or name in current_names:
            continue
        if destination not in GITLAB_VOLUME_DESTINATIONS:
            continue
        if item.get("anonymous") is not True:
            continue
        selected.add(name)
    return sorted(selected)


def gitlab_project_fingerprint(project_paths: list[str], image_identity: str) -> str:
    payload = {
        "image": image_identity,
        "projects": sorted(set(project_paths)),
        "project_count": len(set(project_paths)),
    }
    return _canonical_hash(payload)


def plane_structural_fingerprint(counts: dict[str, int], backup_hashes: dict[str, str]) -> str:
    return _canonical_hash({"counts": dict(sorted(counts.items())), "backup_sha256": dict(sorted(backup_hashes.items()))})


def assert_fingerprints_equal(first: dict[str, str], second: dict[str, str]) -> None:
    if first != second:
        raise ResetError(f"reset fingerprint mismatch: first={first} second={second}")


def _run(argv: list[str], *, check: bool = True, timeout: int = 180) -> subprocess.CompletedProcess[str]:
    proc = subprocess.run(argv, text=True, capture_output=True, timeout=timeout)
    if check and proc.returncode != 0:
        raise ResetError(f"command failed ({proc.returncode}): {argv}\nstdout={proc.stdout}\nstderr={proc.stderr}")
    return proc


def _docker_ps() -> list[dict[str, str]]:
    proc = _run(["docker", "ps", "-a", "--format", "{{json .}}"])
    rows: list[dict[str, str]] = []
    for line in proc.stdout.splitlines():
        line = line.strip()
        if line:
            rows.append(json.loads(line))
    return rows


def _gitlab_volume_mounts(container_name: str) -> list[dict[str, Any]]:
    proc = _run(["docker", "inspect", container_name], check=False, timeout=30)
    if proc.returncode != 0:
        return []
    payload = json.loads(proc.stdout)
    if not isinstance(payload, list) or len(payload) != 1:
        raise ResetError(f"unexpected docker inspect payload for {container_name}")
    mounts: list[dict[str, Any]] = []
    for mount in payload[0].get("Mounts", []):
        if mount.get("Type") != "volume":
            continue
        name = str(mount.get("Name") or "")
        destination = str(mount.get("Destination") or "")
        if not name:
            continue
        volume = _run(["docker", "volume", "inspect", name], timeout=30)
        meta = json.loads(volume.stdout)
        if not isinstance(meta, list) or len(meta) != 1:
            raise ResetError(f"unexpected volume inspect payload for {name}")
        labels = meta[0].get("Labels") or {}
        mounts.append({
            "name": name,
            "destination": destination,
            "anonymous": isinstance(labels, dict) and "com.docker.volume.anonymous" in labels,
        })
    return mounts


def _remove_unreferenced_gitlab_volumes(names: list[str]) -> tuple[list[str], list[str]]:
    removed: list[str] = []
    skipped: list[str] = []
    for name in names:
        refs = _run(["docker", "ps", "-a", "--filter", f"volume={name}", "--format", "{{.ID}}"], timeout=30)
        if refs.stdout.strip():
            skipped.append(name)
            continue
        proc = _run(["docker", "volume", "rm", name], check=False, timeout=60)
        if proc.returncode != 0:
            raise ResetError(f"failed removing unreferenced stale GitLab volume {name}: {proc.stderr.strip()}")
        removed.append(name)
    return removed, skipped


def _container_marker(name: str) -> str | None:
    proc = _run(["docker", "inspect", "-f", "{{.Id}}|{{.State.StartedAt}}", name], check=False, timeout=30)
    if proc.returncode != 0:
        return None
    marker = proc.stdout.strip()
    return marker or None


def _wait_for_marker_change(name: str, before: str | None, timeout: int = 240) -> str:
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        current = _container_marker(name)
        if current and current != before:
            return current
        time.sleep(2)
    raise ResetError(f"container {name} did not restart/recreate within {timeout}s")


def _http_status(url: str, timeout: float = 5.0) -> int | None:
    try:
        with urllib.request.urlopen(url, timeout=timeout) as resp:
            return resp.status
    except urllib.error.HTTPError as exc:
        return exc.code
    except Exception:
        return None


def _wait_health(service: str, timeout: int = 300) -> None:
    deadline = time.monotonic() + timeout
    url = f"{API_BASE}/api/healthcheck/{service}"
    while time.monotonic() < deadline:
        if _http_status(url) == 200:
            return
        time.sleep(3)
    raise ResetError(f"{service} healthcheck did not reach HTTP 200")


def _post_reset(service: str, timeout: int = 300) -> dict[str, Any]:
    req = urllib.request.Request(f"{API_BASE}/api/reset-{service}", data=b"", method="POST")
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            body = resp.read().decode("utf-8", errors="replace")
            if resp.status != 202:
                raise ResetError(f"reset-{service} returned HTTP {resp.status}: {body}")
            try:
                return json.loads(body)
            except json.JSONDecodeError:
                return {"status": resp.status, "body": body}
    except urllib.error.HTTPError as exc:
        body = exc.read().decode("utf-8", errors="replace")
        raise ResetError(f"reset-{service} HTTP error {exc.code}: {body}") from exc


def _stage_gitlab_compose_name() -> str:
    _run(["docker", "inspect", "api-server"], timeout=30)
    _run([
        "docker", "exec", "api-server", "sh", "-lc",
        "test -e /workspace/docker-compose.yml.xspa-upstream || cp /workspace/docker-compose.yml /workspace/docker-compose.yml.xspa-upstream",
    ], timeout=30)
    _run([
        "docker", "exec", "api-server", "sed", "-i",
        f"s/container_name: gitlab$/container_name: {GITLAB_RUNTIME_NAME}/",
        "/workspace/docker-compose.yml",
    ], timeout=30)
    remote = _run(["docker", "exec", "api-server", "cat", "/workspace/docker-compose.yml"], timeout=30)
    if f"container_name: {GITLAB_RUNTIME_NAME}" not in remote.stdout:
        raise ResetError("failed to stage deterministic GitLab compose runtime name")
    return GITLAB_RUNTIME_NAME


def _ensure_gitlab_preconditions() -> list[str]:
    containers = _docker_ps()
    removals = plan_gitlab_cleanup(containers)
    for name in removals:
        _run(["docker", "rm", "-f", name], timeout=120)
    return removals


def _stage_plane_backups(backup_dir: Path) -> dict[str, str]:
    hashes = validate_backup_set(backup_dir)
    _run(["docker", "volume", "create", PLANE_BACKUP_VOLUME], timeout=60)
    shell = (
        "set -eu; rm -f /backup/*.tar.gz; "
        "cp /src/pgdata.tar.gz /src/redisdata.tar.gz /src/uploads.tar.gz /backup/; "
        "test -s /backup/pgdata.tar.gz; test -s /backup/redisdata.tar.gz; test -s /backup/uploads.tar.gz"
    )
    _run(
        [
            "docker",
            "run",
            "--rm",
            "-v",
            f"{PLANE_BACKUP_VOLUME}:/backup",
            "-v",
            f"{backup_dir}:/src:ro",
            "busybox",
            "sh",
            "-c",
            shell,
        ],
        timeout=120,
    )
    return hashes


def _stage_plane_restore_adapter(adapter_path: Path) -> str:
    if not adapter_path.is_file():
        raise ResetError(f"missing Plane restore adapter: {adapter_path}")
    _run(["docker", "inspect", "api-server"], timeout=30)
    _run(
        [
            "docker",
            "exec",
            "api-server",
            "sh",
            "-lc",
            "test -e /plane/plane-app/restore.sh.xspa-upstream || cp /plane/plane-app/restore.sh /plane/plane-app/restore.sh.xspa-upstream",
        ],
        timeout=30,
    )
    _run(["docker", "cp", str(adapter_path), "api-server:/plane/plane-app/restore.sh"], timeout=30)
    _run(["docker", "exec", "api-server", "chmod", "755", "/plane/plane-app/restore.sh"], timeout=30)
    host_hash = _sha256_file(adapter_path)
    remote = _run(["docker", "exec", "api-server", "cat", "/plane/plane-app/restore.sh"], timeout=30)
    remote_hash = hashlib.sha256(remote.stdout.encode()).hexdigest()
    if remote_hash != host_hash:
        raise ResetError(f"Plane restore adapter hash mismatch host={host_hash} remote={remote_hash}")
    return host_hash


def prepare_environment(backup_dir: Path, adapter_path: Path) -> dict[str, Any]:
    runtime_name = _stage_gitlab_compose_name()
    removed = _ensure_gitlab_preconditions()
    backup_hashes = _stage_plane_backups(backup_dir)
    adapter_hash = _stage_plane_restore_adapter(adapter_path)
    return {
        "gitlab_runtime_name": runtime_name,
        "gitlab_removed_conflicts": removed,
        "plane_backup_sha256": backup_hashes,
        "plane_restore_adapter_sha256": adapter_hash,
    }


def _gitlab_projects() -> list[str]:
    url = "http://127.0.0.1:8929/api/v4/projects?simple=true&per_page=100"
    with urllib.request.urlopen(url, timeout=15) as resp:
        data = json.load(resp)
    if not isinstance(data, list):
        raise ResetError("GitLab projects endpoint returned non-list payload")
    paths = sorted(str(item.get("path_with_namespace")) for item in data if item.get("path_with_namespace"))
    if len(paths) != EXPECTED_GITLAB_PROJECT_COUNT:
        raise ResetError(f"unexpected GitLab baseline project count: {len(paths)} != {EXPECTED_GITLAB_PROJECT_COUNT}")
    return paths


def _gitlab_image_identity() -> str:
    proc = _run(["docker", "inspect", "-f", "{{.Config.Image}}|{{.Image}}", GITLAB_RUNTIME_NAME], timeout=30)
    value = proc.stdout.strip()
    if not value.startswith(OFFICIAL_GITLAB_IMAGE + "|"):
        raise ResetError(f"GitLab is not running the exact official image: {value}")
    return value


def reset_gitlab() -> dict[str, Any]:
    _stage_gitlab_compose_name()
    removed = _ensure_gitlab_preconditions()
    previous_mounts = _gitlab_volume_mounts(GITLAB_RUNTIME_NAME)
    before = _container_marker(GITLAB_RUNTIME_NAME)
    response = _post_reset("gitlab", timeout=300)
    marker = _wait_for_marker_change(GITLAB_RUNTIME_NAME, before, timeout=300)
    _wait_health("gitlab", timeout=300)
    projects = _gitlab_projects()
    image_identity = _gitlab_image_identity()
    fingerprint = gitlab_project_fingerprint(projects, image_identity)
    current_mounts = _gitlab_volume_mounts(GITLAB_RUNTIME_NAME)
    stale = select_stale_gitlab_volumes(previous_mounts, current_mounts)
    removed_stale, skipped_stale = _remove_unreferenced_gitlab_volumes(stale)
    return {
        "service": "gitlab",
        "removed_conflicts": removed,
        "removed_stale_volumes": removed_stale,
        "skipped_referenced_stale_volumes": skipped_stale,
        "reset_response": response,
        "container_marker": marker,
        "image_identity": image_identity,
        "project_count": len(projects),
        "project_paths": projects,
        "fingerprint": fingerprint,
    }


def _wait_plane_migrator(timeout: int = 240) -> str:
    deadline = time.monotonic() + timeout
    restarted = False
    while time.monotonic() < deadline:
        proc = _run(
            ["docker", "inspect", "-f", "{{.State.Status}}|{{.State.ExitCode}}", "plane-app-migrator-1"],
            check=False,
            timeout=30,
        )
        if proc.returncode == 0:
            state = proc.stdout.strip()
            if state == "exited|0":
                return state
            if state.startswith("exited|") and state != "exited|0" and not restarted:
                _run(["docker", "restart", "plane-app-migrator-1"], timeout=60)
                restarted = True
            elif state.startswith("exited|") and state != "exited|0" and restarted:
                raise ResetError(f"Plane migrator failed after one deterministic retry: {state}")
        time.sleep(2)
    raise ResetError("Plane migrator did not complete successfully")


def _plane_counts() -> dict[str, int]:
    query = (
        "select count(*) from workspaces where slug='tac'; "
        "select count(*) from projects where workspace_id=(select id from workspaces where slug='tac' limit 1); "
        "select count(*) from issues where workspace_id=(select id from workspaces where slug='tac' limit 1);"
    )
    proc = _run(
        [
            "docker",
            "exec",
            "plane-app-plane-db-1",
            "sh",
            "-lc",
            f"PGPASSWORD=plane psql -U plane -d plane -At -c \"{query}\"",
        ],
        timeout=60,
    )
    lines = [line.strip() for line in proc.stdout.splitlines() if line.strip()]
    if len(lines) != 3:
        raise ResetError(f"unexpected Plane structural query result: {lines}")
    counts = {
        "workspaces_tac": int(lines[0]),
        "projects_tac": int(lines[1]),
        "issues_tac": int(lines[2]),
    }
    if counts != EXPECTED_PLANE_COUNTS:
        raise ResetError(f"unexpected Plane baseline counts: {counts} != {EXPECTED_PLANE_COUNTS}")
    return counts


def reset_plane(backup_hashes: dict[str, str]) -> dict[str, Any]:
    before = _container_marker("plane-app-api-1")
    response = _post_reset("plane", timeout=30)
    marker = _wait_for_marker_change("plane-app-api-1", before, timeout=300)
    _wait_plane_migrator(timeout=300)
    _wait_health("plane", timeout=300)
    counts = _plane_counts()
    return {
        "service": "plane",
        "reset_response": response,
        "container_marker": marker,
        "counts": counts,
        "backup_sha256": dict(sorted(backup_hashes.items())),
        "fingerprint": plane_structural_fingerprint(counts, backup_hashes),
    }


def run_smoke(cycles: int, backup_dir: Path, adapter_path: Path) -> dict[str, Any]:
    if cycles < 2:
        raise ResetError("determinism smoke requires at least 2 cycles")
    preparation = prepare_environment(backup_dir, adapter_path)
    results: list[dict[str, Any]] = []
    baseline: dict[str, str] | None = None
    for index in range(1, cycles + 1):
        gitlab = reset_gitlab()
        plane = reset_plane(preparation["plane_backup_sha256"])
        fingerprints = {"gitlab": gitlab["fingerprint"], "plane": plane["fingerprint"]}
        if baseline is None:
            baseline = fingerprints
        else:
            assert_fingerprints_equal(baseline, fingerprints)
        results.append({"cycle": index, "fingerprints": fingerprints, "gitlab": gitlab, "plane": plane})
    return {
        "ok": True,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "cycles": cycles,
        "preparation": preparation,
        "stable_fingerprints": baseline,
        "results": results,
    }


def _write_or_print(payload: dict[str, Any], output: Path | None) -> None:
    text = json.dumps(payload, indent=2, sort_keys=True)
    if output:
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_text(text + "\n")
    print(text)


def main() -> int:
    parser = argparse.ArgumentParser(description="Deterministic GitLab/Plane reset controller for TAC benchmark")
    parser.add_argument("command", choices=("validate", "prepare", "smoke"))
    parser.add_argument("--backup-dir", type=Path, default=DEFAULT_BACKUP_DIR)
    parser.add_argument("--cycles", type=int, default=2)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()

    adapter = Path(__file__).with_name("plane_restore_local.sh")
    if args.command == "validate":
        payload = {"ok": True, "plane_backup_sha256": validate_backup_set(args.backup_dir), "adapter": str(adapter)}
    elif args.command == "prepare":
        payload = {"ok": True, **prepare_environment(args.backup_dir, adapter)}
    else:
        payload = run_smoke(args.cycles, args.backup_dir, adapter)
    _write_or_print(payload, args.output)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
