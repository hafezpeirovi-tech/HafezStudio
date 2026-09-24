// Owner-authorized native test: the exact desktop broker, no manual clip placement.
'use strict';
const fs=require('fs'), path=require('path');
const root=path.resolve(__dirname,'..');
const broker=require('../electron/glass-finisher');
const outputDir=path.join(root,'proof/automatic-semantic-glass-20260923-05/frozen-package');
const summary=JSON.parse(fs.readFileSync(path.join(outputDir,'engine-validation.json'),'utf8').replace(/^\uFEFF/,''));
const runtime=path.join(process.env.APPDATA,'Adobe/CEP/extensions/ir.hafez.studio.cep/runtime');
async function main(){
  const options={summary,outputDir,runtime,jobId:'HS-SEMANTIC-NATIVE-20260923-01'};
  if(process.argv[2]==='inspect'){
    broker.preflight(runtime);
    const receipt=JSON.parse(fs.readFileSync(path.join(outputDir,'native-receipt.json'),'utf8')).result;
    const request={mode:'inspect',request_id:'HS-SEMANTIC-INSPECT-20260923-01',plan_path:summary.plan,
      expected_project_path:summary.expectedProject,expected_sequence_name:receipt.sequence,expected_sequence_id:receipt.sequence_id};
    fs.writeFileSync(path.join(outputDir,'inspect-request.json'),JSON.stringify(request),{flag:'wx'});
    fs.writeFileSync(path.join(runtime,'active-plan.json'),JSON.stringify(request),{flag:'wx'});
    console.log('Read-only inspection submitted');return;
  }
  if(process.argv[2]==='inspect-collect'){
    const receipt=JSON.parse(fs.readFileSync(path.join(runtime,'last-result.json'),'utf8'));
    if(receipt.request_id!=='HS-SEMANTIC-INSPECT-20260923-01') throw Error('Pending or different response');
    fs.writeFileSync(path.join(outputDir,'inspect-receipt.json'),JSON.stringify(receipt,null,2),{flag:'wx'});
    console.log(JSON.stringify({ok:receipt.result.ok,mogrts:receipt.result.mogrts?.length}));return;
  }
  if(process.argv[2]==='collect'){
    const ledger=path.join(outputDir,'native-dispatch.json');
    const saved=JSON.parse(fs.readFileSync(ledger,'utf8'));
    console.log(JSON.stringify(broker.collect({request:saved.request,ledger,runtime})));
    return;
  }
  if(process.argv[2]!=='dispatch') throw Error('Specify dispatch or collect');
  const prepared=broker.prepare(options);
  broker.dispatch(prepared);
  console.log(JSON.stringify({submitted:true,requestId:prepared.request.request_id,project:prepared.request.expected_project_path,export:false}));
}
main().catch(e=>{console.error(e.message);process.exitCode=1;});
