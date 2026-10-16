"""Reproduce post-hoc engineering case comparisons without retraining models."""
from pathlib import Path
import sys, json, gc
import numpy as np
import pandas as pd
from scipy.io import loadmat

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
sys.path.insert(0, str(HERE.parent))
from pipeline import records, dates

def main():
    pred = pd.read_csv(HERE.parent / 'results/predictions.csv')
    feat = pd.read_csv(HERE.parent / 'results/features.csv')
    ridge = pred[pred.model.eq('Ridge')].copy()
    ridge['error'] = ridge.prediction-ridge.target
    ranking = ridge.groupby('test_group').agg(n=('error','size'), ridge_mae=('error',lambda x:x.abs().mean()))
    ranking = ranking[ranking.n.ge(100)].sort_values('ridge_mae')
    ranking.to_csv(HERE/'selection_ranking.csv')
    selected = [ranking.index[0], ranking.index[-1]]
    keys = ['file','prediction_time','target_start','target_end']
    joined = ridge[ridge.test_group.isin(selected)].merge(feat[keys+[c for c in feat if c.startswith('x_')]], on=keys, validate='one_to_one')
    for k in keys[1:]: joined[k] = pd.to_datetime(joined[k])
    joined.to_csv(HERE/'case_predictions.csv',index=False)
    summaries, slides = [], []
    for group in selected:
        g = joined[joined.test_group.eq(group)].copy()
        counts = g.groupby('file').size().sort_values(ascending=False,kind='stable')
        filename = counts.index[0]
        r = g[g.file.eq(filename)].sort_values('target_end').copy()
        print('Extracting context: '+filename,flush=True)
        m = loadmat(ROOT/'MOSFET_Thermal_Overstress_Aging'/filename,simplify_cells=True,variable_names=['measurement'])['measurement']
        raw = pd.DataFrame([{'time':v.get('date'), **v.get('timeDomain',{})} for v in records(m['steadyState'])])
        raw['time'] = dates(raw.time)
        raw = raw.dropna(subset=['time']).sort_values('time')
        raw = raw[~raw.time.duplicated(keep=False)]
        cols = ['drainCurrent','supplyVoltage','packageTemperature','flangeTemperature']
        for c in cols: raw[c] = pd.to_numeric(raw[c],errors='coerce')
        minute = raw.groupby(raw.time.dt.floor('min'))[cols].mean()
        minute['low_fraction'] = raw.groupby(raw.time.dt.floor('min')).drainCurrent.apply(lambda x:(x.dropna()<.1).mean())
        minute.to_csv(HERE/(group+'_representative_context.csv'))
        r = r.merge(minute, left_on='target_start',right_index=True,how='left',validate='one_to_one')
        if not np.allclose(r.target,r.drainCurrent,atol=1e-10): raise ValueError('Target alignment mismatch')
        r.to_csv(HERE/(group+'_representative_predictions.csv'),index=False)
        peak = r.loc[r.error.abs().idxmax()]
        # Context episode: contiguous scored block containing maximum absolute error.
        segments = r.target_end.diff().ne(pd.Timedelta(minutes=1)).cumsum()
        block = r[segments.eq(segments.loc[peak.name])]
        s = dict(group=group,n=len(g),ridge_mae=float(g.error.abs().mean()),persistence_mae=float((g.persistence-g.target).abs().mean()),bias=float(g.error.mean()),underpredicted=int(g.error.lt(0).sum()),fold=int(g.fold.iloc[0]),file=filename,run_n=len(r),run_ridge_mae=float(r.error.abs().mean()),run_persistence_mae=float((r.persistence-r.target).abs().mean()),peak_target_start=str(peak.target_start),peak_target_end=str(peak.target_end),peak_error=float(peak.error),peak_target=float(peak.target),peak_ridge=float(peak.prediction),peak_persistence=float(peak.persistence),block_start=str(block.target_start.min()),block_end=str(block.target_end.max()),block_n=len(block),block_mae=float(block.error.abs().mean()),settings={c.removeprefix('x_setting_'):float(r[c].iloc[0]) for c in r if c.startswith('x_setting_')},package_temperature_range=[float(r.packageTemperature.min()),float(r.packageTemperature.max())],measured_supply_range=[float(r.supplyVoltage.min()),float(r.supplyVoltage.max())],low_fraction_range=[float(r.low_fraction.min()),float(r.low_fraction.max())])
        summaries.append(s)
        # Complete minute timeline with null values for unscored gaps.
        chart = r.set_index('target_end').reindex(pd.date_range(r.target_end.min(),r.target_end.max(),freq='min'))
        slides.append({'summary':s,'labels':[t.strftime('%H:%M') for t in chart.index], 'series':{c:[None if pd.isna(v) else float(v) for v in chart[c]] for c in ['target','persistence','prediction']}})
        del m,raw; gc.collect()
    (HERE/'case_summary.json').write_text(json.dumps(summaries,indent=2),encoding='utf-8')
    (HERE/'slide_data.json').write_text(json.dumps(slides,indent=2),encoding='utf-8')
    print(json.dumps(summaries,indent=2))

if __name__=='__main__': main()
