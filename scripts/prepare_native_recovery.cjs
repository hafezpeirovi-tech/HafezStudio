"use strict";
// Reuse a failed native handoff's immutable media/ASR/MOGRTs in a NEW folder.
// Never resend the failed request or overwrite any Premiere project.
const fs=require('fs'),path=require('path'),crypto=require('crypto');
const read=p=>JSON.parse(fs.readFileSync(p,'utf8').replace(/^\uFEFF/,''));
const hash=p=>crypto.createHash('sha256').update(fs.readFileSync(p)).digest('hex');
const [sourceArg,destinationArg]=process.argv.slice(2);
if(!sourceArg||!destinationArg) throw Error('Expected failed editorial folder and NEW recovery folder');
const source=fs.realpathSync(sourceArg),destination=path.resolve(destinationArg);
if(fs.existsSync(destination)) throw Error('Recovery destination already exists; inspect, never resend');
const oldReceipt=read(path.join(source,'native-receipt.json'));
if(oldReceipt.result?.ok!==false || oldReceipt.result?.mogrt_count!==0 || oldReceipt.result?.saved!==false)
 throw Error('Not a confirmed zero-MOGRT failed native handoff');
const oldDispatch=read(path.join(source,'native-dispatch.json'));
if(oldDispatch.request.request_id!==oldReceipt.request_id) throw Error('Receipt identity mismatch');
const original=read(path.join(source,'assembly-report.json'));
const plan=read(path.join(source,'Glass-Director.premiere-plan.json'));
for(const file of ['Glass-Director.xml','Glass-Director.srt','Glass-Director.premiere-plan.json']) {
 if(hash(path.join(source,file))!==original.outputs_sha256[file]) throw Error('Original package changed: '+file);
}
if(plan.expected_sequence_id || plan.publication_ready!==false || plan.style_pack!=='glass') throw Error('Unexpected original plan');
const layers=plan.graphics.flatMap(c=>c.template_layers);
for(const layer of layers) if(hash(layer.template_path)!==layer.template_sha256) throw Error('Changed MOGRT: '+layer.template_path);
fs.mkdirSync(destination,{recursive:true});
const project=path.join(destination,'ME-YOUTUBE-10-Motion-Review.prproj');
plan.expected_project_path=project;
const planPath=path.join(destination,'Glass-Director.premiere-plan.json');
fs.writeFileSync(planPath,JSON.stringify(plan,null,2),{flag:'wx'});
for(const file of ['Glass-Director.xml','Glass-Director.srt']) fs.copyFileSync(path.join(source,file),path.join(destination,file),fs.constants.COPYFILE_EXCL);
const report={...original,recovery:{source,failedRequest:oldReceipt.request_id,at:new Date().toISOString(),reusedCompiledAssets:true},outputs_sha256:{}};
for(const file of ['Glass-Director.xml','Glass-Director.srt','Glass-Director.premiere-plan.json']) report.outputs_sha256[file]=hash(path.join(destination,file));
fs.writeFileSync(path.join(destination,'assembly-report.json'),JSON.stringify(report,null,2),{flag:'wx'});
const summary={style:'glass',publicationReady:false,pngTimelineAssets:0,expectedProject:project,
 xml:path.join(destination,'Glass-Director.xml'),srt:path.join(destination,'Glass-Director.srt'),plan:planPath,
 editableMogrtLayers:layers.length,editorialCompiled:plan.graphics.filter(c=>c.id!=='glass-intro').length};
fs.writeFileSync(path.join(destination,'engine-validation.json'),JSON.stringify(summary,null,2),{flag:'wx'});
console.log(JSON.stringify({prepared:destination,layers:layers.length,project,asrRerun:false,mogrtRecompiled:false}));
