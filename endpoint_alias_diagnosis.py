"""Train-only decomposition of raw versus circular heading endpoint residuals."""
import json
from pathlib import Path
import numpy as np
from pipeline import ROOT,save_json,write_csv,digest

def main():
    out=ROOT/'outputs_endpoint_alias_diagnosis'
    if out.exists():raise RuntimeError('Preserve prior output')
    out.mkdir(); rows=[]
    for path in sorted((ROOT/'outputs_motion_endpoint_v16/prepared_training').glob('*.npz')):
        row=json.loads(path.with_suffix('.json').read_text())['row']
        if row['partition']!='train':raise RuntimeError('Not training')
        with np.load(path,allow_pickle=False) as z:
            t=z['t']; valid=z['gt_valid']; imu=z['imu_valid']; gt=z['gt_heading']; m=z['ridge_motion']
        h=np.r_[0,np.cumsum(np.diff(t)*(m[:-1,2]+m[1:,2])/2)];bad=np.r_[0,np.cumsum(~imu)]
        counts=dict(pairs=0,gap_pairs=0,gap_wraps=0,continuous_pairs=0,continuous_wraps=0)
        for a in range(0,len(t),100):
            if not valid[a]:continue
            for horizon in (100,300,500,1000):
                b=a+horizon
                if b>=len(t) or not valid[b] or bad[b+1]!=bad[a]:continue
                gap=not valid[a:b+1].all();wrap=abs(gt[b]-gt[a]-(h[b]-h[a]))>np.pi
                counts['pairs']+=1;counts['gap_pairs' if gap else 'continuous_pairs']+=1
                counts['gap_wraps' if gap else 'continuous_wraps']+=int(wrap)
        rows.append(dict(id=row['id'],participant=row['participant'],condition=row['condition'],**counts))
    totals={k:sum(r[k] for r in rows) for k in counts}
    save_json(out/'summary.json',dict(training_recordings=len(rows),totals=totals,test_evaluated=False,source_sha256=digest(Path(__file__))))
    write_csv(out/'trials.csv',rows)
    print(json.dumps(totals))

if __name__=='__main__':main()
