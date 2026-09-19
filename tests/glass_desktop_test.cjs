"use strict";
// Real Electron orchestration code with isolated IPC/child-process/finisher fakes.
// Tests control flow, not native rendering or a real ASR run.
const fs = require("fs"), path = require("path"), os = require("os"), vm = require("vm"), assert = require("assert"), {EventEmitter} = require("events");
function fixture() {
  const root = fs.mkdtempSync(path.join(os.tmpdir(), "hafez-desktop-glass-"));
  const handlers = {}, events = [], spawns = [], calls = [], preflights = [];
  let accept, reject, preflightFailure = false;
  const pending = new Promise((a, r) => { accept = a; reject = r; });
  const broker = {preflight: r => {preflights.push(r); if (preflightFailure) throw Error("offline");}, finish: async (opts, progress) => {calls.push(opts);progress("native waiting");return pending;}};
  const app = {isPackaged:false, getPath: name => path.join(root, name), whenReady: () => ({then: cb => cb()}), on: () => {}, quit: () => {}};
  class Window { constructor() {this.webContents = {send: (channel,data) => events.push({channel,data})};} isDestroyed(){return false;} loadFile(){} once(){} }
  function spawn(exe,args,options) { const child = new EventEmitter(); child.stdout = new EventEmitter(); child.stderr = new EventEmitter(); child.pid = 42; child.kill = () => {child.killed=true;}; spawns.push({exe,args,options,child}); return child; }
  const ctx = vm.createContext({console, process:{env:{},platform:"win32"},__dirname:path.resolve("electron"),Date, setTimeout,
    require: name => name==="electron" ? {app,BrowserWindow:Window,ipcMain:{handle:(n,f)=>handlers[n]=f},dialog:{},shell:{}} : name==="child_process" ? {spawn} : name==="./glass-finisher" ? broker : name==="./job-recovery" ? {findPreparedJob:(...args)=>{calls.push({recovery:args});return null;}} : require(name)});
  vm.runInContext(fs.readFileSync("electron/main.js", "utf8"), ctx);
  const payload={cam1:path.join(root,"cam1.mp4"),cam2:path.join(root,"cam2.mp4"),config:{outputRoot:path.join(root,"out"),stylePack:"glass",performanceProfile:"balanced"}};
  return {handlers,events,spawns,calls,preflights,accept,reject,payload,offline:()=>preflightFailure=true};
}
function engineComplete(x, code=0) { const c=x.spawns[0].child; c.stdout.emit("data", Buffer.from('HERMES_STAGE finish 100 XML ready\n'+JSON.stringify({event:"completed",summary:{style:"glass",publicationReady:false}})+'\n'));c.emit("close",code); }
const tick=()=>new Promise(resolve=>setImmediate(resolve));
(async()=>{
  let x=fixture();x.handlers["job:start"](null,x.payload);
  assert.equal(x.preflights.length,1);assert(x.spawns[0].args.includes("--glass-review"));
  assert.equal(x.calls[0].recovery[3],"glass");assert.equal(x.spawns[0].options.env.HERMES_PRESERVE_CAMERA1_AUDIO,"1");
  engineComplete(x);await tick();
  assert(!x.events.some(e=>e.data.state==="completed"));assert.throws(()=>x.handlers["job:start"](null,x.payload),/Job/);
  assert.throws(()=>x.handlers["job:cancel"](),/Premiere/);assert(!x.spawns[0].child.killed);
  assert(x.events.filter(e=>e.channel==="job:progress").every(e=>e.data.progress<100));
  x.accept({project:"review.prproj",sequence_id:"seq",receiptPath:"receipt.json",compositing_review_required:true});await tick();
  let end=x.events.findLast(e=>e.channel==="job:state").data;
  assert.equal(end.state,"completed");assert.equal(end.summary.nativeReviewReady,true);assert.equal(end.summary.nativeProject,"review.prproj");assert.equal(end.summary.publicationReady,false);assert.equal(x.handlers["job:cancel"](),false);
  x=fixture();x.handlers["job:start"](null,x.payload);engineComplete(x);x.reject(Error("native failure"));await tick();
  end=x.events.findLast(e=>e.channel==="job:state").data;assert.equal(end.state,"failed");assert.equal(end.message,"native failure");assert(!end.summary.nativeReviewReady);
  x=fixture();x.offline();assert.throws(()=>x.handlers["job:start"](null,x.payload),/offline/);assert.equal(x.spawns.length,0);
  x=fixture();x.handlers["job:start"](null,x.payload);engineComplete(x,1);await tick();assert.equal(x.calls.filter(c=>c.summary).length,0);
  x=fixture();x.payload.config.stylePack="signal-os";x.handlers["job:start"](null,x.payload);engineComplete(x);await tick();assert.equal(x.preflights.length,0);assert(!x.spawns[0].args.includes("--glass-review"));assert.equal(x.events.findLast(e=>e.channel==="job:state").data.state,"completed");
  console.log("PASS Glass desktop IPC: preflight before ASR; Glass flag; style-safe resume; await native receipt; truthful errors; no premature 100%; guarded cancel; legacy path retained.");
})().catch(e=>{console.error(e);process.exitCode=1;});
