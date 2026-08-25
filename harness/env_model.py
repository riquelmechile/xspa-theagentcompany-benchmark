#!/usr/bin/env python3
from __future__ import annotations

import json
import os
import signal
import subprocess
import sys
import time
import urllib.request
from pathlib import Path

BINARY = Path(os.environ.get('XSPA_ENV_MODEL_BINARY', Path.home() / 'llama.cpp-cuda/build/bin/llama-server'))
MODEL = Path('/data/models/Qwen3.8-27B-UD-Q3_K_XL.gguf')
ALIAS = 'xspa-env-qwen3.8-27b'
HOST = '127.0.0.1'
PORT = 18080
STATE = Path(os.environ.get('XSPA_BENCH_STATE_ROOT', Path(__file__).resolve().parents[2] / 'xspa-benchmark' / 'v2-runner-state'))
PID_FILE = STATE / 'env-model.pid'
LOG_FILE = STATE / 'env-model.log'


def healthy() -> bool:
    try:
        req = urllib.request.Request(f'http://{HOST}:{PORT}/v1/models')
        with urllib.request.urlopen(req, timeout=3) as response:
            data = json.loads(response.read().decode('utf-8'))
        ids = [str(item.get('id')) for item in data.get('data', []) if isinstance(item, dict)]
        return response.status == 200 and (ALIAS in ids or bool(ids))
    except Exception:
        return False


def pid_alive(pid: int) -> bool:
    if pid <= 0:
        return False
    try:
        os.kill(pid, 0)
        return True
    except ProcessLookupError:
        return False


def read_pid() -> int:
    try:
        return int(PID_FILE.read_text().strip())
    except Exception:
        return 0


def command() -> list[str]:
    return [
        str(BINARY),
        '-m', str(MODEL),
        '-ngl', '99',
        '--flash-attn', 'on',
        '--cache-type-k', 'q8_0',
        '--cache-type-v', 'q8_0',
        '-c', '32768',
        '--parallel', '1',
        '--host', HOST,
        '--port', str(PORT),
        '--alias', ALIAS,
    ]


def start() -> dict:
    if healthy():
        return {'ok': True, 'state': 'healthy', 'pid': read_pid(), 'alias': ALIAS}
    if not BINARY.is_file() or not MODEL.is_file():
        return {'ok': False, 'error': 'binary or model missing', 'binary': str(BINARY), 'model': str(MODEL)}
    old = read_pid()
    if pid_alive(old):
        return {'ok': False, 'error': 'existing env-model pid is alive but endpoint is unhealthy', 'pid': old}
    STATE.mkdir(parents=True, exist_ok=True)
    log = LOG_FILE.open('ab', buffering=0)
    proc = subprocess.Popen(
        command(),
        stdin=subprocess.DEVNULL,
        stdout=log,
        stderr=subprocess.STDOUT,
        start_new_session=True,
        close_fds=True,
    )
    log.close()
    PID_FILE.write_text(str(proc.pid))
    deadline = time.monotonic() + 150
    while time.monotonic() < deadline:
        if healthy():
            return {'ok': True, 'state': 'started', 'pid': proc.pid, 'alias': ALIAS, 'model': str(MODEL)}
        if proc.poll() is not None:
            return {'ok': False, 'error': f'llama-server exited {proc.returncode}', 'pid': proc.pid, 'log': str(LOG_FILE)}
        time.sleep(2)
    return {'ok': False, 'error': 'llama-server did not become healthy in 150s', 'pid': proc.pid, 'log': str(LOG_FILE)}


def matches(pid: int) -> bool:
    try:
        raw = Path(f'/proc/{pid}/cmdline').read_bytes().replace(b'\x00', b' ').decode('utf-8', 'replace')
    except OSError:
        return False
    return str(BINARY) in raw and str(MODEL) in raw and '--port 18080' in raw and ALIAS in raw


def stop() -> dict:
    pid = read_pid()
    if not pid_alive(pid):
        PID_FILE.unlink(missing_ok=True)
        return {'ok': True, 'state': 'already-stopped'}
    if not matches(pid):
        return {'ok': False, 'error': 'pid does not match benchmark env model; no signal sent', 'pid': pid}
    os.kill(pid, signal.SIGTERM)
    deadline = time.monotonic() + 20
    while time.monotonic() < deadline and pid_alive(pid):
        time.sleep(0.25)
    if pid_alive(pid):
        return {'ok': False, 'error': 'env model did not stop after SIGTERM', 'pid': pid}
    PID_FILE.unlink(missing_ok=True)
    return {'ok': True, 'state': 'stopped', 'pid': pid}


def status() -> dict:
    pid = read_pid()
    return {'ok': healthy(), 'healthy': healthy(), 'pid': pid, 'process_alive': pid_alive(pid), 'alias': ALIAS, 'model': str(MODEL), 'log': str(LOG_FILE)}


def main() -> int:
    op = sys.argv[1] if len(sys.argv) > 1 else 'status'
    if op == 'start':
        result = start()
    elif op == 'status':
        result = status()
    elif op == 'stop':
        result = stop()
    else:
        result = {'ok': False, 'error': f'unsupported op: {op}'}
    print(json.dumps(result, indent=2))
    return 0 if result.get('ok') else 1


if __name__ == '__main__':
    raise SystemExit(main())
