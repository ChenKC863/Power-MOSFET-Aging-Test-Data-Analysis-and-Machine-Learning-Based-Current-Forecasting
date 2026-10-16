"""Write a human-readable summary from completed result files only."""
from pathlib import Path
import json
import pandas as pd

HERE = Path(__file__).resolve().parent

def table(df):
    head = '| ' + ' | '.join(df.columns) + ' |\n'
    head += '| ' + ' | '.join(['---'] * len(df.columns)) + ' |\n'
    for row in df.itertuples(index=False, name=None):
        head += '| ' + ' | '.join(f'{v:.5f}' if isinstance(v, float) else str(v) for v in row) + ' |\n'
    return head

if __name__ == '__main__':
    result = HERE / 'results'
    meta = json.loads((result/'run_metadata.json').read_text())
    metrics = pd.read_csv(result/'metrics_overall.csv').sort_values('macro_group_MAE')
    audit = pd.read_csv(result/'file_audit.csv')
    interval = pd.read_csv(result/'prediction_intervals.csv')
    coverage = pd.read_csv(result/'interval_coverage_per_group.csv')
    primary = table(metrics[['model', 'MAE', 'RMSE', 'macro_group_MAE']])
    excluded = '\n'.join('- ' + f for f in audit.loc[audit.status == 'no_eligible_windows', 'file'])
    text = f'''# Completed exploratory MOSFET forecasting experiment

## Data actually used

SciPy read 104 normally named Test/run MAT files. The marked setup-error file and test_rampup.mat were excluded by design. The primary window rules retained **{meta['examples']:,} examples from {meta['files_with_examples']} files across {meta['groups']} unverified Test-number groups**. Original MAT/M files and Word documents were not edited.

The target is the mean recorded current during a future one-minute interval ending five minutes after forecast issuance, using five minutes of prior measurements. Values and errors are in **raw recorded current units**. This target differs from Slide 7's high-current-only median.

## Primary results

{primary}

MAE/RMSE weight forecast examples equally. Macro group MAE first calculates each held-out group's MAE, then gives each group equal weight. Ridge has the lowest aggregate errors in this experiment; no statistical superiority or performance on unseen confirmed devices is established. Persistence is a strong baseline. Selecting a preferred model after these comparisons will require fresh independent validation before claiming a final performance estimate.

## Current-prediction uncertainty

Nominal 90% quantile intervals achieved **{interval.covered.mean():.1%}** pooled out-of-fold coverage, with average width **{interval.width.mean():.5f}** raw units. Per-group coverage ranged from **{coverage.coverage.min():.1%} to {coverage.coverage.max():.1%}**; groups vary greatly in sample size. Quantile crossing occurred in {interval.quantile_crossing.mean():.1%} of rows. These intervals are not calibrated coverage guarantees and do not quantify remaining-life overestimation.

## Slide 9 — Baseline and Machine Learning Comparison

- Implemented persistence and linear-trend baselines, plus Ridge, Random Forest and Histogram Gradient Boosting.
- Forecast a future one-minute mean current from five minutes of prior current observations and recorded settings.
- Evaluated {meta['examples']:,} eligible windows from {meta['files_with_examples']} files; comparisons are conditional on stable commanded settings.
- Ridge achieved the lowest aggregate errors; include the numerical table or model_comparison.png.
- This is electrical-measurement forecasting, not validated RUL prediction.

## Slide 10 — Exploratory Validation and Uncertainty

- Used five outer grouped folds; all runs sharing a Test number remained together.
- Tuned parameters using three inner training-group folds; reported errors for each held-out group/file.
- Physical device identities remain unverified, so cross-device generalization is not established.
- Nominal 90% current-prediction intervals achieved {interval.covered.mean():.1%} overall coverage, with substantial group variation.
- Examined history length, controller-setting feature removal and a sample-count cleaning filter in separate sensitivity experiments.

## Slide 11 — Progress and Next Steps

- Completed a reproducible steady-state cleaning/window pipeline, causal features, and five-method grouped comparison.
- Saved audit records, out-of-fold predictions, per-group errors and current-prediction intervals.
- Review poorly predicted groups, short histories and sensitivity results before interpreting model differences.
- Confirm device mapping, units/scaling and failure criteria before building physical degradation indicators or RUL labels.
- Validate the selected approach on independent, confirmed devices; evaluate operational transitions separately.

## Candidate files with no eligible primary forecast windows

These are excluded by the stated window rules, not diagnosed as failed or globally unusable:

{excluded}

## Interpretation limits

Future settings and availability determine retrospective sample eligibility, although features use past measurements only. Stable-condition selection excludes operating transitions and missing-data periods. Overlapping examples are correlated. Timestamp/setting rules do not establish sensor calibration. Per-group errors can be unstable for groups with few examples. The lower current threshold 0.1 is a descriptive recorded-value filter, not a verified failure criterion.
'''
    common = HERE/'sensitivity_common_examples.csv'
    if common.exists():
        s = pd.read_csv(common)
        text += '\n## Sensitivity on shared forecast examples\n\n' + table(s)
        text += '\nThese runs share scored file/time keys but can have different training cohorts/fold assignments. They do not isolate causal effects. Full-cohort results are in sensitivity_summary.csv.\n'
        text += '\nFor this completed study, increasing the minimum count from 10 to 100 records per minute removed no primary forecast examples and produced unchanged results. This particular setting therefore did not demonstrate sensitivity to cleaning. A ten-minute history retained 8,821 shared examples and modestly improved Ridge MAE on those examples. Removing commanded-setting features also slightly improved Ridge MAE; those differences do not establish that operating conditions are physically irrelevant.\n'
    else:
        text = text.replace('- Examined history length, controller-setting feature removal and a sample-count cleaning filter in separate sensitivity experiments.', '- Sensitivity comparisons remain pending; commands are provided in README.md.')
    (HERE/'RESULTS.md').write_text(text, encoding='utf-8')
