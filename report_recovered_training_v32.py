"""Plot every validation result and write an auditable retraining PDF."""
from pathlib import Path
import csv,json,hashlib,math,sys
from contextlib import nullcontext
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.backends.backend_pdf import PdfPages
from reportlab.platypus import SimpleDocTemplate,Paragraph,Spacer,Table,TableStyle,PageBreak,Image
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from pypdf import PdfReader,PdfWriter

ROOT=Path(__file__).resolve().parent;OUT=ROOT/'outputs_recovered_training_v32';FIG=OUT/'figures';FIG.mkdir(exist_ok=True)
TMP=ROOT/'tmp/pdfs/recovered_training_v32';TMP.mkdir(parents=True,exist_ok=True)
run=json.loads((OUT/'run.json').read_text());selection=run['selected']['mode'];summaries=run['summary'];names=['original_v21','stored_endpoints','stored_endpoints_and_rates']
labels={'original_v21':'Original v21','stored_endpoints':'Stored endpoints refit','stored_endpoints_and_rates':'Stored endpoints + rates refit'}
# If training selection keeps the original, show the better training-fold refit as a comparator,
# with its experimental status stated. Never choose from validation error.
fold=json.loads((OUT/'selection.json').read_text());refit=min([q for q in fold['candidates'] if q['mode']!='original_v21'],key=lambda q:q['score'])['mode']
if selection!='original_v21':refit=selection
rows={name:list(csv.DictReader((OUT/(name+'_trials.csv')).open(newline=''))) for name in names};scores={name:{r['id']:float(r['position_rmse_m'])*1000 for r in rows[name]} for name in names}
trials=[]
for r in rows['original_v21']:
    with np.load(OUT/'trajectories'/(r['id']+'.npz')) as z:d={k:z[k] for k in z.files}
    trials.append(dict(row=r,data=d))

def paths(ax,t,legend=False):
    d=t['data'];origin=d['reference_xy_m'][0];observed=d['reference_xy_m']-origin;observed[~d['reference_valid']]=np.nan
    ax.plot(*observed.T,color='#171717',lw=1.5,label='Camera-observed reference')
    pr=d['stored_processed_valid'];bridge=pr|np.r_[False,pr[:-1]]|np.r_[pr[1:],False];stored=d['stored_reference_xy_m']-origin;stored[~(bridge&d['stored_reference_valid'])]=np.nan
    ax.plot(*stored.T,color='#8e6c32',ls=':',lw=1.4,label='Stored processed reference (display)')
    for name,color,ls in [('original_v21','#8c97a5','--'),(refit,'#d45127','-')]:
        ax.plot(*(d[name+'_xy_m']-origin).T,color=color,ls=ls,lw=1.25,label=labels[name])
    ax.set_aspect('equal',adjustable='datalim');ax.grid(alpha=.2);ax.set(xlabel='X from initial position (m)',ylabel='Y (m)')
    if legend:ax.legend(fontsize=7)

with (nullcontext(None) if '--reuse-individual' in sys.argv else PdfPages(TMP/'trajectory_pages.pdf')) as pdf:
    for t in ([] if '--reuse-individual' in sys.argv else trials):
        r=t['row'];d=t['data'];fig,axs=plt.subplots(1,3,figsize=(15,4.8),layout='constrained');paths(axs[0],t,True);axs[0].set_title('Trajectory; equal physical scale')
        for name,col in [('original_v21','#8c97a5'),(refit,'#d45127')]:
            mask=d['reference_valid']&np.isfinite(d[name+'_xy_m']).all(1);err=np.linalg.norm(d[name+'_xy_m']-d['reference_xy_m'],axis=1)*1000;err[~mask]=np.nan
            dh=d[name+'_heading_rad']-d['reference_heading_rad'];he=np.rad2deg(np.arctan2(np.sin(dh),np.cos(dh)));he[~mask]=np.nan
            axs[1].plot(d['time_s'],err,color=col,lw=1.1);axs[2].plot(d['time_s'],he,color=col,lw=1.1)
        axs[1].set(xlabel='Time (s)',ylabel='Position error (mm)',title='Unchanged observed score frames');axs[2].set(xlabel='Time (s)',ylabel='Heading error (degrees)',title='Wrapped heading error')
        for ax in axs[1:]:ax.grid(alpha=.2)
        fig.suptitle(r['id']+' | original '+f"{scores['original_v21'][r['id']]:.1f}"+' -> refit '+f"{scores[refit][r['id']]:.1f}"+' mm',fontsize=11)
        fig.savefig(FIG/(r['id']+'.png'),dpi=140);pdf.savefig(fig);plt.close(fig)

