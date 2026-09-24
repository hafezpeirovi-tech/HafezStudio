"use strict";
// Read-only acceptance of the built app; writes evidence only in a new proof directory.
// Does not dispatch to Premiere, launch the desktop app or replace the installed release.
const fs = require("fs");
const path = require("path");
const crypto = require("crypto");
const assert = require("assert/strict");
const { spawnSync } = require("child_process");
const asar = require("@electron/asar");
const root = path.resolve(__dirname, "..");
const revision = process.argv[2] || '01';
const semantic = revision === 'semantic-20260923-01';
assert(semantic || /^\d{2}$/.test(revision), 'Invalid isolated candidate revision');
const candidate = path.join(root, semantic ? 'release-semantic-candidate-20260923-01' : `release-glass-candidate-20260913-${revision}`, "win-unpacked");
const resources = path.join(candidate, "resources");
const attempt = process.argv[3] || '01';
assert(/^\d{2}$/.test(attempt), 'Invalid verification attempt');
const output = path.join(root, "proof", semantic ? `semantic-desktop-verification-20260923-${attempt}` : revision === '01' ? "glass-candidate-20260913-02" : `glass-candidate-${revision}-verification-20260913`);
const hash = bytes => crypto.createHash("sha256").update(bytes).digest("hex");
const fileHash = p => hash(fs.readFileSync(p));
const readJson = p => JSON.parse(fs.readFileSync(p, "utf8").replace(/^\uFEFF/, ""));
function walk(directory) {
  return fs.readdirSync(directory, {withFileTypes:true}).flatMap(e => e.isDirectory()
    ? walk(path.join(directory, e.name)) : [path.join(directory, e.name)]);
}
function confined(base, relative) {
  const file = fs.realpathSync(path.join(base, relative));
  const rel = path.relative(fs.realpathSync(base), file);
  assert(rel && !rel.startsWith("..") && !path.isAbsolute(rel), "Unconfined candidate resource");
  return file;
}
function main() {
  assert(!fs.existsSync(output), "Proof exists; never overwrite acceptance evidence");
  fs.mkdirSync(output);
  const report = {protocol:"hafez-glass-candidate-acceptance-v1", at:new Date().toISOString(),
    app:path.join(candidate, "Hafez Studio.exe"), resources,
    nativeDispatch:false, freshAsrRun:false, publicationReady:false, originalReleaseReplaced:false};
  report.appSha256 = fileHash(report.app);
  report.sourceHashes = {};
  const archive = path.join(resources, "app.asar");
  for (const folder of ["electron", "app"]) {
    for (const file of walk(path.join(root, folder))) {
      const relative = path.relative(root, file).replace(/\\/g, "/");
      // ASAR 3.x requires native separators for nested directories on Windows.
      const actual = hash(asar.extractFile(archive, path.relative(root, file)));
      assert.equal(actual, fileHash(file), "Stale packaged app: " + relative);
      report.sourceHashes[relative] = actual;
    }
  }
  for (const relative of ["panel.js", "jsx/hafez.jsx", "jsx/glass-review.jsx"]) {
    assert.equal(fileHash(path.join(root, "premiere-cep-plugin", relative)),
      fileHash(path.join(resources, "premiere-cep-plugin", relative)), "Stale CEP resource");
  }
  assert(!fs.existsSync(path.join(resources, "premiere-cep-plugin", "runtime")), "Shipped mutable CEP queue");
  report.cepRuntimeExcluded = true;
  const library = readJson(path.join(resources, "config/glass-library.json"));
  assert.equal(fileHash(path.join(root,"config/glass-library.json")), fileHash(path.join(resources,"config/glass-library.json")));
  for (const asset of library.assets) {
    assert.equal(fileHash(confined(resources, asset.path)), asset.sha256, "Damaged MOGRT: " + asset.id);
  }
  report.mogrtAssetsVerified = library.assets.length;
  report.packagesVerified = library.packages.length;
  const audio = readJson(path.join(resources, "config/glass-audio.json"));
  assert.equal(fileHash(confined(resources, audio.chapter_entry.path)), audio.chapter_entry.sha256);
  report.chapterSfxVerified = true;
  const engine = path.join(resources, "engine/hermes-engine/hermes-engine.exe");
  report.engineSha256 = fileHash(engine);
  assert.equal(report.engineSha256, fileHash(path.join(root, semantic ? 'engine/semantic-candidate-20260923-02/dist/hermes-engine/hermes-engine.exe' : `engine/glass-candidate-20260913-${revision}/dist/hermes-engine/hermes-engine.exe`)));
  function frozen(name, args) {
    const result = spawnSync(engine, args, {cwd:output, encoding:"utf8", timeout:120000, windowsHide:true,
      env:{...process.env,PYTHONUTF8:"1"}});
    fs.writeFileSync(path.join(output,name+".stdout.txt"),result.stdout || "",{flag:"wx"});
    fs.writeFileSync(path.join(output,name+".stderr.txt"),result.stderr || "",{flag:"wx"});
    assert.ifError(result.error);
    assert.equal(result.status, 0, name + " failed; see isolated evidence");
    return JSON.parse(result.stdout.trim().replace(/^\uFEFF/, ""));
  }
  report.glassStatus = frozen("glass-status", ["glass-status"]);
  report.doctor = frozen("doctor", ["doctor","--json"]);
  const oldPlan = path.join(root, semantic ? 'proof/automatic-semantic-glass-20260923-05/frozen-package/Glass-Director.premiere-plan.json' : "proof/glass-finalize-20260913-03/F_Hafez_Youtube_8rdvid_C2963.glass-review/Glass-Director.premiere-plan.json");
  const plan = readJson(oldPlan);
  plan.expected_project_path = path.join(output,"NOT-DISPATCHED.prproj");
  for (const cue of plan.graphics) for (const layer of cue.template_layers) {
    const asset = library.assets.find(a=>a.id===layer.asset_id);
    assert(asset, "Unknown asset");
    assert.equal(path.resolve(layer.template_path),path.resolve(root,asset.path));
    layer.template_path = confined(resources,asset.path);
  }
  const planPath = path.join(output,"packaged-resources-qa.plan.json");
  fs.writeFileSync(planPath,JSON.stringify(plan,null,2),{flag:"wx"});
  report.planValidation = frozen("glass-validate",["glass-validate","--qa","--plan",planPath]);
  report.ok = true;
  fs.writeFileSync(path.join(output,"candidate-verification.json"),JSON.stringify(report,null,2),{flag:"wx"});
  console.log(JSON.stringify({ok:report.ok, app:report.app, proof:output,
    appSourceFiles:Object.keys(report.sourceHashes).length, assets:report.mogrtAssetsVerified,
    packages:report.packagesVerified, cepRuntimeExcluded:report.cepRuntimeExcluded,
    planValidation:report.planValidation, freshAsrRun:false, publicationReady:false}));
}
try { main(); } catch(error) { console.error(error.stack); process.exitCode = 1; }
