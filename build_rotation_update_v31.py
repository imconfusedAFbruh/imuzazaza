"""Complete 71-case rebuilt gallery and self-contained rotation update PDF."""
from pathlib import Path
import csv,json,html,sys
from contextlib import nullcontext
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.backends.backend_pdf import PdfPages
from reportlab.platypus import SimpleDocTemplate,Paragraph,Table,TableStyle,Spacer,Image,PageBreak
from reportlab.lib.styles import getSampleStyleSheet,ParagraphStyle
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4,landscape
from pypdf import PdfReader,PdfWriter
from pipeline import ROOT,digest

OUT=ROOT/'outputs_rotation_review_v31';TMP=ROOT/'tmp/pdfs/rotation_v31';OUT.mkdir(exist_ok=True);TMP.mkdir(parents=True,exist_ok=True);(OUT/'individual').mkdir(exist_ok=True)
P=ROOT/'outputs_directional_pivot_v31';OLD=ROOT/'outputs_trajectory_best_v21';CONTROL=ROOT/'outputs_controlled_motion_v25'
def csvrows(path):return list(csv.DictReader(path.open(newline='',encoding='utf-8')))
trials=csvrows(P/'selected_trials.csv');tables={key:{r['id']:r for r in csvrows(path)} for key,path in [('v21',OLD/'candidate_trials.csv'),('v25',CONTROL/'selected_trials.csv'),('v31',P/'selected_trials.csv')]}
assert len(trials)==71 and all(set(tables['v31'])==set(t) for t in tables.values())
labels=['Original v21','Braking v25','Directional pivot v31'];linecolors=['#8492a6','#1d8876','#d65d24'];alltrials=[]
reuse_atlas='--reuse-atlas' in sys.argv
if reuse_atlas and not (TMP/'atlas.pdf').is_file():raise RuntimeError('Missing cached atlas')
with (nullcontext() if reuse_atlas else PdfPages(TMP/'atlas.pdf')) as pdf:
    for row in trials:
        id=row['id']
        with np.load(OLD/'trajectories'/(id+'.npz')) as z:old=dict(z)
        with np.load(CONTROL/'selected/trajectories'/(id+'.npz')) as z:control=dict(z)
        with np.load(P/'selected/trajectories'/(id+'.npz')) as z:new=dict(z)
        assert np.array_equal(new['reference_valid'],old['reference_valid']) and np.array_equal(new['reference_xy'],control['reference_xy'],equal_nan=True)
        origin=new['reference_xy'][0];truth=new['reference_xy']-origin;truth[~new['reference_valid']]=np.nan
        paths=[old['model_2_xy_m']-origin,control['xy']-origin,new['xy']-origin];headings=[old['model_2_heading_rad'],control['heading'],new['heading']]
        if reuse_atlas:
            scores=[float(tables[k][id]['position_rmse_m'])*1000 for k in ('v21','v25','v31')]
            alltrials.append(dict(row=row,truth=truth,paths=paths,scores=scores,new=new));continue
        fig,axes=plt.subplots(1,3,figsize=(15,4.5),layout='constrained');axes[0].plot(*truth.T,color='black',label='Observed reference',lw=1.5)
        for label,color,xy,h in zip(labels,linecolors,paths,headings):
            axes[0].plot(*xy.T,color=color,lw=1.2,label=label);err=np.linalg.norm(xy-(new['reference_xy']-origin),axis=1)*1000;err[~new['reference_valid']]=np.nan
            angle=np.rad2deg(np.arctan2(np.sin(h-new['reference_heading']),np.cos(h-new['reference_heading'])));angle[~new['reference_valid']]=np.nan
            axes[1].plot(new['t'],err,color=color,lw=1);axes[2].plot(new['t'],angle,color=color,lw=1)
        axes[0].set_aspect('equal',adjustable='datalim');axes[0].legend(fontsize=7);axes[0].set(xlabel='X from initial position (m)',ylabel='Y (m)',title='Trajectory; equal physical aspect')
        axes[1].set(xlabel='Time (s)',ylabel='Position error (mm)',title='Observed position error');axes[2].set(xlabel='Time (s)',ylabel='Heading error (degrees)',title='Wrapped heading error')
        for ax in axes:ax.grid(alpha=.2)
        scores=[float(tables[k][id]['position_rmse_m'])*1000 for k in ('v21','v25','v31')]
        fig.suptitle(id+' | v21 / v25 / v31 RMSE: '+' / '.join(f'{v:.1f}' for v in scores)+' mm',fontsize=10)
        fig.savefig(OUT/'individual'/(id+'.png'),dpi=150);pdf.savefig(fig);plt.close(fig);alltrials.append(dict(row=row,truth=truth,paths=paths,scores=scores,new=new))
        if len(alltrials)%20==0:print('Rebuilt',len(alltrials),flush=True)
