"""Report controlled experiments honestly and update the existing methods PDF."""
from pathlib import Path
import csv,json,html,io
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from reportlab.platypus import SimpleDocTemplate,Paragraph,Table,TableStyle,Spacer,Image,PageBreak
from reportlab.lib.styles import getSampleStyleSheet,ParagraphStyle
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4,landscape
from pypdf import PdfReader,PdfWriter

ROOT=Path(__file__).resolve().parent
OUT=ROOT/'outputs_controlled_motion_review';TMP=ROOT/'tmp/pdfs/controlled_update'
OUT.mkdir(exist_ok=True);TMP.mkdir(parents=True,exist_ok=True)
P25=ROOT/'outputs_controlled_motion_v25';P26=ROOT/'outputs_controlled_refit_v26';P27=ROOT/'outputs_matched_motion_v27';P28=ROOT/'outputs_best_base_braking_v28'
def read(p):return json.loads(p.read_text())
def csvrows(p):return list(csv.DictReader(p.open(newline='',encoding='utf-8')))
r25,r26,r27,r28=[read(p/'run.json') for p in (P25,P26,P27,P28)]
s28=read(P28/'selection.json');choice=s28['selected']['name'] if s28['selected'] else 'braking_0.5'
old=ROOT/'outputs_trajectory_best_v21';trials=csvrows(old/'candidate_trials.csv');ids=[r['id'] for r in trials]
score_tables={name:{r['id']:r for r in csvrows(path)} for name,path in [('v21',old/'candidate_trials.csv'),('v25',P25/'selected_trials.csv'),('v28',P28/f'{choice}_trials.csv')]}
assert len(ids)==71 and all(set(x)==set(ids) for x in score_tables.values())
alltrials=[];labels=['v21 original','v25 braking','v28 '+choice];linecolors=['#75839a','#168273','#d65d24']
(OUT/'individual').mkdir(exist_ok=True)
for r in trials:
    id=r['id']
    with np.load(old/'trajectories'/(id+'.npz')) as z:d={k:z[k] for k in z.files}
    with np.load(P25/'selected/trajectories'/(id+'.npz')) as z:b={k:z[k] for k in z.files}
    with np.load(P28/choice/'trajectories'/(id+'.npz')) as z:c={k:z[k] for k in z.files}
    assert np.array_equal(d['reference_valid'],b['reference_valid']) and np.array_equal(b['reference_valid'],c['reference_valid'])
    origin=d['reference_xy_m'][0];truth=d['reference_xy_m']-origin;truth[~d['reference_valid']]=np.nan
    paths=[d['model_2_xy_m']-origin,b['xy']-origin,c['xy']-origin];headings=[d['model_2_heading_rad'],b['heading'],c['heading']]
    fig,axes=plt.subplots(1,3,figsize=(15,4.5),layout='constrained');axes[0].plot(*truth.T,color='black',label='Observed reference',lw=1.5)
    for name,color,path,h in zip(labels,linecolors,paths,headings):
        axes[0].plot(*path.T,color=color,label=name,lw=1.1)
        err=np.linalg.norm(path-(d['reference_xy_m']-origin),axis=1)*1000;err[~d['reference_valid']]=np.nan
        angle=np.rad2deg(np.arctan2(np.sin(h-d['reference_heading_rad']),np.cos(h-d['reference_heading_rad'])));angle[~d['reference_valid']]=np.nan
        axes[1].plot(d['time_s'],err,color=color,lw=1);axes[2].plot(d['time_s'],angle,color=color,lw=1)
    axes[0].set_aspect('equal',adjustable='datalim');axes[0].legend(fontsize=7)
    axes[0].set(xlabel='X from initial position (m)',ylabel='Y (m)',title='Trajectory; equal physical aspect')
    axes[1].set(xlabel='Time (s)',ylabel='Position error (mm)',title='Observed position error');axes[2].set(xlabel='Time (s)',ylabel='Heading error (degrees)',title='Wrapped heading error')
    for ax in axes:ax.grid(alpha=.2)
    scores=[float(score_tables[k][id]['position_rmse_m'])*1000 for k in ('v21','v25','v28')]
    fig.suptitle(id+' | v21 / v25 / v28 RMSE: '+' / '.join(f'{s:.1f}' for s in scores)+' mm',fontsize=10)
    fig.savefig(OUT/'individual'/(id+'.png'),dpi=145);plt.close(fig)
    alltrials.append(dict(row=r,truth=truth,paths=paths,scores=scores))
    if len(alltrials)%20==0:print('Rendered',len(alltrials),'new comparisons',flush=True)
