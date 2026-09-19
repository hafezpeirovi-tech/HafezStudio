"use strict";
// Explicit native acceptance test using the SAME broker as Electron, not a mock.
// One-shot only. A prior dispatch is collected, never submitted twice.
const fs = require("fs");
const path = require("path");
const broker = require("../electron/glass-finisher");
async function main() {
  const [logPath, runtime, mode = "dispatch"] = process.argv.slice(2);
  if (!logPath || !runtime || !["dispatch", "collect"].includes(mode)) throw Error("Usage: node verify_glass_desktop.cjs finalize.log CEP-runtime [dispatch|collect]");
  const completed = fs.readFileSync(logPath, "utf8").split(/\r?\n/).filter(l => l.startsWith("{")).map(l => JSON.parse(l)).findLast(e => e.event === "completed");
  if (!completed?.summary) throw Error("No validated engine completion in this log");
  const ledger = path.join(path.dirname(completed.summary.plan), "native-dispatch.json");
  let result;
  if (mode === "collect") {
    const saved = JSON.parse(fs.readFileSync(ledger, "utf8"));
    result = broker.collect({ request: saved.request, ledger, runtime });
    if (!result) throw Error("No matching receipt yet; do not resend");
  } else {
    let last = -Infinity;
    result = await broker.finish({ summary: completed.summary, outputDir: path.dirname(completed.manifest), runtime, jobId: completed.jobId }, (message, elapsed) => {
      if (elapsed - last >= 10000) { console.log(Math.floor(elapsed / 1000) + "s: " + message); last = elapsed; }
    });
  }
  console.log(JSON.stringify({ event: "native-review-completed", project: result.project, sequence: result.sequence, sequenceId: result.sequence_id, mogrtCount: result.mogrt_count, captionCreated: result.caption_created, receipt: result.receiptPath, publicationReady: false, engineCompletionLog: path.resolve(logPath), asrVerifiedByThisScript: false }));
}
main().catch(error => { console.error(error.message); process.exitCode = 1; });
