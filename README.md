# Power-MOSFET-Aging-Test-Data-Analysis-and-Machine-Learning-Based-Current-Forecasting
Exploratory analysis of MOSFET aging-test data, including data-quality screening, current forecasting with baseline and machine-learning models, nested validation by Test-number group, prediction uncertainty, and engineering case studies.

## Dataset

- **Source**: [Prognostics Center of Excellence Data Set Repository](https://www.nasa.gov/intelligent-systems-division/discovery-and-systems-health/pcoe/pcoe-data-set-repository/)

  Then search the key words "Metal-Oxide-Semiconductor Field-Effect Transistor (MOSFET) Thermal Overstress Aging"

## 📌 Overview

This project investigates power MOSFET aging-test measurements and develops a reproducible workflow for forecasting future current.

The analysis combines data-quality screening, historical feature construction, baseline comparisons, machine-learning models, and engineering interpretation of prediction errors.

**Current scope:** Forecasting measured current during retrospectively selected intervals with unchanged recorded controller settings. The study does not establish physical failure mechanisms, remaining useful life (RUL), or generalization across confirmed independent devices.

## 🎯 Objectives

- Examine the measurement structure, timestamps, controller settings, and data-quality issues.
- Construct forecasting examples using historical measurements.
- Compare simple forecasting baselines with machine-learning models.
- Evaluate prediction errors across held-out Test-number groups.
- Assess prediction uncertainty and investigate groups with different forecasting performance.
- Identify additional measurements and metadata needed for reliability interpretation.

## 📊 Dataset Used in This Study

| Item | Count |
|---|---:|
| Distinct local MAT files in the inventory | 106 |
| Files matching the primary experiment filename rule | 104 |
| Files contributing eligible forecasting examples | 83 |
| Evaluated Test-number groups | 33 |
| Evaluated forecasting examples | 9,304 |

The primary forecasting experiment excludes the explicitly named setup-error file and the ramp-up file. Other files contribute only when they satisfy the data-quality and forecasting-window requirements.

**Test numbers are grouping identifiers, not verified physical-device identities.** Multiple files or runs should not automatically be interpreted as independent devices or complete lifetime trajectories.

The pipeline reads the original `.mat` files using SciPy. Converted `.m` files are not required.

#### What the Original Measurements Look Like
`Test_20_run_1.mat`

<img width="535" height="306" alt="image" src="https://github.com/user-attachments/assets/1a3113bc-d17f-49f0-a6bb-a4b2fa14e958" />

`Test_27_run_4.mat`

<img width="535" height="306" alt="image" src="https://github.com/user-attachments/assets/6a403049-d1eb-4d70-ad0c-75b71ad66691" />

**Figure 1. Original current readings before forecasting feature construction.**
The plots show individual readings from `Test_20_run_1.mat` and `Test_27_run_4.mat` over the first 60 minutes, using the same time and recorded-current scales. No averaging or operating-condition filtering is applied in this illustration.

Both recordings contain higher-current and low-current readings. These patterns alone do not establish physical degradation or failure.
Current values are shown on the original recorded scale; physical units and calibration remain unverified but at least the same unit scale.

## ⚙️ Forecasting Workflow

1. Read steady-state current, timestamps, and controller records.
2. Screen invalid values and timestamps, and remove duplicate steady-state timestamps.
3. Align measurements with earlier controller records.
4. Construct eligible one-minute summaries within recorded-setting segments.
5. Generate historical features and future targets.
6. Train and tune models within grouped cross-validation.
7. Export predictions, evaluation metrics, and prediction intervals.
8. Examine selected prediction errors alongside original measurement context.

#### Pipeline Architecture

<img width="1189" height="543" alt="image" src="https://github.com/user-attachments/assets/2d4b749c-a6da-4cd6-80e3-d93608093442" />

**Figure 2. Implemented current-forecasting pipeline.**
The workflow screens MATLAB measurements, constructs eligible one-minute bins and five-minute historical features, and evaluates forecasts using nested cross-validation grouped by Test number.

Eligibility is determined retrospectively using recorded settings through the target interval. Forecasting features use historical measurements only. Test-number groups are not confirmed independent physical devices.

### Prediction Target

The target is the mean of valid steady-state current readings within one future minute, including low-current states.

The default configuration uses five minutes of history:

| Step | Example |
|---|---|
| Historical measurements | 10:00–10:05 |
| Forecast issued | 10:05 |
| Target averaging interval | 10:09–10:10 |
| Target completed | Five minutes after issuance |

Features include lagged current means, historical statistics and slope, within-minute variability, low-current fractions, sample counts, and recorded controller settings.

## 🤖 Models

| Method | Description |
|---|---|
| Persistence / naïve forecast | Uses the latest observed one-minute mean |
| Linear trend | Extrapolates the recent least-squares slope |
| Ridge regression | Regularized linear regression with standardized features |
| Random Forest | Ensemble of regression trees |
| Histogram Gradient Boosting | Sequentially boosted regression trees |

## 🧪 Validation Strategy

- **Five outer grouped folds** evaluate held-out Test-number groups.
- **Three inner grouped folds** tune model parameters within the outer training data.
- Runs sharing a Test number remain together.
- Ridge standardization is fitted within the training pipeline.

Training, validation, and testing are roles assigned within these folds. The reported experiment does not include an additional untouched final test set.

### Validation Boundary

Forecasting examples require valid consecutive minute bins and unchanged recorded controller settings throughout the history-to-target span.

This eligibility rule uses future setting records retrospectively, although model inputs use historical information only.

Consequently:

- Performance during controller-setting transitions remains unestablished.
- Test-number separation does not confirm physical-device independence.
- Overlapping forecasting examples are dependent.
- Unchanged commands do not guarantee unchanged actual drive, load, or temperature.

## 📈 Results

The following results combine held-out predictions from all five outer folds.

| Method | MAE | RMSE | Mean MAE across groups |
|---|---:|---:|---:|
| **Ridge regression** | **0.02050** | **0.04300** | **0.03236** |
| Persistence | 0.02437 | 0.04615 | 0.03524 |
| Random Forest | 0.02599 | 0.05164 | 0.04593 |
| Histogram Gradient Boosting | 0.03727 | 0.08191 | 0.04717 |
| Linear trend | 0.03935 | 0.06222 | 0.05203 |

Errors are expressed in the **recorded current scale**. Physical units and calibration factors remain unverified.

Ridge achieved approximately **15.9% lower overall MAE** and **8.2% lower mean group MAE** than Persistence. These improvements use the unrounded results.

Persistence remained competitive, outperforming Random Forest and Histogram Gradient Boosting under the evaluated configurations.

### Prediction Uncertainty

Additional Histogram Gradient Boosting models estimated the 5th and 95th conditional quantiles, forming nominal 90% prediction intervals.

- Held-out examples: **9,304**
- Targets inside their intervals: **8,244**
- Empirical coverage: **88.6%**
- Average interval width: **0.12258 in the recorded current scale**

Coverage varied across groups. These intervals belong to the quantile Gradient Boosting models; they are not uncertainty bounds around Ridge predictions or estimates of remaining-life risk.

Selected group-level results illustrate the variation:

| Test group | Examples | Inside interval | Coverage | Mean interval width |
|---|---:|---:|---:|---:|
| Test 20 | 132 | 132 | 100.0% | 0.92424 |
| Test 27 | 111 | 43 | 38.7% | 0.16925 |

Widths are expressed in the recorded current scale.
Coverage and width should be assessed together. These statistics cover all eligible examples in each group, not only the first-hour plots. Overlapping examples are dependent.

## 🔍 Engineering Case Studies

Among groups with at least 100 evaluated examples, the case study selects the lowest and highest Ridge MAE.

| Case | Group examples | Ridge MAE | Persistence MAE |
|---|---:|---:|---:|
| Lower error: Test 27 | 111 | 0.01270 | 0.01683 |
| Higher error: Test 20 | 132 | 0.07221 | 0.03117 |

The representative runs are `Test_27_run_4.mat` and `Test_20_run_1.mat`.

Test 20 illustrates systematic Ridge underprediction and an abrupt current change missed by both methods. Associated temperature-channel changes motivate investigation of actual controller behavior, synchronized electrical measurements, and calibration.

These are post-hoc illustrations of existing held-out results. They do not establish a physical failure cause.

#### Representative Forecasting Comparisons

Five forecasting methods for selected examples from Test_20_run_1 and Test_27_run_4, respectively.

<img width="574" height="263" alt="image" src="https://github.com/user-attachments/assets/73948609-9d23-48bf-bcec-492be281ceff" />

<img width="574" height="263" alt="image" src="https://github.com/user-attachments/assets/8cc66031-59c1-4636-aa98-bfcfbc530cdd" />

**Figure 3. Five-method forecasts within the first 60 minutes of two recordings.**

Predictions are plotted at the end of their target minute. Blank regions contain no evaluated forecasting examples. The two panels use different vertical scales.

The displayed curves show model predictions; observed target means are not included in this version. The MAE values shown above the panels summarize all eligible examples in the corresponding Test-number group, not only the displayed first-hour examples.

The cases were selected retrospectively to illustrate contrasting group-level Ridge errors. They do not establish failure mechanisms or remaining useful life.

## 🚀 Reproduction

### 1. Prepare the Original Dataset

Download the dataset from the NASA source above and place the original MAT files directly inside:

```text
MOSFET_Thermal_Overstress_Aging/
```

Preserve the original filenames. The pipeline does not download the dataset automatically.

### 2. Install Dependencies

The recorded experiment used **Python 3.10.6**. Run the following from the repository root in Windows PowerShell:

```powershell
python -m venv .venv-mosfet

& '.\.venv-mosfet\Scripts\python.exe' -m pip install -r '.\mosfet_forecasting\requirements.txt'
```

### 3. Run the Forecasting Pipeline

```powershell
& '.\.venv-mosfet\Scripts\python.exe' '.\mosfet_forecasting\pipeline.py'
```

Results are written to `mosfet_forecasting/results/`. Running this command again replaces the default result files.

Initial extraction may require substantial memory because MAT files contain nested measurement structures.

### 4. Reproduce the Engineering Cases

With the primary result files and original MAT measurements available:

```powershell
& '.\.venv-mosfet\Scripts\python.exe' '.\mosfet_forecasting\engineering_cases\analyze_cases.py'

& '.\.venv-mosfet\Scripts\python.exe' '.\mosfet_forecasting\engineering_cases\write_report.py'

& '.\.venv-mosfet\Scripts\python.exe' '.\mosfet_forecasting\engineering_cases\export_white_charts.py'
```

These commands generate case-analysis outputs, a Markdown report, and white-background JPG charts.

The written case interpretation contains statements specific to the current results and must be reviewed if the data or selected cases change.

## 📂 Main Outputs

Paths below are relative to `mosfet_forecasting/`.

| Output | Purpose |
|---|---|
| `results/file_audit.csv` | File screening and example counts |
| `results/features.csv` | Historical features and future targets |
| `results/predictions.csv` | Held-out predictions and fold assignments |
| `results/metrics_overall.csv` | Overall model comparison |
| `results/metrics_per_group.csv` | Group-specific prediction errors |
| `results/prediction_intervals.csv` | Held-out prediction intervals |
| `results/interval_coverage_per_group.csv` | Group-level interval coverage |
| `results/run_metadata.json` | Recorded environment and experiment configuration |
| `engineering_cases/case_summary.json` | Numerical case-study summaries |
| `engineering_cases/Engineering_Judgment.md` | Interpretation and engineering follow-up |