for cond in ('10x5','AR','CR','OS','PS','SL','ST'):
    ts=[t for t in alltrials if t['row']['condition']==cond];merged=np.concatenate([p for t in ts for p in [t['truth'],*t['paths']]])
    lo=np.nanmin(merged,axis=0);hi=np.nanmax(merged,axis=0);pad=np.maximum(.15,(hi-lo)*.06);lo-=pad;hi+=pad
    fig,axs=plt.subplots(4,3,figsize=(16,6.5 if cond in ('OS','PS','ST') else 13),layout='constrained');handles=None
    for i,person in enumerate(('No.5','No.10','No.14','No.18')):
        for j in range(3):
            ax=axs[i,j];t=next((t for t in ts if t['row']['participant']==person and f'_Trial{j+1}_' in t['row']['id']),None)
            if not t:ax.text(.5,.5,'No accepted recording\nExisting QC exclusion',ha='center',va='center',transform=ax.transAxes);ax.set_axis_off();continue
            ax.plot(*t['truth'].T,color='black',lw=1.5,label='Observed reference')
            for label,col,xy in zip(labels,linecolors,t['paths']):ax.plot(*xy.T,color=col,lw=1.1,label=label)
            ax.set(xlim=(lo[0],hi[0]),ylim=(lo[1],hi[1]),xlabel='X (m)',ylabel='Y (m)',title=person+f' trial{j+1} | '+' / '.join(f'{s:.0f}' for s in t['scores'])+' mm');ax.set_aspect('equal',adjustable='box');ax.grid(alpha=.2)
            if handles is None:handles=ax.get_legend_handles_labels()
    fig.get_layout_engine().set(rect=(0,.035,1,.87 if cond in ('OS','PS','ST') else .92))
    fig.legend(*handles,loc='upper center',bbox_to_anchor=(.5,.963 if cond in ('OS','PS','ST') else .976),ncol=4,fontsize=8);fig.suptitle(cond+' | 4 October controlled comparisons',y=.997)
    fig.supxlabel('RMSE order: v21 / v25 / v28. Equal scale within maneuver; no fitted alignment. Validation exploratory.',fontsize=9)
    fig.savefig(OUT/(cond+'_all.png'),dpi=140);plt.close(fig)

def mm(run,name):return 1000*run['summary'][name]['equal_participant_mean_position_rmse_m']
quiet=read(P25/'validation_quiet_states.json');eligible=sum(q['eligible'] for q in quiet)
rows=[['Comparator','RMSE mm','Interpretation'],['Original v21','102.585','Existing exploratory minimum'],['v24 / v25 control',f'{mm(r25,"control"):.3f}','Conservative current control'],['v25 braking only',f'{mm(r25,"braking"):.3f}','Selected on three training folds'],['v25 quiet yaw only',f'{mm(r25,"yaw_state"):.3f}',f'Quiet-state eligible {eligible}/71'],['v27 matched combined',f'{mm(r27,"combined_0.0001"):.3f}','Same braking gain; heuristic smoother'],['v26 independently refitted',f'{mm(r26,"selected"):.3f}','New simpler motion model; rejected'],['v28 '+choice,f'{mm(r28,choice):.3f}','Braking extension of stronger base']]
notes=['# Controlled motion experiments: 4 October 2026','', '| Comparator | RMSE mm | Interpretation |','|---|---:|---|']+['| '+' | '.join(row)+' |' for row in rows[1:]]
notes += ['',f'v28 selection: {json.dumps(s28)}', '',f'Quiet yaw-state support: {eligible}/71 validation recordings. All 71 accepted records retained. No test data read.', '', 'Conditional v25 refits the v24 correction and new components within folds; inherited calibration/neural stack remain conditional. Independent v26 refits empirical calibration and every parameter of its new simpler learned motion model, rather than refitting the original neural stack. All branches retain benchmark clocks, optical geometry, QC and reference masks. This is not full independent preprocessing validation.', '', 'v25 braking uses 60 empirical temporal features: center acceleration/gyro, wheel speed/derivative, yaw disagreement, continuous braking/stopped gates and interactions at -0.5/0/+0.5 seconds. Constrained forward-only normal equations combine rate labels and 1/3/5/10-second endpoints; alpha .3, training-only scales/caps. Gain .25/.5 selected by pooled twelve-person folds and <=5% regression vs its control.', '', 'Yaw correction is a bounded zero-rate model-output state estimated during conservative IMU-only quiet intervals, not a verified 3D attitude or sensor calibration. Min1.5s quiet, .5s edges, max .02rad/s state, decay10s. Future quiet intervals make it offline.', '', 'Combined smoothing minimizes velocity measurement disagreement plus acceleration-increment disagreement with confidence inferred from in-fit residuals, per braking regime. Variances are heuristic and not independently calibrated; correlated samples are not modeled as independent sensor measurements. This implements a controlled empirical mechanism comparator, not a complete TLIO/Wheel-INS2 system.', '', 'User mounting update: both wheel IMUs are off-axis and face outward; center IMU faces backward. Exact rotations, lever-arm vectors and raw/library/CSV packing remain unknown. Actual acquisition remains +/-2g and +/-2000degrees/s.', '', 'The original 102.585mm result is exploratory. New validation comparisons were repeatedly inspected. No lower observed score establishes blind generalization or millimeter accuracy. Negative branches and all candidate tables are preserved.']
(ROOT/'research_docs/controlled-motion-update.md').write_text('\n'.join(notes)+'\n',encoding='utf-8')
cards=''.join(f'<article><h3>{html.escape(id)}</h3><img loading="lazy" src="individual/{html.escape(id)}.png"></article>' for id in ids)
(OUT/'gallery.html').write_text('<!doctype html><meta charset="utf-8"><title>Controlled motion comparisons</title><style>body{font:16px system-ui;margin:24px;background:#f1f5f8}article{background:white;margin:20px 0;padding:15px}img{width:100%}</style><h1>All 71 controlled comparisons</h1><p>Reference / v21 / v25 / v28. Validation reused; no test data. v28 is a comparator unless the training guard passes.</p>'+cards,encoding='utf-8')

