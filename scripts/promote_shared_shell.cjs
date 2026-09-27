// One-time mechanical selector migration: preserve specificity and Director layout.
const fs = require('fs');
const path = require('path');
const root = path.resolve(__dirname, '..');
const file = path.join(root, 'app/styles.css');
const shared = /^(?:\.(?:ambient-a|ambient-b|shell|sidebar|brand(?:-mark)?|product-modes|mode|nav|system-card|status-row|status-dot|mini-grid|topbar|top-actions|version|theme-toggle|theme-status|theme-icon|thin-icon)(?=[\s.:>#,{]|$)|#(?:doctorButton|openOutput|themeButton)\b|main\b|nav\b|button\b|select\b)/;
let count = 0;
const css = fs.readFileSync(file, 'utf8').replace(/body\[data-view="director"\](?=([^{}]*))/g, (match, tail) => {
  if (tail.trimStart().startsWith('[')) return match;
  if (tail.trim() === '' || shared.test(tail.trimStart())) { count++; return 'body[data-shell="studio"]'; }
  return match;
});
if (count < 70) throw Error('Unexpected CSS structure: '+count);
fs.writeFileSync(file, css);
for (const name of ['build/upscale-candidate.cjs','scripts/update_desktop_shortcut.ps1','scripts/verify_upscale_package.cjs']) {
  const target = path.join(root,name);
  fs.writeFileSync(target,fs.readFileSync(target,'utf8').replaceAll('release-upscale-candidate-20260926-04','release-upscale-candidate-20260927-01'));
}
console.log('Promoted shared selectors:', count);
