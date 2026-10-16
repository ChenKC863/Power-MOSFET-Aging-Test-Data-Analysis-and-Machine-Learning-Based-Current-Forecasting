"""Auditable steady-state forecasting; no failure labels or inferred unit conversion."""
from pathlib import Path
import argparse, gc, hashlib, json, os, platform, re
import numpy as np
import pandas as pd
from scipy.io import loadmat
from sklearn import __version__ as sklearn_version
from sklearn.ensemble import RandomForestRegressor, HistGradientBoostingRegressor
from sklearn.linear_model import Ridge
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import StandardScaler
from sklearn.model_selection import GroupKFold, GridSearchCV
from sklearn.metrics import mean_absolute_error, mean_squared_error
from threadpoolctl import threadpool_limits

ROOT = Path(__file__).resolve().parents[1]
SETTINGS = ['lowTemp', 'highTemp', 'shutdownTemp', 'gateVoltage', 'supplyVoltage', 'switchingFrequency', 'dutyCycle']

def records(x):
    return [x] if isinstance(x, dict) else list(np.asarray(x, dtype=object).ravel())

def dates(values):
    t = pd.DatetimeIndex(pd.to_datetime(values, format='%m/%d/%Y %H:%M:%S.%f', errors='coerce'))
    return t.where((t.year >= 2000) & (t.year <= 2100))

def extract(path):
    """One MAT at a time. Transient arrays are loaded by SciPy but not used."""
    m = loadmat(path, simplify_cells=True, variable_names=['measurement'])['measurement']
    ss = records(m['steadyState'])
    frame = pd.DataFrame([{'time': r.get('date'), 'current': r.get('timeDomain', {}).get('drainCurrent', np.nan)} for r in ss])
    frame['time'] = dates(frame.time)
    frame['current'] = pd.to_numeric(frame.current, errors='coerce')
    audit = {'file': path.name, 'bytes': path.stat().st_size, 'mtime_ns': path.stat().st_mtime_ns, 'steady_records': len(frame)}
    audit['invalid_time_or_current'] = int((frame.time.isna() | ~np.isfinite(frame.current)).sum())
    frame = frame[frame.time.notna() & np.isfinite(frame.current)].copy()
    audit['backward_timestamp_steps'] = int((frame.time.diff().dt.total_seconds() < 0).sum())
    duplicate = frame.time.duplicated(keep=False)
    audit['duplicate_timestamp_records_removed'] = int(duplicate.sum())
    frame = frame[~duplicate].sort_values('time')
    pwm = records(m['pwmTempControllerState'])
    ctrl = pd.DataFrame([{**{k: r.get(k, np.nan) for k in SETTINGS}, 'time': r.get('time')} for r in pwm])
    ctrl['time'] = dates(ctrl.time)
    ctrl = ctrl.dropna(subset=['time']).sort_values('time').drop_duplicates('time', keep='last')
    for k in SETTINGS:
        ctrl[k] = pd.to_numeric(ctrl[k], errors='coerce')
    ctrl['segment'] = ctrl[SETTINGS].ne(ctrl[SETTINGS].shift()).any(axis=1).cumsum()
    ctrl = ctrl.rename(columns={k: 'setting_' + k for k in SETTINGS})
    frame = pd.merge_asof(frame, ctrl, on='time', direction='backward', tolerance=pd.Timedelta(seconds=60))
    audit['missing_or_stale_settings'] = int(frame.filter(like='setting_').isna().any(axis=1).sum())
    bins = []
    for minute, g in frame.groupby(frame.time.dt.floor('min')):
        gaps = g.time.diff().dt.total_seconds()
        # Complete minute coverage, finite settings, stable commanded settings.
        if len(g) < 10 or (g.time.iloc[-1]-g.time.iloc[0]).total_seconds() < 45 or gaps.max() > 5:
            continue
        if g.segment.isna().any() or g.segment.nunique() != 1 or g.filter(like='setting_').isna().any().any():
            continue
        bins.append({'time': minute, 'mean': g.current.mean(), 'std': g.current.std(ddof=0),
                     'low_fraction': (g.current < .1).mean(), 'count': len(g),
                     'segment': g.segment.iloc[0], **g.filter(like='setting_').iloc[-1].to_dict()})
    audit['eligible_minutes'] = len(bins)
    del m, ss, pwm, frame, ctrl
    gc.collect()
    return pd.DataFrame(bins), audit

