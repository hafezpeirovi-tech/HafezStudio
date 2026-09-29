"use strict";
const fs = require("fs");
const path = require("path");
const crypto = require("crypto");
const { spawn } = require("child_process");
const fast = require('./upscale-fast');
const topaz = require('./upscale-topaz');

function validate(payload) {
  if (!payload || typeof payload.input !== "string" || !path.isAbsolute(payload.input) || !fs.statSync(payload.input).isFile()) throw Error("فایل ورودی معتبر انتخاب کن.");
  if (!/\.(mp4|mov|mxf|mkv|avi)$/i.test(payload.input)) throw Error("فرمت ویدیو پشتیبانی نمی‌شود.");
  if (![720, 1080, 1440, 2160].includes(Number(payload.resolution))) throw Error("رزولوشن نامعتبر است.");
  if (!["preview", "full"].includes(payload.mode)) throw Error("نوع پردازش نامعتبر است.");
  const engine = payload.engine || 'websr';
  if (!['websr','seedvr2','topaz'].includes(engine)) throw Error('موتور انتخابی در دسترس نیست.');
  if (!Number.isFinite(Number(payload.start)) || Number(payload.start) < 0) throw Error("زمان شروع نامعتبر است.");
  return { input: path.resolve(payload.input), resolution: Number(payload.resolution), mode: payload.mode, engine,
    start: payload.mode === "full" ? 0 : Number(payload.start), qualityConfirmed: payload.qualityConfirmed === true,
    directFullRequest: payload.mode === "full" };
}

