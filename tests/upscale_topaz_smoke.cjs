'use strict';
const assert=require('assert/strict'),fs=require('fs'),path=require('path');
const {UpscaleManager}=require('../electron/upscale');
const root=path.resolve(__dirname,'..');
(async()=>{
 const manager=new UpscaleManager({runtime:path.join(root,'runtime/upscale'),tools:path.join(root,'runtime/tools'),outputRoot:()=>path.join(root,'proof/topaz-integration-20260928'),editingBusy:()=>false,send:e=>console.log(JSON.stringify({...e,image:undefined}))});
 assert.equal(manager.status().engines.topaz.installed,true);
 const result=manager.start({input:'E:\\Olymp Trade\\جشن 12 سالگی\\جشن 12 سالگی LQ.mp4',engine:'topaz',mode:'preview',start:30,resolution:1440});
 if(process.argv.includes('--cancel'))setTimeout(()=>manager.cancel(),1500);
 await manager.active.promise;
 assert.equal(manager.active,null);assert.equal(manager.externalBusy(),false);
 const receipt=path.join(result.jobDir,'receipt.json');
 if(process.argv.includes('--cancel'))assert.equal(fs.existsSync(receipt),false);
 else{const r=JSON.parse(fs.readFileSync(receipt));assert.equal(r.engine,'topaz');assert.equal(r.frameCount,150);assert.equal(r.audioPacketHashesMatch,true);}
 console.log('PASS Topaz manager '+(process.argv.includes('--cancel')?'cancellation':'real preview'));
})().catch(e=>{console.error(e);process.exitCode=1;});
