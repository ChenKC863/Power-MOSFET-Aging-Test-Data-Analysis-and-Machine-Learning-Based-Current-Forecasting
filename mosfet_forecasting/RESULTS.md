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
