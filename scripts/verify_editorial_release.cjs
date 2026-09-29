'use strict';
const fs=require('fs'),path=require('path'),crypto=require('crypto'),asar=require('@electron/asar');
const root=path.resolve(__dirname,'..');
const resources=path.join(root,'release-upscale-candidate-20260928-01/win-unpacked/resources');
const backup=path.join(root,'backups/editorial-release-20260929-01');
const hash=p=>crypto.createHash('sha256').update(fs.readFileSync(p)).digest('hex');
const installed=path.join(resources,'app.asar');
if(hash(installed)!==hash(path.join(root,'build/editorial-shell-20260928-01/app.asar')))throw Error('Shell differs');
const main=asar.extractFile(installed,'electron/main.js').toString('utf8');
if(!main.includes('["--glass-review", "--editorial-glass"]'))throw Error('Editorial routing missing');
for(const name of ['app/index.html','app/renderer.js','electron/upscale.js']) {
  if(!asar.extractFile(installed,name).equals(asar.extractFile(path.join(backup,'app.asar'),name)))throw Error('Unrelated component changed: '+name);
}
let count=0;
function verifyTree(relative='') {
  const candidate=path.join(root,'engine/editorial-candidate-20260928-02/dist/hermes-engine',relative);
  for(const entry of fs.readdirSync(candidate,{withFileTypes:true})) {
    const child=path.join(relative,entry.name);
    if(entry.isDirectory())verifyTree(child);
    else {if(hash(path.join(candidate,entry.name))!==hash(path.join(resources,'engine/hermes-engine',child)))throw Error('Engine mismatch: '+child);count++;}
  }
}
verifyTree();
console.log('PASS installed shell, Editorial routing, unchanged UI/Upscale and '+count+' engine files');
