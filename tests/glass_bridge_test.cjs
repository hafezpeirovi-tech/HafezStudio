// Mocked contract tests supplement, never replace, the native Premiere proof.
const fs = require('fs');
const vm = require('vm');
const assert = require('assert');
const context = vm.createContext({$: {}, console, assert});
vm.runInContext(fs.readFileSync('premiere-cep-plugin/jsx/hafez.jsx', 'utf8'), context);
vm.runInContext(`
function scalar(name, value) {
  return {displayName:name, value:value, getValue:function(){return this.value;},
    setValue:function(v){this.value=v;return 0;}, getColorValue:function(){throw Error('not color');}};
}
var color=scalar('Text 1',123);
color.rgba=[255,1,2,3]; color.getColorValue=function(){return this.rgba;};
color.setColorValue=function(a,r,g,b){this.rgba=[a,r,g,b];};
var text=scalar('Text 1',JSON.stringify({textEditValue:'Vendor',fontEditValue:['Original'],
  fontSizeEditValue:[100],fontTextRunLength:[6],capPropFontEdit:true,capPropFontSizeEdit:true}));
var group=scalar('Text 1','group;ids;');
var point=scalar('Position',[0.5,0.5]);
var component={properties:[group,color,text,point]};component.properties.numItems=4;
var bindings=[{name:'Text 1',kind:'color',value:[0,1,0,1]},
 {name:'Text 1',kind:'text',value:'قالب فارسی',font:'TestFont',fontSize:72},
 {name:'Position',kind:'point',value:[0.4,0.6]}];
var report=$._hafez.applyTypedControls(component,bindings);
assert.equal(report.applied,3);assert.equal(report.texts,1);
assert.equal(JSON.parse(text.value).textEditValue,'قالب فارسی');
assert.equal(JSON.parse(text.value).fontEditValue[0],'TestFont');
assert.equal(JSON.parse(text.value).fontSizeEditValue[0],72);
assert.equal(color.rgba.join(','),'255,0,255,0');
assert.equal(group.value,'group;ids;');
assert.equal(point.value.join(','),'0.4,0.6');
assert.throws(function(){$._hafez.applyTypedControls(component,[bindings[0],bindings[0]]);},/Duplicate/);
assert.throws(function(){$._hafez.applyTypedControls(component,[{name:'Absent',kind:'scalar',value:2}]);},/not found/);
var locked=JSON.parse(text.value);locked.capPropFontEdit=false;text.value=JSON.stringify(locked);
assert.throws(function(){$._hafez.applyTypedControls(component,[bindings[1]]);},/locked/);
var name=$._hafez.layerItemName({typed_controls:bindings},{id:'chapter-1'},1);
assert.equal(name,'Hafez Glass chapter-1 L1');
var item={name:name,start:{seconds:0},getMGTComponent:function(){return component;}};
assert($._hafez.matchesCueItem(item,name,0));
assert(!$._hafez.matchesCueItem(item,name,6));
assert(!$._hafez.matchesCueItem({name:name+' owner edit',start:item.start},name,0));
assert(!$._hafez.matchesCueItem(item,'Vendor',0));
assert.throws(function(){$._hafez.layerItemName({typed_controls:bindings},{id:'bad name'},0);});
var nativeScale=scalar('Scale',100), uniform=scalar('Uniform Scale',false);
var nativeProps=[nativeScale,uniform];nativeProps.numItems=2;
var nativeComponents=[{matchName:'AE.ADBE Motion',properties:nativeProps}];nativeComponents.numItems=1;
var nativeItem={components:nativeComponents};
$._hafez.applyNativeScale(nativeItem,70);
assert.equal(nativeScale.value,70);assert.equal(uniform.value,true);
assert.throws(function(){$._hafez.applyNativeScale(nativeItem,NaN);},/Invalid/);
nativeScale.isTimeVarying=function(){return true;};
assert.throws(function(){$._hafez.applyNativeScale(nativeItem,50);},/Animated/);
assert.equal(nativeScale.value,70);
`, context);
console.log('Glass bridge contract tests passed (typed controls, locks, ownership, duplicate protection).');
