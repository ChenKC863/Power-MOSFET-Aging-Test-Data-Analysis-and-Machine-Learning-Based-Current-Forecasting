"""Run prespecified variants; compare on shared out-of-fold example keys."""
from pathlib import Path
import subprocess, sys
import pandas as pd

HERE = Path(__file__).resolve().parent
VARIANTS = {
    'results': [],
    'sensitivity_history10': ['--history', '10'],
    'sensitivity_no_settings': ['--without-settings'],
    'sensitivity_count100': ['--min-bin-count', '100'],
}

if __name__ == '__main__':
    tables, predictions = [], {}
    for name, flags in VARIANTS.items():
        subprocess.run([sys.executable, str(HERE/'pipeline.py'), '--output', str(HERE/name), *flags], check=True)
        table = pd.read_csv(HERE/name/'metrics_overall.csv')
        table.insert(0, 'variant', name)
        tables.append(table)
        predictions[name] = pd.read_csv(HERE/name/'predictions.csv')
    pd.concat(tables).to_csv(HERE/'sensitivity_summary.csv', index=False)
    keys = ['file', 'prediction_time', 'target_start', 'model']
    shared = None
    for p in predictions.values():
        index = pd.MultiIndex.from_frame(p[keys])
        shared = index if shared is None else shared.intersection(index)
    rows = []
    for name, p in predictions.items():
        common = p.set_index(keys).loc[shared].reset_index()
        common['absolute_error'] = (common.prediction-common.target).abs()
        for model, g in common.groupby('model'):
            rows.append({'variant': name, 'model': model, 'shared_examples': len(g),
                         'MAE': g.absolute_error.mean(),
                         'macro_group_MAE': g.groupby('validation_group').absolute_error.mean().mean()})
    pd.DataFrame(rows).to_csv(HERE/'sensitivity_common_examples.csv', index=False)
