"""Reuse independently verified v39 arithmetic on v42, preserving prior artifacts."""
import json
from pathlib import Path
import matplotlib.axes
import audit_clock_routes_v39 as audit
from pipeline import ROOT,digest,save_json

audit.OUT=ROOT/'outputs_clock_routes_v44'
audit.SOURCE=ROOT/'outputs_clock_arbitrated_v42'
original_set=matplotlib.axes.Axes.set


def short_titles(self,**kwargs):
    titles={'Same native support; no fitted alignment':'Trajectory; shared pose',
            'Direct observed common frames':'Observed common frames'}
    if 'title' in kwargs:kwargs['title']=titles.get(kwargs['title'],kwargs['title'])
    return original_set(self,**kwargs)


if __name__=='__main__':
    matplotlib.axes.Axes.set=short_titles
    try:audit.main()
    finally:matplotlib.axes.Axes.set=original_set
    q=json.loads((audit.OUT/'run.json').read_text())
    q['wrapper_sha256']=digest(Path(__file__))
    q['promotion']='Not promoted: v43trainingworstpersonratio1.058005 exceeds5%guard'
    q['plot_change']='Short titles avoid adjacent equalaspect subplot title overlap; no numerical change'
    save_json(audit.OUT/'run.json',q)
    save_json(audit.OUT/'artifact_manifest.json',dict(sha256={str(p.relative_to(audit.OUT)):digest(p) for p in audit.OUT.rglob('*') if p.is_file() and p.name!='artifact_manifest.json'}))
