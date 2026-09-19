"use strict";
// Fresh local ASR acceptance on the owner-selected cameras. Never reuse prior ASR.
const fs=require('fs'),path=require('path'),{spawn}=require('child_process');
const root=path.resolve(__dirname,'..');
const output=path.join(root,'proof/glass-fresh-asr-20260913-01');
const engine=path.join(root,'release-glass-candidate-20260913-01/win-unpacked/resources/engine/hermes-engine/hermes-engine.exe');
const cam1='F:\\Hafez\\Youtube\\8rd vid\\C2963.MP4',cam2='F:\\Hafez\\Youtube\\8rd vid\\2\\C2955.MP4';
for(const p of [engine,cam1,cam2]) if(!fs.statSync(p).isFile()) throw Error('Input missing');
if(fs.existsSync(output)) throw Error('Fresh job exists; inspect it, never overwrite/restart');
fs.mkdirSync(output);
const args=['prepare','--cam1',cam1,'--cam2',cam2,'--output',output,'--style','glass','--language','fa-en','--performance','balanced'];
fs.writeFileSync(path.join(output,'fresh-run.json'),JSON.stringify({started:new Date().toISOString(),engine,args,
  freshAsr:true,mode:'prepare-only',nativeDispatch:false,exportMovie:false,publicationReady:false},null,2),{flag:'wx'});
const stdout=fs.createWriteStream(path.join(output,'prepare.stdout.log'),{flags:'wx'});
const stderr=fs.createWriteStream(path.join(output,'prepare.stderr.log'),{flags:'wx'});
const child=spawn(engine,args,{cwd:root,windowsHide:true,env:{...process.env,PYTHONUTF8:'1',PYTHONUNBUFFERED:'1'}});
child.stdout.on('data',chunk=>{stdout.write(chunk);process.stdout.write(chunk);});
child.stderr.on('data',chunk=>{stderr.write(chunk);process.stderr.write(chunk);});
child.on('error',error=>{console.error(error.message);process.exitCode=1;});
child.on('close',code=>{stdout.end();stderr.end();fs.writeFileSync(path.join(output,'prepare-exit.json'),
  JSON.stringify({ended:new Date().toISOString(),code,publicationReady:false},null,2),{flag:'wx'});process.exitCode=code??1;});