class UpscaleManager {
  constructor({ runtime, tools, outputRoot, send, editingBusy, workerPath }) {
    Object.assign(this, { runtime, tools, outputRoot, send, editingBusy, workerPath });
    this.active = null;
    this.lastPreview = null;
  }
  status() {
    const required = ["venv/Scripts/python.exe", "seedvr2/inference_cli.py", "models-verified.json", "environment-verified.json", "models/seedvr2_ema_3b_fp16.safetensors", "models/ema_vae_fp16.safetensors"];
    const missing = required.filter(p => !fs.existsSync(path.join(this.runtime, p)));
    const externalRunning = !this.active && this.externalBusy();
    const websrReady = fast.assetsReady() && ['ffmpeg.exe','ffprobe.exe'].every(f=>fs.existsSync(path.join(this.tools||'',f)));
    return { installed: websrReady, missing: websrReady?[]:['WebSR/FFmpeg'], running: !!this.active || externalRunning, externalRunning,
      engines: {websr:{installed:websrReady,label:'WebSR · سریع، محلی، فیلم واقعی · خروجی ۸ بیت'},seedvr2:{installed:!missing.length,label:'SeedVR2 FP16 · سنگین و کند'},topaz:{installed:topaz.installed(),label:'Topaz Proteus · محلی · نیازمند لایسنس فعال'}},
      model: 'WebSR', runtime: this.runtime };
  }
  externalBusy() {
    try {
      const lock = JSON.parse(fs.readFileSync(path.join(this.runtime, 'active-job.json'), 'utf8'));
      if (!Number.isInteger(lock.pid) || lock.pid <= 0) return true;
      process.kill(lock.pid, 0);
      return true;
    } catch (error) { return !['ENOENT', 'ESRCH'].includes(error.code); }
  }
  key(p) {
    const stat = fs.statSync(p.input);
    return JSON.stringify([p.input.toLowerCase(), stat.size, stat.mtimeMs, p.resolution]);
  }
  start(payload) {
    if (this.active || this.externalBusy() || this.editingBusy()) throw Error("ابتدا پردازش تدوین یا Upscale در حال اجرا را تمام کن.");
    const request = validate(payload);
    if (!this.status().engines[request.engine]?.installed) throw Error("نصب یا تأیید موتور انتخابی کامل نیست.");
    const key = this.key(request);
    const jobDir = path.join(this.outputRoot(), "Upscale", `${Date.now()}-${crypto.randomBytes(4).toString("hex")}`);
    fs.mkdirSync(jobDir, { recursive: true });
    const requestFile = path.join(jobDir, "request.json");
    fs.writeFileSync(requestFile, JSON.stringify({ ...request, jobDir }, null, 2));
    if (['websr','topaz'].includes(request.engine)) {
      const job = {jobDir,cancelled:false};this.active=job;
      const logEvent=event=>{fs.appendFileSync(path.join(jobDir,'worker.log'),JSON.stringify({...event,image:undefined})+'\n');this.send({...event,jobDir});};
      job.promise=(request.engine==='topaz'?topaz.runTopaz:fast.runFast)({request,jobDir,runtime:this.runtime,tools:this.tools,send:logEvent,job})
        .catch(error=>logEvent(job.cancelled?{stage:'cancelled',message:'متوقف شد؛ فایل اصلی حفظ شده است.'}:{stage:'failed',error:error.message}))
        .finally(()=>{if(this.active===job)this.active=null;logEvent({stage:'idle'});});
      return {jobDir};
    }
    const worker = this.workerPath || path.join(__dirname, "upscale-worker.py");
    const child = spawn(path.join(this.runtime, "venv/Scripts/python.exe"), [worker, requestFile, "--runtime", this.runtime, "--tools", this.tools],
      { windowsHide: true, env: { ...process.env, PYTHONUTF8: "1", PYTHONUNBUFFERED: "1" } });
    const job = { child, jobDir, cancelled: false, completed: false, failed: false };
    this.active = job;
    let pending = "";
    const log = fs.createWriteStream(path.join(jobDir, "worker.log"));
    child.stdout.setEncoding("utf8");
    child.stdout.on("data", data => {
      log.write(data);
      pending += data.toString("utf8");
      const lines = pending.split(/\r?\n/); pending = lines.pop();
      for (const line of lines) {
        let event;
        try { event = JSON.parse(line); } catch (_) { continue; }
        if (job.cancelled) continue;
        if (event.stage === "completed") {
          job.completed = true;
          if (request.mode === "preview") this.lastPreview = key;
          if (event.comparison && path.dirname(event.comparison) === jobDir && fs.statSync(event.comparison).size < 25e6) {
            event.image = "data:image/png;base64," + fs.readFileSync(event.comparison).toString("base64");
          }
        }
        if (event.stage === "failed") job.failed = true;
        this.send({ ...event, jobDir });
      }
    });
    child.stderr.on("data", data => log.write(data));
    child.on("error", error => {
      job.failed = true;
      this.send({ stage: "failed", error: error.message, jobDir });
    });
    child.on("close", code => {
      log.end();
      if (this.active === job) this.active = null;
      if (job.cancelled) this.send({ stage: "cancelled", jobDir, message: "متوقف شد؛ فایل اصلی دست‌نخورده است." });
      else if (!job.completed && !job.failed) this.send({ stage: "failed", error: `Worker exited (${code}); see worker.log`, jobDir });
      this.send({ stage: "idle", jobDir });
    });
    return { jobDir };
  }
  cancel() {
    if (!this.active || this.active.cancelled) return false;
    const job = this.active;
    job.cancelled = true;
    if (job.cancelFast) { job.cancelFast();return true; }
    // Exact owned process tree only. Never kill unrelated Python, Adobe or model processes.
    if (process.platform === "win32") {
      const killer = spawn("taskkill.exe", ["/PID", String(job.child.pid), "/T", "/F"], { windowsHide: true });
      killer.on("error", error => this.send({ stage: "cancel-error", error: error.message }));
      killer.on("close", code => { if (code && this.active === job) { job.cancelled = false; this.send({ stage: "cancel-error", error: "توقف تأیید نشد؛ دوباره امتحان کن." }); } });
    } else job.child.kill("SIGTERM");
    return true;
  }
}
module.exports = { UpscaleManager, validate };
