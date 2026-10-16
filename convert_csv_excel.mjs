import fs from 'node:fs/promises';
import path from 'node:path';
import { spawnSync } from 'node:child_process';
import { Workbook, SpreadsheetFile } from '@oai/artifact-tool';

const root = path.resolve('mosfet_forecasting');
const dest = path.join(root, 'excel_exports');
async function discover(dir) {
  const files = [];
  for (const e of await fs.readdir(dir, {withFileTypes:true})) {
    if (['excel_exports', 'cache', '.matplotlib'].includes(e.name)) continue;
    const p = path.join(dir,e.name);
    if (e.isDirectory()) files.push(...await discover(p));
    else if (e.name.endsWith('.csv')) files.push(p);
  }
  return files.sort();
}
if (!process.argv[2]) {
  const list = await discover(root);
  for (let i=0;i<list.length;i++) {
    const r = spawnSync(process.execPath, ['--max-old-space-size=6144', import.meta.filename, list[i]], {stdio:'inherit'});
    if (r.status !== 0) throw new Error('Conversion failed: '+list[i]);
    console.log(`${i+1}/${list.length} complete`);
  }
} else {
  const input=process.argv[2];
  const output=path.join(dest,path.relative(root,input)).replace(/\.csv$/,'.xlsx');
  await fs.mkdir(path.dirname(output),{recursive:true});
  const wb=await Workbook.fromCSV(await fs.readFile(input,'utf8'),{sheetName:'Data'});
  const sh=wb.worksheets.getItem('Data');
  const values=sh.getUsedRange().values;
  const headers=values[0];
  const nr=values.length, nc=headers.length;
  for(let j=0;j<nc;j++) {
    const isDate = ['history_start','prediction_time','target_start','target_end'].includes(headers[j]);
    for(let i=1;i<nr;i++) {
      let s=values[i][j];
      if(s==='' || s==null) { values[i][j]=null; continue; }
      if(isDate) values[i][j]=new Date(String(s).replace(' ','T')+'Z');
      else if(s==='True'||s==='False') values[i][j]=s==='True';
      else if(headers[j]!=='mtime_ns' && /^[-+]?(?:\d+\.?\d*|\.\d+)(?:[eE][-+]?\d+)?$/.test(String(s)) && Number.isFinite(Number(s))) values[i][j]=Number(s);
      else if(String(s).startsWith('=')) values[i][j]="'"+s;
    }
  }
  sh.getRangeByIndexes(0,0,nr,nc).values=values;
  const used=sh.getRangeByIndexes(0,0,nr,nc);
  used.format.font={name:'Arial',size:10};
  for(let j=0;j<nc;j++) {
    const col=sh.getRangeByIndexes(0,j,nr,1);
    const h=headers[j];
    col.format.columnWidth=Math.min(55,Math.max(18,h.length+3,h==='file'?52:0,h==='model'?27:0));
    if(['history_start','prediction_time','target_start','target_end'].includes(h)) {
      col.format.columnWidth=24;
      sh.getRangeByIndexes(1,j,nr-1,1).setNumberFormat('yyyy-mm-dd hh:mm:ss');
    }
  }
  const header=sh.getRangeByIndexes(0,0,1,nc);
  header.format.fill='#203864';
  header.format.font={name:'Arial',size:10,bold:true,color:'#FFFFFF'};
  header.format.rowHeight=30;
  sh.freezePanes.freezeRows(1);
  sh.tables.add(used,true,'DataTable');
  wb.recalculate();
  await (await SpreadsheetFile.exportXlsx(wb)).save(output);
  if(input===path.join(root,'results','metrics_overall.csv')) {
    const preview=await wb.render({sheetName:'Data',range:'A1:G6',scale:1.4,format:'png'});
    await fs.writeFile(path.join(dest,'preview.png'),new Uint8Array(await preview.arrayBuffer()));
  }
  console.log(path.relative(dest,output),nr-1,'rows');
}
