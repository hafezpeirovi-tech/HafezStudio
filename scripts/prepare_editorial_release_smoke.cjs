'use strict';
// Relocate a COPY of the reviewed assembly to the installed resource identities.
// Media, cuts, text and timestamps are unchanged; no native Premiere mutation.
const fs=require('fs'),path=require('path'),crypto=require('crypto');
const root=path.resolve(__dirname,'..');
const resources=path.join(root,'release-upscale-candidate-20260928-01/win-unpacked/resources');
const source=path.join(root,'proof/automatic-semantic-glass-20260923-05/frozen-package');
const dest=path.join(root,'proof/editorial-release-smoke-20260929-01');
const read=p=>JSON.parse(fs.readFileSync(p,'utf8').replace(/^\uFEFF/,''));
const hash=p=>crypto.createHash('sha256').update(fs.readFileSync(p)).digest('hex');
const plan=read(path.join(source,'Glass-Director.premiere-plan.json'));
const library=read(path.join(resources,'config/glass-library.json'));
for(const cue of plan.graphics) for(const layer of cue.template_layers) {
  const asset=library.assets.find(a=>a.id===layer.asset_id);
  if(!asset) throw Error('Installed library missing '+layer.asset_id);
  const installed=path.resolve(resources,asset.path);
  if(hash(installed)!==layer.template_sha256 || hash(layer.template_path)!==hash(installed)) throw Error('Installed asset identity differs');
  layer.template_path=installed;
}
if(fs.existsSync(dest)) throw Error('Smoke output already exists');
fs.mkdirSync(dest);
plan.expected_project_path=path.join(dest,'Hafez-Glass-Review.prproj');
fs.writeFileSync(path.join(dest,'Glass-Director.premiere-plan.json'),JSON.stringify(plan,null,2),{flag:'wx'});
for(const name of ['Glass-Director.xml','Glass-Director.srt','YouTube-review.md'])fs.copyFileSync(path.join(source,name),path.join(dest,name),fs.constants.COPYFILE_EXCL);
const report=read(path.join(source,'assembly-report.json'));
for(const name of Object.keys(report.outputs_sha256)) report.outputs_sha256[name]=hash(path.join(dest,name));
fs.writeFileSync(path.join(dest,'assembly-report.json'),JSON.stringify(report,null,2),{flag:'wx'});
const outputs={};
for(const [key,name] of Object.entries({xml:'Glass-Director.xml',professional_plan:'Glass-Director.premiere-plan.json',tight_srt:'Glass-Director.srt',audit:'assembly-report.json',youtube:'YouTube-review.md'}))outputs[key]=path.join(dest,name);
fs.writeFileSync(path.join(dest,'smoke.edit.json'),JSON.stringify({style_pack:'glass',glass_review:true,outputs},null,2),{flag:'wx'});
console.log(path.join(dest,'smoke.edit.json'));
