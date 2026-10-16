# Validation Scope and Operating Transitions

## Placement
Add after current slide 14, **Training, Validation and Testing**, and before current slide 15, **Evaluation Metrics**. In the revised 21-slide deck this is slide 15, with printed label 12A. The existing engineering case study remains in the deck and shifts to slide 19. Existing printed page numbers are retained.

## Slide text

### What the evaluation supports
- Five outer folds hold out Test-number groups. The evaluated dataset contains 9,304 examples from 83 files and 33 Test-number groups.
- Physical-device identities and cross-run mappings remain unverified. These results support comparisons on held-out Test-number groups, rather than a claim of verified cross-device generalization.

### Which operating intervals qualify
- Five minutes of historical measurements predict a future one-minute mean current ending five minutes after prediction issuance.
- Eligibility requires consecutive valid minute bins and unchanged recorded controller settings throughout the history-to-target span.
- Selection uses future setting records retrospectively. Historical-only model inputs do not make this an unrestricted online evaluation.

### What remains untested
- Windows crossing recorded setting changes are excluded. Forecast accuracy and interval coverage during these transitions remain unestablished.
- Unchanged commands do not guarantee unchanged actual drive, load or temperature. The same stated limitation applies to missing-data episodes and unsupported operating regimes.
- Before deployment, evaluate stable periods and transition periods separately using eligibility decisions available at prediction time. Report errors, interval coverage and the proportion of forecast opportunities evaluated.

**Claim:** Exploratory current forecasting on held-out Test-number groups during retrospectively selected intervals with unchanged recorded controller settings.

## Presenter notes and engineering interpretation
The current results do not show whether performance remains acceptable when settings change. A change could make an already-issued forecast inaccurate, and the present evaluation removes such a history-to-target window from the scored dataset. State that transition performance is unknown; do not assert that the model necessarily fails or remains valid.

A proposed deployment policy, not implemented by this documentation update, is to flag an outstanding forecast when a recorded setting change occurs and withhold new forecasts until a predefined history/data-quality rule is satisfied. Obtaining five valid history minutes alone does not prove acceptable forecasting performance. Future controls may change again. Any gate, fallback baseline or recovery rule must be evaluated prospectively with coverage of forecast opportunities and errors both reported.

For a subsequent transition evaluation, define issuance-time eligibility from historical information only, retain the targets even when settings subsequently change, and label transition occurrence after prediction solely for stratified scoring. Compare stable versus transition MAE, RMSE, signed bias, and quantile-model coverage/width, with counts by Test group. Keep preprocessing and tuning inside training folds. Confirm physical-device mapping before claiming independent-device validation. No transition-model training or new transition evaluation was executed for this slide.

The 9,304 examples overlap and are dependent. Test-number separation does not prove independence of physical devices. Selection by unchanged commands also does not establish constant measured conditions or validated RUL/failure interpretation.

## Evidence in the existing implementation
Paths are relative to the repository root. Line numbers refer to the version inspected for this update.

| Evidence | Location |
|---|---|
| Settings define segments, with backward controller alignment limited to 60 seconds | `mosfet_forecasting/pipeline.py`, lines 40–48 |
| Minute-level data-quality and known-setting requirements | `mosfet_forecasting/pipeline.py`, lines 51–57 |
| History-to-target span must be consecutive and in one setting segment | `mosfet_forecasting/pipeline.py`, lines 66–74 |
| Historical feature inputs and target timestamps | `mosfet_forecasting/pipeline.py`, lines 75–87 |
| Outer grouped validation and inner grouped tuning | `mosfet_forecasting/pipeline.py`, lines 92–110 |
| Test-number groups used by default; optional device mapping | `mosfet_forecasting/pipeline.py`, lines 211–220 |
| Actual run mode, sample/file/group counts and retrospective selection | `mosfet_forecasting/results/run_metadata.json` |

## Wording to use consistently
Use **held-out Test-number groups**, **unchanged recorded controller settings**, and **transition performance has not been evaluated**.

Avoid **independent-device validation**, **cross-device generalization established**, **constant operating conditions**, or **suitable for arbitrary operating transitions** unless additional evidence supports those statements.

This update documents the existing validation scope. It does not change the model, saved predictions or reported performance metrics.
