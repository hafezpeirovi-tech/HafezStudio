'use strict';
const fs=require('fs'),path=require('path'),crypto=require('crypto');
const {spawn}=require('child_process');
const fraction=s=>{const [a,b=1]=String(s).split('/').map(Number);return a/b;};
function validateMedia(info){
 const videos=info.streams.filter(s=>s.codec_type==='video'&&!s.disposition?.attached_pic);
 if(videos.length!==1)throw Error('WebSR requires exactly one video stream.');
 const v=videos[0],fps=fraction(v.avg_frame_rate);
 if(!['yuv420p','yuvj420p','yuv422p','yuv444p','nv12','rgb24'].includes(v.pix_fmt))throw Error('WebSR currently supports 8-bit SDR only; no silent 10-bit conversion.');
 if(['smpte2084','arib-std-b67'].includes(v.color_transfer)||v.color_primaries==='bt2020')throw Error('HDR is not supported by WebSR.');
 if(v.color_space&&!['bt709','unknown'].includes(v.color_space))throw Error('Explicit color conversion required for non-Rec.709 input.');
 if(v.color_transfer&&!['bt709','unknown'].includes(v.color_transfer))throw Error('Unsupported color transfer.');
 if(!['progressive','unknown',undefined].includes(v.field_order))throw Error('Interlaced footage requires explicit deinterlacing.');
 if(v.sample_aspect_ratio&&!['1:1','N/A'].includes(v.sample_aspect_ratio))throw Error('Non-square pixels are not supported.');
 if(v.side_data_list?.some(s=>Number(s.rotation)))throw Error('Rotated source requires explicit conforming.');
 if(!Number.isFinite(fps)||fps<=0||fps>120||Math.abs(fps-fraction(v.r_frame_rate))>.001)throw Error('Only constant frame rate is supported.');
 if(v.width*v.height>2304*2304)throw Error('Source exceeds the tested WebSR GPU size; use a smaller source.');
 return {v,fps};
}
function assetsReady(){
 try{
  const dir=path.resolve(__dirname,'../app/vendor/websr'),p=JSON.parse(fs.readFileSync(path.join(dir,'provenance.json')));
  const hash=f=>crypto.createHash('sha256').update(fs.readFileSync(path.join(dir,f))).digest('hex');
  return hash('websr.js')===p.bundleSha256&&hash('weights.json')===p.weightsSha256;
 }catch{return false;}
}
function acquireLock(runtime,jobDir){
 fs.mkdirSync(runtime,{recursive:true});const lock=path.join(runtime,'active-job.json');
 for(let attempt=0;attempt<2;attempt++){
  try{fs.writeFileSync(lock,JSON.stringify({pid:process.pid,jobDir,engine:'websr',created:Date.now()/1000}),{flag:'wx'});return ()=>{
   try{const owner=JSON.parse(fs.readFileSync(lock));if(owner.pid===process.pid&&owner.jobDir===jobDir)fs.unlinkSync(lock);}catch{}
  };}catch(e){
   if(e.code!=='EEXIST')throw e;
   const owner=JSON.parse(fs.readFileSync(lock));if(!Number.isInteger(owner.pid)||owner.pid<=0)throw Error('Invalid lock; manual review required.');
   try{process.kill(owner.pid,0);}catch(err){if(err.code==='ESRCH'){fs.unlinkSync(lock);continue;}throw err;}
   throw Error('Another Upscale job is running.');
  }
 }
 throw Error('Could not acquire Upscale lock.');
}
async function runFast({request,jobDir,runtime,tools,send,job}){
 const {BrowserWindow,ipcMain}=require('electron');
 const release=acquireLock(runtime,jobDir),started=Date.now(),children=new Set();
 let win,pending,sequence=0;
 const ffmpeg=path.join(tools,'ffmpeg.exe'),ffprobe=path.join(tools,'ffprobe.exe');
 const log=fs.createWriteStream(path.join(jobDir,'fast.log'));
 const alive=()=>{if(job.cancelled)throw Error('Cancelled');};
 function launch(exe,args){
  alive();const child=spawn(exe,args,{windowsHide:true});children.add(child);
  child.stderr.on('data',d=>log.write(d));
  child.done=new Promise((resolve,reject)=>{child.on('error',reject);child.on('close',code=>{children.delete(child);code===0?resolve():reject(Error(`Process exited ${code}; see fast.log`));});});
  child.done.catch(()=>{});return child;
 }
 async function capture(exe,args){const child=launch(exe,args),chunks=[];for await(const data of child.stdout)chunks.push(data);await child.done;alive();return Buffer.concat(chunks).toString('utf8');}
 const probe=async file=>JSON.parse(await capture(ffprobe,['-v','error','-count_frames','-show_streams','-show_format','-of','json',file]));
 const onReply=(event,result)=>{
  if(event.sender!==win?.webContents||result?.id!==pending?.id)return;
  clearTimeout(pending.timer);const current=pending;pending=null;
  result.ok?current.resolve(result):current.reject(Error(result.error||'GPU failed'));
 };
 function ask(payload){
  alive();return new Promise((resolve,reject)=>{
   const id=++sequence,timer=setTimeout(()=>{pending=null;reject(Error('WebGPU timed out after 90 seconds.'));},90000);
   pending={id,resolve,reject,timer};win.webContents.send('websr:request',{...payload,id});
  });
 }
 job.cancelFast=()=>{
  for(const child of children)child.kill();
  if(pending){clearTimeout(pending.timer);pending.reject(Error('Cancelled'));pending=null;}
  if(win&&!win.isDestroyed())win.destroy();
 };
 try{
  send({stage:'checking',progress:0,message:'WebSR — بررسی فریم‌ها و آماده‌سازی GPU محلی'});
  const stamp=fs.statSync(request.input),sourceInfo=await probe(request.input);
  const {v,fps}=validateMedia(sourceInfo);
  let source=request.input;
  if(request.mode==='preview'){
   if(request.start>=Number(v.duration||sourceInfo.format.duration)-.1)throw Error('Preview start is outside the source.');
   source=path.join(jobDir,'before.mkv');
   await capture(ffmpeg,['-v','error','-n','-i',request.input,'-ss',String(request.start),'-t','5','-map','0:v:0','-map','0:a?','-c:v','ffv1','-c:a','pcm_s24le','-fps_mode','passthrough',source]);
  }
  const before=source===request.input?sourceInfo:await probe(source);
  const stamps=await capture(ffprobe,['-v','error','-select_streams','v:0','-show_entries','frame=best_effort_timestamp_time','-of','csv=p=0',source]);
  const times=stamps.split(/\r?\n/).map(l=>l.split(',')[0].trim()).filter(Boolean).map(Number);
  const tolerance=Math.max(.00015,1.1*fraction(before.streams.find(s=>s.codec_type==='video').time_base));
  if(times.length<2||times.some((t,i)=>!Number.isFinite(t)||(i&&Math.abs(t-times[i-1]-1/fps)>tolerance)))throw Error('Variable frame timestamps detected; refusing output desynchronization.');
  const scale=request.resolution/Math.min(v.width,v.height),outW=Math.round(v.width*scale/2)*2,outH=Math.round(v.height*scale/2)*2;
  if(scale<=1||scale>2)throw Error('WebSR supports enlargement up to 2×. Choose an output larger than the source, at most twice its short edge.');
  const disk=fs.statfsSync(jobDir);if(disk.bavail*disk.bsize<2*1024**3)throw Error('At least 2 GB of free space is required.');
  win=new BrowserWindow({show:false,width:64,height:64,webPreferences:{preload:path.join(__dirname,'upscale-websr-preload.js'),contextIsolation:true,nodeIntegration:false,sandbox:true,backgroundThrottling:false,partition:'websr-local'}});
  win.webContents.setWindowOpenHandler(()=>({action:'deny'}));
  win.webContents.on('will-navigate',e=>e.preventDefault());
  win.webContents.session.webRequest.onBeforeRequest((details,callback)=>callback({cancel:!details.url.startsWith('file://')}));
  ipcMain.on('websr:reply',onReply);
  await win.loadFile(path.resolve(__dirname,'../app/upscale-websr.html'));
  const gpu=await ask({type:'init',width:v.width,height:v.height,outputWidth:outW,outputHeight:outH,weights:JSON.parse(fs.readFileSync(path.resolve(__dirname,'../app/vendor/websr/weights.json')))});
  const interim=path.join(jobDir,'video.partial.mp4');
  const encoder=launch(ffmpeg,['-v','error','-n','-f','rawvideo','-pix_fmt','rgba','-s',`${outW}x${outH}`,'-r',v.avg_frame_rate,'-i','pipe:0','-an','-c:v','h264_nvenc','-preset','p5','-rc','vbr','-cq','18','-b:v','0','-pix_fmt','yuv420p','-color_primaries','bt709','-color_trc','bt709','-colorspace','bt709',interim]);
  encoder.stdout.resume();let encoderError;encoder.stdin.on('error',e=>{encoderError=e;});
  const decoder=launch(ffmpeg,['-v','error','-i',source,'-map','0:v:0','-an','-fps_mode','passthrough','-pix_fmt','rgba','-f','rawvideo','pipe:1']);
  decoder.stdin.end();let count=0,lastReport=0,filled=0;const frameBytes=v.width*v.height*4,frame=Buffer.allocUnsafe(frameBytes);
  for await(const chunk of decoder.stdout){
   let offset=0;
   while(offset<chunk.length){
    const length=Math.min(frameBytes-filled,chunk.length-offset);chunk.copy(frame,filled,offset,offset+length);filled+=length;offset+=length;
    if(filled<frameBytes)continue;
    alive();const bytes=Uint8Array.from(frame).buffer;filled=0;
    const result=await ask({type:'frame',bytes});
    const rendered=Buffer.from(result.bytes);if(rendered.length!==outW*outH*4)throw Error('GPU frame size mismatch.');
    const meanRGB=data=>{let sum=0,n=0;for(let i=0;i<data.length;i+=400){sum+=data[i]+data[i+1]+data[i+2];n+=3;}return sum/n;};
    if(meanRGB(new Uint8Array(bytes))>8&&meanRGB(rendered)<1)throw Error('GPU returned a black frame for a non-black input; output rejected.');
    if(encoderError)throw encoderError;
    await new Promise((resolve,reject)=>encoder.stdin.write(rendered,e=>e?reject(e):resolve()));count++;
    if(Date.now()-lastReport>800){lastReport=Date.now();const elapsed=(Date.now()-started)/1000;send({stage:'processing',progress:Math.min(92,Math.round(count/times.length*92)),etaSeconds:Math.round(elapsed/count*(times.length-count)),message:`WebSR: فریم ${count} از ${times.length}`});}
   }
  }
  await decoder.done;encoder.stdin.end();await encoder.done;alive();
  if(filled||count!==times.length)throw Error('Decoded frame count mismatch.');
  send({stage:'verifying',progress:95,message:'کنترل خروجی، تعداد فریم و حفظ صدا'});
  const audio=before.streams.filter(s=>s.codec_type==='audio');
  const extension=audio.every(s=>['aac','mp3','alac'].includes(s.codec_name))?'mp4':'mov';
  const partial=path.join(jobDir,`upscaled.partial.${extension}`),final=path.join(jobDir,`upscaled.${extension}`);
  await capture(ffmpeg,['-v','error','-n','-itsoffset',String(times[0]),'-i',interim,'-i',source,'-map','0:v:0','-map','1:a?','-map_metadata','1','-c','copy','-movflags','+faststart',partial]);
  const after=await probe(partial),av=after.streams.find(s=>s.codec_type==='video'),aa=after.streams.filter(s=>s.codec_type==='audio');
  if(Number(av.nb_read_frames)!==count||av.width!==outW||av.height!==outH||Math.abs(fraction(av.avg_frame_rate)-fps)>.001)throw Error('Output validation failed.');
  if(audio.length!==aa.length)throw Error('Audio stream count mismatch.');
  for(let i=0;i<audio.length;i++){
   const hash=media=>capture(ffmpeg,['-v','error','-i',media,'-map',`0:a:${i}`,'-c','copy','-f','hash','-hash','sha256','-']);
   if(await hash(source)!==await hash(partial))throw Error('Audio packet hash mismatch.');
   if(Math.abs(Number(audio[i].start_time||0)-Number(aa[i].start_time||0))>1/fps)throw Error('Audio start time mismatch.');
  }
  const now=fs.statSync(request.input);if(now.size!==stamp.size||now.mtimeMs!==stamp.mtimeMs)throw Error('Source changed while processing.');
  await capture(ffmpeg,['-v','error','-i',partial,'-map','0:v:0','-f','null','-']);alive();
  fs.renameSync(partial,final);
  const comparison=path.join(jobDir,'comparison.png');
  await capture(ffmpeg,['-v','error','-n','-ss','0','-i',source,'-ss','0','-i',final,'-filter_complex','[0:v]scale=-2:540[a];[1:v]scale=-2:540[b];[a][b]hstack=inputs=2','-frames:v','1',comparison]);
  const receipt={ok:true,model:'WebSR CNN 2x Large — Real Life',engine:'websr',adapter:gpu.adapter,output:final,comparison,original:request.input,preview:request.mode==='preview',frameCount:count,fps,resolution:request.resolution,audioStreamsPreserved:audio.length,audioPacketHashesMatch:true,decodeCheck:true,qualityApproval:'owner-review-required',seconds:Math.round((Date.now()-started)/1000)};
  fs.writeFileSync(path.join(jobDir,'receipt.json'),JSON.stringify(receipt,null,2));send({stage:'completed',progress:100,...receipt,image:'data:image/png;base64,'+fs.readFileSync(comparison).toString('base64')});
  return receipt;
 }finally{
  job.cancelFast();ipcMain.removeListener('websr:reply',onReply);
  await Promise.allSettled([...children].map(c=>c.done));log.end();release();
 }
}
module.exports={runFast,assetsReady,validateMedia,acquireLock};
