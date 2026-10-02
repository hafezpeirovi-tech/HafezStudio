"use strict";
const test=require("node:test"),assert=require("node:assert/strict"),fs=require("fs"),os=require("os"),path=require("path");
const {ReelsManager}=require("./reels");
function fixture(t){
  const root=fs.mkdtempSync(path.join(os.tmpdir(),"hafez-reels-test-"));
  t.after(()=>fs.rmSync(root,{recursive:true,force:true}));
  fs.mkdirSync(path.join(root,"runtime"));
  return new ReelsManager({root:()=>root,outputRoot:()=>root,premiereRuntime:()=>path.join(root,"runtime"),busy:()=>false,send:()=>{}});
}
test("native request refuses stale or incompatible bridge without queue mutation",async t=>{
  const manager=fixture(t),runtime=manager.options.premiereRuntime();
  fs.writeFileSync(path.join(runtime,"glass-heartbeat.json"),JSON.stringify({at:Date.now()-60000,reels:"hafez-reels-v1"}));
  await assert.rejects(manager.nativeRequest({folder:runtime},{mode:"reels_finish"}),/پنل/);
  assert.equal(fs.existsSync(path.join(runtime,"active-plan.json")),false);
});
test("multiple app and CLI instances share an exclusive lock",t=>{
  const manager=fixture(t);
  fs.writeFileSync(manager.lockPath(),JSON.stringify({id:"earlier"}));
  assert.throws(()=>manager.start({video:"example.mp4"}),/درخواست Reels/);
  assert.equal(JSON.parse(fs.readFileSync(manager.lockPath())).id,"earlier");
});
test("cancellation cannot interrupt a native Adobe mutation",t=>{
  const manager=fixture(t);let killed=false;
  manager.active={native:true,canceled:false,child:{kill:()=>{killed=true;}}};
  assert.throws(()=>manager.cancel(),/Premiere/);assert.equal(killed,false);assert.equal(manager.active.canceled,false);
});
test("existing Premiere queue is not replaced",async t=>{
  const manager=fixture(t),runtime=manager.options.premiereRuntime();
  fs.writeFileSync(path.join(runtime,"glass-heartbeat.json"),JSON.stringify({at:Date.now(),reels:"hafez-reels-v1",running:false}));
  fs.writeFileSync(path.join(runtime,"active-plan.json"),'original');
  await assert.rejects(manager.nativeRequest({folder:runtime},{mode:"reels_finish"}),/درخواست قبلی/);
  assert.equal(fs.readFileSync(path.join(runtime,"active-plan.json"),"utf8"),'original');
});

test("invalid duration is rejected before creating a job or lock",t=>{
  const manager=fixture(t);
  assert.throws(()=>manager.start({video:"example.mp4",min_duration:60,max_duration:20}),/مدت ریلز/);
  assert.equal(fs.existsSync(manager.lockPath()),false);
  assert.throws(()=>manager.start({video:"example.mp4",count:0}),/مدت ریلز/);
});

test("completion followed by a delayed idle heartbeat can start the next native stage",async t=>{
  const manager=fixture(t),runtime=manager.options.premiereRuntime();
  const heartbeat=path.join(runtime,"glass-heartbeat.json"),queue=path.join(runtime,"active-plan.json");
  fs.writeFileSync(heartbeat,JSON.stringify({at:Date.now(),reels:"hafez-reels-v1",running:true}));
  const timer=setTimeout(()=>fs.writeFileSync(heartbeat,JSON.stringify({at:Date.now(),reels:"hafez-reels-v1",running:false})),50);
  const consumer=setInterval(()=>{if(fs.existsSync(queue)){
    const request=JSON.parse(fs.readFileSync(queue));fs.unlinkSync(queue);
    fs.writeFileSync(path.join(runtime,"last-result.json"),JSON.stringify({request_id:request.request_id,result:{ok:true}}));
  }},50);
  t.after(()=>{clearTimeout(timer);clearInterval(consumer);});
  assert.equal((await manager.nativeRequest({folder:runtime},{mode:"reels_export"},5000)).ok,true);
});

test("output directory failure releases only the newly acquired lock",t=>{
  const manager=fixture(t),blocked=path.join(manager.options.root(),"blocked");
  fs.writeFileSync(blocked,"file");manager.options.outputRoot=()=>blocked;
  assert.throws(()=>manager.start({video:"example.mp4"}));
  assert.equal(fs.existsSync(manager.lockPath()),false);
  assert.equal(manager.active,null);
});
