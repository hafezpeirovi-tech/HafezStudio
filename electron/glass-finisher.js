"use strict";
// Local, one-shot native review handoff. Never retries an uncertain mutation.
const fs = require("fs");
const path = require("path");
const crypto = require("crypto");
const VERSION = "glass-review-v1";
const read = p => JSON.parse(fs.readFileSync(p, "utf8").replace(/^\uFEFF/, ""));
const hash = p => crypto.createHash("sha256").update(fs.readFileSync(p)).digest("hex");
const key = p => path.resolve(p).toLowerCase();
function inside(root, p) {
  const relative = path.relative(fs.realpathSync(root), fs.realpathSync(p));
  if (!relative || relative.startsWith("..") || path.isAbsolute(relative)) throw Error("Glass artifact outside its job");
  return p;
}
function preflight(runtime, now = Date.now()) {
  let heartbeat;
  try { heartbeat = read(path.join(runtime, "glass-heartbeat.json")); }
  catch (_) { throw Error("پنل Hafez Premiere Finisher نسخهٔ Glass را در Premiere باز کن؛ اتصال زنده تأیید نشد."); }
  if (heartbeat.version !== VERSION || !Number.isFinite(heartbeat.at) || now - heartbeat.at > 45000 || heartbeat.at > now + 5000) {
    throw Error("پنل Hafez Premiere Finisher نسخهٔ Glass را در Premiere باز کن؛ اتصال زنده تأیید نشد.");
  }
  if (heartbeat.running) throw Error("Premiere Finisher مشغول است؛ درخواست دیگری ارسال نشد.");
  if (fs.existsSync(path.join(runtime, "active-plan.json"))) throw Error("صف Premiere اشغال یا نامطمئن است؛ ارسال مجدد ممنوع.");
  return heartbeat;
}
function prepare({ summary, outputDir, runtime, jobId }) {
  preflight(runtime);
  if (summary.style !== "glass" || summary.publicationReady !== false || summary.pngTimelineAssets !== 0) throw Error("Expected validated Glass review result");
  for (const field of ["xml", "plan", "srt"]) inside(outputDir, summary[field]);
  const plan = read(summary.plan);
  const report = read(path.join(path.dirname(summary.plan), "assembly-report.json"));
  if (plan.style_pack !== "glass" || plan.purpose !== "isolated-native-qa" || plan.publication_ready !== false || !plan.graphics?.length) throw Error("Not an isolated Glass plan");
  for (const field of ["xml", "plan", "srt"]) {
    if (report.outputs_sha256[path.basename(summary[field])] !== hash(summary[field])) throw Error("Glass artifact changed before native handoff");
  }
  const project = plan.expected_project_path;
  if (key(project) !== key(summary.expectedProject) || key(path.dirname(project)) !== key(path.dirname(summary.plan)) || path.extname(project).toLowerCase() !== ".prproj" || fs.existsSync(project)) throw Error("Expected new separate Premiere review project");
  const layers = plan.graphics.flatMap(c => c.template_layers);
  if (layers.length !== summary.editableMogrtLayers) throw Error("MOGRT inventory mismatch");
  for (const layer of layers) if (hash(layer.template_path) !== layer.template_sha256) throw Error("MOGRT changed before native handoff");
  const request = {
    protocol: "hafez-glass-finish-v1", mode: "finish_glass", request_id: crypto.randomUUID(), job_id: jobId,
    plan_path: path.resolve(summary.plan), xml_path: path.resolve(summary.xml), captions_path: path.resolve(summary.srt),
    expected_project_path: path.resolve(project), expected_sequence_name: plan.sequence,
    expected_mogrt_count: layers.length, expected_sfx_count: plan.sfx_cues.length,
    allow_create_project: true, save_review_project: true, export_movie: false
  };
  return { request, ledger: path.join(path.dirname(summary.plan), "native-dispatch.json"), runtime };
}
function dispatch(prepared) {
  const { request, ledger, runtime } = prepared;
  preflight(runtime);
  // A durable intent precedes submission. Any interruption requires collect/inspection, not resend.
  fs.writeFileSync(ledger, JSON.stringify({ version: VERSION, submitted_at: Date.now(), request }, null, 2), { flag: "wx" });
  fs.writeFileSync(path.join(runtime, "active-plan.json"), JSON.stringify(request), { flag: "wx" });
  return prepared;
}
function collect(prepared) {
  const resultPath = path.join(prepared.runtime, "last-result.json");
  if (!fs.existsSync(resultPath)) return null;
  let received;
  try { received = read(resultPath); } catch (_) { return null; } // Writer may still be finishing JSON.
  if (received.request_id !== prepared.request.request_id) return null;
  const receiptPath = path.join(path.dirname(prepared.ledger), "native-receipt.json");
  if (!fs.existsSync(receiptPath)) fs.writeFileSync(receiptPath, JSON.stringify(received, null, 2), { flag: "wx" });
  const result = received.result;
  if (!result?.ok || !result.saved || !result.caption_created || result.publication_ready !== false ||
      key(result.project || "") !== key(prepared.request.expected_project_path) ||
      result.sequence !== prepared.request.expected_sequence_name || !result.sequence_id ||
      result.mogrt_count !== prepared.request.expected_mogrt_count || !fs.existsSync(result.project)) {
    throw Error("پروژهٔ بازبینی نیازمند بررسی است: " + (result?.messages || ["Invalid native receipt"]).join(" | "));
  }
  return { ...result, receiptPath };
}
async function finish(options, progress, { interval = 1000, timeout = 20 * 60 * 1000 } = {}) {
  const prepared = dispatch(prepare(options));
  const start = Date.now();
  while (Date.now() - start < timeout) {
    const result = collect(prepared);
    if (result) return result;
    progress?.("Premiere: ساخت پروژهٔ مستقل، MOGRT و زیرنویس؛ منتظر پاسخ بومی", Date.now() - start);
    await new Promise(resolve => setTimeout(resolve, interval));
  }
  throw Error("پاسخ Premiere هنوز دریافت نشده؛ درخواست حفظ شد. تکرار نکن و native-dispatch.json را بررسی کن.");
}
module.exports = { VERSION, preflight, prepare, dispatch, collect, finish };
