const fs=require('fs'),vm=require('vm'),assert=require('assert/strict');
const nodes={};
const el=id=>nodes[id]||(nodes[id]={value:'',checked:false,disabled:false,removeAttribute(){}});
el('upResolution').value='1080';el('upStart').value='5';
let request,eventHandler;
const hermes={upscaleStatus:async()=>({installed:true,running:false}),selectVideo:async()=> 'C:\\video.mp4',
 upscaleStart:async p=>{request=p;return {jobDir:'test'}},onUpscaleEvent:fn=>{eventHandler=fn}};
vm.runInNewContext(fs.readFileSync(require('path').join(__dirname,'../app/upscale.js'),'utf8'),{document:{getElementById:el},window:{hermes}});
(async()=>{
 await new Promise(r=>setImmediate(r));
 assert.equal(el('upFull').disabled,true);
 await el('upChoose').onclick();
 assert.equal(el('upFull').disabled,false,'No preview or checkbox required');
 await el('upFull').onclick();
 assert.equal(request.mode,'full');assert.equal(request.qualityConfirmed,false);
 assert.equal(el('upFull').disabled,true,'Concurrent jobs remain blocked');
 eventHandler({stage:'idle'});assert.equal(el('upFull').disabled,false);
 console.log('PASS: full UI starts without preview/confirmation; missing input and concurrent jobs blocked.');
})().catch(e=>{console.error(e);process.exitCode=1});
