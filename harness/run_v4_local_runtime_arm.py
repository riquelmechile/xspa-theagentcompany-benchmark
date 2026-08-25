#!/usr/bin/env python3
from __future__ import annotations
import argparse, fcntl, json, os, subprocess, uuid
from datetime import datetime, timezone
from pathlib import Path

REPO_ROOT=Path(__file__).resolve().parents[1]
IMAGE="ghcr.io/theagentcompany/sde-debug-crashed-server-image:1.0.0"
WHEELHOUSE=os.environ.get("XSPA_BENCH_WHEELHOUSE", str(REPO_ROOT.parent / "xspa-benchmark" / "runtime" / "local-runtime-wheelhouse"))
WHEELHOUSE_FINGERPRINT="fb7e151d5957593e2fc16e00cd6fd54dd0eb81678a2513809e06ee5844b3ee8b"
CONDITIONS=["control","kill_after_fix_before_healthcheck","port_contention","stale_process_after_takeover"]
ARMS=["direct","xanxitospa"]

def run(argv,cwd=None,timeout=120,check=True):
    p=subprocess.run(argv,cwd=str(cwd) if cwd else None,text=True,capture_output=True,timeout=timeout)
    if check and p.returncode!=0: raise RuntimeError(f"command failed {argv}: {p.stderr[-1500:]} {p.stdout[-1500:]}")
    return p

def main():
    ap=argparse.ArgumentParser(); ap.add_argument("--arm",choices=ARMS,required=True); ap.add_argument("--condition",choices=CONDITIONS,required=True); ap.add_argument("--xspa-repo",required=True); ap.add_argument("--config",required=True); ap.add_argument("--output",required=True); ap.add_argument("--manifest-fingerprint",required=True); a=ap.parse_args()
    cfg=json.loads(Path(a.config).read_text(encoding="utf-8")); zip_password=str(cfg["zipPassword"]); db_password=str(cfg["dbPassword"])
    out=Path(a.output); out.parent.mkdir(parents=True,exist_ok=True)
    lock=(out.parent/(out.name+".lock")).open("a+")
    try: fcntl.flock(lock.fileno(),fcntl.LOCK_EX|fcntl.LOCK_NB)
    except BlockingIOError: print(json.dumps({"ok":False,"duplicateSuppressed":True})); return 75
    name=f"tac-v4-local-{a.arm[:4]}-{uuid.uuid4().hex[:8]}"
    try:
        cid=run(["docker","run","-d","--name",name,"--workdir","/workspace","-v",f"{WHEELHOUSE}:/wheelhouse:ro",IMAGE,"sleep","infinity"],timeout=90).stdout.strip()
        run(["docker","exec",name,"sh","-lc",f"cd /workspace && unzip -P {zip_password} -oq app.zip"],timeout=30)
        run(["docker","exec",name,"python_default","-m","pip","install","--disable-pip-version-check","--no-index","--find-links","/wheelhouse","flask==3.1.3","duckdb==1.2.2","pyarrow==20.0.0","cryptography==50.0.0"],timeout=120)
        dep_versions=run(["docker","exec",name,"python_default","-c","import flask,duckdb,pyarrow,cryptography; print(flask.__version__ if hasattr(flask, '__version__') else '3.1.3', duckdb.__version__, pyarrow.__version__, cryptography.__version__)"],timeout=30).stdout.strip()
        patch=f"from pathlib import Path; p=Path('/workspace/app/event_viewer/main.py'); s=p.read_text(); s=s.replace('default_password', {db_password!r}).replace('app.run(debug=True)','app.run(debug=False)'); p.write_text(s); assert {db_password!r} in s and 'app.run(debug=False)' in s"
        run(["docker","exec",name,"python_default","-c",patch],timeout=30)
        fixed_hash=run(["docker","exec",name,"sha256sum","/workspace/app/event_viewer/main.py"],timeout=30).stdout.split()[0]
        proc=run(["pnpm","exec","tsx","packages/testing/src/run-tac-local-runtime-fault.ts","--mode",a.arm,"--condition",a.condition,"--container",name],cwd=Path(a.xspa_repo),timeout=120)
        result=json.loads(proc.stdout)
        payload={"benchmark":"XanxitoSpA fault-injection v4","version":"v4-stateful-1","manifestFingerprint":a.manifest_fingerprint,"taskId":"sde-debug-crashed-server","scenarioId":f"sde-debug-crashed-server__{a.condition}","arm":a.arm,"condition":a.condition,"generatedAt":datetime.now(timezone.utc).isoformat(),"reset":{"service":"task-container","containerId":cid,"image":IMAGE,"fixedMainSha256":fixed_hash,"wheelhouseFingerprint":WHEELHOUSE_FINGERPRINT,"dependencyVersions":dep_versions},"result":result}
        out.write_text(json.dumps(payload,indent=2)+"\n"); print(json.dumps(payload,indent=2)); return 0
    finally:
        run(["docker","rm","-f",name],timeout=60,check=False)
if __name__=="__main__": raise SystemExit(main())
