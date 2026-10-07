from pathlib import Path
import csv, io, json, math
from xml.sax.saxutils import escape
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, Image, PageBreak
from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.enums import TA_LEFT
from reportlab.lib.pagesizes import A4
from pypdf import PdfReader, PdfWriter

ROOT=Path(__file__).resolve().parent
SRC=ROOT/'outputs_trajectory_best_v21'
TMP=ROOT/'tmp/pdfs'; TMP.mkdir(parents=True,exist_ok=True)
OUT=ROOT/'output/pdf'; OUT.mkdir(parents=True,exist_ok=True)
FINAL=OUT/'trajectory_methodology_and_results.pdf'
styles=getSampleStyleSheet()
styles.add(ParagraphStyle(name='Body',fontName='Helvetica',fontSize=10,leading=15,spaceAfter=10,textColor=colors.HexColor('#243447')))
styles.add(ParagraphStyle(name='SmallNote',fontName='Helvetica',fontSize=8,leading=11,spaceAfter=7,textColor=colors.HexColor('#526579')))
styles['Title'].fontSize=29; styles['Title'].leading=35; styles['Title'].textColor=colors.HexColor('#12344b')
styles['Heading1'].fontSize=21; styles['Heading1'].leading=27; styles['Heading1'].spaceAfter=16; styles['Heading1'].textColor=colors.HexColor('#12344b')
styles['Heading2'].fontSize=13; styles['Heading2'].spaceBefore=9; styles['Heading2'].spaceAfter=8
story=[]; chapters=[]
def p(t,style='Body'): story.append(Paragraph(t,styles[style]))
def title(t):
    if story: story.append(PageBreak())
    chapters.append(t); p(t,'Heading1')
def sub(t): p(t,'Heading2')
def table(rows,widths=None,small=False):
    data=[[Paragraph(escape(str(x)),styles['SmallNote' if small else 'Body']) for x in r] for r in rows]
    tb=Table(data,colWidths=widths,repeatRows=1,hAlign='LEFT')
    tb.setStyle(TableStyle([('BACKGROUND',(0,0),(-1,0),colors.HexColor('#e6eff4')),('VALIGN',(0,0),(-1,-1),'TOP'),('LINEBELOW',(0,0),(-1,0),.8,colors.HexColor('#7895a6')),('LINEBELOW',(0,1),(-1,-1),.25,colors.HexColor('#dce3e8')),('TOPPADDING',(0,0),(-1,-1),6),('BOTTOMPADDING',(0,0),(-1,-1),4)]))
    story.append(tb); story.append(Spacer(1,8))
def image(path,maxw=475,maxh=360):
    im=Image(str(path)); scale=min(maxw/im.imageWidth,maxh/im.imageHeight)
    im.drawWidth=im.imageWidth*scale; im.drawHeight=im.imageHeight*scale; story.append(im)
def rows(name):
    with (SRC/name).open(newline='',encoding='utf-8') as f:return list(csv.DictReader(f))
trials=rows('candidate_trials.csv'); ridge={r['id']:r for r in rows('ridge_trials.csv')}
assert len(trials)==71

p('Wheelchair trajectory reconstruction','Title')
p('Methodology, development story and complete accepted-recording atlas','Heading2')
story.append(Spacer(1,25))
table([['Current exploratory result','102.585 mm'],['Paired ridge control','116.899 mm'],['Relative reduction','12.24%'],['Validation evidence','71 recordings / 4 participants / 7 maneuvers'],['Conservative next-evaluation candidate','v24: 108.950 mm']],[275,200])
p('Prepared 3 October 2026. Target sessions: 24 and 25 September 2026. Primary target: the 2D path of the midpoint between the wheelchair wheel hubs.')
p('<b>Reading this report.</b> The story explains why reference validity, physical features and interval supervision mattered more than simply training longer. The atlas contains all 71 recordings accepted by the existing quality rules, including cases with substantial reconstruction errors. Accepted does not mean accurately reconstructed.')
p('<b>Evidence status.</b> These are repeatedly inspected development-validation results. They are not a new blind final test, and approximately 100 mm error is not millimeter-level accuracy. Historical test exposure and unresolved calibration limits are disclosed in the methods.')
p('Source: sealed v21 prediction caches, metric tables, the development journal and research findings in this workspace. Existing per-recording plots are appended without rescaling or re-integrating predictions.','SmallNote')

