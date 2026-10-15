# v124 review closure

15 October 2026. The guarded TRAIN screen, full-TRAIN package and reporting
completed exit0. Independent reviewer /root/review_v124 examined the source and
authored independent arithmetic checks; the coordinator executed those scripts
under the exclusive guard and the reviewer inspected the resulting evidence.

Screen review PASS:224 output/636 input/17 source hashes, all207 identities/
12participants/all15No20, all1035pairedprediction sets and314498scoredframes
per model,1242 control-array comparisons, fit exclusions, normalization,
correction caps/lateral invariance, direct core metrics, both-control guards and
winner selection. Prior v121 dependency source hashes match exactly.
Evidence: `research_state/v124_independent_review.json` and
`research_state/review_trial_rmse_v124.py`.

Package/report review PASS:6 bundle outputs/430 inputs/22 dependencies,
3 report outputs/7 recorded inputs, selected penalty10, full207 IDs, frozen
normalization, saved fitting histories and all207 inference/poisoning records.
The executed package verifier measured maximum motion difference0. The reviewer
checked these sealed records and source rather than repeating predictions.
All7100 grouped metric rows and their availability denominators independently
reconstruct, including80 groups with no values and550 partially available groups.
All participant benefits, omission means,4096 bootstrap draws(seed122) and
628/4096 exact sign flips independently reconstruct.

The original sealed report's provenance list omitted the bundle manifest,
model.json and verification.json used for its package claims. The independent
review supplies all three exact input hashes in
`research_state/v124_package_report_review.json` without modifying the sealed
report or recomputing its predictions. Use that supplement with the report.
Checker: `research_state/review_trial_rmse_package_v124.py`.

Accepted matched TRAIN ATE is128.872854348mm versus v121129.739810994mm.
Penalty1's126.775357782mm fails participant guards and remains rejected.
The model is frozen at `models/trial_rmse_v124`; no v124 validation/test result,
deployment approval or independent significance is claimed. Bootstrap95 benefit
[-.126796,1.940807]mm includes zero; No.8 remains close to the v34 guard boundary.
The next explicit decision is `frozen_validation_decision_v124.md`.
