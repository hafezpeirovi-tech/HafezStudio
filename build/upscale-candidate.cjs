const fs = require('fs');
const path = require('path');
const base = require('../package.json').build;
const output = process.env.HAFEZ_UPSCALE_BUILD || 'release-upscale-candidate-20260927-01';
if (!/^release-upscale-candidate-\d{8}-\d{2}$/.test(output)) throw Error('Unsafe build target');
if (fs.existsSync(path.join(__dirname, '..', output))) throw Error('Candidate exists; no overwrite');
// Independent local AI runtime is intentionally not duplicated or bundled in the installer.
module.exports = {
  ...base,
  asarUnpack: ['electron/upscale-worker.py', 'electron/upscale-seed-bridge.py'],
  directories: {...base.directories, output},
  electronDist: 'node_modules/electron/dist',
  extraResources: [...base.extraResources.map(item => item.from === 'runtime'
    ? {...item, filter: ['**/*', '!upscale{,/**/*}']}
    : item.from === 'engine/dist' ? {...item, from: 'engine/semantic-candidate-20260923-02/dist'} : item),
    {from: 'build/upscale-install.json', to: 'upscale-install.json'}],
  win: {...base.win, signAndEditExecutable: false}
};
