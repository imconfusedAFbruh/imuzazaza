"""Exact small-group sensitivity from frozen participant aggregates only."""
import csv,itertools,json,math
import numpy as np
import pipeline as p

OUT=p.ROOT/'outputs_retained_uncertainty_v114'
SOURCE=p.ROOT/'outputs_dynamic_blend_v34'


def sensitivity(effects):
    n=len(effects);mean=math.fsum(effects)/n
    samples=[math.fsum(effects[i] for i in ix)/n for ix in itertools.product(range(n),repeat=n)]
    flips=[math.fsum(s*x for s,x in zip(signs,effects))/n for signs in itertools.product((-1,1),repeat=n)]
    lo,hi=np.quantile(samples,[.025,.975],method='linear')
    probability=sum(abs(x)>=abs(mean)-1e-12 for x in flips)/len(flips)
    return dict(mean_benefit_m=mean,empirical_95pct_low_m=float(lo),empirical_95pct_high_m=float(hi),
        exact_sign_flip_two_sided_p=probability,resamples=len(samples),sign_flips=len(flips)),samples


def main():
    zero,_=sensitivity([0]*4);assert zero['exact_sign_flip_two_sided_p']==1 and zero['empirical_95pct_high_m']==0
    positive,_=sensitivity([1]*4);assert positive['mean_benefit_m']==positive['empirical_95pct_low_m']==1 and positive['exact_sign_flip_two_sided_p']==.125
    names=['original_v21_participants.csv','selected_blend_participants.csv','run.json']
    manifest=json.loads((SOURCE/'artifact_manifest.json').read_text())['sha256']
    for name in names:assert p.digest(SOURCE/name)==manifest[name]
    tables=[{r['participant']:r for r in csv.DictReader((SOURCE/name).open())} for name in names[:2]]
    old,new=tables;assert set(old)==set(new) and len(old)==4
    rows=[]
    for person in sorted(old):
        a,b=old[person],new[person];assert a['trials']==b['trials']
        x,y=float(a['mean_trial_position_rmse_m']),float(b['mean_trial_position_rmse_m'])
        rows.append(dict(participant=person,trials=int(a['trials']),old_rmse_m=x,new_rmse_m=y,benefit_m=x-y))
    assert sum(r['trials'] for r in rows)==71
    effects=[r['benefit_m'] for r in rows];result,samples=sensitivity(effects)
    oldmean=math.fsum(r['old_rmse_m'] for r in rows)/4;newmean=math.fsum(r['new_rmse_m'] for r in rows)/4
    historic=json.loads((SOURCE/'run.json').read_text())['summary']
    assert abs(oldmean-historic['original_v21']['equal_participant_mean_position_rmse_m'])<1e-12
    assert abs(newmean-historic['selected_blend']['equal_participant_mean_position_rmse_m'])<1e-12
    for r in rows:r['leave_person_out_mean_benefit_m']=math.fsum(q['benefit_m'] for q in rows if q is not r)/3
    OUT.mkdir(exist_ok=False);p.write_csv(OUT/'participants.csv',rows);p.save_json(OUT/'resamples.json',samples)
    p.save_json(OUT/'run.json',dict(experiment='v114',participants=4,trials=71,old_mean_m=oldmean,new_mean_m=newmean,
        relative_mean_benefit_percent=100*(oldmean-newmean)/oldmean,**result,
        prior_validation_aggregate_analysis=True,raw_or_prediction_reads=0,test_accessed=False,
        significance_claim=False,outperformance_claim=False,promotion=False,
        source_inputs={n:manifest[n] for n in names},source_manifest_sha256=p.digest(SOURCE/'artifact_manifest.json'),
        protocol_sha256=p.digest(p.ROOT/'research_docs/retained_uncertainty_v114.md')))
    p.save_json(OUT/'artifact_manifest.json',dict(sha256={f.name:p.digest(f) for f in OUT.iterdir() if f.is_file()},source_sha256=p.digest(__file__)))
    print((OUT/'run.json').read_text(),flush=True)


if __name__=='__main__':main()
