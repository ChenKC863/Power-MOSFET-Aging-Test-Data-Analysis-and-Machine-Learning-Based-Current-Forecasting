import fs from 'node:fs/promises';
import path from 'node:path';
import {fileURLToPath} from 'node:url';
import {Presentation,PresentationFile} from '@oai/artifact-tool';
const here=path.dirname(fileURLToPath(import.meta.url));
await fs.mkdir(path.join(here,'.build'),{recursive:true});
const p=Presentation.create({slideSize:{width:1280,height:720}});
const s=p.slides.add();s.background.fill='#FAF7EF';
function text(t,x,y,w,h,size=22,bold=false,color='#102E50'){
 const a=s.shapes.add({geometry:'textbox',position:{left:x,top:y,width:w,height:h},fill:'none',line:{fill:'none',width:0}});
 a.text=t;a.text.style={fontFamily:'Arial',fontSize:size,bold,color};
}
text('Validation Scope and Operating Transitions',42,24,1200,58,38,true);
text('What the evaluation supports',44,107,1180,36,27,true);
text('Five outer folds hold out Test-number groups: 9,304 examples, 83 files, 33 groups.\nPhysical-device identities remain unverified. Cross-device generalization is unconfirmed.',44,150,1180,68,23);
text('Which operating intervals qualify',44,239,1180,36,27,true);
text('Five historical minutes predict a future one-minute mean ending five minutes after issuance.\nEligibility requires valid consecutive bins and unchanged recorded settings through the target.\nThis retrospective selection uses future setting records. Online applicability remains unverified.',44,283,1180,104,22);
text('What remains untested',44,412,1180,36,27,true);
text('Windows crossing setting changes are excluded. Their accuracy and interval coverage are unknown.\nUnchanged commands do not guarantee unchanged actual drive, load or temperature.\nNext: score stable and transition periods separately using eligibility known at prediction time.',44,456,1180,106,22);
text('Supported claim',44,593,1180,30,23,true,'#B7944E');
text('Exploratory current forecasting on held-out Test-number groups during retrospectively\nselected intervals with unchanged recorded controller settings.',44,632,1175,64,22,true);
text('12A',1200,692,64,23,15);
s.speakerNotes.text=await fs.readFile(path.join(here,'Validation_Scope.md'),'utf8');
await fs.writeFile(path.join(here,'Validation_Scope_preview.png'),new Uint8Array(await(await p.export({slide:s,format:'png',scale:1.5})).arrayBuffer()));
await(await PresentationFile.exportPptx(p)).save(path.join(here,'.build/case_slide.pptx'));
console.log('Created validation-scope slide');