title('1 / Study question and data')
p('Can three wheelchair-mounted IMUs reconstruct a maneuvering wheelchair\'s planar hub-midpoint trajectory from one optical starting pose? The objective is accurate position over the full recording, rather than a low instantaneous rate error alone.')
sub('Participants and recording coverage')
p('The user confirmed that target identifiers No.1-20 represent 20 distinct people. No.1-10 belong to September 24 and No.11-20 to September 25. The planned validation design has four people, seven maneuvers and three repetitions: 84 recordings. Quality control accepts 71: 12 each for 10x5, AR, CR, SL and ST; eight PS; and three OS from only two people. Thirteen planned repetitions are absent because of existing synchronization or reference-quality failures.')
table([['Partition','Target participants'],['Training (12)','No.1, 3, 4, 6, 7, 8, 13, 15, 16, 17, 19, 20'],['Validation (4)','No.5, 10, 14, 18'],['Test (4)','No.2, 9, 11, 12']],[110,365])
p('Split participants before making windows. Every recording from one participant follows that assignment across dates. Earlier sessions are training-only; their identities are not fully mapped in files, and non-overlap with target people rests on the user\'s confirmation. Under the corrected current reference protocol, 473 training and 71 validation recordings are accepted.')
sub('What the reference represents')
p('Qualisys C3D markers L_FAL and R_FAL define the optical pair used to construct the hub midpoint and planar heading. Configured outboard marker offsets and axle geometry support the reconstruction. Full mounting vectors, the verified global coordinate convention and independent absolute reference uncertainty remain missing. Accordingly, this report describes operational XY error against this reference, rather than verified absolute physical accuracy.')
p('Maneuver codes are retained from the files; SL is slalom. Codes whose expanded experimental definitions are not established here are not assigned invented meanings.','SmallNote')

title('2 / Geometry, units and physical baseline')
table([['Quantity','Available specification'],['Wheel radius / hub spacing','0.30 m / 0.52 m'],['Wheel IMU / outboard reflector offset','0.04 m / 0.066 m'],['Camber / nominal gravity','0 / 9.80665 m/s2'],['Hardware','XIAO nRF52840 Sense; LSM6DS3TR-C'],['Acquisition ranges supplied by user','Acceleration +/-2 g; gyro +/-2000 degrees/s'],['CSV conversion status','Integer encoding and actual SI scaling unverified']],[200,275])
p('The basic rolling model uses wheel angular speed to estimate forward velocity and chassis gyro motion to estimate yaw. For ideal differential rolling, v = R(wL + wR)/2 and yaw rate = R(wR - wL)/L. Acquisition-dependent axes, signs, scale and bias are established from training data. The later model uses the frozen empirical wheel/chassis predictor rather than treating the ideal equations as an exact slip-free description.')
p('The documentation names Seeed_Arduino_LSM6DS3 and describes nominal g and degrees/s library readings. It also explicitly marks float encoding and units as unverified. The user\'s actual +/-2 g acquisition statement takes precedence over the older 16 g default configuration. A resting norm near 8200 CSV counts does not identify the range or conversion by itself.')
p('Offsets create rotating lever-arm effects. They should be handled with verified 3D mounting and physical equations once available. Camera calibration residuals, including the example 0.610867, are not proof of absolute millimeter positional accuracy. Unknown encoding also prevents a defensible SI saturation analysis.')
sub('Why begin with physics?')
p('Wheel motion supplies strong geometric information, while gyro yaw controls how velocity accumulates into position. A learned residual can correct systematic departures, but cannot manufacture absolute position observations. Wheel-INS2 supports attention to multiple mounting angles and rotating lever arms [1]; its traveled-distance drift metric is not directly comparable to this study\'s path RMSE.')