for cond in ('10x5','AR','CR','OS','PS','SL','ST'):
    ts=[t for t in alltrials if t['row']['condition']==cond];positions=np.concatenate([p for t in ts for p in [t['truth'],*t['paths']]])
    lo=np.nanmin(positions,0);hi=np.nanmax(positions,0);pad=np.maximum(.15,(hi-lo)*.06);lo-=pad;hi+=pad
    fig,axes=plt.subplots(4,3,figsize=(16,6.5 if cond in ('OS','PS','ST') else 13),layout='constrained');handles=None
    for i,person in enumerate(('No.5','No.10','No.14','No.18')):
        for j in range(3):
            ax=axes[i,j];trial=next((t for t in ts if t['row']['participant']==person and f'_Trial{j+1}_' in t['row']['id']),None)
            if trial is None:ax.text(.5,.5,'No accepted recording\nExisting reference/sync QC',ha='center',va='center',transform=ax.transAxes);ax.set_axis_off();continue
            ax.plot(*trial['truth'].T,color='black',lw=1.5,label='Observed reference')
            for label,color,xy in zip(labels,linecolors,trial['paths']):ax.plot(*xy.T,color=color,lw=1.1,label=label)
            ax.set(xlim=(lo[0],hi[0]),ylim=(lo[1],hi[1]),xlabel='X (m)',ylabel='Y (m)',title=person+f' Trial{j+1} | '+' / '.join(f'{v:.0f}' for v in trial['scores'])+' mm');ax.set_aspect('equal',adjustable='box');ax.grid(alpha=.2)
            if handles is None:handles=ax.get_legend_handles_labels()
    fig.get_layout_engine().set(rect=(0,.035,1,.88 if cond in ('OS','PS','ST') else .92));fig.legend(*handles,loc='upper center',bbox_to_anchor=(.5,.963 if cond in ('OS','PS','ST') else .976),ncol=4,fontsize=8)
    fig.suptitle(cond+' | all accepted validation recordings',y=.997);fig.supxlabel('RMSE order v21 / v25 / v31. Same axes within maneuver; reference gaps blank. No orientation amendment.',fontsize=9)
    fig.savefig(OUT/(cond+'_all.png'),dpi=145);plt.close(fig)

# Diagnostic sensitivity only: the alternative initial orientation is never selected.
caseids=['2026-09-24__AR__AR_Trial2_No.5','2026-09-24__AR__AR_Trial3_No.5','2026-09-24__CR__CR_Trial3_No.5']
fig,axs=plt.subplots(1,2,figsize=(10,4.5),layout='constrained')
for ax,id in zip(axs,caseids[:2]):
    trial=next(t for t in alltrials if t['row']['id']==id);xy=trial['paths'][2];ax.plot(*trial['truth'].T,color='black',label='Observed reference');ax.plot(*xy.T,color='#d65d24',label='Official original starting pose');ax.plot(*(-xy).T,color='#a4468c',ls='--',label='Alternative pi starting pose: diagnostic only')
    ax.set_aspect('equal',adjustable='datalim');ax.set(title=id.split('__')[-1],xlabel='X (m)',ylabel='Y (m)');ax.grid(alpha=.2);ax.legend(fontsize=7)
