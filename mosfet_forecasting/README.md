# MOSFET: exploratory current forecasting

## Scope and model choice

This implementation forecasts **recorded current**, not remaining useful life (RUL), physical health, or a confirmed failure endpoint. No unit conversion is applied. The target differs from Slide 7's conditional high-current median: it is the arithmetic mean of **all finite steady-state drainCurrent readings** in one complete future minute. It includes switching/low-current states and is sensitive to operating conditions and sampling. It is a sample-weighted mean, not an integrated time-weighted current.

| Method | Purpose |
|---|---|
| Persistence | Predict the last complete minute's mean; essential baseline |
| Linear trend | Extrapolate the historical least-squares slope from the latest mean |
| Ridge regression | Regularized linear relationship between history, settings, and future current |
| Random Forest | Nonlinear interactions; averaging many trees |
| Histogram Gradient Boosting | Nonlinear sequential tree corrections; also quantile interval estimation |

Ridge, Random Forest and Gradient Boosting are **three ML models**. A neural network is not necessary for this initial study: the number of independent physical devices is unknown, and many overlapping rows do not establish a large independent sample.

## Which files?

Use the original `.mat` files. `scipy.io.loadmat(..., simplify_cells=True)` reads the measurements directly. The huge generated `.m` text files add no information to this workflow and are not executed.

- Default candidate cohort: every filename matching `Test_<number>_run_<number>.mat`, Tests 1–42, all runs. This is 104 of the 106 files in the current folder.
- Exclude `Test_13_run_1 1 (error setting up this run).mat` because its filename explicitly identifies a setup error.
- Exclude `test_rampup.mat` from the primary comparison as a ramp-up experiment. It remains available for a separately designed operational study.
- A candidate file contributes only if it has sufficient contiguous valid history and future observations with unchanged commanded settings. See **results/file_audit.csv** for actual inclusion and example counts, not just candidate membership.
- Tests 35–38 and 41 are useful event/trend case studies. Tests 39, 40 and 42 illustrate changes in operating conditions. These roles are not failure/health labels. The code does not hand-label them or reserve them based on their observed outcomes.
- Tests 1, 31 and 33 are not automatically discarded: problematic temperature or gate-waveform channels are not used here. This does not certify their current measurements.

## Data preparation and exact target timing

Only `measurement.steadyState.date`, `timeDomain.drainCurrent`, and `measurement.pwmTempControllerState` are used. SciPy may still need to load the complete MATLAB structure, including waveforms, into memory; files are processed sequentially.

1. Parse dates explicitly. Missing dates or years outside 2000–2100 are invalid. This is a screening rule, not proof that every remaining timestamp is correct.
2. Remove nonfinite currents and all duplicate steady-state timestamp records. Record backward steps before chronological sorting.
3. Associate each reading with the latest earlier controller record, at most 60 seconds old. No forward interpolation.
4. Split controller segments whenever lowTemp, highTemp, shutdownTemp, gateVoltage, supplyVoltage, switchingFrequency or dutyCycle changes. gateState is omitted from segment identity because normal control cycles can change it; it is not assumed constant.
5. Form calendar-aligned one-minute bins. Require at least 10 finite records, at least 45 seconds between first and last records, no adjacent gap above 5 seconds, complete settings, and one controller segment.
6. Require consecutive eligible minutes over both history and target interval, entirely within the same file and commanded-setting segment. Never concatenate runs into an assumed lifetime.
7. Default history = five minutes; default forecast horizon = five minutes. Example: observe bins 10:00–10:05, issue forecast at 10:05, predict mean over **10:09–10:10**, available at 10:10. Thus the target completion is five minutes after the forecast, with its averaging interval starting four minutes after the forecast.

Eligibility checks use future timestamps/settings to identify a **retrospective stable-condition evaluation subset**. Future measurements/settings are never features, but this conditional selection is not a fully prospective deployment simulation. Results do not measure performance during arbitrary future setting changes or missing-data episodes. Excluding these periods can make errors smaller.

Features: latest and lagged one-minute means, history mean/std/min/max/slope, average within-minute standard deviation, fraction below raw threshold 0.1, sample count, and latest commanded settings. The threshold is an exploratory recorded-value threshold, not a confirmed ampere-scale failure criterion. No flange/package temperature, RDS(on), transient amplitudes, filename IDs, absolute timestamps, elapsed lifetime, or future settings are predictors. Physical indicators can be added only after appropriate unit/scaling/synchronization checks.

## Validation and interpretation

- Outer five-fold GroupKFold holds out complete Test-number groups. All runs of a Test stay together.
- Inner three-fold GroupKFold selects parameters using only outer-training groups and MAE. Ridge standardization is inside its fitted pipeline. Feature list and cleaning rules are fixed in advance; no test-based feature selection is performed.
- These are **unverified Test groups, not confirmed devices**. Different Test numbers could share a device. Device leakage cannot be ruled out until mapping is independently verified. Also, this grouped experiment is not a chronological deployment backtest across recording dates.
- A complete CSV `test_group,device_id,evidence` can be supplied with `--device-map`. It must have one row per Test group and documentary evidence for the identity. Multiple Test groups may map to one device. Only use this option after verification; a nonempty evidence string alone is not factual verification. This format assumes a Test group does not contain several physical devices; use a finer mapping before analysis if that assumption is false.
- Report both sample-weighted MAE/RMSE and mean MAE across held-out groups. Also inspect per-file and per-group errors. Overlapping windows are correlated; row count is not an independent sample size.
- Quantile Gradient Boosting fits the 5th and 95th percentiles using outer-training data, using the point model's training-selected tree size. Crossing bounds are reordered and counted. Report actual outer-test coverage and interval width. A nominal 90% interval is not guaranteed to achieve 90% coverage.
- Positive prediction error means overprediction of current. It is **not lifetime overestimation risk**. Time-to-failure/time-to-event uncertainty remains pending because no defensible target endpoints were provided.
- Never declare failure at the end of a file, or call every low-current interval a failure.

