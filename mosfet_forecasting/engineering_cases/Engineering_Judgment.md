# How Forecasts Support Engineering Judgment

## Placement in the presentation
Insert after the original **slide 17, Prediction Uncertainty**, and before the original **slide 18, Discussion**. These pages carry printed numbers 15 and 16. The added page is slide 18 in the revised deck, with printed label 15A, so existing printed page references remain intact.

## Selection and scope
These are post-hoc illustrations using saved outer-fold held-out predictions, not a new independent validation. Among Test-number groups with at least 100 evaluated examples, select the lowest and highest Ridge MAE. The 100-example minimum is a presentation selection rule, not evidence of statistical independence. Overlapping windows remain dependent.

Select each group's run with the most evaluated examples for the chart, breaking ties by filename order. Group metrics below include all eligible runs. The charts use Test 27 run 4 (46 examples) and Test 20 run 1 (70 examples). Test 27 run 5 also has 46 examples. No refitting or model selection is performed here.

Observed means and forecasts are aligned at the END of the target minute. Predictions were issued five minutes earlier. Thus a point at 10:54 predicts the observed mean during 10:53–10:54, issued at 10:49. Gaps identify minutes absent from the evaluated target set and do not imply absence of raw measurements. The target includes all valid current states, rather than only high-current readings.

## Quantitative evidence
| Test group | Examples | Outer fold | Ridge MAE | Persistence MAE | Ridge bias | Ridge underpredictions |
|---|---:|---:|---:|---:|---:|---:|
| Test_27 | 111 | 5 | 0.01270482 | 0.01682859 | -0.00521043 | 69 |
| Test_20 | 132 | 2 | 0.07221421 | 0.03117213 | -0.06126201 | 129 |

All current values/errors and operating values below are in their recorded scales. Physical units and calibration factors remain unverified.

### Test_27: representative file Test_27_run_4.mat

Run MAE: Ridge 0.01204063, Persistence 0.01645712.

Largest absolute Ridge error occurs in target interval [2010-08-05 12:05:00, 2010-08-05 12:06:00). Observed mean 1.70849105, Ridge 1.74440232, Persistence 1.73984127. Signed Ridge error +0.03591126.

Controller settings in the plotted evaluated examples: {'lowTemp': 229.0, 'highTemp': 230.0, 'shutdownTemp': 240.0, 'gateVoltage': 10.0, 'supplyVoltage': 5.0, 'switchingFrequency': 1000.0, 'dutyCycle': 40.0}.

Target-minute mean package-temperature channel range: [124.8551923125307, 125.64976783799096]. Measured supply-channel mean range: [5.608859274985212, 5.61166877293728]. Fraction of current samples below the raw threshold 0.1: [0.0, 0.0]. These diagnostic target-period measurements are used only for retrospective interpretation; they were not added as forecasting inputs.

### Test_20: representative file Test_20_run_1.mat

Run MAE: Ridge 0.07475007, Persistence 0.03474586.

Largest absolute Ridge error occurs in target interval [2010-07-20 10:53:00, 2010-07-20 10:54:00). Observed mean 1.79509457, Ridge 2.29203323, Persistence 2.35614408. Signed Ridge error +0.49693865.

Controller settings in the plotted evaluated examples: {'lowTemp': 209.0, 'highTemp': 210.0, 'shutdownTemp': 230.0, 'gateVoltage': 10.0, 'supplyVoltage': 5.0, 'switchingFrequency': 1000.0, 'dutyCycle': 40.0}.

Target-minute mean package-temperature channel range: [117.06540611285132, 121.95278993535605]. Measured supply-channel mean range: [5.613230323019595, 5.61744769382043]. Fraction of current samples below the raw threshold 0.1: [0.013333333333333334, 0.10810810810810811]. These diagnostic target-period measurements are used only for retrospective interpretation; they were not added as forecasting inputs.

