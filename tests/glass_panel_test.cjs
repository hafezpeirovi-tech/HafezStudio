const assert=require('assert'),fs=require('fs'),vm=require('vm');
function boot(missing,fail=false) {
  const writes=[],timers=[],nodes={};let created=0;
  const ctx={document:{getElementById:id=>nodes[id]||(nodes[id]={textContent:'',addEventListener(){}})},
    window:{__adobe_cep__:{getSystemPath:()=>'/extension'},cep:{fs:{readdir:()=>({err:missing?3:0}),makedir:()=>{created++;return{err:fail?1:0};},writeFile:(p,s)=>writes.push({p,s})}},setInterval:f=>timers.push(f),setTimeout:f=>timers.push(f)}};
  vm.runInNewContext(fs.readFileSync('premiere-cep-plugin/panel.js','utf8'),ctx);
  return {writes,timers,nodes,created};
}
let r=boot(true);assert.equal(r.created,1);assert.equal(JSON.parse(r.writes[0].s).version,'glass-review-v1');assert.equal(r.timers.length,3);
r=boot(false);assert.equal(r.created,0);assert.equal(r.writes.length,1);
r=boot(true,true);assert.equal(r.writes.length,0);assert.equal(r.timers.length,0);assert(r.nodes.apply.disabled);
console.log('PASS CEP clean install: runtime created; live heartbeat; no shipped queue; failure disables processing.');