for condition in sorted({t['row']['condition'] for t in trials}):
    subset=[t for t in trials if t['row']['condition']==condition];fig,axs=plt.subplots(math.ceil(len(subset)/3),3,figsize=(15,3.8*math.ceil(len(subset)/3)),layout='constrained',squeeze=False)
    for ax,t in zip(axs.flat,subset):
        paths(ax,t);r=t['row'];trial=r['id'].split('_Trial')[1].split('_')[0];ax.set_title(r['participant']+' / trial '+trial+' | '+f"{scores['original_v21'][r['id']]:.0f} -> {scores[refit][r['id']]:.0f} mm",fontsize=10)
    for ax in list(axs.flat)[len(subset):]:ax.set_axis_off()
    h,l=axs.flat[0].get_legend_handles_labels();height=fig.get_size_inches()[1];fig.legend(h,l,loc='upper center',bbox_to_anchor=(.5,1-.35/height),ncol=2,fontsize=9);fig.get_layout_engine().set(rect=(0,0,1,1-.95/height));fig.suptitle(condition+' | all accepted validation trials',fontsize=15,y=1-.05/height)
    fig.savefig(FIG/(condition+'_all.png'),dpi=130);plt.close(fig)

fig,axs=plt.subplots(1,2,figsize=(12,4.2),layout='constrained');cols=['#8c97a5','#167c9a','#d45127'];values=[summaries[n]['equal_participant_mean_position_rmse_m']*1000 for n in names]
axs[0].bar(range(3),values,color=cols);axs[0].set_xticks(range(3),['Original v21','Endpoints','Endpoints + rates']);axs[0].set(ylabel='Equal-participant mean trajectory RMSE (mm)',title='All 71 validation trials');axs[0].set_ylim(0,max(values)*1.18)
for i,v in enumerate(values):axs[0].text(i,v+max(values)*.02,f'{v:.2f}',ha='center')
conditions=sorted({r['condition'] for r in rows['original_v21']});x=np.arange(len(conditions));width=.25
for j,name in enumerate(names):
    table={r['condition']:float(r['equal_participant_mean_position_rmse_m'])*1000 for r in csv.DictReader((OUT/(name+'_maneuvers.csv')).open(newline=''))}
    axs[1].bar(x+(j-1)*width,[table[c] for c in conditions],width,color=cols[j],label=labels[name])
axs[1].set_xticks(x,conditions);axs[1].set(ylabel='Equal-participant mean RMSE (mm)',title='Maneuver breakdown');axs[1].legend(fontsize=8);fig.savefig(FIG/'rmse_comparison.png',dpi=160);plt.close(fig)

styles=getSampleStyleSheet();story=[]
def para(s):story.extend([Paragraph(s,styles['BodyText']),Spacer(1,10)])
def table(rows,widths=None):
    cells=[[Paragraph(str(c),styles['BodyText']) for c in row] for row in rows];t=Table(cells,colWidths=widths,repeatRows=1);t.setStyle(TableStyle([('BACKGROUND',(0,0),(-1,0),colors.HexColor('#e5edf2')),('VALIGN',(0,0),(-1,-1),'TOP'),('LINEBELOW',(0,0),(-1,-1),.3,colors.HexColor('#c8d3da')),('TOPPADDING',(0,0),(-1,-1),6),('BOTTOMPADDING',(0,0),(-1,-1),6)]));story.extend([t,Spacer(1,12)])
