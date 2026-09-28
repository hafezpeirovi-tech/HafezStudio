const fs=require('fs'),path=require('path'),crypto=require('crypto');
const root=path.resolve(__dirname,'../app/vendor/websr');
const file=path.join(root,'websr.js');
const original=fs.readFileSync(file,'utf8');
// Upstream distributes a webpack development bundle. Unwrap only literal eval
// modules so our isolated renderer can use a strict CSP, without unsafe-eval.
let count=0;
const prepared=original.replace(/\beval\(("(?:[^"\\]|\\.)*")\);/g,(_,literal)=>{count++;return JSON.parse(literal);});
if(!count || /\beval\(/.test(prepared.replace(/\/\*[\s\S]*?\*\//g,'')))throw Error('Unrecognized upstream bundle');
fs.writeFileSync(file,prepared);
const sha=data=>crypto.createHash('sha256').update(data).digest('hex');
fs.writeFileSync(path.join(root,'provenance.json'),JSON.stringify({source:'https://github.com/sb2702/websr',license:'MIT',model:'anime4k/cnn-2x-l, Real Life weights',downloaded:'2026-09-27',originalSha256:sha(original),bundleSha256:sha(prepared),weightsSha256:sha(fs.readFileSync(path.join(root,'weights.json'))),transform:'Unwrap literal webpack eval modules; no network calls added'},null,2));
console.log('Prepared strict-CSP bundle:',count,'modules');
