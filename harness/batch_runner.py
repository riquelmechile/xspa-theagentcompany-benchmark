#!/usr/bin/env python3
from __future__ import annotations

import argparse
import fcntl
import hashlib
import json
import os
import shutil
import subprocess
import sys
import time
import urllib.request
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

HERE = Path(__file__).resolve().parent
REPO = HERE.parent
WORK_ROOT = Path(os.environ.get("XSPA_BENCH_WORK_ROOT", REPO.parent / "xspa-benchmark"))
UPSTREAM = Path(os.environ.get("XSPA_TAC_UPSTREAM", REPO.parent / "TheAgentCompany-upstream"))
PAIR_ROOT = WORK_ROOT / "pairs"
STATE_ROOT = WORK_ROOT / "v2-runner-state"
RESET_CONTROLLER = HERE / "reset_controller.py"
ENV_MODEL_HELPER = HERE / "env_model.py"
PLANE_BACKUPS = WORK_ROOT / "infra-backups/plane-20241031-0351"
CODEX_PACKAGE = Path(os.environ.get("XSPA_CODEX_PACKAGE", Path.home() / ".npm-global/lib/node_modules/@openai/codex"))
CODEX_AUTH = Path(os.environ.get("XSPA_CODEX_AUTH", Path.home() / ".codex/auth.json"))
GLOBAL_LOCK = WORK_ROOT / ".v2-hard-isolation.lock"
MODEL = "gpt-5.6-sol"
ENV_MODEL = "openai/xspa-env-qwen3.8-27b"
ENV_BASE_URL = "http://127.0.0.1:18080/v1"
ENV_API_KEY = "xspa-local-benchmark"
DECRYPTION_KEY = "theagentcompany is all you need"
AGENT_TIMEOUT = int(os.environ.get("XSPA_AGENT_TIMEOUT", "600"))
INIT_TIMEOUT = int(os.environ.get("XSPA_INIT_TIMEOUT", "360"))
EVAL_TIMEOUT = int(os.environ.get("XSPA_EVAL_TIMEOUT", "600"))

REMAINING_TASKS = [
    "admin-arrange-meeting-rooms",
    "admin-employee-info-reconciliation",
    "admin-get-best-vendor-quote",
    "ds-answer-numerical-data-question",
    "ds-coffee-shop-database-management",
    "ds-visualize-data-in-pie-and-bar-chart",
    "finance-budget-variance",
    "sde-check-and-run-unit-test",
    "sde-debug-crashed-server",
    "sde-add-one-gitlab-pipeline",
    "qa-escalate-emergency",
    "qa-update-issue-status-according-to-colleagues",
    "research-answer-questions-on-paper",
    "research-reproduce-figures",
    "ml-grade-exam",
    "bm-classify-nationality",
]

ARM_DIRS = {"direct": "direct-hard-v2", "xanxitospa": "xanxitospa-v2"}
READ_ONLY_XSPA_TOOLS = {
    "xspa_status",
    "xspa_work_get",
    "xspa_company_plan",
    "xspa_company_status",
    "xspa_kast_status",
    "xspa_asset_get",
    "xspa_creative_status",
    "xspa_skills_list",
    "xspa_skills_search",
    "xspa_skill_get",
    "xspa_skills_health",
    "xspa_company_skill_plan",
}
WRITE_MARKERS = ("create", "apply", "install", "propose", "reflect", "submit", "update", "delete", "write")


class BatchError(RuntimeError):
    pass


class IsolationError(BatchError):
    pass


class ExternalQuotaError(BatchError):
    pass


class EvidenceExistsError(BatchError):
    pass


def now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _run(argv: list[str], *, cwd: Path | None = None, timeout: int = 120, check: bool = True) -> subprocess.CompletedProcess[str]:
    proc = subprocess.run(
        argv,
        cwd=str(cwd) if cwd else None,
        capture_output=True,
        text=True,
        timeout=timeout,
        shell=False,
    )
    if check and proc.returncode != 0:
        raise BatchError(
            f"command failed ({proc.returncode}): {argv}\nstdout={proc.stdout[-6000:]}\nstderr={proc.stderr[-6000:]}"
        )
    return proc


