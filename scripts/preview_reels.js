"use strict";
// Render a saved native Reel into a new job-owned file, without saving timeline changes.
const fs=require("fs"),path=require("path"),crypto=require("crypto");
const {ReelsManager}=require("../electron/reels");
const root=path.resolve(__dirname,"..");
async function main(){
  if(!process.argv[2]||!process.argv[3])throw Error("Usage: node scripts/preview_reels.js plan.json reel-01 [start] [end] [preset.epr]");
  const planPath=path.resolve(process.argv[2]),plan=JSON.parse(fs.readFileSync(planPath,"utf8"));
  if(plan.protocol!=="hafez-reels-v1"||!fs.existsSync(plan.expected_project))throw Error("Saved native project required");
  const folder=path.join(path.dirname(planPath),"preview");fs.mkdirSync(folder,{recursive:true});
  const id=crypto.randomUUID(),sequence=process.argv[3];
  if(!plan.clips.some(c=>c.id===sequence))throw Error("Unknown sequence");
  const manager=new ReelsManager({root:()=>root,premiereRuntime:()=>path.join(process.env.APPDATA,"Adobe","CEP","extensions","ir.hafez.studio.cep","runtime")});
  const job={id,folder:path.join(folder,id),native:false};fs.mkdirSync(job.folder);
  fs.mkdirSync(path.dirname(manager.lockPath()),{recursive:true});
  fs.writeFileSync(manager.lockPath(),JSON.stringify({id,folder:job.folder,pid:process.pid}),{flag:"wx"});
  try {
    const result=await manager.nativeRequest(job,{mode:"reels_preview",plan_path:planPath,sequence,
      start:Number(process.argv[4]||0),...(process.argv[5]?{end:Number(process.argv[5])}:{}),
      preset:process.argv[6]||path.join(process.env.ProgramFiles,"Adobe","Adobe Premiere Pro 2026","MediaIO","systempresets","3F3F3F3F_4D6F6F56","H264 Match Source - High bitrate.epr"),
      output:path.join(folder,`${sequence}-${id}.mov`)});
    console.log(JSON.stringify(result));
  } finally {if(!job.native&&JSON.parse(fs.readFileSync(manager.lockPath())).id===id)fs.unlinkSync(manager.lockPath());}
}
main().catch(error=>{console.error(error.message);process.exitCode=1;});