title('3 / Clock alignment and optical validity')
sub('Time is a prerequisite')
p('Timing is derived from IMU device timestamps and C3D metadata. Raw IMU timing is approximately 102.4 Hz; model caches use 100 Hz, and the inspected target C3Ds use 100 Hz. Older nominal 20 Hz ground-truth configuration must not be mistaken for actual target metadata.')
p('The offline benchmark uses corresponding motion peaks in IMU and C3D signals for synchronization, with a fixed fallback and rejection procedure. The current production correlation gate is 0.6. All compared current models use the same fixed v5 clocks. External optical clock alignment is part of this evaluation assumption; it is not an IMU-only autonomous synchronization demonstration.')
sub('The reference correction that changed the story')
p('Earlier reading accepted nonnegative C3D residuals, including zero-residual processed or generated leading coordinates. These could produce a false starting heading. The corrected v7 protocol requires positive residuals and camera support when the export populates camera masks. Across 646 readable training/validation C3Ds, zero residual coincided with no camera support.')
table([['Same weights and clocks; revised reference/initial pose','Position RMSE'],['Old initialization on the same observed frames','373.243 mm'],['First genuinely observed initialization','118.490 mm'],['OS: before / after','1574.721 / 109.488 mm'],['PS: before / after','1920.428 / 193.911 mm']],[345,130])
p('<b>This was a reference and initialization protocol correction.</b> It must be separated from subsequent learned-model improvements. The old and corrected benchmarks are not interchangeable.')
p('Optical derivatives are filtered within valid observation runs (configured 6 Hz low-pass, order 2) with boundary masks. Missing optical coordinates are not invented as evaluation labels. Reconstruction continues through optical gaps and is not reset when markers return.')

title('4 / Reconstruction, supervision and metrics')
sub('One starting pose, then IMU motion')
p('The initial position and heading come from the first synchronized camera-observed pose. Afterwards, the model predicts forward velocity v, lateral velocity l and yaw rate w from IMU information. There is no later optical feedback, fitted trajectory rotation or scale, cone snapping or template loop closure.')
p('For each valid time interval, average the adjacent velocities and yaw rate. Set heading_next = heading + dt * average(w). Rotate [average(v), average(l)] by the midpoint heading and add dt times that vector to XY. This midpoint/trapezoidal integration couples yaw error to accumulated positional error. Reconstruction stops at invalid IMU gaps rather than hiding a missing interval.')
sub('Current v21 correction')
p('The inherited frozen predictor supplies motion. The residual model corrects forward velocity and yaw; the lateral channel stays exactly the ridge control. It starts with 75 gravity/temporal features and adds eight kinematic products over five contexts (-0.5, -0.25, 0, 0.25, 0.5 s), producing 115 features. Products include forward-yaw interaction, squared terms, wheel mean/difference interactions and acceleration/gyro norm terms.')
p('Training-only product clipping uses 0.001/0.999 bounds. Feature normalization, correction weights and residual caps are fitted on training data. The selected v21 setting uses alpha 0.1, endpoint weight 1 and correction gain 0.5. The inherited base uses 1.28 s of future IMU context: this is an offline method, not a demonstrated causal real-time estimator.')
sub('Primary metric')
p('Trial RMSE = sqrt(mean(||XY_prediction - XY_reference|| squared)), evaluated only at camera-observed reference frames. Average trial RMSE within each participant, then average the four participant means equally. This is neither pooled-frame RMSE nor coordinate-wise RMSE. Supporting diagnostics include wrapped heading RMSE, endpoint drift and relative errors over 1/5/10 m.')
p('Training supervision combines group-balanced point/rate terms with observed relative SE2 endpoint constraints at 1/3/5/10 s. First-order interval Jacobians account for how forward and yaw corrections alter displacement. Endpoint pairs can span optical gaps without inventing intermediate reference coordinates; hidden full-turn counts across those gaps remain unidentified.')

