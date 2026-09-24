// Package the tested semantic engine without replacing the installed application.
const fs = require('fs');
const path = require('path');
const crypto = require('crypto');
const base = require('../package.json').build;
const root = path.resolve(__dirname, '..');
const output = 'release-semantic-candidate-20260923-01';
if (fs.existsSync(path.join(root, output))) throw Error('Candidate already exists; no overwrite');
const engine = 'engine/semantic-candidate-20260923-02';
const hashes = JSON.parse(fs.readFileSync(path.join(root, engine, 'source-hashes.json'), 'utf8').replace(/^\uFEFF/, ''));
const sha = p => crypto.createHash('sha256').update(fs.readFileSync(p)).digest('hex').toUpperCase();
for (const item of hashes) {
  if (sha(item.Path) !== item.Hash) throw Error('Engine source changed; rebuild before packaging: ' + path.basename(item.Path));
}
if (sha(path.join(root, engine, 'dist/hermes-engine/hermes-engine.exe')) !== 'E3B0DC7F24729528B643EF12F77FEB47E286F5A59FBF10547F59DD79EEE2CE9D') throw Error('Unexpected candidate engine');
module.exports = {
  ...base,
  directories: {...base.directories, output},
  electronDist: 'node_modules/electron/dist',
  extraResources: base.extraResources.map(item => item.from === 'engine/dist'
    ? {...item, from: engine + '/dist'} : item),
  win: {...base.win, signAndEditExecutable: false}
};
