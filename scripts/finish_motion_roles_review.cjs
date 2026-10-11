"use strict";
// One-shot exact-project handoff; no retry and no movie export.
const fs=require('fs'), path=require('path');
const finisher=require('../electron/glass-finisher');
const folder=path.resolve(process.argv[2]||'');
const summary=JSON.parse(fs.readFileSync(path.join(folder,'engine-validation.json'),'utf8'));
const plan=JSON.parse(fs.readFileSync(summary.plan,'utf8'));
if(plan.motion_role_policy!=='hafez-glass-motion-roles-v1') throw Error('Expected native role candidate');
const runtime=path.join(process.env.APPDATA,'Adobe/CEP/extensions/ir.hafez.studio.cep/runtime');
let last=0;
finisher.finish({summary,outputDir:folder,runtime,jobId:path.basename(folder)},
  (message,elapsed)=>{if(elapsed-last>30000){console.log(message);last=elapsed;}})
 .then(result=>console.log(JSON.stringify({ok:result.ok,project:result.project,
   sequence:result.sequence,mogrts:result.mogrt_count,receipt:result.receiptPath})))
 .catch(error=>{console.error(error.message);process.exitCode=1;});