title('5 / Selection and leakage protections')
p('Calibration, normalization and model parameters are fitted with training recordings. New correction selection initially uses an inner four-person training fold: No.3, 8, 15 and 20. Those participants are excluded from fitting the new normalization, nonlinear bounds and correction parameters. The selected correction is then refitted on all 473 accepted training recordings before the 71-recording validation comparison.')
p('<b>Conditional selection limitation.</b> The inherited pretrained base and calibration previously saw those training people. This is an independent split for the new correction, not independent cross-validation of the entire pipeline.')
sub('The broader guard in v24')
table([['Training fold','Participants'],['A','No.3, 8, 15, 20'],['B','No.1, 4, 13, 16'],['C','No.6, 7, 17, 19']],[100,375])
p('v24 refits the correction separately over three disjoint folds covering all twelve target training people. Earlier unmapped training recordings remain in each fit. A common maximum 5% participant regression guard is applied across all twelve people. The alpha 0.3 / endpoint weight 1 / gain 0.25 choice passes with worst regression 0.65%; v21\'s setting has 6.47% worst regression and fails that broader guard.')
sub('Validation reuse and historical test exposure')
p('Repeated plot inspection and comparisons reuse the same validation cohort. Its minimum error is therefore exploratory. The original pipeline had already evaluated a historical accepted test subset: 32 recordings from No.2 and No.9, with no accepted No.11/12 recordings because of clock/synchronization failures. Historical baseline/TCN errors were 0.5020/0.6139 m under that earlier protocol. Those values are not comparable current-protocol results and do not establish a learned gain.')
p('No final-test acquisitions were reopened in the current improvement loop. The historical test exposure means a truly blind new accuracy claim requires a separately protected evaluation after model and protocol freezing. Participant separation prevents identity leakage; it does not undo repeated validation selection or prior test exposure.')

title('6 / How the experiments reached this result')
p('The first learned TCN reduced development error but failed to generalize on the historical test subset. That failure motivated better reference validity, synchronization and physical features. The corrected observed reference removed false initial poses. A frozen ridge residual became the paired current-protocol control at 116.899 mm.')
p('Early alternatives did not provide a consistent solution. A three-seed long-horizon ensemble reached 114.057 mm overall but worsened SL to 147.682 mm and split participant gains. Empirical three-axis yaw bias gave 230.680 mm versus 222.128 mm for its static comparator. Observed-only synchronization gave only a small paired change (116.823 to 116.508 mm), so clocks stayed fixed. Training-calibration changes helped SL while regressing PS/OS. All 24 nonzero acceleration-smoother settings lost on the training fold.')
table([['Version','Overall mm','SL mm','Main lesson'],['v12','115.918','138.418','Yaw TCN: mixed generalization'],['v13','118.172','137.641','Nonlinear point loss: rejected'],['v14','112.622','136.853','Temporal/physical features help'],['v15','114.744','135.418','Seed ensemble: residual SL failures'],['v16','104.452','119.725','Coupled interval loss: large gain'],['v17','111.077','145.464','Forward context: braking still poor'],['v19 / v20','104.452','119.725','Refinement/blend retain v16'],['v21','102.585','122.943','Nonlinear interval correction wins overall'],['v22','116.879','151.760','Aggressive endpoint weight rejected'],['v23','103.445','122.496','Offline gravity state does not beat v21'],['v24','108.950','131.316','Broader participant guard']],[63,75,60,277],small=True)
p('The decisive improvement came from teaching corrections how motion accumulates into displacement. A lower instantaneous error need not give a better integrated path. v16 addressed that relationship; v21 added bounded nonlinear products to the same interval formulation. Larger corrections and extra optimization did not consistently help.','SmallNote')

