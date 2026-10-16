# Revised PDF versus MATLAB exports: consistency review

Reviewed: `MOSFET_Current_Forecasting_Revised.pdf`, 15 October 2026.
Page references below are the PDF viewer's 1-based page numbers, not older numbers embedded in slide images.

## Conclusion

No numerical contradiction was found in the checked dataset, quality, trend, and engineering-case claims. The model summaries also agree with the saved Python results and implementation inspected separately. This is a claim-level consistency review, not a certification of every value in every waveform or of physical calibration.

**A significant separate issue was found in the MATLAB exports: all 106 `.m` files contain malformed numeric `reshape` assignments in their first 64 KiB.** Their numbers can be extracted as text, but the files should not be described as executable MATLAB reproductions until repaired. The forecasting pipeline reads original `.mat` files, so these syntax errors are outside its input path.

## Direct `.m` evidence

| PDF page | Claim | Check result |
|---|---|---|
| 5–6 | 106 local measurement files | 106 `.m` exports inventoried; each has controller, transient, and steady-state structure declarations. |
| 6 | Summed steady-state recording spans: 214.416 hours | Parsed steady-state date strings across all 106 exports: 1,906,566 records, sum of valid within-file maximum-minus-minimum timestamps = **214.4163191667 hours**. This remains recording span, including gaps, not verified stress exposure. |
| 6 | Test 1 negative flange readings | Run 1: **−2279.691271 to −2278.224991**. Run 2: **−2272.907215 to −2271.462546**. These support the reported approximate raw readings. They do not establish a physical unit. |
| 6 | Empty waveforms in Test 2 run 2 and Test 40 run 2 | Exactly one empty gate-source array in each; the inspected first Test 40 run 2 transient record also has empty gate-signal, drain-source, and drain-current arrays and an anomalous **1903-12-31** date. |
| 6 | Constant gate-source waveforms | Directly parsed every gate-source array in Test 31 and Test 33: **33,973/33,980** and **38,350/38,356**, respectively. |
| 6 | Acquisition settings vary | Test 6 run 1: **5,000** samples, `dt=2e-7`; run 2: **1,000** samples, `dt=1e-6`. Test 40 run 2 contains **500, 501, and 502** sample arrays and multiple `dt` values. The anomalous empty record has `dt=1`; do not interpret that as normal acquisition timing. |
| 7 | Test 38 current trend | Medians for 17:10–17:20 and 18:10–18:20, restricting recorded current to >1: **2.5474422473** and **2.3775506453**. The PDF's **6.6% using rounded values** is consistent with 2.547 and 2.378. Full-precision values yield about 6.67%, conventionally rounded to 6.7%. |
| 7 | Test 38 prolonged low current | Consecutive records below 0.1 span **12,611.339 s**, from **18:23:46.326 to 21:53:57.665**, or elapsed **1.389648–4.892798 h**. This supports approximately 3.5 hours and 1.39–4.89 hours. |
| 7 | Test 41 current trend and longest low sequence | Medians **2.6706123221 → 2.6719502946**, about +0.05%; longest consecutive below-0.1 sequence **18.336 s**, rounding to 18.34 s. |
| 19 | Test 20 event values | At 10:53–10:54, mean current **1.7950945729**. Package-channel mean changes from **121.4552395** in 10:52–10:53 to **117.0654061** in 10:53–10:54. These agree with 1.795 and 121.46 → 117.07. |
| 19 | Test 27 selected event | At 12:05–12:06, raw current mean **1.7084910533**, consistent with the saved observed target used in the engineering case. |

## Model claims require Python evidence

The `.m` files contain serialized measurements and settings, not trained forecasts, fold assignments, or evaluation metrics. These statements were compared separately with `mosfet_forecasting/pipeline.py` and the existing files under `mosfet_forecasting/results/`; models were not retrained.

