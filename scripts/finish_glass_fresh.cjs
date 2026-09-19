"use strict";
// Continue exactly the fresh prepare job. Local inference only; no Premiere/export.
const fs=require('fs'),path=require('path'),crypto=require('crypto'),{spawn}=require('child_process');
const root=path.resolve(__dirname,'..');
const output=path.join(root,'proof/glass-fresh-asr-20260913-01');
const read=p=>JSON.parse(fs.readFileSync(p,'utf8').replace(/^\uFEFF/,''));
if(read(path.join(output,'prepare-exit.json')).code!==0) throw Error('Prepare did not succeed');
const manifests=fs.readdirSync(output).filter(n=>n.endsWith('.edit.json'));
if(manifests.length!==1) throw Error('Ambiguous fresh manifest');
const manifest=path.join(output,manifests[0]);
const original=fs.readFileSync(manifest);
const payload=read(manifest);
if(payload.glass_review || !payload.source_word_evidence?.evidence_id) throw Error('Not a new unfinalized source job');
const backup=path.join(output,'before-finalize');
if(fs.existsSync(backup)) throw Error('Finalization already attempted; inspect logs/checkpoint, never blindly replay');
fs.mkdirSync(backup);
fs.copyFileSync(manifest,path.join(backup,manifests[0]),fs.constants.COPYFILE_EXCL);
const python='C:\\Users\\1SKY.IR\\AppData\\Local\\Programs\\Python\\Python311\\python.exe';
const args=['-X','utf8',path.join(root,'engine/src/hermes_video/studio_cli.py'),'finalize','--manifest',manifest,
  '--style','glass','--glass-review','--performance','balanced','--job-id','HS-GLASS-FRESH-20260913'];
fs.writeFileSync(path.join(output,'finalize-intent.json'),JSON.stringify({at:new Date().toISOString(),args,
  evidenceId:payload.source_word_evidence.evidence_id,manifestSha256:crypto.createHash('sha256').update(original).digest('hex'),
  localInferenceOnly:true,rawPrepareReused:false,nativeDispatch:false,publicationReady:false},null,2),{flag:'wx'});
const stdout=fs.createWriteStream(path.join(output,'finalize.stdout.log'),{flags:'wx'});
const stderr=fs.createWriteStream(path.join(output,'finalize.stderr.log'),{flags:'wx'});
const child=spawn(python,args,{cwd:root,windowsHide:true,env:{...process.env,PYTHONUTF8:'1',PYTHONUNBUFFERED:'1',
  HERMES_OLLAMA_GENERATE_URL:'http://127.0.0.1:11434/api/generate',
  HERMES_FAST_DIRECTOR_MODEL:'qwen3.5:4b-q4_K_M',HERMES_DIRECTOR_MODEL:'qwen3.5:4b-q4_K_M'}});
child.stdout.on('data',chunk=>{stdout.write(chunk);process.stdout.write(chunk);});
child.stderr.on('data',chunk=>{stderr.write(chunk);process.stderr.write(chunk);});
child.on('error',error=>{console.error(error.message);process.exitCode=1;});
child.on('close',code=>{stdout.end();stderr.end();fs.writeFileSync(path.join(output,'finalize-exit.json'),
  JSON.stringify({ended:new Date().toISOString(),code,publicationReady:false},null,2),{flag:'wx'});process.exitCode=code??1;});