title('7 / Why more training did not solve it')
image(ROOT/'outputs_trajectory_loop/epochs_vs_trajectory.png',maxh=330)
p('Figure 1. Yaw-model training-fold trajectory error and training behavior. At fixed gain 0.5, epochs 3/6/12/24/36 gave about 147.0/146.6/145.5/154.6/149.7 mm. Epoch 12 was selected before validation. Training loss fell from about 0.437 at epoch 12 to 0.399 at epoch 24 while path error worsened.','SmallNote')
p('v19 repeated nonlinear endpoint fitting and lowered the actual clipped training objective, but later iterations worsened the participant fold. v20 found no additional gain from blending the forward-context correction with v16. v22 improved its inner-fold score but regressed validation people No.14/18. These negative comparisons are part of the evidence.')
p('v23 estimated unit gravity direction from quiet IMU observations within continuous runs, keeping calibration, gyro bias/scale and gravity magnitude fixed. It reached 103.445 mm, failing to beat v21 overall. Most target recordings start active: only one of 71 validation recordings passed the initial-five-second stationary gate. Thus the temporal-feature gain cannot be attributed chiefly to successful per-recording mount initialization.')
p('A dGPU enables more experiments but does not correct uncertain units, reference assumptions, bias accumulation or mismatched supervision. The successful direction here is calibrated wheel/body motion with domain-trained interval correction and robust attitude/bias handling [1-3]. A pedestrian RoNIN checkpoint or reinforcement-learning skid correction has not demonstrated a superior result in these data [4].')

title('8 / Results and interpretation')
base_m={r['condition']:r for r in rows('ridge_maneuvers.csv')}
table([['Maneuver','Trials','Ridge mm','v21 mm']]+[[r['condition'],r['trials'],f"{1000*float(base_m[r['condition']]['equal_participant_mean_position_rmse_m']):.3f}",f"{1000*float(r['equal_participant_mean_position_rmse_m']):.3f}"] for r in rows('candidate_maneuvers.csv')],[135,65,135,140])
base_p={r['participant']:r for r in rows('ridge_participants.csv')}
table([['Participant','Trials','Ridge mm','v21 mm']]+[[r['participant'],r['trials'],f"{1000*float(base_p[r['participant']]['mean_trial_position_rmse_m']):.3f}",f"{1000*float(r['mean_trial_position_rmse_m']):.3f}"] for r in rows('candidate_participants.csv')],[135,65,135,140])
p('v21 lowers equal-participant position RMSE from 116.899 to 102.585 mm (14.314 mm; 12.24%). Heading RMSE falls from 1.484 to 1.362 degrees. All four participant and all seven maneuver means improve versus ridge. That does not imply every trial improves or establish statistical significance with four validation people. OS has only three accepted recordings from two people.')
p('<b>Two useful choices.</b> v21 is the best measured exploratory overall result. v16 has a better SL average (119.725 versus 122.943 mm). v24 is the more conservative candidate for the next frozen evaluation (108.950 mm). No date-, participant- or maneuver-specific winner is deployed.')

title('9 / What the images reveal')
sub('Slalom: accumulated heading')
p('Late SL bending reflects accumulated yaw error. No.14 SL trials 1/2/3 worsen approximately 137 to 166, 176 to 184 and 105 to 114 mm; No.18 SL1 worsens 164 to 216 mm. Other trials improve enough to reduce the overall SL average. Dates contain different people, so a date pattern cannot prove a hardware fault.')
sub('PS: braking and wheel-body disagreement')
p('No.18 PS2 improves from roughly 448 to 416 mm yet remains poor. During about 1.5-2.8 s, observed body velocity exceeds wheel-derived velocity by about 0.707 m/s; model underprediction is about 0.39 m/s and costs roughly 0.51 m of displacement. Wheels almost stop around 1.9 s while body deceleration continues until 2.8 s. Training clock residuals are milliseconds, and longer +/-1 s context did not win: this does not establish a global 0.8 s latency.')
sub('AR and CR: geometry must precede cosmetic fixes')
p('No.5 AR2/AR3 show a possible 180-degree marker-side or initial-heading ambiguity despite high observed coverage and a stable optical pair. With two axle markers, physical front is not independently observed. No automatic flip or error-based exclusion was applied. No.5 CR3 is genuine near-in-place rotation, with a midpoint footprint near 231 by 120 mm; the small irregular path should not be forced into a circle.')
sub('Path to lower errors')
p('Verify actual raw/float/CSV encoding and full mounting vectors; measure reference uncertainty and geometry independently; obtain reliable stationary or attitude information; model wheel-body disagreement during braking with uncertainty; and train displacement/orientation interval corrections with participant robustness. Absolute aiding may be necessary for sustained millimeter accuracy. More expressive networks alone are not evidence of that accuracy.')
p('The following atlas displays black observed reference, gray dashed ridge and orange v21. Individual pages contain XY trajectory, position error and heading error. Display translation is allowed; no best-fit path alignment is used. Overview sheets use equal physical aspect and consistent scales within each maneuver.')

