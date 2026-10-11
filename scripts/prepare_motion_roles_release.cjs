'use strict';
// Relocate a COPY of native-tested media bindings to the current installation.
// No new transcription, no Premiere dispatch, no changes to the review source.
const fs=require('fs'),path=require('path'),crypto=require('crypto'),asar=require('@electron/asar');
const root=path.resolve(__dirname,'..');
const resources=path.join(root,'release-upscale-candidate-20260928-01/win-unpacked/resources');
const source=path.resolve(process.argv[2]||''),dest=path.resolve(process.argv[3]||'');
const inside=p=>{const r=path.relative(path.join(root,'proof'),p);if(!r||r.startsWith('..')||path.isAbsolute(r))throw Error('Expected a scoped proof directory');};
inside(source);inside(dest);
const read=p=>JSON.parse(fs.readFileSync(p,'utf8').replace(/^\uFEFF/,''));
const hash=p=>crypto.createHash('sha256').update(fs.readFileSync(p)).digest('hex');
const manifest=read(path.join(source,'motion-review.edit.json'));
const plan=read(manifest.outputs.professional_plan);
const receipt=read(path.join(path.dirname(manifest.outputs.professional_plan),'native-receipt.json')).result;
if(!receipt?.ok||!receipt.saved||receipt.project!==plan.expected_project_path)throw Error('Native saved proof missing');
if(plan.motion_role_policy!=='hafez-glass-motion-roles-v1')throw Error('Expected tested role plan');
// Compiled portraits must retain exact-job/authoring-source identity. Test
// those separately in their original proof; never relocate their recipes.
if(plan.editorial_compilation)throw Error('Compiled proof cannot be relocated');
const installedMain=asar.extractFile(path.join(resources,'app.asar'),'electron/main.js').toString('utf8');
if(!installedMain.includes('--editorial-glass')||!installedMain.includes('--glass-review'))throw Error('Installed routing missing');
const library=read(path.join(resources,'config/glass-library.json'));
for(const cue of plan.graphics)for(const layer of cue.template_layers){
  if(layer.compiled_binding)continue;
  const asset=library.assets.find(a=>a.id===layer.asset_id);
  if(!asset)throw Error('Installed asset missing: '+layer.asset_id);
  const installed=path.resolve(resources,asset.path);
  if(hash(installed)!==layer.template_sha256||hash(layer.template_path)!==layer.template_sha256)throw Error('Asset identity mismatch');
  layer.template_path=installed;
}
if(fs.existsSync(dest))throw Error('Smoke directory already exists; no overwrite');
fs.mkdirSync(dest);
plan.expected_project_path=path.join(dest,'Hafez-Motion-Roles-Review.prproj');
const outputs={};
for(const [key,name]of Object.entries({xml:'Glass-Director.xml',professional_plan:'Glass-Director.premiere-plan.json',tight_srt:'Glass-Director.srt',audit:'assembly-report.json',youtube:'YouTube-review.md'}))outputs[key]=path.join(dest,name);
for(const key of ['xml','tight_srt','youtube'])fs.copyFileSync(manifest.outputs[key],outputs[key],fs.constants.COPYFILE_EXCL);
fs.writeFileSync(outputs.professional_plan,JSON.stringify(plan,null,2),{flag:'wx'});
const report=read(manifest.outputs.audit);
for(const key of ['xml','professional_plan','tight_srt'])report.outputs_sha256[path.basename(outputs[key])]=hash(outputs[key]);
fs.writeFileSync(outputs.audit,JSON.stringify(report,null,2),{flag:'wx'});
manifest.outputs=outputs;
fs.writeFileSync(path.join(dest,'smoke.edit.json'),JSON.stringify(manifest,null,2),{flag:'wx'});
console.log(JSON.stringify({manifest:path.join(dest,'smoke.edit.json'),resources,nativeProof:receipt.project}));
