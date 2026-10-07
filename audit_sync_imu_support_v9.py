"""Audit full pre-crop IMU support for the sealed v9 synchronization inputs."""
import csv
import json
from pathlib import Path

import numpy as np

import pipeline as p


def main():
    out=p.ROOT/'outputs_observed_sync_imu_audit_v9'
    if out.exists():raise RuntimeError('Preserve prior audit')
    source=p.ROOT/'outputs_observed_reference_v7'
    cfg=json.loads((source/'run.json').read_text())['settings']
    inventory={r['id']:r for r in json.loads((p.ROOT/'outputs_amended_v2/inventory.json').read_text())}
    accepted=[r for r in csv.DictReader((source/'qc.csv').open(newline='')) if r['status']=='accepted']
    records=[]
    for record in accepted:
        row=inventory[record['id']]
        if row['partition'] not in ('train','validation'):raise RuntimeError('Test signals forbidden')
        streams=p.imu_streams(p.ROOT/row['imu'])
        t,raw,valid=p.sample_streams(streams,cfg)
        records.append(dict(id=row['id'],partition=row['partition'],frames=len(valid),invalid_frames=int((~valid).sum()),
                            invalid_runs_s=[[float(t[a]),float(t[b-1])+.01] for a,b in p.runs(~valid)],
                            imu_sha256=p.digest(p.ROOT/row['imu'])))
        if len(records)%100==0:print(f'{len(records)} full streams audited',flush=True)
    out.mkdir()
    result=dict(records=records,recordings=len(records),total_frames=sum(r['frames'] for r in records),
                invalid_frames=sum(r['invalid_frames'] for r in records),
                recordings_with_invalid_imu=sum(r['invalid_frames']>0 for r in records),test_evaluated=False,
                source_sha256=p.digest(Path(__file__)),pipeline_sha256=p.digest(p.ROOT/'pipeline.py'),
                interpretation='Full sample_streams output before first reference pose crop; this is the IMU array passed into synchronization.')
    p.save_json(out/'audit.json',result)
    print(json.dumps({k:v for k,v in result.items() if k!='records'}),flush=True)


if __name__=='__main__':main()