fig.suptitle('Initial-orientation sensitivity: not a reference correction',fontsize=12);fig.savefig(OUT/'orientation_sensitivity.png',dpi=155);plt.close(fig)
run=json.loads((P/'run.json').read_text());selection=json.loads((P/'selection.json').read_text())['selected'];current=run['summary']['selected']['equal_participant_mean_position_rmse_m']*1000
case_table=[['Recording','Original v21 mm','Braking v25 mm','New v31 mm']]+[[id.split('__')[-1]]+[f"{1000*float(tables[k][id]['position_rmse_m']):.3f}" for k in ('v21','v25','v31')] for id in caseids]
text=['# Directional pivot build v31','',f'Overall equal-participant validation RMSE: {current:.6f}mm vs v25 106.309394mm. Original v21 remains102.585179mm; the new model does not beat its overall minimum. Reused validation exploratory, no test data.', '', f'Selected on training folds: {json.dumps(selection)}', '', '| Recording | v21 mm | v25 mm | v31 mm |','|---|---:|---:|---:|']+['| '+' | '.join(r)+' |' for r in case_table[1:]]
text += ['', 'All473 accepted training recordings are represented in the inherited full-training model: 266 earlier recordings and207 Sept24/25 training-person recordings. New pivot strengths selected on three four-person training folds, then applied to the existing all473 fit. No.5 is validation, never used for fitting. New guard also limits each held participant/maneuver cell regression to5%. Inherited calibration/neural weights previously saw innerfold training people; conditional selection, not independently refitted whole neural stack.', '', 'Mechanism: raw-calibrated wheel velocities determine a continuous counterrotation gate, attenuated at low yaw. For positive predicted yaw, blend model forward velocity halfway toward wheel mean; for negative yaw use no additional blend. Lateral and yaw stay exactlyv25. No condition, participant or recording ID enters inference. No ideal-circle forcing. No automatic heading swap.', '', 'User confirmed no independent video/QTM evidence for AR2/AR3 marker identity. Their physical-front ambiguity remains unresolved. Preserve original reference/starting orientation, retain these trials and their official scores. Alternativepi visualization is diagnostic sensitivity only and never selected by reference error.', '', 'All71 reference-free inference arrays reproduce exactly. Original pipeline/learning/test locks and reference caches remain preserved. No test access. Rotational trial CR3 is preserved relative tov25 rather than cosmetically repaired.', '', 'Sources: rotation_motion_experiment_v29.py, pivot_channel_selection_v30.py, directional_pivot_selection_v31.py, directional_pivot_inference_v31.py; versioned foldersoutputs_rotation_motion_v29/,outputs_pivot_channels_v30/,outputs_directional_pivot_v31/.']
(ROOT/'research_docs/directional-pivot-build-v31.md').write_text('\n'.join(text)+'\n',encoding='utf-8')
cards=''.join(f'<article data-key="{html.escape(t["row"]["id"].lower())}"><h3>{html.escape(t["row"]["id"])}</h3><img loading="lazy" src="individual/{html.escape(t["row"]["id"])}.png"></article>' for t in alltrials)
(OUT/'gallery.html').write_text('<!doctype html><meta charset="utf-8"><title>Rebuilt pivot trajectories</title><style>body{font:16px system-ui;margin:24px;background:#eef3f6}article{background:white;padding:16px;margin:20px 0}img{width:100%}input{padding:12px;width:80%}</style><h1>All 71 rebuilt trajectories</h1><p>Black observed reference; gray original v21; green braking v25; orange directional pivot v31. No orientation flips. AR2/AR3 side identity unresolved. Validation exploratory.</p><input id="q" placeholder="Filter participant or maneuver">'+cards+'<script>q.oninput=e=>document.querySelectorAll("article").forEach(a=>a.hidden=!a.dataset.key.includes(e.target.value.toLowerCase()))</script>',encoding='utf-8')

styles=getSampleStyleSheet();styles.add(ParagraphStyle(name='BodyX',fontName='Helvetica',fontSize=10,leading=15,spaceAfter=10));styles.add(ParagraphStyle(name='TinyX',fontName='Helvetica',fontSize=8,leading=11,spaceAfter=6));styles['Heading1'].fontSize=22;styles['Heading1'].leading=28;styles['Heading1'].textColor=colors.HexColor('#163e54');story=[]
def p(s,sty='BodyX'):story.append(Paragraph(s,styles[sty]))
def title(s):
    if story:story.append(PageBreak())
    p(s,'Heading1')
def table(data,widths):
    t=Table([[Paragraph(html.escape(str(x)),styles['TinyX']) for x in r] for r in data],colWidths=widths,repeatRows=1);t.setStyle(TableStyle([('BACKGROUND',(0,0),(-1,0),colors.HexColor('#dfedf4')),('VALIGN',(0,0),(-1,-1),'TOP'),('LINEBELOW',(0,0),(-1,-1),.3,colors.HexColor('#cbdce7')),('TOPPADDING',(0,0),(-1,-1),7),('BOTTOMPADDING',(0,0),(-1,-1),6)]));story.append(t);story.append(Spacer(1,12))