story.extend([Paragraph('Recovered C3D supervision: retraining results',styles['Title']),Spacer(1,14)])
para('4 October 2026. A controlled retraining experiment for the planar wheel-hub midpoint. All 71 accepted validation trajectories are included, including failures. This is development evidence on repeatedly inspected validation participants; it is not a new independent test result.')
table([['Model','Position RMSE (mm)','Heading RMSE (deg)']]+[[labels[n],f"{summaries[n]['equal_participant_mean_position_rmse_m']*1000:.3f}",f"{summaries[n]['equal_participant_mean_heading_rmse_deg']:.3f}"] for n in names],[260,125,125])
para('Primary position result is the arithmetic mean of per-participant mean trial RMSE across four participants, with each trial using exactly the frozen directly observed reference frames. It is not pooled frame RMSE. No post-hoc trajectory rotation, translation, scaling or optical updates are fitted.')
story.append(Image(str(FIG/'rmse_comparison.png'),width=510,height=178.5));story.append(PageBreak())
story.extend([Paragraph('Method and data split',styles['Heading1']),Spacer(1,10)])
para('The previous recovery audit found stored XYZ in every native frame of the 71 accepted validation C3Ds. Some positions are flagged as processed rather than directly camera-observed. This experiment separately inspects all 473 accepted training C3Ds and uses those processed training values as weak supervision. Negative-residual/non-finite coordinates and geometry rejects remain unavailable. Original acquisitions are unchanged.')
para(f"Accepted training coverage: {run['training_trials']} trials ({run['earlier_training_trials']} earlier trials plus {run['target_training_trials']} target-date training trials). Training augmentation adds {run['added_training_endpoint_frames']:,} resampled endpoint frames and {run['added_training_rate_frames']:,} candidate rate-label frames. These counts are at the existing model time grid, not native C3D frames.")
table([['Partition','Target participants'],['Train','No.1, 3, 4, 6, 7, 8, 13, 15, 16, 17, 19, 20'],['Validation','No.5, 10, 14, 18; 71 accepted trials'],['Test','No.2, 9, 11, 12; signals not accessed in this experiment']],[90,420])
para('Every target participant stays in one partition across dates. Earlier sessions remain training only under the prior user-confirmed non-overlap assumption. Earlier trial-to-person mapping is incomplete, so older training balancing uses date groups. Accepted coverage is held fixed; this experiment does not reopen excluded recordings.')
para('The inherited physics/learned ridge base, sensor calibration, clock mapping, startup gravity/bias states and geometry thresholds remain fixed. The v21 physical-product forward/yaw interval correction is refitted: 75 contextual features plus 40 physical products, training-only clipping and normalization, alpha 0.1, endpoint weight 1.0 and gain 0.5. Lateral velocity remains the inherited ridge output. This is correction retraining, not end-to-end base-model retraining.')
para('Two controlled variants: (1) add geometry-accepted stored endpoint poses to the 1/3/5/10-second interval equations, retaining all original observed derivative labels; (2) additionally add filtered forward-speed/yaw labels from stored positions. Exact original observed positions, heading and rate labels are preserved. Derivative labels exclude segment boundaries. No new missing-coordinate interpolation is performed; existing clock-grid resampling is retained.')
story.append(PageBreak());story.extend([Paragraph('Selection and interpretation',styles['Heading1']),Spacer(1,10)])
table([['Conditional training fold candidate','RMSE (mm)','Worst-person ratio']]+[[labels[q['mode']],f"{q['score']*1000:.3f}",f"{q['worst_person_ratio']:.3f}"] for q in fold['candidates']],[300,100,110])
para('Inner participants are No.3, 8, 15 and 20. Selection considers the original model and the two fixed refits, requiring no more than 5% worst-participant regression against the original correction refitted on the same fitting subset. The inherited calibration/base previously saw these inner participants; this is a conditional correction comparison, not an independent whole-pipeline fold.')
para('Training-fold selection: <b>'+labels[selection]+'</b>. The trajectory atlas compares original v21 against <b>'+labels[refit]+'</b>, selected from training-fold scores before validation. If the original is retained, the refit is shown as an experimental comparator only. Both full-training refits and their validation outcomes are retained; no validation failures are dropped.')
base=values[0];delta=values[names.index(refit)]-base
para(f"The plotted refit changes primary validation RMSE by {delta:+.3f} mm ({delta/base*100:+.2f}%). Negative change means improvement. Restoring supervision can increase label coverage without improving trajectory accuracy; processed positions have uncertain accuracy, and heading ambiguity, calibration, slip and timing remain potential limitations. No millimeter-level accuracy claim follows from this experiment.")
para('Reference semantics: C3D positive residuals indicate measured data, zero residuals indicate processed data, and negative residuals indicate invalid data. Camera masks are optional and checked when populated. Source: https://www.c3d.org/HTML/Documents/gloss_residual.htm and https://www.c3d.org/HTML/Documents/3ddatafloatingpointformat.htm .')
para('The report stays planar: restored ST/SL optical XYZ can be viewed in the separate source-data report. No predicted Z or 3D accuracy is claimed. Outputs contain model coefficients, training recovery audit, frozen protocol/selection, all trial metrics and full prediction arrays.')
story.append(PageBreak());story.extend([Paragraph('Validation participant results',styles['Heading1']),Spacer(1,10)])
people={n:{r['participant']:float(r['mean_trial_position_rmse_m'])*1000 for r in csv.DictReader((OUT/(n+'_participants.csv')).open(newline=''))} for n in names}
table([['Participant','Original (mm)','Endpoints (mm)','Endpoints + rates (mm)']]+[[p,*[f'{people[n][p]:.3f}' for n in names]] for p in ['No.5','No.10','No.14','No.18']],[90,135,135,150])
para('The following overview pages show every accepted recording by maneuver. Each of the final 71 pages contains the trajectory, directly observed position error and wrapped heading error. Stored processed reference sections are displayed with a dotted style and excluded from all primary validation scores.')
def footer(c,d):
    c.setFont('Helvetica',8);c.drawString(42,24,'Recovered-supervision experiment v32 | exploratory validation');c.drawRightString(A4[0]-42,24,str(d.page))
