"use strict";
// Preserve the installed UI/Upscale; patch only the approved engine flag.
const fs = require('fs');
const path = require('path');
const asar = require('@electron/asar');
const root = path.resolve(__dirname,'..');
const installed = path.join(root,'release-upscale-candidate-20260928-01/win-unpacked/resources/app.asar');
const output = path.join(root,'build/editorial-shell-20260928-01');
const old = asar.extractFile(installed,'electron/main.js').toString('utf8');
const current = fs.readFileSync(path.join(root,'electron/main.js'),'utf8');
const normalize = s => s.replace(/\r\n/g,'\n');
const reverted = current.replace('["--glass-review", "--editorial-glass"]','["--glass-review"]');
if(normalize(old)!==normalize(reverted)) throw Error('Installed main differs beyond the intended routing change; inspect before packaging');
if(fs.existsSync(output)) throw Error('Shell candidate already exists');
fs.mkdirSync(output,{recursive:true});
const stage=path.join(output,'app');
asar.extractAll(installed,stage);
fs.writeFileSync(path.join(stage,'electron/main.js'),current);
asar.createPackageWithOptions(stage,path.join(output,'app.asar'),{unpack:'**/*.py'})
  .then(()=>{
    const result=asar.extractFile(path.join(output,'app.asar'),'electron/main.js').toString('utf8');
    if(result!==current) throw Error('Packaged routing differs');
    console.log('PASS same installed shell; only Editorial engine flag changed');
  }).catch(error=>{console.error(error.message);process.exitCode=1;});