styles=getSampleStyleSheet();styles.add(ParagraphStyle(name='BodyX',fontName='Helvetica',fontSize=10,leading=15,spaceAfter=10,textColor=colors.HexColor('#23364a')));styles.add(ParagraphStyle(name='TinyX',fontName='Helvetica',fontSize=8,leading=11,spaceAfter=6));styles['Heading1'].textColor=colors.HexColor('#143b52');styles['Heading1'].fontSize=22;styles['Heading1'].leading=27
story=[]
def p(t,style='BodyX'):story.append(Paragraph(t,styles[style]))
def title(t):
    if story:story.append(PageBreak())
    p(t,'Heading1')
def table(data,widths):
    t=Table([[Paragraph(html.escape(str(x)),styles['TinyX']) for x in r] for r in data],colWidths=widths,repeatRows=1)
    t.setStyle(TableStyle([('BACKGROUND',(0,0),(-1,0),colors.HexColor('#e1edf4')),('VALIGN',(0,0),(-1,-1),'TOP'),('LINEBELOW',(0,0),(-1,-1),.3,colors.HexColor('#cddae4')),('TOPPADDING',(0,0),(-1,-1),7),('BOTTOMPADDING',(0,0),(-1,-1),6)]));story.append(t);story.append(Spacer(1,12))