def features(b, filename, history, horizon):
    out = []
    if b.empty:
        return out
    b = b.sort_values('time').reset_index(drop=True)
    for i in range(history - 1, len(b) - horizon):
        span = b.iloc[i-history+1:i+horizon+1]
        if not (span.time.diff().dropna() == pd.Timedelta(minutes=1)).all() or span.segment.nunique() != 1:
            continue
        past = b.iloc[i-history+1:i+1]
        y = past['mean'].to_numpy()
        slope = np.polyfit(np.arange(history), y, 1)[0]
        row = {'file': filename, 'test_group': re.match(r'(Test_\d+)_', filename).group(1),
               'history_start': past.time.iloc[0], 'prediction_time': b.time.iloc[i] + pd.Timedelta(minutes=1),
               'target_start': b.time.iloc[i+horizon], 'target_end': b.time.iloc[i+horizon] + pd.Timedelta(minutes=1),
               'target': b['mean'].iloc[i+horizon], 'persistence': y[-1],
               'linear_trend': y[-1] + slope*horizon,
               'x_last': y[-1], 'x_mean': y.mean(), 'x_std': y.std(), 'x_slope': slope,
               'x_min': y.min(), 'x_max': y.max(), 'x_within_std': past['std'].mean(),
               'x_low_fraction': past.low_fraction.mean(), 'x_count': past['count'].mean()}
        row.update({'x_lag_' + str(j): y[-1-j] for j in range(history)})
        row.update({'x_' + k: b[k].iloc[i] for k in b.columns if k.startswith('setting_')})
        out.append(row)
    return out

