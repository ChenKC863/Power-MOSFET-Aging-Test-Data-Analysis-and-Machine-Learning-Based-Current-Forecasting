"""Inspect encoded MATLAB character arrays, including labels invisible to text search."""
from pathlib import Path
import mmap, re, json
ROOT=Path(__file__).resolve().parents[1]
pattern=re.compile(rb'char\(reshape\(uint16\(\[([^]]*)\]')
date=re.compile(r'^\d{2}/\d{2}/\d{4} \d{2}:\d{2}:\d{2}\.\d+$')
rows=[]
for p in sorted((ROOT/'MOSFET_Thermal_Overstress_Aging/matlab_scripts').glob('*.m')):
    count=0
    other={}
    with p.open('rb') as f,mmap.mmap(f.fileno(),0,access=mmap.ACCESS_READ) as m:
        for match in pattern.finditer(m):
            count+=1
            s=''.join(chr(int(v)) for v in match[1].split())
            if not date.fullmatch(s):
                other[s]=other.get(s,0)+1
    rows.append({'file':p.name,'character_arrays':count,'non_timestamp_strings':other})
    print(p.name,count,'non-timestamp strings:',other,flush=True)
Path(__file__).with_name('current_unit_encoded_string_audit.json').write_text(json.dumps(rows,indent=2))
print('TOTAL',len(rows),'FILES;',sum(r['character_arrays'] for r in rows),'CHARACTER ARRAYS',flush=True)
