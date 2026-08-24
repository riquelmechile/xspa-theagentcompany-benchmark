#!/usr/bin/env python3
from __future__ import annotations
import argparse, base64, fcntl, json, subprocess, urllib.error, urllib.request
from datetime import datetime, timezone
from pathlib import Path

CONDITIONS=["control","lost_ack_after_upload","credential_expiry","concurrent_revision_write"]
ARMS=["direct","xanxitospa"]
API_BASE="http://127.0.0.1:2999"

def run(argv,cwd=None,timeout=180):
    p=subprocess.run(argv,cwd=str(cwd) if cwd else None,text=True,capture_output=True,timeout=timeout)
    if p.returncode!=0: raise RuntimeError(f"command failed {argv}: {p.stderr[-1500:]} {p.stdout[-1500:]}")
    return p

def post_reset():
    req=urllib.request.Request(f"{API_BASE}/api/reset-owncloud",data=b"",method="POST")
    with urllib.request.urlopen(req,timeout=60) as r:
        body=r.read().decode();
        if r.status!=202: raise RuntimeError(f"reset-owncloud HTTP {r.status}: {body}")
    for _ in range(90):
        try:
            with urllib.request.urlopen(f"{API_BASE}/api/healthcheck/owncloud",timeout=5) as r:
                if r.status==200: return
        except Exception: pass
        import time; time.sleep(2)
    raise RuntimeError("OwnCloud health did not recover")

def ensure_absent(config_path:Path,path:str):
    cfg=json.loads(config_path.read_text())
    url=cfg["davRoot"].rstrip("/")+"/"+path.lstrip("/")
    token=base64.b64encode(f'{cfg["username"]}:{cfg["password"]}'.encode()).decode()
    req=urllib.request.Request(url,headers={"Authorization":f"Basic {token}"})
    try:
        with urllib.request.urlopen(req,timeout=15) as r: raise RuntimeError(f"campaign object unexpectedly exists HTTP {r.status}")
    except urllib.error.HTTPError as e:
        if e.code!=404: raise

def main():
    ap=argparse.ArgumentParser(); ap.add_argument("--arm",choices=ARMS,required=True); ap.add_argument("--condition",choices=CONDITIONS,required=True); ap.add_argument("--xspa-repo",required=True); ap.add_argument("--config",required=True); ap.add_argument("--output",required=True); ap.add_argument("--path",default="/Documents/xspa-v4-reconciled.csv"); ap.add_argument("--manifest-fingerprint",required=True); a=ap.parse_args()
    out=Path(a.output); out.parent.mkdir(parents=True,exist_ok=True)
    lock=(out.parent/(out.name+".lock")).open("a+")
    try: fcntl.flock(lock.fileno(),fcntl.LOCK_EX|fcntl.LOCK_NB)
    except BlockingIOError: print(json.dumps({"ok":False,"duplicateSuppressed":True})); return 75
    post_reset(); ensure_absent(Path(a.config),a.path)
    body=f"xspa-v4-owncloud-designated-revision:{a.condition}\n"; stale=f"xspa-v4-owncloud-stale-revision:{a.condition}\n"
    p=run(["pnpm","exec","tsx","packages/testing/src/run-tac-owncloud-fault.ts","--mode",a.arm,"--condition",a.condition,"--config",a.config,"--path",a.path,"--body",body,"--stale-body",stale],cwd=Path(a.xspa_repo),timeout=180)
    result=json.loads(p.stdout)
    payload={"benchmark":"XanxitoSpA fault-injection v4","version":"v4-stateful-1","manifestFingerprint":a.manifest_fingerprint,"taskId":"admin-employee-info-reconciliation","scenarioId":f"admin-employee-info-reconciliation__{a.condition}","arm":a.arm,"condition":a.condition,"generatedAt":datetime.now(timezone.utc).isoformat(),"reset":{"service":"owncloud","baselineObjectAbsent":True},"result":result}
    out.write_text(json.dumps(payload,indent=2)+"\n"); print(json.dumps(payload,indent=2)); return 0
if __name__=="__main__": raise SystemExit(main())
