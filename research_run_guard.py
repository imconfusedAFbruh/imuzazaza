"""Exclusive workspace owner with live PID identity and a 15-second heartbeat."""
import datetime,json,os,runpy,subprocess,sys,threading,uuid
from pathlib import Path

LOCK=Path(__file__).resolve().parent/'research_state/ACTIVE_RUN.json'


def process(pid):
    q=subprocess.run(['powershell','-NoProfile','-Command',f'Get-CimInstance Win32_Process -Filter "ProcessId = {int(pid)}" | Select-Object ProcessId,CreationDate,CommandLine | ConvertTo-Json -Compress'],capture_output=True,text=True,check=True)
    return json.loads(q.stdout) if q.stdout.strip() else None


def main():
    if LOCK.exists():
        owner=json.loads(LOCK.read_text()); current=process(owner['pid'])
        raise RuntimeError(f'Existing lock requires explicit process verification; never override by age: {owner}; live={current}')
    owner=dict(run_id='native-v80-'+uuid.uuid4().hex,pid=os.getpid(),process=process(os.getpid()),started_utc=datetime.datetime.now(datetime.timezone.utc).isoformat(),commands=sys.argv[1:],stage='',status='running')
    with LOCK.open('x') as f:json.dump(owner,f,indent=2)
    stop=threading.Event()
    def heartbeat():
        while not stop.is_set():
            owner['heartbeat_utc']=datetime.datetime.now(datetime.timezone.utc).isoformat()
            temp=LOCK.with_suffix('.tmp'); temp.write_text(json.dumps(owner,indent=2)); temp.replace(LOCK)
            stop.wait(15)
    thread=threading.Thread(target=heartbeat,daemon=True);thread.start()
    try:
        for script in sys.argv[1:]:
            owner['stage']=script
            runpy.run_path(script,run_name='__main__')
        owner['status']='complete'
    except BaseException as exc:
        owner['status']='failed';owner['error']=repr(exc)
        raise
    finally:
        stop.set();thread.join()
        owner['finished_utc']=datetime.datetime.now(datetime.timezone.utc).isoformat()
        (LOCK.parent/'LAST_RUN.json').write_text(json.dumps(owner,indent=2))
        if json.loads(LOCK.read_text())['run_id']==owner['run_id']:LOCK.unlink()


if __name__=='__main__':main()
