"use strict";
// Same guarded dispatcher used by the desktop, for an already validated review.
const fs=require('fs');
const path=require('path');
const finisher=require('../electron/glass-finisher');
const folder=path.resolve(process.argv[2]||'');
const summary=JSON.parse(fs.readFileSync(path.join(folder,'engine-validation.json'),'utf8'));
if(!summary.editorialCompiled) throw Error('No validated Editorial compilation');
const runtime=path.join(process.env.APPDATA,'Adobe/CEP/extensions/ir.hafez.studio.cep/runtime');
let last=0;
finisher.finish({summary,outputDir:folder,runtime,jobId:'Editorial-Batch-20260928'},
  (message,elapsed)=>{if(elapsed-last>30000){console.log(message);last=elapsed;}})
 .then(result=>console.log(JSON.stringify({ok:result.ok,project:result.project,
   sequence:result.sequence,mogrts:result.mogrt_count,receipt:result.receiptPath})))
 .catch(error=>{console.error(error.message);process.exitCode=1;});
