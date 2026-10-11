"use strict";
// Read-only inspection through the same exact-project CEP contract.
const fs=require('fs'), path=require('path'), crypto=require('crypto');
const broker=require('../electron/glass-finisher');
const folder=path.resolve(process.argv[3]||'');
const read=p=>JSON.parse(fs.readFileSync(p,'utf8').replace(/^\uFEFF/,''));
const runtime=path.join(process.env.APPDATA,'Adobe/CEP/extensions/ir.hafez.studio.cep/runtime');
const requestFile=path.join(folder,'inspect-request.json');
if(process.argv[2]==='dispatch') {
  broker.preflight(runtime);
  const summary=read(path.join(folder,'engine-validation.json'));
  const receipt=read(path.join(path.dirname(summary.plan),'native-receipt.json')).result;
  if(!receipt?.ok || !receipt.saved || receipt.project!==summary.expectedProject) throw Error('No matching saved review');
  const request={mode:'inspect',request_id:crypto.randomUUID(),plan_path:summary.plan,
    expected_project_path:receipt.project,expected_sequence_name:receipt.sequence,
    expected_sequence_id:receipt.sequence_id};
  fs.writeFileSync(requestFile,JSON.stringify(request),{flag:'wx'});
  fs.writeFileSync(path.join(runtime,'active-plan.json'),JSON.stringify(request),{flag:'wx'});
  console.log('Read-only exact-project inspection submitted');
} else if(process.argv[2]==='collect') {
  const request=read(requestFile), receipt=read(path.join(runtime,'last-result.json'));
  if(receipt.request_id!==request.request_id) throw Error('Pending or different response; do not redispatch');
  fs.writeFileSync(path.join(folder,'inspect-receipt.json'),JSON.stringify(receipt,null,2),{flag:'wx'});
  console.log(JSON.stringify({ok:receipt.result?.ok,mogrts:receipt.result?.mogrts?.length}));
} else throw Error('Expected dispatch or collect and exact review folder');
