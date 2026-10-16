import fs from 'node:fs/promises';
import path from 'node:path';
import {fileURLToPath, pathToFileURL} from 'node:url';
import {Presentation, PresentationFile} from '@oai/artifact-tool';
const here=path.dirname(fileURLToPath(import.meta.url));
const build=path.join(here,'.build');
await fs.mkdir(build,{recursive:true});
const data=JSON.parse(await fs.readFile(path.join(here,'slide_data.json'),'utf8'));
const p=Presentation.create({slideSize:{width:1280,height:720}});
const s=p.slides.add(); s.background.fill='#FAF7EF';
const navy='#102E50',gold='#B7944E';
const skill='C:/Users/user/.codex/plugins/cache/openai-primary-runtime/presentations/26.1011.11113/skills/presentations';
const {applyPresentationChartFont}=await import(pathToFileURL(path.join(skill,'container_tools/artifact_tool_utils.mjs')).href);
function text(str,x,y,w,h,size=20,bold=false,color=navy){const q=s.shapes.add({geometry:'textbox',position:{left:x,top:y,width:w,height:h},fill:'none',line:{fill:'none',width:0}});q.text=str;q.text.style={fontFamily:'Arial',fontSize:size,bold,color};return q;}
text('How Forecasts Support Engineering Judgment',40,18,1200,54,38,true);
text('Post-hoc cases: lowest and highest Ridge MAE among Test groups with at least 100 examples',42,78,1190,32,18);
for(let i=0;i<2;i++){
 const d=data[i],a=d.summary,x=42+i*620;
 text(`${i===0?'Lower error':'Higher error'}: ${a.group.replace('_',' ')} (${a.n} examples)`,x,119,590,32,25,true);
 text(`Group MAE: Ridge ${a.ridge_mae.toFixed(5)} / Persistence ${a.persistence_mae.toFixed(5)}`,x,154,590,28,18);
 const blocks=[]; for(let j=0;j<d.labels.length;j++){if(d.series.target[j]!==null){if(j===0||d.series.target[j-1]===null)blocks.push([]);blocks.at(-1).push(j);}}
 text('Observed',x+125,190,105,22,14,false,'#152F45');text('Persistence',x+232,190,105,22,14,false,'#C28A25');text('Ridge',x+350,190,85,22,14,false,'#1375AE');
 const axis={textStyle:{fontSize:13,fill:navy},line:{fill:'#9C9C96',width:1}};
 const chart=s.charts.add('scatter',{position:{left:x,top:218,width:582,height:213},scatterOptions:{style:'line'},series:['target','persistence','prediction'].flatMap((k,j)=>blocks.map(ids=>({name:['Observed','Persistence','Ridge'][j],values:ids.map(t=>Number(d.series[k][t].toFixed(8))),xValues:ids,line:{fill:['#152F45','#C28A25','#1375AE'][j],width:2},marker:{symbol:'none'}}))),hasLegend:false,legend:{position:'top',overlay:false,textStyle:{fontSize:14}},displayBlanksAs:'gap',chartFill:'#FAF7EF',plotAreaFill:'#FAF7EF',xAxis:{...axis,min:0,max:d.labels.length-1,majorUnit:i?20:10,title:{text:'Minutes after '+d.labels[0]+' (target-minute end)',textStyle:{fontSize:13}}},yAxis:{...axis,min:i?1.7:1.68,max:i?2.5:1.8,numberFormatCode:'0.00',majorGridlines:{fill:'#DEDACF',width:.7}}});
 chart.yAxis={majorUnit:i?.2:.04,title:{text:'Mean current (recorded scale)',textStyle:{fontSize:12}}};
 applyPresentationChartFont(chart,{fontFamily:'Arial'});
 text(`${a.file}   ${a.peak_target_start.slice(0,10)}`,x,433,590,25,17,true);
 text(`Fixed settings: duty 40, supply 5, gate 10\nTemperature setpoints: ${a.settings.lowTemp}/${a.settings.highTemp}`,x,465,590,51,18);
 text(i===0?'Largest run error: +0.03591 at 12:05–12:06.\nRidge tracks this run closely. This does not\nconfirm device health.':'Persistent group bias: −0.06126. At 10:53–10:54,\nobserved 1.795 vs Ridge 2.292 / Persistence 2.356.\nPackage-temperature mean falls 121.46 to 117.07.',x,525,593,77,18);
}
text('Engineering follow-up',42,610,1190,28,21,true,gold);
text('Investigate model bias and thermal/control-state effects. Confirm synchronized current, VGS/VDS,\nactual duty cycle and temperature calibration before attributing the change to degradation.',42,642,1190,49,19);
text('Raw recorded scales. Charts show representative runs, with gaps where targets were not evaluated. Details and sources in notes.',42,697,1160,19,12);
text('15A',1210,691,50,25,16,true);
s.speakerNotes.text=await fs.readFile(path.join(here,'Engineering_Judgment.md'),'utf8');
await fs.writeFile(path.join(here,'engineering_judgment_preview.png'),new Uint8Array(await (await p.export({slide:s,format:'png',scale:1.5})).arrayBuffer()));
await (await PresentationFile.exportPptx(p)).save(path.join(build,'case_slide.pptx'));
console.log('Created editable case slide and preview');



