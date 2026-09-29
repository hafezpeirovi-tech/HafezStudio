(function(){
 var base=new File($.fileName).parent, src=new File(base.fsName+'/Hafez-Editorial-Intro-v1.aep'), dest=new File(base.fsName+'/Hafez-FX-Editorial-Intro-v2.aep');
 var out=new File(base.fsName+'/refine-v2.log');out.encoding='UTF-8';function log(s){out.open('a');out.writeln(s);out.close();}
 function find(){for(var i=1;i<=app.project.numItems;i++)if(app.project.item(i) instanceof CompItem && app.project.item(i).name==='Hafez Editorial Intro v1')return app.project.item(i);throw Error('Missing comp');}
 if(!app.project.file || app.project.file.fsName!==src.fsName || dest.exists){log('BLOCKED: wrong source or existing output');return;}
 app.beginSuppressDialogs();
 try{
  var c=find();c.time=2;
  var names=['Title Line 1','Title Line 2','Subtitle','Topic Label'];
  for(var i=0;i<names.length;i++){
   var l=c.layer(names[i]);l.transform.anchorPoint.expression='var r=sourceRectAtTime(time,false);[r.left+r.width,0]';
   if(i<2)l.transform.scale.expression='var r=sourceRectAtTime(time,false);var requested=thisComp.layer("HAFEZ CONTROLS").effect("Title Scale")(1);var s=Math.min(requested,840/Math.max(1,r.width)*100);[s,s]';
   else l.transform.scale.expression='var r=sourceRectAtTime(time,false);var s=Math.min(100,'+(i===2?840:215)+'/Math.max(1,r.width)*100);[s,s]';
  }
  // Native source text stays editable. Highlight the final word, not the entire line.
  var line=c.layer('Title Line 2');line.property('ADBE Effect Parade').property(1).enabled=false;
  var d=line.property('Source Text').value;d.fillColor=[243/255,247/255,244/255];line.property('Source Text').setValue(d);
  var anim=line.property('ADBE Text Properties').property('ADBE Text Animators').addProperty('ADBE Text Animator');anim.name='Editable last-word accent';
  anim.property('ADBE Text Animator Properties').addProperty('ADBE Text Fill Color').expression='thisComp.layer("HAFEZ CONTROLS").effect("Accent Color")(1)';
  var sel=anim.property('ADBE Text Selectors').addProperty('ADBE Text Selector');
  sel.property('ADBE Text Range Advanced').property('ADBE Text Range Units').setValue(2);
  sel.property('ADBE Text Index Start').expression='var s=text.sourceText.toString();Math.max(0,s.lastIndexOf(" ")+1)';
  sel.property('ADBE Text Index End').expression='text.sourceText.toString().length';
  // Place brand at the established left margin regardless of its length.
  var brand=c.layer('Brand');brand.transform.anchorPoint.expression='var r=sourceRectAtTime(time,false);[r.left,0]';brand.transform.position.setValue([110,91]);
  // Soft ambient gradient light behind supplied background, avoiding any glow on text.
  function haze(name,pos,size,color,opacity){
   var l=c.layers.addShape();l.name=name;l.transform.position.setValue(pos);
   var g=l.property('ADBE Root Vectors Group').addProperty('ADBE Vector Group').property('ADBE Vectors Group');
   g.addProperty('ADBE Vector Shape - Ellipse').property('ADBE Vector Ellipse Size').setValue(size);
   var f=g.addProperty('ADBE Vector Graphic - Fill');f.property('ADBE Vector Fill Color').setValue(color);
   l.transform.opacity.setValue(opacity);
   var blur=l.property('ADBE Effect Parade').addProperty('ADBE Gaussian Blur 2');blur.property(1).setValue(260);
   l.moveBefore(c.layer('Qss supplied gradient'));
  }
  haze('Soft sage ambient light',[-80,150],[1700,1400],[.20,.36,.28],50);
  haze('Soft teal ambient light',[1390,1090],[1500,620],[.10,.22,.23],36);
  // Retain saved originals and give the corrected export its own identity.
  c.motionGraphicsTemplateName='Hafez-FX Editorial Intro v2';
  app.project.save(dest);log('SOURCE_SAVED');
  if(!c.exportAsMotionGraphicsTemplate(false,base.fsName))throw Error('MOGRT export failed');log('MOGRT_EXPORTED');
  c=find();
  var q=app.project.renderQueue.items.add(c);q.timeSpanStart=0;q.timeSpanDuration=6;
  q.outputModule(1).applyTemplate('H.264 - Match Render Settings - 15 Mbps');q.outputModule(1).file=new File(base.fsName+'/Hafez-FX-intro-v2.mp4');
  app.project.save(dest);app.project.renderQueue.render();log('RENDER_DONE '+(q.status===RQItemStatus.DONE));
 }catch(e){log('ERROR line='+e.line+' '+e.toString());}finally{app.endSuppressDialogs(false);}
})();
