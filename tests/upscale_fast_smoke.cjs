const {app}=require('electron');
const fs=require('fs'),path=require('path');
const {UpscaleManager}=require('../electron/upscale');
const root=path.resolve(__dirname,'..');
app.on('window-all-closed',()=>{});
app.whenReady().then(async()=>{
 const original=JSON.parse(fs.readFileSync('C:/Users/1SKY.IR/Videos/Hafez Studio Outputs/Upscale/1790506546282-24d6dd0e/request.json'));
 const manager=new UpscaleManager({runtime:path.join(root,'runtime/upscale'),tools:path.join(root,'runtime/tools'),outputRoot:()=>path.join(root,'proof/websr-20260927'),editingBusy:()=>false,send:event=>console.log(JSON.stringify({...event,image:undefined}))});
 const result=manager.start({...original,engine:'websr',mode:process.argv.includes('--full')?'full':'preview',start:5});
 console.log('JOB '+result.jobDir);
 if(process.argv.includes('--cancel'))setTimeout(()=>manager.cancel(),2000);
 await manager.active.promise;
 if(process.argv.includes('--cancel')){
  if(manager.active || fs.existsSync(path.join(result.jobDir,'receipt.json')) || manager.externalBusy())throw Error('Cancellation did not release the job');
  console.log('PASS: cancellation released GPU job and lock without final output');app.exit(0);return;
 }
 app.exit(fs.existsSync(path.join(result.jobDir,'receipt.json'))?0:1);
}).catch(error=>{console.error(error);app.exit(1)});
