#!/usr/bin/env python3
from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import shlex
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from harness import batch_runner as br

STATE_ROOT = br.WORK_ROOT / "v3-chatgpt-host-state"
ACTIVE_FILE = STATE_ROOT / "active.json"
HOST_ARM_DIRS = {"direct": "direct-chatgpt-v3", "xanxitospa": "xanxitospa-chatgpt-v3"}


class HostSessionError(RuntimeError):
    pass


def now() -> str:
    return datetime.now(timezone.utc).isoformat()


def command_event(command: str, output: str, exit_code: int) -> dict[str, Any]:
    return {
        "type": "item.completed",
        "item": {
            "id": f"hostcmd-{time.time_ns()}",
            "type": "command_execution",
            "command": command,
            "aggregated_output": output,
            "exit_code": int(exit_code),
            "status": "completed" if int(exit_code) == 0 else "failed",
        },
    }


def mcp_event(tool: str, arguments: dict[str, Any], result: Any | None = None) -> dict[str, Any]:
    return {
        "type": "item.completed",
        "item": {
            "id": f"hostmcp-{time.time_ns()}",
            "type": "mcp_tool_call",
            "server": "chatgpt_apps",
            "tool": tool,
            "arguments": arguments,
            "result": result,
            "error": None,
            "status": "completed",
        },
    }


def message_event(text: str) -> dict[str, Any]:
    return {
        "type": "item.completed",
        "item": {
            "id": f"hostmsg-{time.time_ns()}",
            "type": "agent_message",
            "text": text,
        },
    }


