"use strict";

const fs = require("node:fs");
const path = require("node:path");
const key = value => path.resolve(value).toLowerCase();

// Store only delivery metadata, never engine transcripts or credentials.
function validate(record) {
  if (!record || record.version !== 1 || !path.isAbsolute(record.project || "") ||
      path.extname(record.project).toLowerCase() !== ".prproj" || !path.isAbsolute(record.receipt || "")) return null;
  try {
    const result = JSON.parse(fs.readFileSync(record.receipt, "utf8")).result;
    if (!result?.ok || !result.saved || !result.caption_created || result.publication_ready !== false ||
        !result.sequence_id || key(result.project || "") !== key(record.project) ||
        result.sequence_id !== record.sequenceId || !Number.isInteger(result.mogrt_count) || result.mogrt_count < 1 ||
        result.apply?.failed > 0 || result.apply?.safetyFailures > 0 ||
        !fs.statSync(record.project).isFile() || fs.statSync(record.project).size === 0) return null;
    return { ...record, mogrtCount: result.mogrt_count, sequence: result.sequence, publicationReady: false };
  } catch (_) { return null; }
}

function atomicWrite(file, value) {
  fs.mkdirSync(path.dirname(file), { recursive: true });
  const temp = `${file}.${process.pid}.tmp`;
  fs.writeFileSync(temp, JSON.stringify(value, null, 2), "utf8");
  fs.renameSync(temp, file);
}

function save(userData, event) {
  const summary = event.summary || {};
  const candidate = event.state === "completed" && summary.nativeReviewReady ? validate({
    version: 1, jobId: event.jobId, outputDir: event.outputDir, savedAt: new Date().toISOString(),
    project: summary.nativeProject, receipt: summary.nativeReceipt, sequenceId: summary.nativeSequenceId
  }) : null;
  if (event.state === "completed" && summary.nativeReviewReady && !candidate) {
    throw Error("رسید پروژهٔ Premiere معتبر نیست؛ پروژه به‌عنوان خروجی آماده ثبت نشد.");
  }
  atomicWrite(path.join(event.outputDir, "hafez-delivery.json"), {
    version: 1, state: event.state, jobId: event.jobId, updatedAt: new Date().toISOString(),
    review: candidate, nativeReviewReady: !!candidate, publicationReady: false
  });
  // A failed or XML-only job must not erase the previous successful review.
  if (candidate) atomicWrite(path.join(userData, "last-premiere-review.json"), candidate);
  return candidate;
}

function latest(userData) {
  try {
    const stored = JSON.parse(fs.readFileSync(path.join(userData, "last-premiere-review.json"), "utf8"));
    const review = validate(stored);
    return review ? { status: "ready", review } : { status: "unavailable", review: null };
  } catch (error) { return { status: error.code === "ENOENT" ? "none" : "unavailable", review: null }; }
}

module.exports = { save, latest, validate };