@threadpool_limits.wrap(limits=2)
def evaluate(df, out, folds, without_settings=False):
    cols = [c for c in df if c.startswith('x_') and not (without_settings and c.startswith('x_setting_'))]
    groups = df.validation_group
    if groups.nunique() < 4:
        raise ValueError('At least four eligible validation groups are required for nested grouped validation.')
    outer = GroupKFold(n_splits=min(folds, groups.nunique()))
    predictions, tuning, intervals = [], [], []
    for fold, (train, test) in enumerate(outer.split(df[cols], df.target, groups), 1):
        tr, te = df.iloc[train], df.iloc[test]
        inner = GroupKFold(n_splits=min(3, tr.validation_group.nunique()))
        models = {
            'Ridge': (make_pipeline(StandardScaler(), Ridge()), {'ridge__alpha': [1., 100.]}),
            'RandomForest': (RandomForestRegressor(n_estimators=100, random_state=42, n_jobs=2), {'min_samples_leaf': [5, 20]}),
            'HistGradientBoosting': (HistGradientBoostingRegressor(max_iter=100, early_stopping=False, random_state=42), {'max_leaf_nodes': [7, 15]})}
        results = {'Persistence': te.persistence.to_numpy(), 'LinearTrend': te.linear_trend.to_numpy()}
        for name, (model, grid) in models.items():
            search = GridSearchCV(model, grid, cv=inner, scoring='neg_mean_absolute_error', n_jobs=1)
            search.fit(tr[cols], tr.target, groups=tr.validation_group)
            results[name] = search.predict(te[cols])
            tuning.append({'fold': fold, 'model': name, 'parameters': search.best_params_, 'inner_MAE': -search.best_score_})
            if name == 'HistGradientBoosting':
                bounds = []
                for q in [.05, .95]:
                    qm = HistGradientBoostingRegressor(loss='quantile', quantile=q, max_iter=100,
                         early_stopping=False, random_state=42, **search.best_params_)
                    qm.fit(tr[cols], tr.target)
                    bounds.append(qm.predict(te[cols]))
                ip = te[['file', 'validation_group', 'prediction_time', 'target']].copy()
                ip['lower'], ip['upper'] = np.minimum(*bounds), np.maximum(*bounds)
                ip['quantile_crossing'] = bounds[0] > bounds[1]
                ip['covered'] = (ip.target >= ip.lower) & (ip.target <= ip.upper)
                ip['width'] = ip.upper - ip.lower
                ip['fold'] = fold
                intervals.append(ip)
        for name, pred in results.items():
            p = te[['file', 'test_group', 'validation_group', 'prediction_time', 'target_start', 'target_end', 'target', 'persistence']].copy()
            p['model'], p['prediction'], p['fold'] = name, pred, fold
            predictions.append(p)
        print(f'Completed outer fold {fold}; held out {te.validation_group.nunique()} groups', flush=True)
    pred = pd.concat(predictions, ignore_index=True)
    pred.to_csv(out / 'predictions.csv', index=False)
    ip = pd.concat(intervals, ignore_index=True)
    ip.to_csv(out / 'prediction_intervals.csv', index=False)
    ip.groupby('validation_group').agg(n=('target', 'size'), coverage=('covered', 'mean'), mean_width=('width', 'mean'), crossing_fraction=('quantile_crossing', 'mean')).to_csv(out / 'interval_coverage_per_group.csv')
    def metrics(g):
        e = g.prediction - g.target
        return {'n': len(g), 'MAE': mean_absolute_error(g.target, g.prediction),
                'RMSE': np.sqrt(mean_squared_error(g.target, g.prediction)), 'bias': e.mean(),
                'positive_error_fraction': (e > 0).mean()}
    rows = []
    for (name, group), g in pred.groupby(['model', 'validation_group']):
        rows.append({'model': name, 'validation_group': group, **metrics(g)})
    per = pd.DataFrame(rows)
    per.to_csv(out / 'metrics_per_group.csv', index=False)
    pd.DataFrame([{'model': name, 'file': file, **metrics(g)} for (name, file), g in pred.groupby(['model', 'file'])]).to_csv(out / 'metrics_per_file.csv', index=False)
    overall = pd.DataFrame([{'model': name, **metrics(g), 'macro_group_MAE': per.loc[per.model == name, 'MAE'].mean()} for name, g in pred.groupby('model')])
    overall.to_csv(out / 'metrics_overall.csv', index=False)
    (out / 'tuning.json').write_text(json.dumps(tuning, indent=2), encoding='utf-8')
    print(overall.to_string(index=False), flush=True)
    os.environ.setdefault('MPLCONFIGDIR', str(ROOT / 'mosfet_forecasting' / '.matplotlib'))
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    fig, ax = plt.subplots(figsize=(9, 4.5))
    ordered = overall.sort_values('macro_group_MAE')
    ax.barh(ordered.model, ordered.macro_group_MAE)
    ax.invert_yaxis()
    ax.set_xlabel('Mean of held-out group MAEs (raw current units)')
    ax.set_title('Exploratory grouped forecasting comparison')
    fig.tight_layout()
    fig.savefig(out / 'model_comparison.png', dpi=180)
    plt.close(fig)

