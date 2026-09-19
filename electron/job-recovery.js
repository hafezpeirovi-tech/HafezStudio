"use strict";
const fs = require("fs");
const path = require("path");

// Only incomplete manifests from these exact, unchanged source files qualify.
function findPreparedJob(outputRoot, cam1, cam2, style = "signal-os") {
  const canonical = (p) => path.resolve(p).toLowerCase();
  const sourceTime = Math.max(fs.statSync(cam1).mtimeMs, fs.statSync(cam2).mtimeMs);
  const folders = fs.readdirSync(outputRoot, { withFileTypes: true })
    .filter((entry) => entry.isDirectory() && /^\d{8}-\d{6}-/.test(entry.name))
    .map((entry) => path.join(outputRoot, entry.name)).sort().reverse().slice(0, 30);
  for (const folder of folders) {
    try {
      const project = JSON.parse(fs.readFileSync(path.join(folder, "project.json"), "utf8"));
      if ((project.stylePack || "signal-os") !== style) continue;
    } catch (_) { if (style !== "signal-os") continue; }
    for (const name of fs.readdirSync(folder).filter((entry) => entry.endsWith(".edit.json"))) {
      try {
        const manifestPath = path.join(folder, name);
        const manifest = JSON.parse(fs.readFileSync(manifestPath, "utf8").replace(/^\uFEFF/, ""));
        if (canonical(manifest.cam1_path) !== canonical(cam1) || canonical(manifest.cam2_path) !== canonical(cam2)) continue;
        if (fs.statSync(manifestPath).mtimeMs < sourceTime || !manifest.mapped_words?.length) continue;
        const outputs = manifest.outputs || {};
        if (!outputs.xml || canonical(path.dirname(outputs.xml)) !== canonical(folder)) continue;
        if (Object.values(outputs).some((p) => typeof p === "string" && canonical(path.dirname(p)) !== canonical(folder))) continue;
        if (fs.existsSync(outputs.xml) && outputs.professional_plan && fs.existsSync(outputs.professional_plan)) continue;
        return { manifestPath, outputDir: folder };
      } catch (_) { /* Partial/corrupt manifests never prevent a new job. */ }
    }
  }
  return null;
}
module.exports = { findPreparedJob };
