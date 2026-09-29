// Regression: focus can return to an owner's project after app.newProject().
// Never use focus as the mutation destination of the isolated finisher.
const fs=require('fs'),vm=require('vm'),assert=require('assert');
const context=vm.createContext({$: {},assert,console});
vm.runInContext(fs.readFileSync('premiere-cep-plugin/jsx/hafez.jsx','utf8'),context);
vm.runInContext(fs.readFileSync('premiere-cep-plugin/jsx/glass-review.jsx','utf8'),context);
vm.runInContext(`
function File(p){this.fsName=p;this.name=p.split('/').pop();this.parent={fsName:'/review'};this.exists=p!='/review/new.prproj';}
var owner={path:'/owner.prproj',documentID:'owner',activeSequence:{name:'Owner'}};
var target={path:'/review/new.prproj',documentID:'new',sequences:{numSequences:0}};
var app={project:owner,projects:[owner,target]};app.projects.numProjects=2;
assert.equal($._hafez.findOpenProject(target.path),target);
assert.equal($._hafez.requireProject(target.path,target),target);
assert.throws(function(){$._hafez.requireProject(target.path);},/Active project/);
assert.throws(function(){$._hafez.requireProject(owner.path,target);},/identity mismatch/);
app.projects[1]={path:target.path,documentID:'reopened'};
assert.throws(function(){$._hafez.requireProject(target.path,target);},/document changed/);
app.projects=[owner];app.projects.numProjects=1;
assert.throws(function(){$._hafez.requireProject(target.path,target);},/missing/);
app.projects=[owner,target,target];app.projects.numProjects=3;
assert.throws(function(){$._hafez.findOpenProject(target.path);},/Ambiguous/);
app.projects=[owner,target];app.projects.numProjects=2;

// Actual XML importer must mutate target, even with owner's panel focused.
var bins=[];bins.numItems=0;target.rootItem={children:bins,createBin:function(name){
 var bin={name:name,type:2,children:{numItems:0}};bins.push(bin);bins.numItems=bins.length;return bin;
}};
target.importFiles=function(){target.sequences=[{sequenceID:'new-seq',name:'Review'}];target.sequences.numSequences=1;return true;};
target.openSequence=function(id){assert.equal(id,'new-seq');this.activeSequence=this.sequences[0];return true;};
var importRequest={protocol:'hafez-native-import-v1',mode:'import_xml',expected_project_path:target.path,
 xml_path:'/review/a.xml',bin_name:'New bin',expected_sequence_name:'Review',expected_sequence_names:['Review']};
var imported=JSON.parse($._hafez.importXmlRequest(JSON.stringify(importRequest),target));
assert(imported.ok,JSON.stringify(imported));assert.equal(app.project,owner);assert.equal(imported.sequence_id,'new-seq');

// Full orchestration: import, apply, captions and save stay on bound project.
var calls=[],saved=false,plan={style_pack:'glass',purpose:'isolated-native-qa',publication_ready:false,
 expected_project_path:target.path,sequence:'Review',graphics:[{template_layers:[{}]}],sfx_cues:[]};
File.prototype.open=function(){return true;};File.prototype.write=function(){};File.prototype.close=function(){};
app.newProject=function(){calls.push('create');target.sequences={numSequences:0};return true;};
$._hafez.readJson=function(){return plan;};
function track(muted){return {clips:{numItems:0},isMuted:function(){return muted;}};}
var seq={sequenceID:'new-seq',name:'Review',videoTracks:[track(false),track(false),track(false),track(false)],
 audioTracks:[track(false),track(true),track(false),track(false),track(false)],createCaptionTrack:function(){calls.push('captions');return true;}};
seq.videoTracks.numTracks=4;seq.audioTracks.numTracks=5;
$._hafez.importXmlRequest=function(raw,bound){assert.equal(bound,target);calls.push('import');target.activeSequence=seq;return JSON.stringify({ok:true,sequence_id:'new-seq',sequence:'Review'});};
$._hafez.applyPlan=function(p,mute,bound){assert.equal(bound,target);assert.equal(mute,false);calls.push('apply');return JSON.stringify({ok:true,inserted:1});};
var captionBin={children:[{getMediaPath:function(){return '/review/a.srt';}}]};captionBin.children.numItems=1;
target.rootItem.createBin=function(){return captionBin;};target.importFiles=function(){calls.push('srt');return true;};
target.save=function(){saved=true;calls.push('save');};
// Saving target makes the mock destination exist; bound plan is initially absent.
File=function(p){this.fsName=p;this.name=p.split('/').pop();this.parent={fsName:'/review'};
 this.exists=p==='/review/Glass-Native-Bound.plan.json'?false:(p===target.path?saved:true);};
File.prototype.open=function(){return true;};File.prototype.write=function(){};File.prototype.close=function(){};
var request={protocol:'hafez-glass-finish-v1',mode:'finish_glass',allow_create_project:true,save_review_project:true,export_movie:false,
 expected_project_path:target.path,plan_path:'/review/plan.json',xml_path:'/review/a.xml',captions_path:'/review/a.srt',
 expected_sequence_name:'Review',expected_mogrt_count:1,expected_sfx_count:0};
var result=JSON.parse($._hafez.finishGlassReview(JSON.stringify(request)));
assert(result.ok,JSON.stringify(result));assert(result.saved);assert(result.caption_created);assert.equal(result.mogrt_count,1);
assert.equal(calls.join(','),'create,import,apply,srt,captions,save');assert.equal(app.project,owner);
assert.equal(owner.activeSequence.name,'Owner');
`,context);
console.log('PASS multi-project binding: exact path + document ID; wrong/closed/replaced/duplicate denied; owner focus preserved.');