def main():
    p = argparse.ArgumentParser()
    p.add_argument('--data', type=Path, default=ROOT / 'MOSFET_Thermal_Overstress_Aging')
    p.add_argument('--output', type=Path, default=ROOT / 'mosfet_forecasting' / 'results')
    p.add_argument('--tests', help='Optional comma-separated Test numbers; default all numbered tests')
    p.add_argument('--history', type=int, default=5)
    p.add_argument('--horizon', type=int, default=5, help='Minutes from last observed bin start to target bin start')
    p.add_argument('--folds', type=int, default=5)
    p.add_argument('--min-bin-count', type=int, default=10, help='Additional sample-count sensitivity filter')
    p.add_argument('--without-settings', action='store_true', help='Operating-setting feature ablation; segmentation still applies')
    p.add_argument('--device-map', type=Path, help='CSV: test_group,device_id,evidence; complete independently verified mapping only')
    args = p.parse_args()
    if args.history < 2 or args.horizon < 1 or args.folds < 2:
        p.error('history >= 2, horizon >= 1 and folds >= 2 required')
    args.output.mkdir(parents=True, exist_ok=True)
    cache = ROOT / 'mosfet_forecasting' / 'cache'
    cache.mkdir(exist_ok=True)
    chosen = set(map(int, args.tests.split(','))) if args.tests else None
    rows, audits = [], []
    files = sorted(args.data.glob('*.mat'))
    for path in files:
        match = re.fullmatch(r'Test_(\d+)_run_(\d+)\.mat', path.name)
        if not match or (chosen and int(match[1]) not in chosen):
            audits.append({'file': path.name, 'status': 'excluded_setup_or_rampup' if not match else 'outside_requested_cohort'})
            continue
        key = hashlib.sha256(f'v1:{path.resolve()}:{path.stat().st_size}:{path.stat().st_mtime_ns}'.encode()).hexdigest()[:20]
        cached = cache / (key + '.json')
        print('Reading ' + path.name, flush=True)
        if cached.exists():
            obj = json.loads(cached.read_text(encoding='utf-8'))
            b, audit = pd.DataFrame(obj['bins']), obj['audit']
            if not b.empty:
                b['time'] = pd.to_datetime(b.time)
        else:
            b, audit = extract(path)
            cached.write_text(json.dumps({'bins': json.loads(b.to_json(orient='records', date_format='iso')), 'audit': audit}), encoding='utf-8')
        if not b.empty:
            b = b[b['count'] >= args.min_bin_count]
        r = features(b, path.name, args.history, args.horizon)
        audit.update({'examples': len(r), 'status': 'included' if r else 'no_eligible_windows'})
        rows.extend(r)
        audits.append(audit)
    pd.DataFrame(audits).to_csv(args.output / 'file_audit.csv', index=False)
    df = pd.DataFrame(rows)
    if df.empty:
        raise ValueError('No eligible examples; inspect file_audit.csv')
    df['validation_group'] = df.test_group
    mode = 'exploratory_Test_number_groups_NOT_verified_devices'
    if args.device_map:
        mapping = pd.read_csv(args.device_map, dtype=str)
        if mapping.test_group.duplicated().any() or mapping[['device_id', 'evidence']].fillna('').apply(lambda s: s.str.strip().eq('')).any().any():
            raise ValueError('Mapping requires unique Test groups, nonempty device IDs and evidence.')
        df['validation_group'] = df.test_group.map(mapping.set_index('test_group').device_id)
        if df.validation_group.isna().any():
            raise ValueError('Incomplete device mapping')
        mode = 'user_supplied_verified_device_mapping'
    df.to_csv(args.output / 'features.csv', index=False)
    metadata = {'mode': mode, 'target': 'future complete one-minute mean drainCurrent, raw recorded units',
                'history_minutes': args.history, 'horizon_bin_start_minutes': args.horizon,
                'target_completion_minutes_after_prediction': args.horizon,
                'examples': len(df), 'files_with_examples': df.file.nunique(), 'groups': df.validation_group.nunique(),
                'python': platform.python_version(), 'sklearn': sklearn_version,
                'min_bin_count': args.min_bin_count, 'without_settings': args.without_settings,
                'selection': 'Retrospectively restrict history-to-target span to stable known commanded settings and eligible bins; conditional forecast, not an unrestricted deployment simulation.'}
    (args.output / 'run_metadata.json').write_text(json.dumps(metadata, indent=2), encoding='utf-8')
    evaluate(df, args.output, args.folds, args.without_settings)

if __name__ == '__main__':
    main()
