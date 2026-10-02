"use strict";
// Same manager as the app; useful for local orchestration (including n8n Execute Command).
// Input is a JSON file, never interpolated into a shell command from transcript text.
const fs = require("fs"), path = require("path");
const { ReelsManager } = require("../electron/reels");
const root = path.resolve(__dirname, "..");
async function main() {
  const inputFile = process.argv[2];
  if (!inputFile) throw Error("Usage: node scripts/run_reels.js request.json");
  const input = JSON.parse(fs.readFileSync(inputFile, "utf8").replace(/^\uFEFF/, ""));
  const manager = new ReelsManager({root:()=>root,
    outputRoot:()=>input.outputRoot || path.join(root,"output"), busy:()=>false,
    premiereRuntime:()=>path.join(process.env.APPDATA,"Adobe","CEP","extensions","ir.hafez.studio.cep","runtime"),
    invocation:request=>({exe:process.env.HERMES_PYTHON || path.join(process.env.LOCALAPPDATA,"Programs","Python","Python311","python.exe"),
      args:[path.join(root,"engine","src","hermes_video","studio_cli.py"),"reels","--request",request]}),
    send:event=>{ console.log(JSON.stringify(event)); if(event.state==="failed" || event.state==="canceled")process.exitCode=1; }
  });
  manager.start(input);
}
main().catch(error=>{console.error(error.message);process.exitCode=1;});
