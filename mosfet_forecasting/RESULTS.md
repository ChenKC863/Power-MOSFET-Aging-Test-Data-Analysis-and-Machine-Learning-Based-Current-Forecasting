# Completed exploratory MOSFET forecasting experiment

## Data actually used

SciPy read 104 normally named Test/run MAT files. The marked setup-error file and test_rampup.mat were excluded by design. The primary window rules retained **9,304 examples from 83 files across 33 unverified Test-number groups**. Original MAT/M files and Word documents were not edited.

The target is the mean recorded current during a future one-minute interval ending five minutes after forecast issuance, using five minutes of prior measurements. Values and errors are in **raw recorded current units**. This target differs from Slide 7's high-current-only median.

## Primary results

| model | MAE | RMSE | macro_group_MAE |
| --- | --- | --- | --- |
| Ridge | 0.02050 | 0.04300 | 0.03236 |
| Persistence | 0.02437 | 0.04615 | 0.03524 |
| RandomForest | 0.02599 | 0.05164 | 0.04593 |
| HistGradientBoosting | 0.03727 | 0.08191 | 0.04717 |
| LinearTrend | 0.03935 | 0.06222 | 0.05203 |


MAE/RMSE weight forecast examples equally. Macro group MAE first calculates each held-out group's MAE, then gives each group equal weight. Ridge has the lowest aggregate errors in this experiment; no statistical superiority or performance on unseen confirmed devices is established. Persistence is a strong baseline. Selecting a preferred model after these comparisons will require fresh independent validation before claiming a final performance estimate.

## Current-prediction uncertainty

Nominal 90% quantile intervals achieved **88.6%** pooled out-of-fold coverage, with average width **0.12258** raw units. Per-group coverage ranged from **33.3% to 100.0%**; groups vary greatly in sample size. Quantile crossing occurred in 0.0% of rows. These intervals are not calibrated coverage guarantees and do not quantify remaining-life overestimation.

## Slide 9 — Baseline and Machine Learning Comparison

- Implemented persistence and linear-trend baselines, plus Ridge, Random Forest and Histogram Gradient Boosting.
- Forecast a future one-minute mean current from five minutes of prior current observations and recorded settings.
- Evaluated 9,304 eligible windows from 83 files; comparisons are conditional on stable commanded settings.
- Ridge achieved the lowest aggregate errors; include the numerical table or model_comparison.png.
- This is electrical-measurement forecasting, not validated RUL prediction.

## Slide 10 — Exploratory Validation and Uncertainty

- Used five outer grouped folds; all runs sharing a Test number remained together.
- Tuned parameters using three inner training-group folds; reported errors for each held-out group/file.
- Physical device identities remain unverified, so cross-device generalization is not established.
- Nominal 90% current-prediction intervals achieved 88.6% overall coverage, with substantial group variation.
- Examined history length, controller-setting feature removal and a sample-count cleaning filter in separate sensitivity experiments.

## Slide 11 — Progress and Next Steps

- Completed a reproducible steady-state cleaning/window pipeline, causal features, and five-method grouped comparison.
- Saved audit records, out-of-fold predictions, per-group errors and current-prediction intervals.
- Review poorly predicted groups, short histories and sensitivity results before interpreting model differences.
- Confirm device mapping, units/scaling and failure criteria before building physical degradation indicators or RUL labels.
- Validate the selected approach on independent, confirmed devices; evaluate operational transitions separately.

## Candidate files with no eligible primary forecast windows

These are excluded by the stated window rules, not diagnosed as failed or globally unusable:

- Test_13_run_5.mat
- Test_19_run_1.mat
- Test_19_run_2.mat
- Test_1_run_1.mat
- Test_1_run_2.mat
- Test_23_run_2.mat
- Test_24_run_1.mat
- Test_25_run_4.mat
- Test_2_run_1.mat
- Test_2_run_2.mat
- Test_2_run_3.mat
- Test_39_run_1.mat
- Test_3_run_1.mat
- Test_40_run_1.mat
- Test_40_run_2.mat
- Test_42_run_1.mat
- Test_4_run_1.mat
- Test_4_run_2.mat
- Test_5_run_1.mat
- Test_5_run_2.mat
- Test_6_run_2.mat

## Interpretation limits

Future settings and availability determine retrospective sample eligibility, although features use past measurements only. Stable-condition selection excludes operating transitions and missing-data periods. Overlapping examples are correlated. Timestamp/setting rules do not establish sensor calibration. Per-group errors can be unstable for groups with few examples. The lower current threshold 0.1 is a descriptive recorded-value filter, not a verified failure criterion.

## Sensitivity on shared forecast examples

| variant | model | shared_examples | MAE | macro_group_MAE |
| --- | --- | --- | --- | --- |
| results | HistGradientBoosting | 8821 | 0.03744 | 0.05422 |
| results | LinearTrend | 8821 | 0.03842 | 0.05757 |
| results | Persistence | 8821 | 0.02408 | 0.04024 |
| results | RandomForest | 8821 | 0.02551 | 0.05360 |
| results | Ridge | 8821 | 0.02016 | 0.03776 |
| sensitivity_history10 | HistGradientBoosting | 8821 | 0.04358 | 0.06733 |
| sensitivity_history10 | LinearTrend | 8821 | 0.02754 | 0.04671 |
| sensitivity_history10 | Persistence | 8821 | 0.02408 | 0.04024 |
| sensitivity_history10 | RandomForest | 8821 | 0.02597 | 0.06216 |
| sensitivity_history10 | Ridge | 8821 | 0.01946 | 0.03719 |
| sensitivity_no_settings | HistGradientBoosting | 8821 | 0.04190 | 0.05819 |
| sensitivity_no_settings | LinearTrend | 8821 | 0.03842 | 0.05757 |
| sensitivity_no_settings | Persistence | 8821 | 0.02408 | 0.04024 |
| sensitivity_no_settings | RandomForest | 8821 | 0.02481 | 0.05219 |
| sensitivity_no_settings | Ridge | 8821 | 0.01972 | 0.03676 |
| sensitivity_count100 | HistGradientBoosting | 8821 | 0.03744 | 0.05422 |
| sensitivity_count100 | LinearTrend | 8821 | 0.03842 | 0.05757 |
| sensitivity_count100 | Persistence | 8821 | 0.02408 | 0.04024 |
| sensitivity_count100 | RandomForest | 8821 | 0.02551 | 0.05360 |
| sensitivity_count100 | Ridge | 8821 | 0.02016 | 0.03776 |

These runs share scored file/time keys but can have different training cohorts/fold assignments. They do not isolate causal effects. Full-cohort results are in sensitivity_summary.csv.

For this completed study, increasing the minimum count from 10 to 100 records per minute removed no primary forecast examples and produced unchanged results. This particular setting therefore did not demonstrate sensitivity to cleaning. A ten-minute history retained 8,821 shared examples and modestly improved Ridge MAE on those examples. Removing commanded-setting features also slightly improved Ridge MAE; those differences do not establish that operating conditions are physically irrelevant.
