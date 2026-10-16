from pathlib import Path
import re,json
root=Path(__file__).resolve().parents[1]
rows=[]
for p in sorted((root/'MOSFET_Thermal_Overstress_Aging/matlab_scripts').glob('*.m')):
    with p.open('rb') as f: b=f.read(65536)
    x=re.search(rb'(?m)^([^\r\n]* = reshape\(\[\r?\n[^]]*\]\), \[[^]]*\]\);)',b)
    rows.append({'file':p.name,'malformed_numeric_reshape_in_prefix':bool(x),'line':b[:x.start()].count(b'\n')+1 if x else None})
Path(__file__).with_name('export_syntax_audit.json').write_text(json.dumps(rows,indent=2))
print('Affected prefixes:',sum(r['malformed_numeric_reshape_in_prefix'] for r in rows),'/',len(rows))
for i,s in enumerate((root/'MOSFET_Thermal_Overstress_Aging/mat_to_m.py').read_text().splitlines(),1):
    if 'stream.write(f"]),' in s: print(i,s)
