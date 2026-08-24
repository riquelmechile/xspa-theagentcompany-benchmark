#!/usr/bin/env python3
from __future__ import annotations
import argparse, json, os, subprocess, sys
from datetime import datetime, timezone
from pathlib import Path


def main() -> int:
    ap=argparse.ArgumentParser(); ap.add_argument('--start-pair',type=int,required=True); ap.add_argument('--end-pair',type=int,required=True); ap.add_argument('--log',required=True); a=ap.parse_args()
    log=Path(a.log); log.parent.mkdir(parents=True,exist_ok=True)
    state=log.with_suffix(log.suffix+'.launch.json')
    if state.exists():
        try:
            prior=json.loads(state.read_text()); pid=int(prior.get('pid') or 0)
            if pid>0:
                try: os.kill(pid,0); print(json.dumps({'ok':True,'state':'already-running',**prior})); return 0
                except ProcessLookupError: pass
        except Exception: pass
    handle=log.open('ab',buffering=0)
    argv=[sys.executable,'-m','harness.run_v5_campaign','--start-pair',str(a.start_pair),'--end-pair',str(a.end_pair)]
    proc=subprocess.Popen(argv,cwd=str(Path(__file__).resolve().parents[1]),stdin=subprocess.DEVNULL,stdout=handle,stderr=subprocess.STDOUT,start_new_session=True,close_fds=True)
    handle.close()
    payload={'ok':True,'state':'launched','pid':proc.pid,'startPair':a.start_pair,'endPair':a.end_pair,'log':str(log),'launchedAt':datetime.now(timezone.utc).isoformat()}
    state.write_text(json.dumps(payload,indent=2)+'\n'); print(json.dumps(payload)); return 0
if __name__=='__main__': raise SystemExit(main())
