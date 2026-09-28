const {app}=require('electron');
const assert=require('assert/strict'),path=require('path');
app.whenReady().then(()=>{
 const archive=path.resolve(__dirname,'../release-upscale-candidate-20260928-01/win-unpacked/resources/app.asar');
 const fast=require(path.join(archive,'electron/upscale-fast.js'));
 assert.equal(fast.assetsReady(),true);
 assert.equal(require(path.join(archive,'electron/upscale-topaz.js')).installed(),true);
 console.log('PASS: packaged WebSR and model hashes resolve from app.asar through Electron.');
 app.exit(0);
}).catch(e=>{console.error(e);app.exit(1)});