title('Development update / 4 October 2026')
p('Controlled braking, quiet-yaw state and confidence-weighted dynamics experiments','Heading2')
table(rows,[175,80,220])
p(f'<b>Measured gain:</b> braking correction reduces the conservative control by {mm(r25,"control")-mm(r25,"braking"):.3f} mm ({100*(1-mm(r25,"braking")/mm(r25,"control")):.2f}%). It does not establish an improvement over original v21 unless the stronger-base extension shown above beats 102.585 mm. All scores are equal-participant mean trial Euclidean XY RMSE on the same 71 observed-reference recordings.')
p('<b>Development decision:</b> use v25 braking as the conservative candidate for the next separately frozen evaluation. It improves all four validation participant means and passes the twelve-person training guard (worst regression 1.91% versus v24; 2.25% versus original ridge). Preserve v21 as the prior minimum-error comparator. The v28 extension measures 102.297 mm but fails the training guard at 6.20% worst-participant regression and is not promoted.')
p('<b>Report structure.</b> These update pages and new comparison sheets precede the preserved 3 October methodology and 71-page v21 atlas. The original chapters describe the prior development state; this update supplies the newer evidence and selection status. Both versions use identical reference masks and initial-pose-only integration.')
p('No test recordings were accessed. Validation reuse, unverified CSV units and full mounting/reference geometry remain limitations.','TinyX')
title('New methods / controlled components')
p('<b>Braking:</b> a forward-only residual uses 60 IMU-derived temporal features, wheel-body disagreement and continuous braking/stopped gates. Fit point labels and observed SE2 endpoint equations at 1/3/5/10 s, with training-only normalization, caps and weights. No maneuver or participant identifier is a predictor input. It is an empirical body-velocity correction, not independently measured tire slip.')
p('<b>Quiet yaw state:</b> require both wheels below 0.03 m/s, center gyro norm below 0.08 rad/s, acceleration axis spread below 0.015 empirical g and norm 0.9-1.1 for at least 1.5 s. Exclude half-second edges. Estimate the model-output zero-rate offset, cap it at 0.02 rad/s and decay over 10 s away from quiet observations. No optical label updates the state.')
p(f'Only {eligible} of 71 validation recordings support that state. This explains its limited effect. It does not supply independently validated full attitude or replace sensor calibration. Future IMU observations make the method offline.')
p('<b>Combined dynamics smoother:</b> fit an empirical mapping from IMU features to body forward acceleration using observed training derivative runs. Minimize disagreement with corrected velocity and predicted adjacent acceleration increments using a tridiagonal solve. Train residual second moments supply regime-dependent confidence. These are in-fit heuristic weights, not calibrated probabilistic covariance.')
p('<b>Matched ablation:</b> v27 holds braking gain at 0.5, adds yaw gain 0.25, then tests smoother weights 0.0001/0.001/0.01. This corrects the unequal braking-strength comparison in v25. The fixed grids and all unsuccessful candidates are saved.')
title('Selection / what is and is not independent')
p('Three disjoint four-person training folds cover all twelve target training people. Each new correction excludes held people from fitting. Selection uses pooled equal-person path error and a maximum 5% participant regression guard. Earlier unmapped training sessions stay in every fit.')
p('v25/v27/v28 inherit the existing empirical calibration and neural base, so their folds are conditional. v26 fits empirical calibration, feature normalization, lateral/forward/yaw motion parameters and new corrections within each fold, with no inherited pretrained predictor. It is a different, simpler empirical model and performs much worse. It does not establish the original neural stack\'s independent generalization.')
p('Every branch retains the fixed benchmark clock alignment, quality decisions, optical geometry and observed masks. Those preprocessing stages were not independently refitted within these folds. A fully nested refit of the original neural stack and its preprocessing remains future work.')
p('v28 tests braking on the stronger v21 base, with the original ridge as the participant-regression reference. Candidate gains are 0, 0.25 and 0.5. Its selection status follows:')
p(html.escape(json.dumps({k:s28[k] for k in ('selected','passes_original_ridge_guard','preferred_over_v24_on_training_folds')},indent=2)),'TinyX')
p('A lower inspected validation score is an exploratory comparator. Do not promote a candidate rejected by the training guard because its validation plot looks better. Future frozen evaluation must compare the selected candidate and baselines together.')
p('Reference-free inference replay reproduced every one of the 71 conditional prediction arrays exactly and every independently fitted array to a maximum absolute difference of 1.8e-18. Predictor input contains only IMU fields and optional IMU startup state; reference pose is supplied separately to the integrator. This is an artifact reproducibility check, not independent generalization evidence.')
title('Results / maneuver errors and remaining failures')
mans={k:{r['condition']:r for r in csvrows(path)} for k,path in [('v21',old/'candidate_maneuvers.csv'),('v25',P25/'selected_maneuvers.csv'),('v28',P28/f'{choice}_maneuvers.csv')]}
table([['Maneuver','v21 mm','v25 mm','v28 mm']]+[[c]+[f"{1000*float(mans[k][c]['equal_participant_mean_position_rmse_m']):.3f}" for k in ('v21','v25','v28')] for c in ('10x5','AR','CR','OS','PS','SL','ST')],[145,110,110,110])
psid='2026-09-25__PS__PS_Trial2_No.18'
p('No.18 PS2 RMSE: '+', '.join(f"{k} {1000*float(score_tables[k][psid]['position_rmse_m']):.1f} mm" for k in ('v21','v25','v28'))+'. The braking residual helps, but the unresolved displacement deficit is substantial. No optical feedback or end-of-trial alignment is used to hide it.')
p('The matched yaw addition changes overall validation error by roughly a tenth of a millimeter; its training-fold path score is worse than braking alone. The smoother supplies no clear further gain at matched strengths. These differences do not demonstrate statistical significance or support millimeter accuracy.')
p('Read the following seven overview sheets to compare all accepted recordings, including regressions. Four selected diagnostic pages show the major braking and slalom cases in detail. The preserved original atlas remains complete.')
title('Mounting update / evidence needed next')
p('User confirmation: both wheel IMUs are mounted off-axis and face outward; the center IMU faces backward. This confirms qualitative placement and mirrored wheel sides. It does not determine the exact local X/Y/Z rotations or measured three-dimensional lever arms. The configured wheel offset remains 0.04 m pending measurement.')
p('Actual acquisition remains +/-2 g and +/-2000 degrees/s. To verify conversion, retain the actual firmware and CSV receiver/packing code and record simultaneous library readings and stored values during known static and rotational conditions. Do not infer a different range from the resting integer norm.')
p('Before claiming much lower physical error, validate the initial heading convention using an independently identifiable front marker, measure mounting vectors and reference uncertainty, and collect deliberate braking/slip conditions with reliable timing and pretrial stationary periods.')
p('Current evidence favors keeping the existing stack and adding a bounded braking mechanism where participant evaluation supports it. The independently fitted simpler branch is a negative control. Neither a full multi-IMU INS nor a calibrated displacement-uncertainty filter has yet been established by these experiments.')
p('Sources: outputs_controlled_motion_v25/, outputs_controlled_refit_v26/, outputs_matched_motion_v27/, outputs_best_base_braking_v28/, research_docs/controlled-motion-update.md. All contain train-fold selection evidence and versioned comparison artifacts.','TinyX')
def foot(canvas,doc):
    canvas.setFont('Helvetica',8);canvas.setFillColor(colors.HexColor('#536d7c'));canvas.drawString(60,35,'4 October update | Exploratory validation | No new test access');canvas.drawRightString(535,35,str(doc.page))