title('10 / Reproducibility and primary literature')
p('The independent audit reproduced all 71 v16/v21 trial scores exactly and found no prediction change when reference fields were poisoned. Correction-fold exclusion and nonlinear clipping bounds were checked. Sampled endpoint Jacobians agreed numerically to about 2.4e-8; this is a local numerical check, not a proof for every parameter or clipping branch.')
p('Of 30,640 training endpoint pairs, 10,543 bridge optical gaps. All 4,807 raw heading residuals exceeding pi occur across gaps; none occur in the 20,097 continuously observed pairs. Separate segment unwrapping explains branch differences. Circular endpoint orientation is appropriate, but hidden whole rotations across gaps remain undetermined.')
p('<b>Local evidence:</b> research_docs/trajectory-loop-findings.md; research_docs/trajectory-loop-audit.md; docs/design.md; outputs_trajectory_loop/progress.md; outputs_trajectory_best_v21/summary.json; candidate/ridge trial, participant and maneuver CSVs; sealed trajectories/*.npz. Current inference entry: nonlinear_endpoint_inference_v21.load_nonlinear_endpoint(). Original core and frozen protocol artifacts are preserved.','SmallNote')
for ref in [
    '[1] Wu, Kuang and Niu. Wheel-INS2: Multiple IMUs for wheel-mounted inertial navigation. DOI 10.1109/TITS.2022.3220508. https://arxiv.org/abs/2012.10593',
    '[2] Brossard, Bonnabel and Barrau. Denoising IMU Gyroscopes with Deep Learning for Open-Loop Attitude Estimation (2020). https://arxiv.org/abs/2002.10718',
    '[3] Liu et al. TLIO: Tight Learned Inertial Odometry. Learned displacement uncertainty and filtering. https://cathias.github.io/TLIO/',
    '[4] Herath, Yan and Furukawa. RoNIN: Robust Neural Inertial Navigation in the Wild. https://arxiv.org/abs/1905.12853',
]:p(escape(ref),'SmallNote')
p('These papers motivate physical mounting models and interval supervision. They do not validate this dataset\'s units, establish millimeter accuracy, or provide a measured RL advantage. Wheelchair-specific data and a separately frozen evaluation are still necessary.')

title('Atlas / Coverage and recording index')
p('All 71 quality-accepted validation recordings follow the seven maneuver overview sheets. No high-error accepted recording is removed. The index gives v21 and paired ridge trial RMSE, so readers can find both strong paths and failures. Each individual page has a PDF bookmark with its complete recording identifier.')
table([['Condition','Planned','Accepted','Missing'],['10x5','12','12','0'],['AR','12','12','0'],['CR','12','12','0'],['OS','12','3','9'],['PS','12','8','4'],['SL','12','12','0'],['ST','12','12','0'],['Total','84','71','13']],[155,100,110,110])
p('Missing repetitions are quality failures, not model-error exclusions. Their existing labels remain on overview sheets. Coverage is unequal across maneuvers and participants. The atlas documents the best exploratory v21 candidate, not the conservative v24 model.')
for start in range(0,71,24):
    title(f'Atlas index / recordings {start+1}-{min(start+24,71)}')
    data=[['No.','Recording identifier','v21 mm','Ridge mm']]
    for k,r in enumerate(trials[start:start+24],start+1):
        data.append([k,r['id'].replace('2026-09-','09-'),f"{1000*float(r['position_rmse_m']):.1f}",f"{1000*float(ridge[r['id']]['position_rmse_m']):.1f}"])
    table(data,[28,319,64,64],small=True)
    p('Identifiers retain date, maneuver, repetition and participant. Trial RMSE is Euclidean XY error on camera-observed frames.','SmallNote')

