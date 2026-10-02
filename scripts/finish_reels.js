"use strict";
// Finish an existing plan only once. Useful after reviewing an analysis-only run.
const fs=require("fs"),path=require("path"),crypto=require("crypto");
const {ReelsManager}=require("../electron/reels");
const root=path.resolve(__dirname,"..");
const digest=p=>crypto.createHash("sha256").update(fs.readFileSync(p)).digest("hex");
async function main(){
  const planPath=path.resolve(process.argv[2]||"");
  const plan=JSON.parse(fs.readFileSync(planPath,"utf8"));
  if(plan.protocol!=="hafez-reels-v1" || !plan.clips.length || plan.missing_templates.length)throw Error("Plan is not ready");
  if(plan.native_source && (digest(plan.native_source.path)!==plan.native_source.sha256 || digest(plan.expected_project)!==plan.native_source.sha256))throw Error("Project copy changed before native finishing");
  for(const clip of plan.clips)for(const cue of clip.motions)if(digest(cue.template_path)!==cue.template_sha256)throw Error("Template changed since analysis");
  const manager=new ReelsManager({root:()=>root,premiereRuntime:()=>path.join(process.env.APPDATA,"Adobe","CEP","extensions","ir.hafez.studio.cep","runtime")});
  const job={id:crypto.randomUUID(),folder:path.dirname(planPath),native:false};
  fs.writeFileSync(manager.lockPath(),JSON.stringify({id:job.id,folder:job.folder,pid:process.pid}),{flag:"wx"});
  try{
    const result=await manager.nativeRequest(job,{mode:"reels_finish",plan_path:planPath});
    if(!result.saved || result.sequences.length!==plan.clips.length)throw Error("Native delivery incomplete");
    fs.writeFileSync(path.join(job.folder,"native-delivery.json"),JSON.stringify(result,null,2),{flag:"wx"});
    console.log(JSON.stringify(result));
  }finally{if(!job.native && JSON.parse(fs.readFileSync(manager.lockPath())).id===job.id)fs.unlinkSync(manager.lockPath());}
}
main().catch(error=>{console.error(error.message);process.exitCode=1;});