SimpleDocTemplate(str(TMP/'update_narrative.pdf'),pagesize=A4,leftMargin=60,rightMargin=60,topMargin=55,bottomMargin=60).build(story,onFirstPage=foot,onLaterPages=foot)
plots=[]
for cond in ('10x5','AR','CR','OS','PS','SL','ST'):
    if plots:plots.append(PageBreak())
    plots.append(Paragraph(cond+' / controlled trajectory comparison',styles['Heading1']))
    im=Image(str(OUT/(cond+'_all.png')));scale=min(745/im.imageWidth,440/im.imageHeight);im.drawWidth=im.imageWidth*scale;im.drawHeight=im.imageHeight*scale;plots.append(im)
    plots.append(Paragraph('Black observed reference; blue-gray v21; green v25 braking; orange v28 comparator. All accepted recordings shown; identical axes within maneuver. RMSE order v21 / v25 / v28.',styles['TinyX']))
for id in ['2026-09-25__PS__PS_Trial2_No.18','2026-09-25__SL__SL_Trial1_No.14','2026-09-25__SL__SL_Trial1_No.18','2026-09-24__AR__AR_Trial2_No.5']:
    plots.append(PageBreak());plots.append(Paragraph(id,styles['Heading2']));im=Image(str(OUT/'individual'/(id+'.png')));scale=min(745/im.imageWidth,440/im.imageHeight);im.drawWidth=im.imageWidth*scale;im.drawHeight=im.imageHeight*scale;plots.append(im)
    plots.append(Paragraph('No fitted rotation/scale or later reference resets. Blank error intervals represent unavailable observed reference. This diagnostic is not an error-based exclusion.',styles['TinyX']))
SimpleDocTemplate(str(TMP/'update_plots.pdf'),pagesize=landscape(A4),leftMargin=48,rightMargin=48,topMargin=25,bottomMargin=25).build(plots)
writer=PdfWriter();a=PdfReader(TMP/'update_narrative.pdf');b=PdfReader(TMP/'update_plots.pdf');writer.append(a);writer.append(b)
writer.add_outline_item('4 October controlled experiment update',0)
for j,cond in enumerate(('10x5','AR','CR','OS','PS','SL','ST')):writer.add_outline_item(cond+' new comparisons',len(a.pages)+j)
offset=len(writer.pages);original=ROOT/'output/pdf/trajectory_methodology_and_results.pdf';writer.append(original);writer.add_outline_item('Preserved 3 October methods and all 71 trajectories',offset)
writer.add_metadata({'/Title':'Wheelchair trajectory methodology and controlled experiment update - 4 October 2026','/Subject':'Complete 71-recording atlas and controlled braking/yaw/smoothing comparisons'})
final=ROOT/'output/pdf/trajectory_methodology_and_results_updated.pdf'
with final.open('wb') as f:writer.write(f)
check=PdfReader(final);assert len(check.pages)==len(a.pages)+len(b.pages)+93
summary=dict(pdf=str(final),pages=len(check.pages),update_pages=len(a.pages)+len(b.pages),original_atlas_pages=71,comparison_images=71,quiet_eligible=eligible,v28_choice=choice,v28_selection=s28,metrics=r25['summary'])
(OUT/'summary.json').write_text(json.dumps(summary,indent=2));print(json.dumps({k:v for k,v in summary.items() if k!='metrics'},indent=2),flush=True)