def _write_json(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(json.dumps(value, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    tmp.replace(path)


def _load_active() -> dict[str, Any] | None:
    if not ACTIVE_FILE.exists():
        return None
    try:
        return json.loads(ACTIVE_FILE.read_text(encoding="utf-8"))
    except Exception as exc:
        raise HostSessionError(f"invalid active state: {exc}") from exc


def _container_exists(name: str) -> bool:
    if not name:
        return False
    proc = br._run(["docker", "inspect", name], timeout=30, check=False)
    return proc.returncode == 0


def _require_active(task: str, arm: str) -> dict[str, Any]:
    state = _load_active()
    if not state:
        raise HostSessionError("no active ChatGPT-hosted benchmark arm")
    if state.get("task") != task or state.get("arm") != arm:
        raise HostSessionError(f"active arm is {state.get('task')}/{state.get('arm')}")
    container = str(state.get("container") or "")
    if not _container_exists(container):
        raise HostSessionError(f"active task container is missing: {container}")
    return state


def host_arm_path(task: str, arm: str) -> Path:
    if arm not in HOST_ARM_DIRS:
        raise HostSessionError(f"unknown hosted arm: {arm}")
    return br.PAIR_ROOT / task / HOST_ARM_DIRS[arm]


def _trajectory_path(state: dict[str, Any]) -> Path:
    return Path(str(state["output_dir"])) / "trajectory.jsonl"


def _append_event(state: dict[str, Any], event: dict[str, Any]) -> None:
    path = _trajectory_path(state)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(event, ensure_ascii=False) + "\n")



def _compare_host_baseline(task: str, arm: str, baseline: dict[str, Any], out: Path) -> None:
    _write_json(out / "baseline.json", baseline)
    if arm != "xanxitospa":
        return
    direct_file = host_arm_path(task, "direct") / "baseline.json"
    if not direct_file.exists():
        raise HostSessionError("XANXITOSPA arm requires completed DIRECT baseline first")
    direct = json.loads(direct_file.read_text(encoding="utf-8"))
    if direct != baseline:
        raise HostSessionError(f"cross-arm baseline mismatch: direct={direct} xspa={baseline}")


def parse_launched_npcs(init_log: str) -> list[str]:
    names: list[str] = []
    for line in init_log.splitlines():
        match = re.match(r"^Launching\s+(.+?)\s*$", line)
        if match:
            name = match.group(1).strip()
            if name and name not in names:
                names.append(name)
    return names


def _npc_top(container: str) -> str:
    proc = br._run(["docker", "top", container], timeout=30, check=False)
    if proc.returncode != 0:
        raise HostSessionError(f"docker top failed for {container}: {proc.stderr.strip()}")
    return proc.stdout


def npc_is_running(top_text: str, name: str) -> bool:
    normalized = top_text.replace('\\"', '"')
    variants = (f"--agent_name={name}", f'--agent_name="{name}"', f"--agent_name=\'{name}\'")
    return any(v in normalized for v in variants)


def _ensure_npc_processes(container: str, out: Path) -> dict[str, Any]:
    init_text = (out / "init.log").read_text(encoding="utf-8")
    expected = parse_launched_npcs(init_text)
    if not expected:
        payload = {"expected": [], "relaunched": [], "running": [], "attempts": 0}
        _write_json(out / "npc-runtime.json", payload)
        return payload

    # Service health=200 can precede stable RocketChat auth after a reset. Give the
    # task-specific NPCs a short grace period, then retry only missing processes.
    time.sleep(2.0)
    relaunched: list[str] = []
    running: list[str] = []
    attempts = 0
    for attempt in range(1, 4):
        attempts = attempt
        top = _npc_top(container)
        running = [name for name in expected if npc_is_running(top, name)]
        missing = [name for name in expected if name not in running]
        if not missing:
            break
        for name in missing:
            marker = f"--agent_name={name}"
            proc = br._run([
                "docker", "exec", "-d",
                "-e", f"LITELLM_API_KEY={br.ENV_API_KEY}",
                "-e", f"LITELLM_BASE_URL={br.ENV_BASE_URL}",
                "-e", f"LITELLM_MODEL={br.ENV_MODEL}",
                container,
                "python_default", "/npc/run_one_npc.py", marker,
            ], timeout=30, check=False)
            if proc.returncode != 0:
                raise HostSessionError(f"failed to relaunch NPC {name}: {proc.stderr.strip()}")
            relaunched.append(name)
        time.sleep(2.0 + attempt * 2.0)

    top_after = _npc_top(container)
    running = [name for name in expected if npc_is_running(top_after, name)]
    missing = [name for name in expected if name not in running]
    payload = {"expected": expected, "relaunched": relaunched, "running": running, "attempts": attempts}
    _write_json(out / "npc-runtime.json", payload)
    if missing:
        raise HostSessionError(f"NPC runtime not healthy after recovery: {missing}")
    return payload

def _start_task_container(task: str, name: str) -> str:
    image = br.task_image(task)
    br._ensure_image(image)
    br._docker_remove(name)
    proc = br._run([
        "docker", "run", "-d",
        "--name", name,
        "--network", "host",
        "--hostname", "zanachyOS",
        "--add-host", "the-agent-company.com:127.0.0.1",
        "--workdir", "/workspace",
        "-e", "SERVER_HOSTNAME=the-agent-company.com",
        "-e", f"LITELLM_BASE_URL={br.ENV_BASE_URL}",
        "-e", f"LITELLM_MODEL={br.ENV_MODEL}",
        "-e", f"LITELLM_API_KEY={br.ENV_API_KEY}",
        image,
        "sleep", "infinity",
    ], timeout=120)
    return proc.stdout.strip()


def _init_task(container: str, out: Path) -> tuple[str, dict[str, Any]]:
    init = br._run(["docker", "exec", container, "/utils/init.sh"], timeout=br.INIT_TIMEOUT, check=False)
    (out / "init.log").write_text(
        init.stdout + ("\nSTDERR\n" + init.stderr if init.stderr else ""),
        encoding="utf-8",
    )
    if init.returncode != 0:
        raise HostSessionError(f"task init failed ({init.returncode}); see {out / 'init.log'}")
    br._run(["docker", "cp", f"{container}:/instruction/task.md", str(out / "task.md")], timeout=30)
    dependencies = br._task_dependencies(container)
    (out / "dependencies.yml").write_text(dependencies, encoding="utf-8")
    baseline = br._structural_baseline(dependencies)
    return dependencies, baseline


def prepare(task: str, arm: str) -> dict[str, Any]:
    if task not in br.REMAINING_TASKS:
        raise HostSessionError(f"task not pending: {task}")
    if arm not in br.ARM_DIRS:
        raise HostSessionError(f"unknown arm: {arm}")
    active = _load_active()
    if active and _container_exists(str(active.get("container") or "")):
        raise HostSessionError(f"another hosted arm is active: {active.get('task')}/{active.get('arm')}")
    if arm == "xanxitospa":
        direct = host_arm_path(task, "direct")
        if not (direct / "eval.json").is_file():
            raise HostSessionError("XANXITOSPA requires a completed DIRECT evaluation first")

    STATE_ROOT.mkdir(parents=True, exist_ok=True)
    out = host_arm_path(task, arm)
    archived = br.prepare_arm_dir(out)
    br._ensure_env_model()
    br._prepare_reset_adapter()
    token = hashlib.sha256(f"{task}:{arm}:{time.time_ns()}".encode()).hexdigest()[:10]
    container = f"tac-chatgpt-{token}"
    started = now()
    try:
        container_id = _start_task_container(task, container)
        _, baseline = _init_task(container, out)
        npc_runtime = _ensure_npc_processes(container, out)
        _compare_host_baseline(task, arm, baseline, out)
        state = {
            "task": task,
            "arm": arm,
            "container": container,
            "container_id": container_id,
            "output_dir": str(out),
            "started_at": started,
            "baseline": baseline,
            "npc_runtime": npc_runtime,
            "archived_incomplete_predecessor": str(archived) if archived else None,
            "state": "prepared",
        }
        _write_json(ACTIVE_FILE, state)
        br._set_status(task, arm, state="running", phase="chatgpt-hosted", agent_host="chatgpt-mcp", baseline=baseline)
        return {"ok": True, **state}
    except Exception:
        br._docker_remove(container)
        raise


def read_task(task: str, arm: str) -> dict[str, Any]:
    state = _require_active(task, arm)
    path = Path(str(state["output_dir"])) / "task.md"
    text = path.read_text(encoding="utf-8")
    _append_event(state, command_event("cat /workspace/task.md", text, 0))
    return {"ok": True, "task": task, "arm": arm, "task_text": text}


def exec_in_task(task: str, arm: str, argv: list[str], timeout: int = 120) -> dict[str, Any]:
    if not argv:
        raise HostSessionError("exec requires argv")
    state = _require_active(task, arm)
    container = str(state["container"])
    proc = br._run(["docker", "exec", container, *argv], timeout=timeout, check=False)
    combined = proc.stdout + ("\nSTDERR\n" + proc.stderr if proc.stderr else "")
    _append_event(state, command_event(shlex.join(argv), combined, proc.returncode))
    return {
        "ok": proc.returncode == 0,
        "exit_code": proc.returncode,
        "stdout": proc.stdout,
        "stderr": proc.stderr,
    }


def log_mcp(task: str, arm: str, tool: str, arguments: dict[str, Any], result: Any | None = None) -> dict[str, Any]:
    state = _require_active(task, arm)
    if arm != "xanxitospa":
        raise HostSessionError("DIRECT arm cannot log or use MCP")
    if tool not in {"xanxito.mcp_server_tools", "xanxito.mcp_read"}:
        raise HostSessionError(f"forbidden benchmark MCP surface: {tool}")
    _append_event(state, mcp_event(tool, arguments, result))
    return {"ok": True}


def log_message(task: str, arm: str, text: str) -> dict[str, Any]:
    state = _require_active(task, arm)
    _append_event(state, message_event(text))
    (Path(str(state["output_dir"])) / "last-message.txt").write_text(text + "\n", encoding="utf-8")
    return {"ok": True}


def _run_evaluator(container: str, out: Path) -> dict[str, Any]:
    trajectory = out / "trajectory.jsonl"
    br._run(["docker", "cp", str(trajectory), f"{container}:/tmp/trajectory.jsonl"], timeout=30)
    proc = br._run([
        "docker", "exec",
        "-e", f"DECRYPTION_KEY={br.DECRYPTION_KEY}",
        "-e", f"LITELLM_API_KEY={br.ENV_API_KEY}",
        "-e", f"LITELLM_BASE_URL={br.ENV_BASE_URL}",
        "-e", f"LITELLM_MODEL={br.ENV_MODEL}",
        container,
        "python_default", "/utils/eval.py",
        "--trajectory_path", "/tmp/trajectory.jsonl",
        "--result_path", "/tmp/eval.json",
    ], timeout=br.EVAL_TIMEOUT, check=False)
    (out / "evaluator.log").write_text(
        proc.stdout + ("\nSTDERR\n" + proc.stderr if proc.stderr else ""), encoding="utf-8"
    )
    if proc.returncode != 0:
        raise HostSessionError(f"official evaluator failed ({proc.returncode}); see {out / 'evaluator.log'}")
    br._run(["docker", "cp", f"{container}:/tmp/eval.json", str(out / "eval.json")], timeout=30)
    value = json.loads((out / "eval.json").read_text(encoding="utf-8"))
    score = value.get("final_score") or {}
    if not isinstance(score.get("total"), int) or not isinstance(score.get("result"), int):
        raise HostSessionError(f"invalid evaluator result: {value}")
    return value


def finalize(task: str, arm: str) -> dict[str, Any]:
    state = _require_active(task, arm)
    out = Path(str(state["output_dir"]))
    container = str(state["container"])
    trajectory = (out / "trajectory.jsonl").read_text(encoding="utf-8")
    gate = br.validate_trajectory(arm, trajectory)
    _write_json(out / "isolation-gate.json", gate)
    evaluation = _run_evaluator(container, out)
    diff = br._run(["docker", "diff", container], timeout=30, check=False)
    (out / "container-diff.txt").write_text(diff.stdout, encoding="utf-8")
    workspace_final = out / "workspace-final"
    workspace_final.mkdir(parents=True, exist_ok=True)
    copy_proc = br._run(["docker", "cp", f"{container}:/workspace/.", str(workspace_final)], timeout=180, check=False)
    if copy_proc.returncode != 0:
        (out / "workspace-copy-error.log").write_text(copy_proc.stderr, encoding="utf-8")
    meta = {
        "task": task,
        "arm": arm,
        "started_at": state["started_at"],
        "finished_at": now(),
        "task_image": br.task_image(task),
        "task_container_id": state["container_id"],
        "agent_host": "chatgpt-mcp",
        "model": "gpt-5.6-sol",
        "reasoning_effort": "max",
        "environment_model": br.ENV_MODEL,
        "environment_base_url": br.ENV_BASE_URL,
        "baseline": state["baseline"],
        "isolation_gate": gate,
        "official_final_score": evaluation["final_score"],
        "archived_incomplete_predecessor": state.get("archived_incomplete_predecessor"),
        "dataset": "v3-chatgpt-hosted-mcp",
    }
    _write_json(out / "run-meta.json", meta)
    result = {
        "ok": True,
        "task": task,
        "arm": arm,
        "output_dir": str(out),
        "score": evaluation["final_score"],
        "baseline": state["baseline"],
        "isolation_gate": gate,
    }
    br._set_status(task, arm, state="complete", phase="done", result=result, agent_host="chatgpt-mcp")
    br._docker_remove(container)
    ACTIVE_FILE.unlink(missing_ok=True)
    return result


def abort(task: str, arm: str) -> dict[str, Any]:
    state = _require_active(task, arm)
    br._docker_remove(str(state["container"]))
    br._set_status(task, arm, state="aborted", phase="aborted", agent_host="chatgpt-mcp")
    ACTIVE_FILE.unlink(missing_ok=True)
    return {"ok": True, "task": task, "arm": arm, "state": "aborted"}


def status() -> dict[str, Any]:
    state = _load_active()
    if not state:
        return {"ok": True, "state": "idle"}
    state = dict(state)
    state["container_exists"] = _container_exists(str(state.get("container") or ""))
    return {"ok": True, **state}


def main() -> int:
    parser = argparse.ArgumentParser(description="ChatGPT-hosted TAC v2 runtime lifecycle")
    sub = parser.add_subparsers(dest="cmd", required=True)
    p = sub.add_parser("prepare")
    p.add_argument("task")
    p.add_argument("arm", choices=sorted(br.ARM_DIRS))
    p = sub.add_parser("read-task")
    p.add_argument("task")
    p.add_argument("arm", choices=sorted(br.ARM_DIRS))
    p = sub.add_parser("exec")
    p.add_argument("task")
    p.add_argument("arm", choices=sorted(br.ARM_DIRS))
    p.add_argument("--timeout", type=int, default=120)
    p.add_argument("argv", nargs=argparse.REMAINDER)
    p = sub.add_parser("log-mcp")
    p.add_argument("task")
    p.add_argument("arm", choices=sorted(br.ARM_DIRS))
    p.add_argument("tool")
    p.add_argument("arguments_json")
    p.add_argument("result_json", nargs="?", default="null")
    p = sub.add_parser("message")
    p.add_argument("task")
    p.add_argument("arm", choices=sorted(br.ARM_DIRS))
    p.add_argument("text")
    p = sub.add_parser("finalize")
    p.add_argument("task")
    p.add_argument("arm", choices=sorted(br.ARM_DIRS))
    p = sub.add_parser("abort")
    p.add_argument("task")
    p.add_argument("arm", choices=sorted(br.ARM_DIRS))
    sub.add_parser("status")
    args = parser.parse_args()
    try:
        if args.cmd == "prepare":
            result = prepare(args.task, args.arm)
        elif args.cmd == "read-task":
            result = read_task(args.task, args.arm)
        elif args.cmd == "exec":
            argv = args.argv[1:] if args.argv[:1] == ["--"] else args.argv
            result = exec_in_task(args.task, args.arm, argv, args.timeout)
        elif args.cmd == "log-mcp":
            result = log_mcp(args.task, args.arm, args.tool, json.loads(args.arguments_json), json.loads(args.result_json))
        elif args.cmd == "message":
            result = log_message(args.task, args.arm, args.text)
        elif args.cmd == "finalize":
            result = finalize(args.task, args.arm)
        elif args.cmd == "abort":
            result = abort(args.task, args.arm)
        else:
            result = status()
        print(json.dumps(result, indent=2, ensure_ascii=False))
        return 0 if result.get("ok") else 1
    except Exception as exc:
        print(json.dumps({"ok": False, "error": f"{type(exc).__name__}: {exc}"}, ensure_ascii=False))
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