def _write_json(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(json.dumps(value, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    tmp.replace(path)


def task_image(task: str) -> str:
    if task not in REMAINING_TASKS:
        raise BatchError(f"task is not in frozen remaining manifest: {task}")
    return f"ghcr.io/theagentcompany/{task}-image:1.0.0"


def arm_path(task: str, arm: str) -> Path:
    if arm not in ARM_DIRS:
        raise BatchError(f"unknown arm: {arm}")
    return PAIR_ROOT / task / ARM_DIRS[arm]


def prepare_arm_dir(path: Path) -> Path | None:
    archived = None
    if path.exists() and any(path.iterdir()):
        if (path / "trajectory.jsonl").is_file() and (path / "eval.json").is_file():
            raise EvidenceExistsError(f"clean-looking evidence already exists and is immutable: {path}")
        stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
        archived = path.with_name(f"{path.name}.invalid-prebatch-{stamp}")
        if archived.exists():
            raise EvidenceExistsError(f"archive destination already exists: {archived}")
        path.rename(archived)
    path.mkdir(parents=True, exist_ok=True)
    return archived


def base_prompt(arm: str) -> str:
    common = (
        "Read /workspace/task.md and solve it exactly. The official TheAgentCompany 1.0.0 task environment has just been initialized from a fresh service reset. "
        "Work only inside /workspace and the benchmark services required by the task. Do not inspect evaluator/checkpoint/grader code, the upstream benchmark repository, another arm's files, or internet answer sources. "
        "Synthetic service URLs in the task refer to this local benchmark host; if DNS for the-agent-company.com resolves publicly, use 127.0.0.1 with the appropriate Host header rather than the public internet. "
        "Benchmark credentials when needed: GitLab root / theagentcompany; ownCloud theagentcompany / theagentcompany; RocketChat theagentcompany / theagentcompany; Plane agent@company.com / theagentcompany. "
        "Independently verify the requested end state before finishing and do not ask for human help."
    )
    if arm == "direct":
        return (
            "You are the DIRECT arm of a paired benchmark under hard capability isolation. "
            + common
            + " Apps, MCP, plugins, browser/computer-use, Xanxito, XanxitoSpA, memory, SDD, review and external connectors are unavailable and must not be used."
        )
    if arm == "xanxitospa":
        return (
            "You are the XANXITOSPA arm of a paired benchmark under hard capability isolation. First read only /workspace/task.md. BEFORE accessing task data beyond task.md or benchmark services, perform a bounded read-only preflight through the Xanxito app: discover only downstream server xanxitospa with xanxito.mcp_server_tools, then use xanxito.mcp_read addressed only to xanxitospa for task-relevant production runtime/company/skill guidance. "
            "Allowed downstream operations are read-only status/company/skill/asset/work/plan reads. You MUST NOT call HostOps, browser, memory, SDD, review, controlmcp, commerce-control, quinto-estado-ops, any other downstream server, any MCP write, or external connector. After that preflight, do all task execution only through /workspace and benchmark services. "
            + common
        )
    raise BatchError(f"unknown arm: {arm}")


def codex_args(arm: str, prompt: str) -> list[str]:
    args = [
        "exec",
        "--skip-git-repo-check",
        "--ephemeral",
        "--ignore-user-config",
        "--model",
        MODEL,
        "-c",
        'model_reasoning_effort="max"',
        "--sandbox",
        "danger-full-access",
    ]
    disables = [
        "plugins",
        "remote_plugin",
        "plugin_sharing",
        "browser_use",
        "browser_use_external",
        "browser_use_full_cdp_access",
        "computer_use",
        "in_app_browser",
        "recommended_plugins",
    ]
    if arm == "direct":
        disables.insert(0, "apps")
    elif arm != "xanxitospa":
        raise BatchError(f"unknown arm: {arm}")
    for feature in disables:
        args.extend(["--disable", feature])
    args.extend(["--json", "--output-last-message", "/workspace/last-message.txt", prompt])
    return args


def _completed_items(trajectory: str) -> list[dict[str, Any]]:
    items: list[dict[str, Any]] = []
    for raw in trajectory.splitlines():
        raw = raw.strip()
        if not raw:
            continue
        try:
            event = json.loads(raw)
        except json.JSONDecodeError:
            continue
        if event.get("type") != "item.completed":
            continue
        item = event.get("item")
        if isinstance(item, dict):
            items.append(item)
    return items


def _is_only_task_read(command: str) -> bool:
    lower = command.lower()
    if "task.md" not in lower:
        return False
    forbidden = ("http://", "https://", "curl ", "wget ", "git clone", "rocket", "owncloud", "plane", ":8929", ":8091", ":8092", ":3000")
    return not any(marker in lower for marker in forbidden)


def validate_trajectory(arm: str, trajectory: str) -> dict[str, Any]:
    items = _completed_items(trajectory)
    mcp_calls: list[tuple[int, dict[str, Any]]] = [
        (idx, item) for idx, item in enumerate(items) if item.get("type") == "mcp_tool_call"
    ]
    if arm == "direct":
        if mcp_calls:
            raise IsolationError(f"DIRECT arm emitted {len(mcp_calls)} MCP call(s)")
        return {"arm": arm, "mcp_calls": 0, "required_preflight_seen": False}
    if arm != "xanxitospa":
        raise IsolationError(f"unknown arm: {arm}")
    if not mcp_calls:
        raise IsolationError("XANXITOSPA arm did not perform the required read-only preflight")

    saw_discovery = False
    saw_read = False
    first_mcp_index = mcp_calls[0][0]
    for idx, item in mcp_calls:
        if item.get("server") not in {"codex_apps", "chatgpt_apps"}:
            raise IsolationError(f"unexpected MCP server surface: {item.get('server')}")
        tool = str(item.get("tool") or "")
        args = item.get("arguments") or {}
        if tool == "xanxito.mcp_server_tools":
            if args.get("name") != "xanxitospa":
                raise IsolationError(f"XANXITOSPA discovered forbidden downstream: {args.get('name')}")
            saw_discovery = True
            continue
        if tool == "xanxito.mcp_read":
            if args.get("server") != "xanxitospa":
                raise IsolationError(f"mcp_read addressed forbidden downstream: {args.get('server')}")
            downstream_tool = str(args.get("tool") or "")
            if downstream_tool not in READ_ONLY_XSPA_TOOLS:
                if not downstream_tool.startswith("xspa_") or any(marker in downstream_tool.lower() for marker in WRITE_MARKERS):
                    raise IsolationError(f"downstream tool is not approved read-only guidance: {downstream_tool}")
            saw_read = True
            continue
        raise IsolationError(f"forbidden Xanxito capability in benchmark arm: {tool}")

    if not (saw_discovery and saw_read):
        raise IsolationError("XANXITOSPA preflight must include discovery and at least one downstream read")

    for idx, item in enumerate(items[:first_mcp_index]):
        if item.get("type") == "command_execution" and not _is_only_task_read(str(item.get("command") or "")):
            raise IsolationError("XANXITOSPA accessed non-task.md data/services before the required preflight")

    return {"arm": arm, "mcp_calls": len(mcp_calls), "required_preflight_seen": True}


def _docker_remove(name: str) -> None:
    _run(["docker", "rm", "-f", name], timeout=60, check=False)


def _ensure_image(image: str) -> None:
    found = _run(["docker", "image", "inspect", image], timeout=30, check=False)
    if found.returncode != 0:
        _run(["docker", "pull", image], timeout=600)


def _prepare_reset_adapter() -> None:
    _run([
        sys.executable,
        str(RESET_CONTROLLER),
        "prepare",
        "--backup-dir",
        str(PLANE_BACKUPS),
    ], cwd=REPO, timeout=120)


def _healthcheck_env_model() -> None:
    req = urllib.request.Request(ENV_BASE_URL.replace("/v1", "/health"), method="GET")
    try:
        with urllib.request.urlopen(req, timeout=4) as response:
            if response.status >= 500:
                raise BatchError(f"environment model health returned {response.status}")
    except Exception:
        # OpenAI-compatible local servers do not consistently expose /health; a models call is stronger.
        req = urllib.request.Request(ENV_BASE_URL + "/models", headers={"Authorization": f"Bearer {ENV_API_KEY}"})
        with urllib.request.urlopen(req, timeout=8) as response:
            if response.status != 200:
                raise BatchError(f"environment model /models returned {response.status}")


def _ensure_env_model() -> None:
    try:
        _healthcheck_env_model()
        return
    except Exception:
        pass
    proc = _run([sys.executable, str(ENV_MODEL_HELPER), "start"], cwd=REPO, timeout=180, check=False)
    if proc.returncode != 0:
        raise BatchError(f"environment model failed to start: {proc.stdout[-3000:]} {proc.stderr[-3000:]}")
    _healthcheck_env_model()


def _task_dependencies(container: str) -> str:
    proc = _run(["docker", "exec", container, "sh", "-lc", "cat /utils/dependencies.yml 2>/dev/null || true"], timeout=30)
    return proc.stdout


def _structural_baseline(dependencies_text: str) -> dict[str, Any]:
    # Import only after the task environment is initialized. These are read-only snapshots.
    import importlib.util
    spec = importlib.util.spec_from_file_location("reset_controller_runtime", RESET_CONTROLLER)
    if spec is None or spec.loader is None:
        raise BatchError("cannot import reset controller")
    rc = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(rc)
    value: dict[str, Any] = {}
    lower = dependencies_text.lower()
    if "gitlab" in lower:
        projects = rc._gitlab_projects()
        identity = rc._gitlab_image_identity()
        value["gitlab"] = {
            "project_count": len(projects),
            "fingerprint": rc.gitlab_project_fingerprint(projects, identity),
        }
    if "plane" in lower:
        counts = rc._plane_counts()
        hashes = rc.validate_backup_set(PLANE_BACKUPS)
        value["plane"] = {
            "counts": counts,
            "fingerprint": rc.plane_structural_fingerprint(counts, hashes),
        }
    return value


def _start_task_container(task: str, arm_dir: Path, name: str) -> str:
    image = task_image(task)
    _ensure_image(image)
    _docker_remove(name)
    proc = _run([
        "docker", "run", "-d",
        "--name", name,
        "--network", "host",
        "--hostname", "zanachyOS",
        "--workdir", "/workspace",
        "--mount", f"type=bind,source={arm_dir},target=/workspace",
        "-e", "SERVER_HOSTNAME=127.0.0.1",
        "-e", f"LITELLM_BASE_URL={ENV_BASE_URL}",
        "-e", f"LITELLM_MODEL={ENV_MODEL}",
        "-e", f"LITELLM_API_KEY={ENV_API_KEY}",
        image,
        "sleep", "infinity",
    ], timeout=120)
    return proc.stdout.strip()


def _initialize_task(container: str, arm_dir: Path) -> tuple[str, dict[str, Any]]:
    init = _run(["docker", "exec", container, "/utils/init.sh"], timeout=INIT_TIMEOUT)
    (arm_dir / "init.log").write_text(init.stdout + ("\nSTDERR\n" + init.stderr if init.stderr else ""), encoding="utf-8")
    _run(["docker", "cp", f"{container}:/instruction/task.md", str(arm_dir / "task.md")], timeout=30)
    dependencies = _task_dependencies(container)
    (arm_dir / "dependencies.yml").write_text(dependencies, encoding="utf-8")
    return dependencies, _structural_baseline(dependencies)


def _compare_pair_baseline(task: str, arm: str, baseline: dict[str, Any], arm_dir: Path) -> None:
    _write_json(arm_dir / "baseline.json", baseline)
    if arm != "xanxitospa":
        return
    direct_file = arm_path(task, "direct") / "baseline.json"
    if not direct_file.exists():
        raise BatchError("XANXITOSPA arm requires completed DIRECT baseline first")
    direct = json.loads(direct_file.read_text(encoding="utf-8"))
    if direct != baseline:
        raise BatchError(f"cross-arm baseline mismatch for {task}: direct={direct} xspa={baseline}")


def _agent_docker_command(arm: str, arm_dir: Path, agent_name: str) -> list[str]:
    if not CODEX_PACKAGE.is_dir() or not CODEX_AUTH.is_file():
        raise BatchError("Codex package/auth mount is unavailable")
    prompt = base_prompt(arm)
    return [
        "docker", "run", "--name", agent_name,
        "--network", "host",
        "--workdir", "/workspace",
        "--mount", f"type=bind,source={arm_dir},target=/workspace",
        "--mount", f"type=bind,source={CODEX_PACKAGE},target=/opt/codex,readonly",
        "--mount", f"type=bind,source={CODEX_AUTH},target=/root/.codex/auth.json,readonly",
        "node:24-bookworm",
        "node", "/opt/codex/bin/codex.js",
        *codex_args(arm, prompt),
    ]


def _run_agent(arm: str, arm_dir: Path, agent_name: str) -> dict[str, Any]:
    _ensure_image("node:24-bookworm")
    _docker_remove(agent_name)
    cmd = _agent_docker_command(arm, arm_dir, agent_name)
    started = time.monotonic()
    proc = _run(cmd, timeout=AGENT_TIMEOUT, check=False)
    elapsed = round(time.monotonic() - started, 3)
    trajectory = proc.stdout
    (arm_dir / "trajectory.jsonl").write_text(trajectory, encoding="utf-8")
    (arm_dir / "trajectory.log").write_text(trajectory, encoding="utf-8")
    if proc.stderr:
        (arm_dir / "agent.stderr.log").write_text(proc.stderr, encoding="utf-8")
    if proc.returncode != 0:
        lower = trajectory.lower()
        if "usage limit" in lower or "purchase more credits" in lower:
            raise ExternalQuotaError("Codex ChatGPT quota exhausted for gpt-5.6-sol")
        raise BatchError(f"Codex agent exited {proc.returncode}; see {arm_dir / 'agent.stderr.log'}")
    gate = validate_trajectory(arm, trajectory)
    gate["agent_exit_code"] = proc.returncode
    gate["agent_elapsed_seconds"] = elapsed
    _write_json(arm_dir / "isolation-gate.json", gate)
    return gate


def _run_evaluator(task_container: str, arm_dir: Path) -> dict[str, Any]:
    result_path = arm_dir / "eval.json"
    proc = _run([
        "docker", "exec",
        "-e", f"DECRYPTION_KEY={DECRYPTION_KEY}",
        "-e", f"LITELLM_API_KEY={ENV_API_KEY}",
        "-e", f"LITELLM_BASE_URL={ENV_BASE_URL}",
        "-e", f"LITELLM_MODEL={ENV_MODEL}",
        task_container,
        "python_default", "/utils/eval.py",
        "--trajectory_path", "/workspace/trajectory.jsonl",
        "--result_path", "/workspace/eval.json",
    ], timeout=EVAL_TIMEOUT, check=False)
    (arm_dir / "evaluator.log").write_text(proc.stdout + ("\nSTDERR\n" + proc.stderr if proc.stderr else ""), encoding="utf-8")
    if proc.returncode != 0 or not result_path.is_file():
        raise BatchError(f"official evaluator failed ({proc.returncode}); see {arm_dir / 'evaluator.log'}")
    value = json.loads(result_path.read_text(encoding="utf-8"))
    score = value.get("final_score") or {}
    if not isinstance(score.get("total"), int) or not isinstance(score.get("result"), int):
        raise BatchError(f"invalid evaluator result: {value}")
    return value


def _status_path(task: str, arm: str) -> Path:
    return STATE_ROOT / f"{task}--{arm}.json"


def _set_status(task: str, arm: str, **fields: Any) -> None:
    current: dict[str, Any] = {}
    path = _status_path(task, arm)
    if path.exists():
        try:
            current = json.loads(path.read_text(encoding="utf-8"))
        except Exception:
            current = {}
    current.update({"task": task, "arm": arm, "updated_at": now(), **fields})
    _write_json(path, current)


def run_arm(task: str, arm: str) -> dict[str, Any]:
    if task not in REMAINING_TASKS:
        raise BatchError(f"task not pending: {task}")
    if arm not in ARM_DIRS:
        raise BatchError(f"bad arm: {arm}")
    STATE_ROOT.mkdir(parents=True, exist_ok=True)
    GLOBAL_LOCK.parent.mkdir(parents=True, exist_ok=True)
    with GLOBAL_LOCK.open("a+") as lock_handle:
        try:
            fcntl.flock(lock_handle.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError as exc:
            raise BatchError("another benchmark arm currently owns the shared-service lock") from exc

        stamp = datetime.now(timezone.utc).strftime("%H%M%S")
        token = hashlib.sha256(f"{task}:{arm}:{time.time_ns()}".encode()).hexdigest()[:10]
        task_container = f"tac-v2-{token}"
        agent_container = f"agent-v2-{token}"
        out = arm_path(task, arm)
        archived: Path | None = None
        started_at = now()
        _set_status(task, arm, state="running", phase="prepare", started_at=started_at, pid=os.getpid())
        try:
            archived = prepare_arm_dir(out)
            _ensure_env_model()
            _prepare_reset_adapter()
            _set_status(task, arm, state="running", phase="task-init", output_dir=str(out), archived=str(archived) if archived else None)
            task_id = _start_task_container(task, out, task_container)
            dependencies, baseline = _initialize_task(task_container, out)
            _compare_pair_baseline(task, arm, baseline, out)
            _set_status(task, arm, state="running", phase="agent", baseline=baseline)
            gate = _run_agent(arm, out, agent_container)
            _set_status(task, arm, state="running", phase="evaluator", isolation_gate=gate)
            evaluation = _run_evaluator(task_container, out)
            meta = {
                "task": task,
                "arm": arm,
                "started_at": started_at,
                "finished_at": now(),
                "task_image": task_image(task),
                "task_container_id": task_id,
                "model": MODEL,
                "reasoning_effort": "max",
                "environment_model": ENV_MODEL,
                "environment_base_url": ENV_BASE_URL,
                "codex_ignore_user_config": True,
                "codex_ephemeral": True,
                "baseline": baseline,
                "isolation_gate": gate,
                "official_final_score": evaluation["final_score"],
                "archived_incomplete_predecessor": str(archived) if archived else None,
            }
            _write_json(out / "run-meta.json", meta)
            result = {
                "ok": True,
                "task": task,
                "arm": arm,
                "output_dir": str(out),
                "score": evaluation["final_score"],
                "baseline": baseline,
                "isolation_gate": gate,
            }
            _set_status(task, arm, state="complete", phase="done", result=result)
            return result
        except ExternalQuotaError as exc:
            _set_status(task, arm, state="blocked", phase="external-quota", error=f"{type(exc).__name__}: {exc}")
            raise
        except Exception as exc:
            _set_status(task, arm, state="failed", phase="failed", error=f"{type(exc).__name__}: {exc}")
            raise
        finally:
            _docker_remove(agent_container)
            _docker_remove(task_container)


def launch_arm(task: str, arm: str) -> dict[str, Any]:
    if task not in REMAINING_TASKS or arm not in ARM_DIRS:
        raise BatchError("invalid pending task/arm")
    STATE_ROOT.mkdir(parents=True, exist_ok=True)
    state_path = _status_path(task, arm)
    if state_path.exists():
        try:
            old = json.loads(state_path.read_text(encoding="utf-8"))
        except Exception:
            old = {}
        if old.get("state") in {"launched", "running"}:
            pid = int(old.get("pid") or 0)
            if pid > 0:
                try:
                    os.kill(pid, 0)
                    raise BatchError(f"arm already running with pid {pid}")
                except ProcessLookupError:
                    pass
    log_path = STATE_ROOT / f"{task}--{arm}.runner.log"
    handle = log_path.open("ab", buffering=0)
    proc = subprocess.Popen(
        [sys.executable, str(Path(__file__).resolve()), "_run-arm", task, arm],
        cwd=str(REPO),
        stdin=subprocess.DEVNULL,
        stdout=handle,
        stderr=subprocess.STDOUT,
        start_new_session=True,
        close_fds=True,
    )
    handle.close()
    payload = {"task": task, "arm": arm, "state": "launched", "phase": "spawned", "pid": proc.pid, "launched_at": now(), "log": str(log_path)}
    _write_json(state_path, payload)
    return {"ok": True, **payload}


def read_status(task: str, arm: str) -> dict[str, Any]:
    path = _status_path(task, arm)
    if not path.exists():
        return {"ok": False, "task": task, "arm": arm, "state": "missing"}
    value = json.loads(path.read_text(encoding="utf-8"))
    pid = int(value.get("pid") or 0)
    alive = False
    if pid > 0:
        try:
            os.kill(pid, 0)
            alive = True
        except ProcessLookupError:
            pass
    value["process_alive"] = alive
    value["ok"] = value.get("state") == "complete"
    return value


def preflight() -> dict[str, Any]:
    _ensure_env_model()
    _prepare_reset_adapter()
    checks = {
        "reset_controller": RESET_CONTROLLER.is_file(),
        "plane_backups": all((PLANE_BACKUPS / name).is_file() for name in ("pgdata.tar.gz", "redisdata.tar.gz", "uploads.tar.gz")),
        "codex_package": CODEX_PACKAGE.is_dir(),
        "codex_auth": CODEX_AUTH.is_file(),
        "environment_model": True,
    }
    missing = [name for name, ok in checks.items() if not ok]
    if missing:
        raise BatchError(f"preflight failed: {missing}")
    return {"ok": True, "checks": checks, "remaining_tasks": REMAINING_TASKS}


def main() -> int:
    parser = argparse.ArgumentParser(description="TAC v2 hard-isolation batch runner")
    sub = parser.add_subparsers(dest="command", required=True)
    sub.add_parser("preflight")
    launch = sub.add_parser("launch-arm")
    launch.add_argument("task", choices=REMAINING_TASKS)
    launch.add_argument("arm", choices=sorted(ARM_DIRS))
    status = sub.add_parser("status")
    status.add_argument("task", choices=REMAINING_TASKS)
    status.add_argument("arm", choices=sorted(ARM_DIRS))
    run = sub.add_parser("_run-arm")
    run.add_argument("task", choices=REMAINING_TASKS)
    run.add_argument("arm", choices=sorted(ARM_DIRS))
    args = parser.parse_args()
    try:
        if args.command == "preflight":
            value = preflight()
        elif args.command == "launch-arm":
            value = launch_arm(args.task, args.arm)
        elif args.command == "status":
            value = read_status(args.task, args.arm)
        else:
            value = run_arm(args.task, args.arm)
        print(json.dumps(value, indent=2, ensure_ascii=False))
        return 0 if value.get("ok", True) or args.command == "status" else 1
    except Exception as exc:
        print(json.dumps({"ok": False, "error": f"{type(exc).__name__}: {exc}"}, ensure_ascii=False))
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