## Running

From the project root in PowerShell (a local environment was created during implementation):

```powershell
& '.\.venv-mosfet\Scripts\python.exe' 'mosfet_forecasting\pipeline.py'
```

Fresh environment:

```powershell
python -m venv .venv-mosfet
& '.\.venv-mosfet\Scripts\python.exe' -m pip install -r 'mosfet_forecasting\requirements.txt'
& '.\.venv-mosfet\Scripts\python.exe' 'mosfet_forecasting\pipeline.py'
```

First extraction can take several minutes and substantial RAM. Per-file minute summaries are cached using resolved path, size and modification timestamp; original files are not modified. Change or delete the cache when extraction logic changes. Cache fingerprinting is not a cryptographic content verification of the dataset.

Example smaller exploratory cohort (not a substitute for the full comparison):

```powershell
& '.\.venv-mosfet\Scripts\python.exe' 'mosfet_forecasting\pipeline.py' --tests 35,36,37,38,41 --output 'mosfet_forecasting\case_results'
```

Sensitivity experiments (separate outputs; report all results, do not choose the best test result):

```powershell
& '.\.venv-mosfet\Scripts\python.exe' 'mosfet_forecasting\pipeline.py' --history 10 --output 'mosfet_forecasting\sensitivity_history10'
& '.\.venv-mosfet\Scripts\python.exe' 'mosfet_forecasting\pipeline.py' --without-settings --output 'mosfet_forecasting\sensitivity_no_settings'
& '.\.venv-mosfet\Scripts\python.exe' 'mosfet_forecasting\pipeline.py' --min-bin-count 100 --output 'mosfet_forecasting\sensitivity_count100'
```

The sample-count filter is one cleaning sensitivity; it is not a comprehensive quality-rule analysis. Operating-setting feature ablation does not isolate temperature or causal aging effects. Changes in cohort between sensitivity settings must be reported. When comparing runs, use their feature tables to identify common file/time examples; overall errors from different cohorts are not paired comparisons.

Run the primary experiment and all three variants together:

```powershell
& '.\.venv-mosfet\Scripts\python.exe' 'mosfet_forecasting\run_sensitivity.py'
```

This additionally writes `sensitivity_summary.csv` and `sensitivity_common_examples.csv`. The latter restricts scoring to file/time keys present in every variant. GroupKFold assignments can change when cohort sizes change, so common-example results still include training/fold differences; they are exploratory sensitivity results, not a controlled causal comparison. Predictions for each scored group always exclude that group from training.

## Outputs

`results/` contains:

- `file_audit.csv`: all file dispositions, invalid records, eligible minutes and forecast examples.
- `features.csv`: causal predictors and history/prediction/target timestamps, with validation groups.
- `run_metadata.json`: exact target, settings, grouping qualification and software version.
- `predictions.csv`: out-of-fold predictions for both baselines and all three ML models.
- `metrics_overall.csv`, `metrics_per_group.csv`, `metrics_per_file.csv`: point forecast errors.
- `tuning.json`: parameters and inner-validation scores selected separately for every outer fold.
- `prediction_intervals.csv`, `interval_coverage_per_group.csv`: held-out quantile intervals and coverage.
- `model_comparison.png`: group-averaged MAE chart suitable for a draft slide.

Fold models are refitted for evaluation and are not saved as deployment-ready models. Do not infer a final production model or validated RUL model from this experiment.

## Slides 9–11: honest status wording

**Slide 9 — Baseline and Machine Learning Implementation**

- Forecast a future one-minute mean current from five minutes of prior observations.
- Compare persistence and linear-trend baselines with Ridge, Random Forest, and Histogram Gradient Boosting.
- Use historical current features and recorded controller settings; restrict evaluation to eligible stable-setting intervals.
- This target represents an electrical measurement, not confirmed remaining useful life.

**Slide 10 — Exploratory Grouped Validation**

- Keep all runs sharing a Test number in the same outer fold; physical device mapping remains unverified.
- Tune model parameters within training groups using nested grouped validation.
- Report held-out MAE/RMSE by group and file, alongside baseline results.
- Evaluate empirical coverage of nominal 90% current-prediction intervals.
- Report sensitivity results only after the corresponding commands have actually run. Confirmed-device validation and lifetime-overestimation assessment remain pending.

**Slide 11 — Progress and Next Steps**

- Implemented auditable steady-state extraction, window filtering, causal features and model comparison.
- Insert the actual number of eligible files/examples and measured errors from the generated outputs.
- Review poorly predicted groups and operational-state effects before claiming degradation prediction.
- Verify physical device identities, units/scaling and failure/event definitions before extending to RUL.
- Incorporate empirical results and remaining limitations into the final report.

## Method references

- SciPy loadmat: https://docs.scipy.org/doc/scipy/reference/generated/scipy.io.loadmat.html
- Scikit-learn Ridge: https://scikit-learn.org/stable/modules/generated/sklearn.linear_model.Ridge.html
- Random Forest: https://scikit-learn.org/stable/modules/generated/sklearn.ensemble.RandomForestRegressor.html
- Histogram Gradient Boosting: https://scikit-learn.org/stable/modules/generated/sklearn.ensemble.HistGradientBoostingRegressor.html
- Grouped validation: https://scikit-learn.org/stable/modules/generated/sklearn.model_selection.GroupKFold.html
