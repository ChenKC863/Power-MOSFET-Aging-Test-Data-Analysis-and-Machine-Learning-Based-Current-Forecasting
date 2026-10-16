"""Read serialized MATLAB assignments without executing MATLAB code."""
from pathlib import Path
import mmap, re, json
import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
OUT = Path(__file__).resolve().parent
DATA = ROOT / 'MOSFET_Thermal_Overstress_Aging' / 'matlab_scripts'

def dates(block, field):
    p = rb'\.' + field + rb' = char\(reshape\(uint16\(\[([^]]*)\]'
    strings = [''.join(chr(int(x)) for x in b.split()) for b in re.findall(p, block)]
    return pd.to_datetime(strings, format='%m/%d/%Y %H:%M:%S.%f', errors='coerce')

def values(block, field):
    p = rb'\.' + field + rb' = (?:cast\()?reshape\(\[([^]]*)\]'
    return np.array([float(b.strip()) for b in re.findall(p, block)])

rows, detail = [], {}
for p in sorted(DATA.glob('*.m')):
    with p.open('rb') as f, mmap.mmap(f.fileno(), 0, access=mmap.ACCESS_READ) as m:
        start = m.rfind(b'measurement(1).steadyState =')
        endctrl = m.find(b'measurement(1).transient =')
        ss = m[start:]
        ctrl = m[:endctrl]
        t = dates(ss, b'date')
        valid = t[(t.year >= 2000) & (t.year <= 2100)]
        row = {'file': p.name, 'steady_records': len(t), 'invalid_dates': int(t.isna().sum()),
               'start': str(valid.min()), 'end': str(valid.max()),
               'span_hours': (valid.max()-valid.min()).total_seconds()/3600,
               'has_controller': b'.pwmTempControllerState =' in ctrl,
               'has_transient': endctrl >= 0}
        rows.append(row)
        if p.stem in ['Test_1_run_1','Test_1_run_2','Test_38_run_1','Test_41_run_1','Test_20_run_1','Test_27_run_4']:
            current = values(ss,b'drainCurrent')
            flange = values(ss,b'flangeTemperature')
            d = {'flange_min': float(flange.min()), 'flange_max': float(flange.max())}
            if p.stem in ['Test_38_run_1','Test_41_run_1']:
                windows = [('17:10','17:20'),('18:10','18:20')] if '38' in p.stem else [('22:40','23:00'),('05:20','05:40')]
                d['high_current_medians'] = []
                for a,b in windows:
                    mask = (t.strftime('%H:%M') >= a) & (t.strftime('%H:%M') < b) & (current > 1)
                    d['high_current_medians'].append(float(np.median(current[mask])))
                low = current < .1
                starts = np.flatnonzero(low & ~np.r_[False,low[:-1]])
                ends = np.flatnonzero(low & ~np.r_[low[1:],False])
                dur = np.array([(t[e]-t[s]).total_seconds() for s,e in zip(starts,ends)])
                k = dur.argmax()
                d['longest_low_seconds'] = float(dur[k])
                d['longest_low_start'] = str(t[starts[k]])
                d['longest_low_end'] = str(t[ends[k]])
                d['low_elapsed_hours'] = [(t[i]-t[0]).total_seconds()/3600 for i in [starts[k],ends[k]]]
            if p.stem in ['Test_20_run_1','Test_27_run_4']:
                package = values(ss,b'packageTemperature')
                for minute in (['10:52','10:53'] if '20' in p.stem else ['12:05']):
                    mask=t.strftime('%H:%M')==minute
                    d[minute]={'current_mean':float(current[mask].mean()), 'package_mean':float(package[mask].mean())}
                d['controller_values']={k:np.unique(values(ctrl,k.encode())).tolist() for k in ['lowTemp','highTemp','gateVoltage','supplyVoltage','dutyCycle']}
            detail[p.name]=d
    if len(rows)%10==0: print('Steady-state files checked:',len(rows),flush=True)
pd.DataFrame(rows).to_csv(OUT/'matlab_recording_audit.csv',index=False)
detail['inventory']={'m_files':len(rows),'summed_span_hours':sum(r['span_hours'] for r in rows),'steady_records':sum(r['steady_records'] for r in rows)}
(OUT/'matlab_claim_checks.json').write_text(json.dumps(detail,indent=2))
print(json.dumps(detail,indent=2),flush=True)
