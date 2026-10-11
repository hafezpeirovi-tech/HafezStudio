"use strict";
const {test} = require('node:test');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const os = require('node:os');
const delivery = require('../electron/review-delivery');
function fixture(t) {
  const root = fs.mkdtempSync(path.join(os.tmpdir(),'hafez-delivery-test-'));
  t.after(()=>fs.rmSync(root,{recursive:true,force:true}));
  const project = path.join(root,'Review.prproj'), receipt=path.join(root,'native-receipt.json');
  fs.writeFileSync(project,'test fixture');
  const result={ok:true,saved:true,caption_created:true,publication_ready:false,sequence_id:'seq1',sequence:'Review',project,mogrt_count:8,apply:{failed:0,safetyFailures:0}};
  fs.writeFileSync(receipt,JSON.stringify({result}));
  const event={state:'completed',jobId:'job1',outputDir:root,summary:{nativeReviewReady:true,nativeProject:project,nativeReceipt:receipt,nativeSequenceId:'seq1'}};
  return {root,project,receipt,result,event};
}
test('successful native delivery survives a new module instance',t=>{
  const f=fixture(t); delivery.save(f.root,f.event);
  delete require.cache[require.resolve('../electron/review-delivery')];
  const restored=require('../electron/review-delivery').latest(f.root);
  assert.equal(restored.review.mogrtCount,8); assert.equal(restored.review.project,f.project);
  assert.equal(restored.review.publicationReady,false);
  assert.equal(JSON.parse(fs.readFileSync(path.join(f.root,'hafez-delivery.json'))).nativeReviewReady,true);
});
test('failure and XML-only completion never replace last native review',t=>{
  const f=fixture(t); delivery.save(f.root,f.event);
  for(const state of ['failed','completed']) {
    delivery.save(f.root,{...f.event,state,summary:{plan:'intermediate.json'}});
    assert.equal(delivery.latest(f.root).review.project,f.project);
    assert.equal(JSON.parse(fs.readFileSync(path.join(f.root,'hafez-delivery.json'))).nativeReviewReady,false);
  }
});
test('reject bad native receipts',t=>{
  const f=fixture(t);
  for(const patch of [{ok:false},{saved:false},{caption_created:false},{publication_ready:true},{mogrt_count:0},{sequence_id:'other'},{project:path.join(f.root,'other.prproj')},{apply:{failed:1}}]) {
    fs.writeFileSync(f.receipt,JSON.stringify({result:{...f.result,...patch}}));
    assert.throws(()=>delivery.save(f.root,f.event));
    assert.equal(delivery.latest(f.root).review,null);
  }
});
test('missing project, missing receipt or corrupt pointer cannot appear ready',t=>{
  const f=fixture(t); delivery.save(f.root,f.event);
  fs.unlinkSync(f.project); assert.equal(delivery.latest(f.root).status,'unavailable');
  fs.writeFileSync(f.project,'restored'); fs.unlinkSync(f.receipt);
  assert.equal(delivery.latest(f.root).status,'unavailable');
  fs.writeFileSync(path.join(f.root,'last-premiere-review.json'),'{');
  assert.equal(delivery.latest(f.root).status,'unavailable');
});
test('new installation has no delivery',t=>{
  const f=fixture(t); assert.equal(delivery.latest(f.root).status,'none');
});