- Pages 8–10: 106 inventory files, two filename-based exclusions, 104 candidates, 83 contributing files, 21 candidates without eligible examples, 9,304 examples, and 33 Test-number groups agree with `file_audit.csv`, `features.csv`, and `run_metadata.json`.
- Pages 8–10 and 15: five past one-minute bins predict a one-minute target ending five minutes after issuance. Historical features use past values; sample eligibility additionally checks future setting stability. This is correctly presented as conditional retrospective evaluation.
- Page 14: held-out example/group counts by fold are 1,864/6, 1,860/7, 1,864/7, 1,853/6, and 1,863/7. These match the table.
- Pages 16–17 and 20–21: the formulas and saved model scores agree. Ridge MAE = 0.0205008473, RMSE = 0.0430032001, macro group MAE = 0.0323587878. Reported reductions versus persistence round to 15.9% and 8.2%.
- Page 18: recalculating inclusion within the saved lower/upper bounds gives **8,244/9,304**, or **88.607%**. These are quantile Histogram Gradient Boosting intervals, not Ridge intervals. No crossed intervals are present in this saved output.
- Page 19: Test 27 has 111 examples and Ridge MAE 0.0127048211; Test 20 has 132 examples, Ridge MAE 0.0722142079, and Ridge bias approximately −0.061262. These match the displayed rounded values.

## MATLAB export defect

For example, `Test_1_run_1.m`, lines 9–11, contains:

```matlab
measurement(1).pwmTempControllerState(1).timeEpoch = reshape([
    734186.7399151736
]), [1 1]);
```

The numeric array closes with an extra parenthesis before the size argument. The correct form is:

```matlab
measurement(1).pwmTempControllerState(1).timeEpoch = reshape([
    734186.7399151736
], [1 1]);
```

The source is the real numeric serialization branch in `MOSFET_Thermal_Overstress_Aging/mat_to_m.py`, line 167:

```python
# Current
stream.write(f"]), {matlab_size(shape)})")
# Required in this branch
stream.write(f"], {matlab_size(shape)})")
```

Do **not** globally replace every `]),`: the character and complex serialization branches legitimately close `uint16(...)` or `complex(...)` before supplying the reshape dimensions. This review identifies the defect without changing the converter or the exported data. No MATLAB execution was performed; the issue was established by inspecting the expressions and converter.

## Suggested PDF refinements

1. **Page 19:** clarify that temperature setpoints apply to the evaluated segments, not the entire original file. Both original files contain earlier setpoint changes. Suggested label: **“Commanded settings in the evaluated segments: duty 40, supply 5, gate 10; temperature setpoints … (recorded scales).”**
2. **Page 4:** add **“Illustrative device/package diagram; actual package type and sensor locations are not established by the exported data.”** The `.m` field names support temperature-channel names, but not the exact sensor placements shown in the illustration.
3. **Page 6:** remove one of the two overlapping unresolved-metadata bullets if desired. This is redundancy, not a data contradiction.
4. **Page 17:** change the heading from **“2. Model Comparison”** to **“3. Model Comparison”**, since page 16 already uses “2. Evaluation Metrics.” This is numbering only.
5. If mentioning `.m` exports in the PDF or README, use: **“Forecasting uses the original `.mat` files loaded with SciPy. Converted `.m` exports were used for text-based inspection; their current numeric-assignment syntax requires correction before MATLAB execution.”**

The existing caveats about unverified units/calibration, Test numbers versus physical-device identities, and unconfirmed failure/RUL endpoints should remain. The `.m` values do not resolve those metadata gaps. External dataset provenance and references were outside this local-file consistency check.

## Reproducible review files

- `check_matlab.py` → `matlab_recording_audit.csv`, `matlab_claim_checks.json`: all-file steady-state inventory, recording spans, selected numerical claims.
- `check_waveforms.py` → `waveform_checks.json`: selected waveform quality/acquisition claims, including all gate-source waveforms in Tests 31 and 33.
- `check_export_syntax.py` → `export_syntax_audit.json`: first-64-KiB numeric syntax inspection for all 106 scripts.

The scripts parse the serialized text; they do not execute MATLAB or establish complete `.mat`/`.m` round-trip equivalence.
