'use strict';
const fs=require('fs'),path=require('path');
const {spawn}=require('child_process');
const {acquireLock,validateMedia}=require('./upscale-fast');
const install='C:\\Program Files\\Topaz Labs LLC\\Topaz Video';
const models='C:\\ProgramData\\Topaz Labs LLC\\Topaz Video\\models';
function installed(){return ['Topaz Video.exe','ffmpeg.exe','ffprobe.exe'].every(f=>fs.existsSync(path.join(install,f)))&&fs.existsSync(path.join(models,'prob-4.json'));}
async function runTopaz({request,jobDir,runtime,send,job}){
 const release=acquireLock(runtime,jobDir),started=Date.now(),children=new Set();
 const log=fs.createWriteStream(path.join(jobDir,'topaz.log'));
 const alive=()=>{if(job.cancelled)throw Error('Cancelled');};
 job.cancelFast=()=>{for(const c of children)c.kill();};
 function launch(tool,args,onData){
  alive();const c=spawn(path.join(install,tool+'.exe'),args,{windowsHide:true,env:{...process.env,TVAI_MODEL_DIR:models,TVAI_MODEL_DATA_DIR:models}});children.add(c);
  c.stdin.end();c.stderr.on('data',d=>log.write(d));
  let text='';c.stdout.on('data',d=>{if(onData)onData(d.toString());else text+=d.toString();});
  c.done=new Promise((resolve,reject)=>{c.on('error',reject);c.on('close',code=>{children.delete(c);code===0?resolve(text):reject(Error('Topaz متوقف شد؛ لایسنس، مدل و topaz.log را بررسی کن. کد: '+code));});});return c.done;
 }
 const probe=async f=>JSON.parse(await launch('ffprobe',['-v','error','-count_frames','-show_streams','-show_format','-of','json',f]));
 try{
  if(!installed())throw Error('نصب Topaz یا مدل Proteus پیدا نشد.');
  send({stage:'checking',progress:0,message:'Topaz Proteus — بررسی و آماده‌سازی مدل؛ نخستین اجرا ممکن است دانلود مدل لازم داشته باشد.'});
  const stamp=fs.statSync(request.input),info=await probe(request.input),{v,fps}=validateMedia(info);
  let source=request.input;
  if(request.mode==='preview'){
   if(request.start>=Number(v.duration||info.format.duration)-.1)throw Error('زمان نمونه خارج از ویدیو است.');
   source=path.join(jobDir,'before.mkv');
   await launch('ffmpeg',['-v','error','-n','-i',request.input,'-ss',String(request.start),'-t','5','-map','0:v:0','-map','0:a?','-c:v','ffv1','-c:a','pcm_s24le','-fps_mode','passthrough',source]);
  }
  const before=source===request.input?info:await probe(source),bv=before.streams.find(s=>s.codec_type==='video'),audio=before.streams.filter(s=>s.codec_type==='audio');
  const times=(await launch('ffprobe',['-v','error','-select_streams','v:0','-show_entries','frame=best_effort_timestamp_time','-of','csv=p=0',source])).split(/\r?\n/).map(l=>l.split(',')[0].trim()).filter(Boolean).map(Number);
  const fraction=s=>{const [a,b=1]=String(s).split('/').map(Number);return a/b;};
  const tolerance=Math.max(.00015,1.1*fraction(bv.time_base));
  if(times.length<2||times.some((t,i)=>!Number.isFinite(t)||(i&&Math.abs(t-times[i-1]-1/fps)>tolerance)))throw Error('ویدیوی نرخ فریم متغیر فعلاً پشتیبانی نمی‌شود.');
  const scale=request.resolution/Math.min(v.width,v.height),w=Math.round(v.width*scale/2)*2,h=Math.round(v.height*scale/2)*2;
  if(scale<1||scale>4)throw Error('Topaz: خروجی باید هم‌اندازه تا حداکثر ۴ برابر ورودی باشد.');
  const disk=fs.statfsSync(jobDir);if(disk.bavail*disk.bsize<2*1024**3)throw Error('حداقل ۲ گیگابایت فضای خالی لازم است.');
  const ext=audio.every(s=>['aac','mp3','alac'].includes(s.codec_name))?'mp4':'mov';
  const partial=path.join(jobDir,'topaz.partial.'+ext),output=path.join(jobDir,'topaz-proteus.'+ext);
  let pending='',frame=0,lastReport=0;
  await launch('ffmpeg',['-hide_banner','-nostdin','-nostats','-n','-i',source,'-map','0:v:0','-map','0:a?','-vf',`tvai_up=model=prob-4:scale=0:w=${w}:h=${h}:estimate=8:device=0:vram=0.7:instances=0,scale=${w}:${h}:flags=lanczos`,'-fps_mode','passthrough','-c:v','h264_nvenc','-preset','p5','-cq','18','-b:v','0','-pix_fmt','yuv420p','-c:a','copy','-map_metadata','0','-movflags','+faststart','-progress','pipe:1',partial],data=>{
   pending+=data;const lines=pending.split(/\r?\n/);pending=lines.pop();
   for(const line of lines){if(line.startsWith('frame='))frame=Number(line.slice(6));if(line.startsWith('progress=')&&Date.now()-lastReport>800){lastReport=Date.now();send({stage:'processing',progress:Math.min(94,Math.round(frame/times.length*94)),etaSeconds:frame?Math.round((Date.now()-started)/1000/frame*(times.length-frame)):undefined,message:`Topaz Proteus: فریم ${frame} از ${times.length}`});}}
  });
  alive();send({stage:'verifying',progress:95,message:'کنترل خروجی Topaz و حفظ صدا'});
  const after=await probe(partial),av=after.streams.find(s=>s.codec_type==='video'),aa=after.streams.filter(s=>s.codec_type==='audio');
  if(Number(av.nb_read_frames)!==times.length||av.width!==w||av.height!==h||Math.abs(fraction(av.avg_frame_rate)-fps)>.001||aa.length!==audio.length)throw Error('کنترل تعداد فریم یا مشخصات خروجی ناموفق بود.');
  for(let i=0;i<audio.length;i++){
   const hash=f=>launch('ffmpeg',['-v','error','-i',f,'-map',`0:a:${i}`,'-c','copy','-f','hash','-hash','sha256','-']);
   if(await hash(source)!==await hash(partial)||Math.abs(Number(audio[i].start_time||0)-Number(aa[i].start_time||0))>1/fps)throw Error('کنترل حفظ صدا ناموفق بود.');
  }
  const now=fs.statSync(request.input);if(stamp.size!==now.size||stamp.mtimeMs!==now.mtimeMs)throw Error('فایل ورودی هنگام پردازش تغییر کرد.');
  await launch('ffmpeg',['-v','error','-xerror','-i',partial,'-map','0:v:0','-f','null','-']);
  const comparison=path.join(jobDir,'comparison.png');
  await launch('ffmpeg',['-v','error','-n','-i',source,'-i',partial,'-filter_complex','[0:v]scale=-2:540[a];[1:v]scale=-2:540[b];[a][b]hstack','-frames:v','1',comparison]);
  alive();fs.renameSync(partial,output);
  const receipt={ok:true,engine:'topaz',model:'Proteus prob-4 Auto',output,comparison,original:request.input,preview:request.mode==='preview',frameCount:times.length,fps,width:w,height:h,audioPacketHashesMatch:true,decodeCheck:true,qualityApproval:'owner-review-required',seconds:Math.round((Date.now()-started)/1000)};
  fs.writeFileSync(path.join(jobDir,'receipt.json'),JSON.stringify(receipt,null,2));send({stage:'completed',progress:100,...receipt,image:'data:image/png;base64,'+fs.readFileSync(comparison).toString('base64')});return receipt;
 }finally{job.cancelFast();await Promise.allSettled([...children].map(c=>c.done));log.end();release();}
}
module.exports={installed,runTopaz};
