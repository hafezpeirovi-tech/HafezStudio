const fs = require('fs'), path = require('path'), crypto = require('crypto');
const asar = require('@electron/asar');
const root = path.resolve(__dirname,'..');
const packaged = path.join(root,'release-upscale-candidate-20260928-01/win-unpacked/resources');
const sha = buffer => crypto.createHash('sha256').update(buffer).digest('hex');
const files = ['electron/upscale.js','electron/upscale-fast.js','electron/upscale-websr-preload.js','electron/main.js','electron/preload.js','app/index.html','app/upscale.js','app/upscale-websr.html','app/upscale-websr-renderer.js','app/vendor/websr/websr.js','app/vendor/websr/weights.json','app/vendor/websr/provenance.json','app/vendor/websr/LICENSE','app/renderer.js','app/styles.css'];
files.push('electron/upscale-topaz.js');
for (const file of files) {
  if (sha(fs.readFileSync(path.join(root,file))) !== sha(asar.extractFile(path.join(packaged,'app.asar'),path.normalize(file)))) throw Error('Packaged source differs: '+file);
}
for (const file of ['electron/upscale-worker.py','electron/upscale-seed-bridge.py']) {
  if (sha(fs.readFileSync(path.join(root,file))) !== sha(fs.readFileSync(path.join(packaged,'app.asar.unpacked',file)))) throw Error('Unpacked Python differs: '+file);
}
const install = JSON.parse(fs.readFileSync(path.join(packaged,'upscale-install.json')));
if (!fs.existsSync(path.join(install.runtime,'environment-verified.json'))) throw Error('Missing isolated environment');
if (fs.existsSync(path.join(packaged,'runtime/upscale'))) throw Error('Runtime unexpectedly duplicated in release');
console.log('PASS: '+(files.length+2)+' packaged files match; WebSR bundled; Python unpacked; local runtime resolved, not duplicated.');
