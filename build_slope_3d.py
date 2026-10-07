"""Add measured 3-D slope views without model fitting or invented predicted Z."""
from pathlib import Path
import json,csv,hashlib,math,sys
import numpy as np
import ezc3d
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.ticker import MaxNLocator
from matplotlib.backends.backend_pdf import PdfPages
from reportlab.platypus import SimpleDocTemplate,Paragraph,Spacer,Table,TableStyle
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.lib import colors
from pypdf import PdfReader,PdfWriter

ROOT=Path(__file__).resolve().parent
subject='--subject' in sys.argv
restore='--processed' in sys.argv
if restore and not subject:raise RuntimeError('Recovery view is scoped to subject ST/SL')
OUT=ROOT/('outputs_subject_st_sl_3d_restored' if restore else 'outputs_subject_st_sl_3d' if subject else 'outputs_slope_3d');OUT.mkdir(exist_ok=True);(OUT/'trajectories').mkdir(exist_ok=True)
TMP=ROOT/('tmp/pdfs/subject_st_sl_3d_restored' if restore else 'tmp/pdfs/subject_st_sl_3d' if subject else 'tmp/pdfs/slope_3d');TMP.mkdir(parents=True,exist_ok=True)
source=ROOT/'outputs_observed_reference_v7';inventory={r['id']:r for r in json.loads((ROOT/'outputs_amended_v2/inventory.json').read_text())}
qc=list(csv.DictReader((source/'qc.csv').open(newline='',encoding='utf-8')))
rows=[r for r in qc if r['partition']=='validation' and r['status']=='accepted' and r['condition'] in ['ST','SL']] if subject else [r for r in qc if r['partition']=='train' and r['status']=='accepted' and 'slope' in r['condition'].lower()]
cfg=json.loads((source/'run.json').read_text())['settings'];parent_manifest=json.loads((source/'artifact_manifest.json').read_text())['sha256']
def digest(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def runs(mask):
    ix=np.flatnonzero(np.diff(np.r_[False,mask,False].astype(int)));return zip(ix[::2],ix[1::2])
def equal_axes(ax,points):
    lo=np.nanmin(points,axis=0);hi=np.nanmax(points,axis=0);extent=np.maximum(hi-lo,.05);center=(hi+lo)/2;pad=extent*.08
    ax.set_xlim(lo[0]-pad[0],hi[0]+pad[0]);ax.set_ylim(lo[1]-pad[1],hi[1]+pad[1]);ax.set_zlim(lo[2]-pad[2],hi[2]+pad[2]);ax.set_box_aspect(extent+2*pad)
def plot(ax,r,small=False):
    xyz=r['xyz'];observed=xyz.copy();observed[~r['valid']]=np.nan;ax.plot(*observed.T,color='#167c9a',lw=1.1 if small else 1.6,label='Camera-observed')
    if restore:
        filled=xyz.copy();pr=r['processed'];bridge=pr|np.r_[False,pr[:-1]]|np.r_[pr[1:],False];filled[~bridge]=np.nan;ax.plot(*filled.T,color='#bd742c',ls='--',lw=1.1 if small else 1.6,label='Stored processed')
    mask=np.isfinite(xyz).all(1);first,last=xyz[mask][[0,-1]]
    ax.scatter(*first,s=12 if small else 30,color='#197a47',marker='o',label='Start');ax.scatter(*last,s=14 if small else 30,color='#b34926',marker='D',label='End')
    equal_axes(ax,xyz);ax.view_init(elev=24,azim=-55);ax.set_xlabel('X (m)',labelpad=2)
    # Thin Y/Z ranges cannot accommodate default tick/label stacks at true aspect.
    ax.xaxis.set_major_locator(MaxNLocator(4));ax.set_yticks([]);ax.set_zticks([]);ax.set_ylabel('');ax.set_zlabel('')
    lo=np.nanmin(xyz,axis=0);hi=np.nanmax(xyz,axis=0)
    ax.text2D(.02,.02,f'Y [{lo[1]:.2f}, {hi[1]:.2f}] m | C3D Z [{lo[2]:.2f}, {hi[2]:.2f}] m',transform=ax.transAxes,fontsize=8 if small else 10)
    ax.tick_params(labelsize=7 if small else 9,pad=0);ax.set_title(r['row']['condition']+' / '+r['row']['participant'].replace('earlier:','')+' / trial '+str(r['row']['repetition']),fontsize=9 if small else 12,pad=5)

records=[];summaries=[];inputs={};inline=[]
for q in rows:
    row=inventory[q['id']];assert row['partition']==('validation' if subject else 'train')
    cache=source/'cache'/(row['id']+'.npz');metadata=cache.with_suffix('.json');meta=json.loads(metadata.read_text())
    for p in [cache,metadata]:
        if digest(p)!=parent_manifest[str(p.relative_to(source))]:raise RuntimeError('Changed development cache '+str(p))
    rawpath=ROOT/row['c3d'];rawhash=digest(rawpath)
    if rawhash!=meta['signature']['c3d_sha256']:raise RuntimeError('Changed source C3D')
    inputs[str(rawpath.relative_to(ROOT))]=rawhash;inputs[str(cache.relative_to(ROOT))]=digest(cache)
    with np.load(cache) as f:d=dict(f)
    c=ezc3d.c3d(str(rawpath));p=c['parameters']['POINT'];labels=[x.strip() for x in p['LABELS']['value']];ids=[labels.index(n) for n in ['L_FAL','R_FAL']]
    unit=p['UNITS']['value'][0].strip().lower();scale={'mm':.001,'cm':.01,'m':1}[unit]
    points=c['data']['points'][:3,ids,:].transpose(2,1,0)*scale;res=c['data']['meta_points']['residuals'][0,ids,:].T
    nativevalid=(res>0).all(1)&np.isfinite(points).all((1,2))&(np.linalg.norm(points,axis=2)>1e-8).all(1)
    masks=c['data']['meta_points'].get('camera_masks')
    if masks is not None:
        support=np.asarray(masks)[:,ids,:].any(0).T
        if support.any():nativevalid&=support.all(1)
    sep=np.linalg.norm(points[:,0]-points[:,1],axis=1);policy=cfg['reference_geometry']['setups'][row['setup']];allowed=np.zeros(len(points),bool)
    for band in policy['bands']:allowed|=(sep>=band['lower_m'])&(sep<=band['upper_m'])
    geometry=allowed&(np.abs(sep-np.median(sep[nativevalid]))<=policy['rigidity_tolerance_m']);nativevalid&=geometry
    nativeusable=(res>=0).all(1)&np.isfinite(points).all((1,2))&(np.linalg.norm(points,axis=2)>1e-8).all(1)&geometry
    hz=float(c['header']['points']['frame_rate']);native_t=np.arange(len(points))/hz;query=d['ref_t'];idx=np.clip(np.searchsorted(native_t,query),1,len(points)-1)
    valid=d['gt_valid']&d['imu_valid']&nativevalid[idx]&nativevalid[idx-1]&(query>=0)&(query<=native_t[-1])
    midpoint=points.mean(1);world=np.column_stack([np.interp(query,native_t,midpoint[:,j]) for j in range(3)])
    if not valid.any():raise RuntimeError('No observed XYZ '+row['id'])
    xy_diff=float(np.max(np.abs(world[valid,:2]-d['gt_xy'][valid])))
    if xy_diff>1e-7:raise RuntimeError('XYZ view disagrees with frozen XY reference '+row['id'])
    displayvalid=(nativeusable[idx]&nativeusable[idx-1]&d['imu_valid']&(query>=0)&(query<=native_t[-1])) if restore else valid
    processed=displayvalid&~valid;origin=world[np.flatnonzero(valid)[0]];xyz=world-origin;xyz[~displayvalid]=np.nan
    np.savez_compressed(OUT/'trajectories'/(row['id']+'.npz'),time_s=d['t'],reference_time_s=query,reference_xyz_m=world,reference_valid=valid,display_valid=displayvalid,processed_source_valid=processed,relative_xyz_m=xyz,origin_xyz_m=origin)
    r=dict(row=row,t=d['t'],xyz=xyz,valid=valid,processed=processed);records.append(r)
    zr=float(np.ptp(xyz[displayvalid,2]));summaries.append(dict(id=row['id'],condition=row['condition'],participant=row['participant'],partition=row['partition'],observed_frames=int(valid.sum()),processed_display_frames=int(processed.sum()),display_frames=int(displayvalid.sum()),reference_z_range_m=zr,xy_cache_max_difference_m=xy_diff,source_c3d=row['c3d']))
    # Preserve every provenance transition and unavailable gap during display sampling.
    spans=list(runs(displayvalid));budget=150;total=sum(b-a for a,b in spans);coords=[];times=[];obsflags=[]
    for a,b in spans:
        cuts=np.r_[a,a+np.flatnonzero(np.diff(valid[a:b].astype(int)))+1,b]
        for aa,bb in zip(cuts[:-1],cuts[1:]):
            n=min(bb-aa,max(2,round(budget*(bb-aa)/total)));ii=np.unique(np.linspace(aa,bb-1,n,dtype=int));coords.extend(np.round(xyz[ii],4).tolist());times.extend(np.round(d['t'][ii],3).tolist());obsflags.extend(valid[ii].tolist())
        coords.append(None);times.append(None);obsflags.append(False)
    inline.append(dict(id=row['id'],label=row['condition']+' / '+row['participant'].replace('earlier:','')+' / trial '+str(row['repetition']),condition=row['condition'],points=coords,times=times,observed=obsflags,n=int(valid.sum()),processed_n=int(processed.sum()),zrange=round(zr,4)))
    if len(records)%36==0:print('Measured XYZ',len(records),flush=True)

with (OUT/'slope_index.csv').open('w',newline='',encoding='utf-8') as f:
    w=csv.DictWriter(f,fieldnames=list(summaries[0]));w.writeheader();w.writerows(summaries)
inline.sort(key=lambda r:(r['condition'].lower(),r['label']))
fragment=(ROOT/'slope-3d-template.html').read_text(encoding='utf-8').replace('__SLOPE_DATA__',json.dumps(inline,separators=(',',':'),allow_nan=False))
if subject:
    fragment=fragment.replace('Measured slope trajectories in 3D','Subject ST / SL trajectories in 3D' if restore else 'Measured subject ST / SL trajectories in 3D').replace('training recordings','subject validation recordings').replace("r.condition==='SlopeF'","r.condition==='ST'")
visual=Path('C:/Users/poon1/.codex/visualizations/2026/10/02/01a0fdfe-26f7-7b80-9bc3-f59af6a526e3/slope-trajectories-3d.html');visual.parent.mkdir(parents=True,exist_ok=True);visual.write_text(fragment,encoding='utf-8')
if visual.stat().st_size>1_000_000:raise RuntimeError('Reduce inline data size')

conditions=sorted({r['row']['condition'] for r in records},key=str.lower);page_labels=[]
with PdfPages(TMP/'slope_views.pdf') as pdf:
    for condition in conditions:
        subset=sorted([r for r in records if r['row']['condition']==condition],key=lambda r:r['row']['repetition'])
        for start in range(0,len(subset),6):
            fig=plt.figure(figsize=(14,9));fig.subplots_adjust(left=.045,right=.96,bottom=.08,top=.88,wspace=.15,hspace=.3)
            for j,r in enumerate(subset[start:start+6]):ax=fig.add_subplot(2,3,j+1,projection='3d');plot(ax,r,True)
            fig.suptitle(condition+(' / source 3D paths / ' if restore else ' / measured 3D paths / ')+str(start+1)+'-'+str(min(start+6,len(subset)))+' of '+str(len(subset)),fontsize=16)
            fig.text(.5,.94,('Subject validation' if subject else 'Training')+' recordings; first observed midpoint origin; equal metric axis scaling in each panel',ha='center',fontsize=10)
            fig.text(.5,.025,('Blue=observed; orange dashed=stored processed C3D. Geometry failures remain blank. No new interpolation or accuracy claim.' if restore else 'Observed C3D XYZ only. Gaps blank. Green circle=start; orange diamond=end. No predicted height or 3D accuracy claim.'),ha='center',fontsize=10)
            name=condition+'_page_'+str(start//6+1);fig.savefig(OUT/(name+'.png'),dpi=125);pdf.savefig(fig);plt.close(fig);page_labels.append(name)
        print('3D views',condition,len(subset),flush=True)

hero=next(r for r in records if r['row']['condition']==('ST' if subject else 'SlopeF'));fig=plt.figure(figsize=(12,5),layout='constrained');ax=fig.add_subplot(1,2,1,projection='3d');plot(ax,hero);ax.legend(fontsize=8,loc='upper left')
ax=fig.add_subplot(1,2,2);zz=hero['xyz'][:,2].copy();zz[~hero['valid']]=np.nan;ax.plot(hero['t'],zz,color='#167c9a')
if restore:
    zz=hero['xyz'][:,2].copy();pr=hero['processed'];keep=pr|np.r_[False,pr[:-1]]|np.r_[pr[1:],False];zz[~keep]=np.nan;ax.plot(hero['t'],zz,color='#bd742c',ls='--')
ax.set(xlabel='Time from prepared start (s)',ylabel='C3D Z from first observed midpoint (m)',title='Source Z profile; processed sections dashed' if restore else 'Measured Z profile; gaps remain blank');ax.grid(alpha=.2)
fig.suptitle('Slope 3D reference / '+hero['row']['id'],fontsize=11);fig.savefig(OUT/'slope_3d_example.png',dpi=155);plt.close(fig)

styles=getSampleStyleSheet();story=[Paragraph(('Subject ST / SL trajectories' if subject else 'Slope trajectories')+' / measured 3D appendix',styles['Title']),Spacer(1,16),Paragraph('4 October 2026. Added to the frozen trajectory report without training a model or changing any existing score.',styles['BodyText']),Spacer(1,12)]
for text in [
    ('This appendix shows all 24 accepted subject-validation recordings in ST (12) and SL (12), from No.5, No.10, No.14 and No.18 across 24-25 September. The user confirms that ST is wheelchair ascent on a slope. This corrects the earlier SP-to-PS interpretation. These are the already exposed validation recordings from the existing report. The original 71 pages remain intact and no test recordings were opened.' if subject else 'The 144 quality-accepted slope recordings are earlier TRAINING data from 19 September, not additional held-out trials. The original 71 validation trajectory pages remain intact. No test recordings were opened.'),
    ('Full XYZ comes from the stored midpoint of L_FAL and R_FAL in C3D, in metres. Blue segments retain the unchanged observed mask; dashed orange restores stored processed coordinates for display. Frozen timing, initial pose and geometry gates are preserved. Positions on observed frames agree exactly with frozen reference XY. Processed coordinates are not independent observed truth and are not added to the scoring mask.' if restore else 'XYZ comes from the observed midpoint of L_FAL and R_FAL in C3D, with source units converted to metres. Positive residual and camera-support masks, existing training-derived geometry gates, frozen preparation times and observed-frame masks are preserved. XYZ views agree with frozen reference XY to within 0.0000001 m. Reference gaps remain blank.'),
    'Every plot uses the first observed midpoint as origin. Box proportions track the coordinate ranges to preserve equal physical scale. C3D Z is shown explicitly; the global gravity/up convention and absolute reference uncertainty still require verification. Two axle markers provide a 3D midpoint but do not independently resolve full chassis pitch or physical front.',
    'The current model outputs planar XY and yaw. These pages visualize optical reference XYZ only. Optical height has not been attached to model XY to create a false 3D prediction, and no new 3D RMSE or slope generalization result is claimed.',
    ('The next four sheets contain every accepted subject ST/SL path. The interactive view includes rotation, zoom and a separate Z profile; observed and processed sections are labeled separately. Full arrays are preserved in outputs_subject_st_sl_3d_restored/trajectories/.' if restore else 'The next four sheets contain every accepted subject ST/SL path, six per sheet. The accompanying interactive view offers recording selection, rotation, zoom, coordinate/time hover and a separate measured Z-versus-time panel. It replaces the earlier PS/SL view. Display data are rounded and subsampled within observed runs; full-resolution arrays are preserved in outputs_subject_st_sl_3d/trajectories/.' if subject else 'The next 25 sheets contain every accepted slope path, six per sheet where available. The accompanying interactive view offers recording selection, rotation, zoom and coordinate/time hover. Display data are rounded and subsampled within observed runs; full-resolution arrays are preserved in outputs_slope_3d/trajectories/.')]:
    story.extend([Paragraph(text,styles['BodyText']),Spacer(1,10)])
if restore:
    story.extend([Paragraph('Recovery audit: all 148,712 native frames across the accepted 71 validation C3Ds contain stored nonnegative-residual marker positions. 111,323 are directly observed pairs and 37,389 contain a processed marker. No coordinates were newly interpolated, no original C3D was modified, and frozen accuracy scores remain unchanged. Separate geometry flags reject 378 native pairs. Full XYZ/provenance CSV exports are in outputs_c3d_recovery/full_xyz_csv/. C3D residual conventions: https://www.c3d.org/HTML/Documents/gloss_residual.htm',styles['BodyText']),Spacer(1,10)])
data=[['Condition','Accepted '+('subject-validation' if subject else 'training')+' recordings']]+[[c,str(sum(r['row']['condition']==c for r in records))] for c in conditions]
table=Table(data,colWidths=[245,230]);table.setStyle(TableStyle([('BACKGROUND',(0,0),(-1,0),colors.HexColor('#e4eef4')),('LINEBELOW',(0,0),(-1,-1),.3,colors.HexColor('#d4dce2')),('TOPPADDING',(0,0),(-1,-1),7),('BOTTOMPADDING',(0,0),(-1,-1),7)]));story.append(table)
SimpleDocTemplate(str(TMP/'intro.pdf'),leftMargin=60,rightMargin=60,topMargin=50,bottomMargin=50).build(story)
base=ROOT/'output/pdf/trajectory_directional_pivot_report.pdf';writer=PdfWriter();writer.append(base);intro_start=len(writer.pages);writer.append(TMP/'intro.pdf');writer.add_outline_item(('Subject ST/SL' if subject else 'Slope')+' 3D reference appendix',intro_start);start=len(writer.pages);writer.append(TMP/'slope_views.pdf')
for j,label in enumerate(page_labels):writer.add_outline_item(label,start+j)
final=ROOT/('output/pdf/trajectory_report_with_subject_3d.pdf' if subject else 'output/pdf/trajectory_report_with_slope_3d.pdf');writer.add_metadata({'/Title':'Wheelchair trajectory report with measured 3D '+('subject ST/SL' if subject else 'slope')+' reference appendix'})
with final.open('wb') as f:writer.write(f)
summary=dict(slope_recordings=len(records),slope_view_pages=len(page_labels),total_pdf_pages=len(PdfReader(final).pages),partition='validation' if subject else 'train',training_only=not subject,stored_processed_display=restore,newly_interpolated_frames=0,model_retrained=False,predicted_z_available=False,test_accessed=False,inline_bytes=visual.stat().st_size,max_xy_cache_difference_m=max(r['xy_cache_max_difference_m'] for r in summaries),pdf=str(final),visual=str(visual),counts={c:sum(r['row']['condition']==c for r in records) for c in conditions})
(OUT/'summary.json').write_text(json.dumps(summary,indent=2));(OUT/'artifact_manifest.json').write_text(json.dumps(dict(source_sha256=inputs,base_pdf_sha256=digest(base),pdf_sha256=digest(final),visual_sha256=digest(visual),output_sha256={str(p.relative_to(OUT)):digest(p) for p in OUT.rglob('*') if p.is_file() and p.name!='artifact_manifest.json'}),indent=2));print(json.dumps(summary,indent=2),flush=True)