title('Rebuilt trajectories / directional pivot correction')
p('4 October 2026 | Methods, result history and all 71 accepted trajectories','Heading2')
table([['Model','Overall RMSE mm'],['Original v21 exploratory comparator','102.585'],['v25 braking control','106.309'],['v29 coupled pivot blend','104.949'],['v30 shared forward blend','104.423'],['v31 stricter directional selection',f'{current:.3f}']],[320,155])
p(f'<b>Measured change:</b> v31 improves the conservative braking control by {106.309394-current:.3f} mm ({100*(1-current/106.309394):.2f}%). It does not beat the original v21 overall minimum. Its purpose is a training-selected physical correction with an additional maneuver-cell regression guard, not a claim of perfect reconstruction.')
table(case_table,[190,95,95,95])
p('AR2 and AR3 improve but remain poor. CR3 retains its preceding v25 motion rather than accepting the deterioration caused by the shared blend. Its error remains meaningful relative to its small true midpoint path.')
p('No optical reference coordinates, initial heading or quality masks were changed. All 71 accepted recordings remain in the atlas. No test recordings were accessed.','TinyX')
title('Implementation and training scope')
p('The final parent uses all 473 accepted training recordings: 266 from earlier sessions and 207 from the twelve target training people. The validation participant No.5 is not among the fitting IDs. Training participants remain grouped across dates, and selection occurs before this candidate\'s validation comparison.')
p('Three disjoint four-person folds cover twelve target training people. Candidate directional blending strengths are 0, 0.25, 0.5, 0.75 and 1 for each yaw sign. Choose the lowest pooled equal-participant path RMSE subject to at most 5% regression for every participant, every participant-maneuver cell, and every participant versus the original ridge.')
p('Selected strengths: positive yaw 0.5; negative yaw 0.0. Worst training-person regression versus v25: 0.68%. Worst participant-maneuver cell: 4.94%. Worst participant versus original ridge: 2.23%. These are conditional correction folds: the inherited neural base and calibration previously saw the training-fold participants.')
p('Calibrated wheel speeds determine counterrotation intensity: 1 - abs(left + right)/(abs(left) + abs(right)), with a floor near zero motion. A continuous gate rises with counterrotation and yaw magnitude. During positive-yaw pivots, blend model forward speed halfway toward calibrated wheel mean. Preserve the lateral and yaw channels. Neither maneuver names nor participant IDs enter inference.')
p('The independent forward/lateral ablation showed that coupling the channels can improve AR while worsening CR. The final stricter selection is based on training data and yaw sign; it does not switch models using validation maneuver labels or errors. One global rule applies to all recordings.')
p('Replay from IMU-only inputs reproduces all 71 selected prediction arrays exactly. Existing initial optical pose, external clock alignment, reference masks and integration rules stay fixed. CSV units and full mounting rotations remain empirically calibrated/unverified.','TinyX')
title('What remains unresolved in the attached examples')
p('No.5 AR2/AR3 show opposite signed optical/wheel forward velocities with nearly matching yaw rates. Two exported axle markers identify a heading only if physical side identity is correct. They do not independently identify the wheelchair front. The user confirms no video/QTM/acquisition evidence is available to settle these cases.')
p('<b>Consequently, their initial orientation cannot be corrected defensibly from the available evidence.</b> A 180-degree change selected because it makes the evaluated path look better would use the reference to choose the reconstruction. The official output preserves the original heading and error. The sensitivity plot below displays the alternative starting pose solely to explain this ambiguity.')
im=Image(str(OUT/'orientation_sensitivity.png'));sc=min(475/im.imageWidth,260/im.imageHeight);im.drawWidth=im.imageWidth*sc;im.drawHeight=im.imageHeight*sc;story.append(im)
p('Diagnostic only: orange is the official original-pose trajectory; purple dashed is the same IMU motion with a pi-shifted starting heading. The alternative is not selected, not an amended reference, and not reported as an accuracy improvement.','TinyX')
p('CR3 is a genuine near-in-place turn, not a missing circular reference. Its midpoint should not be forced into a circle. The directional model preserves this recording relative to the v25 parent; the underlying residual error remains.')
from audit_freeze_report import append_audit
append_audit(story,p,title,table,styles)
title('Reading the rebuilt report')
p('The next section preserves the original 3 October methodology and development story (15 pages). Those original numerical results describe that prior stage. This update supplies the current rotation experiments and limitations. Seven new maneuver overview sheets and a complete new 71-page comparison atlas follow.')
p('Each individual page shows the observed reference, original v21, braking v25 and directional pivot v31. Gray: v21; green: v25; orange: v31. Position and wrapped heading errors use camera-observed frames only. Reference gaps remain blank and never reset reconstruction.')
p('The original v21 remains the lower-error exploratory comparator overall. v31 is the stricter rotation-aware conservative candidate for a future separately frozen comparison. Repeated validation inspection prevents these values from being treated as a new blind test. Unknown physical-front identity and sensor conversion still prevent an absolute millimeter-accuracy claim.')
p('Versioned sources and all rejected candidates: outputs_rotation_motion_v29/, outputs_pivot_channels_v30/, outputs_directional_pivot_v31/. IMU-only loader: directional_pivot_inference_v31.load_directional_pivot(). Complete gallery: outputs_rotation_review_v31/gallery.html.','TinyX')
def footer(can,doc):can.setFont('Helvetica',8);can.drawString(60,35,'Directional pivot update | Exploratory validation | Original reference preserved');can.drawRightString(535,35,str(doc.page))
SimpleDocTemplate(str(TMP/'narrative.pdf'),pagesize=A4,leftMargin=60,rightMargin=60,topMargin=55,bottomMargin=60).build(story,onFirstPage=footer,onLaterPages=footer)
over=[]
for cond in ('10x5','AR','CR','OS','PS','SL','ST'):
    if over:over.append(PageBreak())
    over.append(Paragraph(cond+' / all accepted validation trajectories',styles['Heading1']));im=Image(str(OUT/(cond+'_all.png')));sc=min(745/im.imageWidth,440/im.imageHeight);im.drawWidth=im.imageWidth*sc;im.drawHeight=im.imageHeight*sc;over.append(im);over.append(Paragraph('Black observed reference; gray v21; green v25; orange v31. Same physical scale within maneuver. Missing panels retain existing QC status. No orientation/reference amendment.',styles['TinyX']))
