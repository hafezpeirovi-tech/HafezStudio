const fs = require('fs'), vm = require('vm'), assert = require('node:assert/strict');
const source = fs.readFileSync('app/renderer.js','utf8');
const html = fs.readFileSync('app/index.html','utf8');
assert(html.indexOf('data-mode="upscale"') > html.indexOf('data-mode="podcast"'));
assert(html.indexOf('data-mode="upscale"') < html.indexOf('<nav>'));
assert(!html.includes('data-view="upscale"'));
assert(!html.includes('data-youtube-view="upscale"'));
function node(dataset={}) { return {dataset, hidden:false, classList:{toggle(){},remove(){}}}; }
const panels = [node({youtubeView:'director'}),node({youtubeView:'motion'}),node({workspace:'upscale'})];
const elements = Object.fromEntries(['#plannedWorkspace','#workspaceKicker','#workspaceTitle','#plannedIcon','#plannedPhase','#plannedTitle','#plannedCopy','#plannedWorkspace .planned-steps'].map(k=>[k,node()]));
const state = {mode:'youtube',view:'motion'};
const context = vm.createContext({state,document:{body:node(),querySelectorAll:s=>s==='.studio-view'?panels:[]},
  $:s=>elements[s],youtubeViewCopy:{director:{title:'Director'},motion:{title:'Motion'}},modeCopy:{reels:{steps:[]}},iconMarkup:()=>''});
vm.runInContext(source.slice(source.indexOf('function selectView('), source.indexOf('function updateDirectorReadiness(')),context);
vm.runInContext("selectMode('upscale')",context);
assert.deepEqual(panels.map(p=>p.hidden),[true,true,false]);
assert.equal(state.view,'motion','Standalone upscale does not replace the remembered YouTube view');
assert.equal(elements['#plannedWorkspace'].hidden,true);
vm.runInContext("selectMode('youtube')",context);
assert.deepEqual(panels.map(p=>p.hidden),[true,false,true]);
vm.runInContext("selectMode('reels')",context);
assert(panels.every(p=>p.hidden));
vm.runInContext("selectMode('upscale')",context);
assert.deepEqual(panels.map(p=>p.hidden),[true,true,false]);
console.log('PASS independent Upscale mode: placement, visibility, YouTube return, Reels switch; no processing triggered by navigation.');