SimpleDocTemplate(str(TMP/'methods.pdf'),pagesize=A4,rightMargin=42,leftMargin=42,topMargin=40,bottomMargin=40).build(story,onFirstPage=footer,onLaterPages=footer)
with PdfPages(TMP/'overview.pdf') as pdf:
    for condition in conditions:
        img=plt.imread(FIG/(condition+'_all.png'));fig=plt.figure(figsize=(11.7,8.3));ax=fig.add_axes([.015,.025,.97,.95]);ax.imshow(img);ax.axis('off');pdf.savefig(fig);plt.close(fig)
writer=PdfWriter()
for p in [TMP/'methods.pdf',TMP/'overview.pdf',TMP/'trajectory_pages.pdf']:writer.append(str(p))
pdf=ROOT/'output/pdf/recovered_training_results.pdf';writer.add_metadata({'/Title':'Recovered C3D supervision - retraining results and all 71 trajectories'});writer.write(str(pdf))
result=dict(pdf=str(pdf),pages=len(PdfReader(pdf).pages),methods_pages=len(PdfReader(TMP/'methods.pdf').pages),overview_pages=len(conditions),trajectory_pages=71,plotted_refit=refit,training_selected=selection,summary=summaries)
(OUT/'report_summary.json').write_text(json.dumps(result,indent=2));manifest=json.loads((OUT/'artifact_manifest.json').read_text());manifest['sha256'].update({str(p.relative_to(OUT)):hashlib.sha256(p.read_bytes()).hexdigest() for p in OUT.rglob('*') if p.is_file() and p.name!='artifact_manifest.json'});manifest['pdf_sha256']=hashlib.sha256(pdf.read_bytes()).hexdigest();(OUT/'artifact_manifest.json').write_text(json.dumps(manifest,indent=2));print(json.dumps(result,indent=2))
