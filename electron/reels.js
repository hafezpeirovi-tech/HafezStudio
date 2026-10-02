"use strict";
const fs = require("fs");
const path = require("path");
const crypto = require("crypto");
const { spawn } = require("child_process");
const read = p => JSON.parse(fs.readFileSync(p, "utf8").replace(/^\uFEFF/, ""));
const hash = p => crypto.createHash("sha256").update(fs.readFileSync(p)).digest("hex");
const delay = ms => new Promise(resolve => setTimeout(resolve, ms));

class ReelsManager {
  constructor(options) { this.options = options; this.active = null; this.last = null; }
  lockPath() { return path.join(this.options.root(), "runtime", "reels-active.lock"); }
  status() {
    const root = this.options.root();
    const baseTemplates=path.join(root,"motion-pack","reels","dist");
    const templates=fs.existsSync(path.join(baseTemplates,"v2"))?path.join(baseTemplates,"v2"):baseTemplates;
    return { running: !!this.active || fs.existsSync(this.lockPath()), last: this.last,
      aiConfigured: !!(process.env.GEMINI_API_KEY && process.env.HAFEZ_REELS_GEMINI_MODEL),
      templates: ["editorial", "pause-card"].map(name => ({ name,
        ready: fs.existsSync(path.join(templates, `${name}.mogrt`)) })) };
  }
  emit(event) { this.last = { ...(this.last || {}), ...event }; this.options.send(event); }
  start(input) {
    if (this.active || this.options.busy()) throw Error("یک پردازش دیگر فعال است؛ پس از پایان آن شروع کن.");
    if (!input || (!input.video && !input.project)) throw Error("ویدیوی تدوین‌شده یا پروژه را انتخاب کن.");
    if(input.selector === "gemini" && !this.status().aiConfigured) throw Error("Gemini هنوز تنظیم نشده است؛ کلید و نام مدل را محلی تنظیم کن یا انتخاب آفلاین را انتخاب کن.");
    const minimum=Number(input.min_duration ?? 20),maximum=Number(input.max_duration ?? 60),count=Number(input.count ?? 6);
    if(!Number.isFinite(minimum)||!Number.isFinite(maximum)||minimum<8||minimum>maximum||maximum>90||!Number.isInteger(count)||count<1||count>6)throw Error("مدت ریلز باید بین ۸ تا ۹۰ ثانیه و تعداد بین ۱ تا ۶ باشد.");
    const id = crypto.randomUUID();
    const folder = path.join(this.options.outputRoot(), "Reels", id);
    fs.mkdirSync(path.dirname(this.lockPath()), { recursive: true });
    try { fs.writeFileSync(this.lockPath(), JSON.stringify({id, folder, pid:process.pid}), {flag:"wx"}); }
    catch(error) { if(error.code === "EEXIST") throw Error("یک درخواست Reels دیگر فعال یا تعیین‌تکلیف‌نشده است؛ ابتدا وضعیت قبلی را بررسی کن."); throw error; }
    try {fs.mkdirSync(folder, { recursive: true });}
    catch(error) {if(read(this.lockPath()).id === id)fs.unlinkSync(this.lockPath());throw error;}
    const job = { id, folder, child: null, canceled: false, native: false };
    this.active = job; this.last = null;
    this.emit({ state: "running", jobId: id, output: folder, progress: 0, message: "آماده‌سازی ریلز" });
    this.run(job, input).catch(error => this.emit({ state: job.canceled ? "canceled" : "failed", message: error.message }))
      .finally(() => {
        // Keep unresolved native jobs locked; re-running may duplicate an Adobe mutation.
        if (!job.native) { try { if(read(this.lockPath()).id === job.id) fs.unlinkSync(this.lockPath()); } catch (_) {} }
        if (this.active === job) this.active = null;
      });
    return { jobId: id, output: folder };
  }
  async nativeRequest(job, request, timeout = 45 * 60 * 1000) {
    const runtime = this.options.premiereRuntime();
    let heartbeat;
    try { heartbeat = read(path.join(runtime, "glass-heartbeat.json")); } catch (_) { /* handled below */ }
    if (!heartbeat || heartbeat.reels !== "hafez-reels-v1" || Date.now() - heartbeat.at > 45000 || heartbeat.at > Date.now() + 5000) {
      throw Error("پنل Hafez Finisher با پشتیبانی Reels را در Premiere باز کن.");
    }
    // A completed request may precede the panel's next 10-second heartbeat.
    // Wait only for a fresh idle heartbeat; never replace a queued request.
    for (let attempt=0; heartbeat.running && attempt<15; attempt++) {
      await delay(1000);
      heartbeat=read(path.join(runtime,"glass-heartbeat.json"));
      if(heartbeat.reels!=="hafez-reels-v1" || Date.now()-heartbeat.at>45000 || heartbeat.at>Date.now()+5000)throw Error("ارتباط پنل Premiere تازه نیست.");
    }
    if (heartbeat.running) throw Error("Premiere در حال پردازش است.");
    const queue = path.join(runtime, "active-plan.json");
    if (fs.existsSync(queue)) throw Error("درخواست قبلی Premiere هنوز تعیین تکلیف نشده است.");
    request = { ...request, request_id: crypto.randomUUID(), protocol: "hafez-reels-v1" };
    const ledger = path.join(job.folder, `${request.mode}.request.json`);
    fs.writeFileSync(ledger, JSON.stringify(request, null, 2), { flag: "wx" });
    job.native = true;
    try { fs.writeFileSync(queue, JSON.stringify(request), { flag: "wx" }); }
    catch(error) { job.native = false; throw error; }
    const started = Date.now();
    while (Date.now() - started < timeout) {
      let receipt;
      try { receipt = read(path.join(runtime, "last-result.json")); } catch (_) { /* writer may be busy */ }
      if (receipt?.request_id === request.request_id) {
        fs.writeFileSync(path.join(job.folder, `${request.mode}.receipt.json`), JSON.stringify(receipt, null, 2), { flag: "wx" });
        job.native = false;
        if (!receipt.result?.ok) throw Error(receipt.result?.message || "Premiere نتیجهٔ موفق تأیید نکرد؛ پروژهٔ ناقص برای بررسی حفظ شده است.");
        return receipt.result;
      }
      await delay(1000);
    }
    throw Error("پاسخ Premiere نرسید. درخواست را تکرار نکن؛ وضعیت پروژه و رسید را بررسی کن.");
  }
  async run(job, input) {
    let video = input.video;
    let snapshot = input.project;
    let nativeMedia = null;
    if (input.project) {
      if (!/\.prproj$/i.test(input.project) || !fs.statSync(input.project).isFile() || !input.sequence?.trim()) throw Error("پروژه و نام دقیق سکانس لازم است.");
    }
    if (!video) {
      const preset = input.preset || path.join(process.env.ProgramFiles || "C:\\Program Files", "Adobe", "Adobe Premiere Pro 2026", "MediaIO", "systempresets", "3F3F3F3F_57415645", "Waveform Audio 48kHz 16-bit.epr");
      if (!/\.epr$/i.test(preset) || !fs.existsSync(preset)) throw Error("برای تحلیل مستقیم پروژه، preset خروجی WAV پریمیر (.epr) لازم است.");
      // Copy first: open/analyze a saved snapshot, never the user's live editing project.
      const copy = path.join(job.folder, "Analysis-Source.prproj");
      fs.copyFileSync(input.project, copy, fs.constants.COPYFILE_EXCL);
      snapshot = copy;
      this.emit({ progress: 2, message: "تهیهٔ نسخهٔ تحلیلی از سکانس ذخیره‌شده در پریمیر" });
      const result = await this.nativeRequest(job, { mode: "reels_export", plan_path: copy, project: copy,
        sequence: input.sequence, preset, output: path.join(job.folder, "analysis.wav") });
      video = result.output;
      nativeMedia = result.media;
    }
    if (job.canceled) return;
    const request = { video, project: snapshot || null, sequence: input.sequence || null,
      matching_sequence_export: input.project ? (!input.video || input.matching_sequence_export === true) : false,
      native_media: nativeMedia,
      reuse_plan: input.reuse_plan || null,
      output: path.join(job.folder, "package"), srt: input.srt || null,
      selector: input.selector || "local", count: Number(input.count || 6),
      min_duration: Number(input.min_duration || 20), max_duration: Number(input.max_duration || 60), style: input.style || "editorial" };
    const requestPath = path.join(job.folder, "request.json");
    fs.writeFileSync(requestPath, JSON.stringify(request, null, 2), { flag: "wx" });
    const invocation = this.options.invocation(requestPath);
    const child = spawn(invocation.exe, invocation.args, { cwd: this.options.root(), windowsHide: true,
      env: { ...process.env, PYTHONUTF8: "1", PYTHONIOENCODING: "utf-8", PYTHONUNBUFFERED: "1",
        HERMES_STUDIO_ROOT: this.options.root(), HERMES_RUNTIME_ROOT: path.join(this.options.root(), "runtime") } });
    job.child = child;
    let result = null, failure = "", buffer = "";
    const line = raw => {
      try {
        const event = JSON.parse(raw);
        if (event.event === "progress") this.emit({ progress: Math.round(event.progress * 0.85), message: event.message });
        if (event.event === "completed") result = event;
        if (event.event === "failed") failure = event.message;
      } catch (_) { /* non-protocol ASR library output */ }
    };
    child.stdout.on("data", chunk => { const parts = (buffer + chunk.toString("utf8")).split(/\r?\n/); buffer = parts.pop(); parts.forEach(line); });
    // Do not forward provider or library errors that may contain credentials.
    child.stderr.on("data", () => {});
    const code = await new Promise((resolve, reject) => { child.once("error", reject); child.once("close", resolve); });
    if (buffer) line(buffer);
    job.child = null;
    if (job.canceled) { this.emit({ state: "canceled", message: "پردازش متوقف شد؛ فایل‌های منبع حفظ شدند." }); return; }
    if (code !== 0 || !result) throw Error(failure || "پردازش Reels کامل نشد؛ ورودی و runtime را بررسی کن.");
    this.emit({ result, progress: 86, message: "برنامهٔ تدوین و زیرنویس آماده شد" });
    if (input.finish !== false && result.status === "ready_for_premiere") {
      const plan = read(result.plan);
      if(plan.native_source && (hash(plan.native_source.path)!==plan.native_source.sha256 || hash(plan.expected_project)!==plan.native_source.sha256))throw Error("نسخهٔ پروژه پس از تحلیل تغییر کرده است؛ ساخت خودکار متوقف شد.");
      for (const clip of plan.clips) for (const cue of clip.motions) {
        if (hash(cue.template_path) !== cue.template_sha256) throw Error("قالب موشن پس از ساخت برنامه تغییر کرده است.");
      }
      const native = await this.nativeRequest(job, { mode: "reels_finish", plan_path: result.plan });
      if (!native.saved || !fs.existsSync(native.project) || native.sequences?.length !== plan.clips.length) throw Error("ذخیرهٔ پروژهٔ کامل تأیید نشد.");
      result = { ...result, native_saved: true, native_project: native.project, status: "native_review_ready" };
      fs.writeFileSync(path.join(job.folder, "delivery.json"), JSON.stringify(result, null, 2), { flag: "wx" });
    }
    this.emit({ state: "completed", progress: 100, result, message: result.native_saved ? "پروژهٔ پریمیر برای بازبینی آماده است" :
      result.status === "templates_missing" ? "بستهٔ تدوین آماده است؛ قالب‌های موشن باید ساخته شوند" :
      result.status === "no_candidates" ? "بخش مناسبی با تنظیمات فعلی پیدا نشد" : "بستهٔ تدوین آمادهٔ ارسال به پریمیر است" });
  }
  cancel() {
    if (!this.active) return false;
    if (this.active.native) throw Error("Premiere در حال ساخت یا رندر است؛ برای جلوگیری از پروژهٔ ناقص از داخل Adobe توقف را انجام بده.");
    this.active.canceled = true;
    this.active.child?.kill();
    return true;
  }
}
module.exports = { ReelsManager };