## Interpretation and engineering checks

### Test 27: lower error
The group Ridge MAE is approximately 24.5% below Persistence. In run 4, all target-minute current samples exceed the raw 0.1 threshold, and the package-temperature mean varies narrowly (124.86–125.65). This documents a relatively steady observed regime. The largest Ridge error is +0.03591 during 12:05–12:06 on 2010-08-05. Good forecast agreement alone does not confirm device health, calibration, or a failure endpoint.

### Test 20: higher error
Ridge MAE is approximately 2.32 times Persistence. Ridge underpredicts 129/132 group targets, consistent with a systematic negative forecasting bias in this evaluated group. This pattern warrants checking whether the training groups adequately represent this group's current regime and whether omitted thermal/control-state information explains residuals. These are hypotheses, not a demonstrated cause.

Within run 1, Ridge usually underpredicts over the eligible intervals 10:03–10:53, 11:37–11:39 and 11:49–12:06 on 2010-07-20. The exceptional target minute 10:53–10:54 produces an overprediction by both methods: Ridge +0.49694 and Persistence +0.56105. Between target minutes starting 10:52 and 10:53, the mean current changes from 2.35678 to 1.79509 and the package-temperature mean from 121.45524 to 117.06541. Measured supply means change only from 5.61495 to 5.61745. Recorded duty/supply/gate settings remain 40/5/10 for these eligible examples. Unchanged commands do not establish unchanged actual drive, load or thermal state.

The low-current sample fraction decreases from about 9.4% to 1.3% across those two minutes. Therefore the mean-current decrease cannot be explained merely as a larger proportion of samples below 0.1. Sampling phase, changes in the non-low-current distribution, thermal response or measurement effects remain possible. The existing evidence cannot identify the physical mechanism.

### Measurements and analysis needed to distinguish explanations
- Synchronize current and drain-source/gate-source voltage waveforms, actual gate duty/frequency and load measurements around the error interval. Check waveform quality and switching-phase coverage first.
- Verify current-probe scaling, temperature calibration and sensor response. Confirm whether the package-temperature change is physical or instrumental.
- Retrieve actual controller state, shutdown/interlock events and load changes in addition to command setpoints.
- Compare residuals under matched thermal/operating conditions and check training-data coverage. Any revised feature/model choice needs fresh validation.
- Retain Persistence as a comparison for model acceptance. A lower overall Ridge MAE does not establish that it is preferable for every Test group.

This page concerns point forecasts from Ridge. Test 27's previously reported poor interval coverage concerns different quantile Gradient Boosting models, so good Ridge MAE does not contradict that result. Test-number groups remain unverified physical-device identifiers. This exercise does not establish failure or RUL.

## Inputs, outputs and reproduction
Inputs: `../results/predictions.csv`, `../results/features.csv`, and original `Test_27_run_4.mat` / `Test_20_run_1.mat` in `../../MOSFET_Thermal_Overstress_Aging/`.

The script recomputes group ranking from predictions, merges historical features by file and timestamps, and extracts steady-state context with SciPy. It checks agreement between plotted target means and means re-extracted from the raw MAT files.

Outputs: `selection_ranking.csv` (all eligible candidate groups), `case_predictions.csv` (all selected-group examples), `Test_*_representative_predictions.csv` (plotted targets and operating context), `Test_*_representative_context.csv` (minute context throughout the raw representative files), `case_summary.json` and `slide_data.json`.

From the project root:
```powershell
& '.\.venv-mosfet\Scripts\python.exe' '.\mosfet_forecasting\engineering_cases\analyze_cases.py'
& '.\.venv-mosfet\Scripts\python.exe' '.\mosfet_forecasting\engineering_cases\write_report.py'
```
Slide authoring source: `build_slide.mjs` (requires the bundled @oai/artifact-tool runtime). The new slide uses editable charts and text. Existing source slides are preserved when inserting it into the revised copy.