def footer(canvas,doc):
    canvas.setStrokeColor(colors.HexColor('#cbd9e2')); canvas.line(60,48,535,48)
    canvas.setFont('Helvetica',8);canvas.setFillColor(colors.HexColor('#526579'))
    canvas.drawString(60,34,'Wheelchair reconstruction | Exploratory development evidence')
    canvas.drawRightString(535,34,str(doc.page))
doc=SimpleDocTemplate(str(TMP/'narrative.pdf'),pagesize=A4,rightMargin=60,leftMargin=60,topMargin=55,bottomMargin=65,title='Wheelchair trajectory methodology and results',author='Wheelchair reconstruction project')
doc.build(story,onFirstPage=footer,onLaterPages=footer)
writer=PdfWriter(); narrative=PdfReader(TMP/'narrative.pdf'); writer.append(narrative)
for i,page in enumerate(narrative.pages):
    txt=page.extract_text() or ''
    heading=next((c for c in chapters if c in txt),None)
    if heading:writer.add_outline_item(heading,i)

# Overview sheets get landscape pages with titles and captions, keeping all plots legible.
overview_story=[]
for cond in ['10x5','AR','CR','OS','PS','SL','ST']:
    if overview_story:overview_story.append(PageBreak())
    overview_story.append(Paragraph(f'{cond} / all planned validation repetitions',styles['Heading1']))
    im=Image(str(SRC/f'{cond}_all.png'));sc=min(745/im.imageWidth,440/im.imageHeight);im.drawWidth=im.imageWidth*sc;im.drawHeight=im.imageHeight*sc;overview_story.append(im)
    overview_story.append(Paragraph('Black: observed reference. Gray dashed: ridge. Orange: v21. Missing recordings retain their QC labels. Equal XY aspect; consistent physical scale within maneuver. All accepted trials are included.',styles['SmallNote']))
SimpleDocTemplate(str(TMP/'overviews.pdf'),pagesize=(842,595),leftMargin=48,rightMargin=48,topMargin=25,bottomMargin=28).build(overview_story)
overview_start=len(writer.pages); writer.append(TMP/'overviews.pdf')
for j,c in enumerate(['10x5','AR','CR','OS','PS','SL','ST']):writer.add_outline_item(f'{c} overview',overview_start+j)
atlas_start=len(writer.pages); atlas=PdfReader(SRC/'all_71_trajectories.pdf');assert len(atlas.pages)==71
parent=writer.add_outline_item('All 71 accepted trajectories',atlas_start)
writer.append(atlas,import_outline=False)
ids=set(r['id'] for r in trials)
for j,page in enumerate(atlas.pages):
    txt=page.extract_text() or ''
    trialid=next((x for x in ids if x in txt),None)
    if trialid is None:raise RuntimeError(f'Missing identifier on atlas page {j+1}')
    writer.add_outline_item(trialid,atlas_start+j,parent=parent)
writer.add_metadata({'/Title':'Wheelchair trajectory reconstruction: methodology, development story and all accepted trajectories','/Author':'Wheelchair reconstruction project','/Subject':'71 validation trajectories, training-only corrections and exploratory results'})
with FINAL.open('wb') as f:writer.write(f)
check=PdfReader(FINAL)
assert len(check.pages)==len(narrative.pages)+7+71
(TMP/'report_manifest.json').write_text(json.dumps({'pdf':str(FINAL),'pages':len(check.pages),'narrative_pages':len(narrative.pages),'overview_pages':7,'trajectory_pages':71,'atlas_start_page':atlas_start+1,'recordings':71},indent=2))
print((TMP/'report_manifest.json').read_text())
