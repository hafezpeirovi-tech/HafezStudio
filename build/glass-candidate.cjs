// Isolated local acceptance build; never replaces release/win-unpacked.
const base = require('../package.json').build;
const revision = process.env.HAFEZ_GLASS_CANDIDATE_REVISION || '01';
if (!/^\d{2}$/.test(revision)) throw Error('Invalid isolated candidate revision');
module.exports = {
  ...base,
  directories: {...base.directories, output:`release-glass-candidate-20260913-${revision}`},
  electronDist:'node_modules/electron/dist',
  extraResources:base.extraResources.map(item => item.from==='engine/dist'
    ? {...item,from:`engine/glass-candidate-20260913-${revision}/dist`}
    : item.from==='premiere-cep-plugin' ? {...item,filter:['**/*','!runtime{,/**/*}']} : item),
  win:{...base.win,signAndEditExecutable:false}
};
