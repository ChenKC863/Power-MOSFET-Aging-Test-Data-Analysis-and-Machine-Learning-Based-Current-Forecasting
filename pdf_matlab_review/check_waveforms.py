from pathlib import Path
import mmap, re, json
import numpy as np
ROOT=Path(__file__).resolve().parents[1]
out={}
for name in ['Test_31_run_1','Test_33_run_1','Test_2_run_2','Test_40_run_2','Test_6_run_1','Test_6_run_2']:
    p=ROOT/'MOSFET_Thermal_Overstress_Aging'/'matlab_scripts'/(name+'.m')
    with p.open('rb') as f,mmap.mmap(f.fileno(),0,access=mmap.ACCESS_READ) as m:
        n=int(re.search(rb'\.transient = repmat\(struct\(\), \[1 (\d+)\]',m)[1])
        d={'transient_records':n}
        if name.startswith(('Test_31','Test_33')):
            total=constant=0
            for match in re.finditer(rb'\.gateSourceVoltage = (?:cast\()?reshape\(\[([^]]*)\]',m):
                v=np.fromstring(match[1].decode(),sep=' ')
                total+=1
                constant+=int(len(v)>0 and np.all(v==v[0]))
            d.update(parsed_gate_waveforms=total,constant_gate_waveforms=constant)
        else:
            d['empty_gate_records']=len(re.findall(rb'\.gateSourceVoltage = zeros\(\[1 0\]',m))
            d['sample_counts']=sorted(set(int(x) for x in re.findall(rb'\.gateSourceVoltage = (?:cast\()?reshape\(\[[^]]*\]\)?, \[1 (\d+)\]',m)))
            d['dt_values']=sorted(set(float(x) for x in re.findall(rb'\.dt = (?:cast\()?reshape\(\[\s*([^]]*)\]',m)))
        out[name]=d
        print(name,d,flush=True)
(Path(__file__).parent/'waveform_checks.json').write_text(json.dumps(out,indent=2))