SimpleDocTemplate(str(TMP/'overviews.pdf'),pagesize=landscape(A4),leftMargin=48,rightMargin=48,topMargin=25,bottomMargin=25).build(over)
writer=PdfWriter();n=PdfReader(TMP/'narrative.pdf');writer.append(n);writer.add_outline_item('4 October directional pivot update',0)
writer.append(ROOT/'output/pdf/trajectory_methodology_and_results.pdf',pages=(0,15));writer.add_outline_item('Preserved original methodology and experiment story',len(n.pages))
overview_start=len(writer.pages);writer.append(TMP/'overviews.pdf')
for j,c in enumerate(('10x5','AR','CR','OS','PS','SL','ST')):writer.add_outline_item(c+' rebuilt overview',overview_start+j)
start=len(writer.pages);atlas=PdfReader(TMP/'atlas.pdf');assert len(atlas.pages)==71;writer.append(atlas);parent=writer.add_outline_item('All 71 rebuilt trajectories',start)
for j,r in enumerate(trials):writer.add_outline_item(r['id'],start+j,parent=parent)
writer.add_metadata({'/Title':'Wheelchair trajectory methodology and directional pivot reconstruction','/Subject':'All 71 accepted recordings; original reference preserved; unresolved direction ambiguity disclosed'})
final=ROOT/'output/pdf/trajectory_directional_pivot_report.pdf'
with final.open('wb') as f:writer.write(f)
summary=dict(pdf=str(final),pages=len(PdfReader(final).pages),atlas_pages=71,overall_rmse_mm=current,selected=selection,reference_amended=False,case_table=case_table,inference_replay_max_difference=0.,test_evaluated=False)
(OUT/'summary.json').write_text(json.dumps(summary,indent=2));(OUT/'artifact_manifest.json').write_text(json.dumps(dict(sha256={str(p.relative_to(OUT)):digest(p) for p in OUT.rglob('*') if p.is_file() and p.name!='artifact_manifest.json'},pdf_sha256=digest(final)),indent=2));print(json.dumps(summary,indent=2),flush=True)
