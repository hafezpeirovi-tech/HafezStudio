"use strict";
const fs=require('fs'),path=require('path'),os=require('os'),crypto=require('crypto'),assert=require('assert'),vm=require('vm');
const broker=require('../electron/glass-finisher');
const hash=p=>crypto.createHash('sha256').update(fs.readFileSync(p)).digest('hex');
const write=(p,d)=>fs.writeFileSync(p,JSON.stringify(d));
function fixture() {
 const root=fs.mkdtempSync(path.join(os.tmpdir(),'hafez-glass-finish-')), runtime=path.join(root,'runtime'), job=path.join(root,'job');
 fs.mkdirSync(runtime);fs.mkdirSync(job);const output=path.join(job,'review');fs.mkdirSync(output);
 const xml=path.join(output,'Glass.xml'),srt=path.join(output,'Glass.srt'),planPath=path.join(output,'Glass.plan.json'),template=path.join(root,'vendor.mogrt');
 fs.writeFileSync(xml,'fixture');fs.writeFileSync(srt,'fixture');fs.writeFileSync(template,'vendor');
 const plan={style_pack:'glass',purpose:'isolated-native-qa',publication_ready:false,expected_project_path:path.join(output,'Review.prproj'),sequence:'Glass',sfx_cues:[{}],graphics:[{template_layers:[{template_path:template,template_sha256:hash(template)}]}]};
 write(planPath,plan);write(path.join(output,'assembly-report.json'),{outputs_sha256:{'Glass.xml':hash(xml),'Glass.srt':hash(srt),'Glass.plan.json':hash(planPath)}});
 write(path.join(runtime,'glass-heartbeat.json'),{version:broker.VERSION,at:Date.now(),running:false});
 return {root,runtime,outputDir:job,jobId:'test',summary:{style:'glass',publicationReady:false,pngTimelineAssets:0,xml,srt,plan:planPath,expectedProject:plan.expected_project_path,editableMogrtLayers:1}};
}
let x=fixture(), p=broker.prepare(x);assert.equal(p.request.export_movie,false);assert.equal(p.request.mode,'finish_glass');
broker.dispatch(p);assert(fs.existsSync(p.ledger));assert.throws(()=>broker.dispatch(p),/صف/);
write(path.join(x.runtime,'last-result.json'),{request_id:'other',result:{ok:true}});assert.equal(broker.collect(p),null);
fs.writeFileSync(p.request.expected_project_path,'native');
write(path.join(x.runtime,'last-result.json'),{request_id:p.request.request_id,result:{ok:true,saved:true,caption_created:true,publication_ready:false,project:p.request.expected_project_path,sequence:'Glass',sequence_id:'native-id',mogrt_count:1}});
assert(broker.collect(p).saved);
x=fixture();write(path.join(x.runtime,'glass-heartbeat.json'),{version:broker.VERSION,at:Date.now()-50000,running:false});assert.throws(()=>broker.prepare(x),/اتصال زنده/);
x=fixture();fs.appendFileSync(x.summary.xml,'changed');assert.throws(()=>broker.prepare(x),/artifact changed/);
x=fixture();fs.writeFileSync(x.summary.expectedProject,'existing');assert.throws(()=>broker.prepare(x),/new separate/);
x=fixture();x.summary.xml=path.join(x.root,'vendor.mogrt');assert.throws(()=>broker.prepare(x),/outside/);
x=fixture();p=broker.dispatch(broker.prepare(x));write(path.join(x.runtime,'last-result.json'),{request_id:p.request.request_id,result:{ok:false,messages:['native failed']}});assert.throws(()=>broker.collect(p),/native failed/);

// Host guard tests do not impersonate a native Premiere pass.
const ctx=vm.createContext({$: {_hafez:{parseJson:JSON.parse,stringify:JSON.stringify}}, console, assert});
vm.runInContext(fs.readFileSync('premiere-cep-plugin/jsx/glass-review.jsx','utf8'),ctx);
vm.runInContext(`
var mutations=0;
function File(p){this.fsName=p;this.name=String(p).split('/').pop();this.parent={fsName:'/review'};this.exists=p!='/review/new.prproj';}
var app={newProject:function(){mutations++;return true;}};
var request={protocol:'hafez-glass-finish-v1',mode:'finish_glass',allow_create_project:true,save_review_project:true,export_movie:false,expected_project_path:'/review/existing.prproj',plan_path:'/review/plan.json',xml_path:'/review/a.xml',captions_path:'/review/a.srt'};
var r=JSON.parse($._hafez.finishGlassReview(JSON.stringify(request)));assert(!r.ok);assert.equal(mutations,0);
request.expected_project_path='/review/new.prproj';request.export_movie=true;
r=JSON.parse($._hafez.finishGlassReview(JSON.stringify(request)));assert(!r.ok);assert.equal(mutations,0);
request.export_movie=false;
$._hafez.readJson=function(){return {style_pack:'signal-os'};};
r=JSON.parse($._hafez.finishGlassReview(JSON.stringify(request)));assert(!r.ok);assert.equal(mutations,0);
`,ctx);
console.log('PASS Glass handoff: heartbeat, hashes, exact paths, new-project guard, one-shot dispatch, receipts, no export.');
