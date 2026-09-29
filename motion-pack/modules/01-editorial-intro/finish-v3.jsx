(function(){
 var base=new File($.fileName).parent,src=new File(base.fsName+'/Hafez-FX-Editorial-Intro-v2.aep'),dest=new File(base.fsName+'/Hafez-FX-Editorial-Intro-v3.aep');
 var out=new File(base.fsName+'/finish-v3.log');out.encoding='UTF-8';function log(s){out.open('a');out.writeln(s);out.close();}
 function find(){for(var i=1;i<=app.project.numItems;i++)if(app.project.item(i) instanceof CompItem && app.project.item(i).name==='Hafez Editorial Intro v1')return app.project.item(i);throw Error('Missing comp');}
 if(!app.project.file || app.project.file.fsName!==src.fsName || dest.exists){log('BLOCKED');return;}
 app.beginSuppressDialogs();try{
  var c=find();
  var names=['Soft sage ambient light','Soft teal ambient light'];
  for(var i=0;i<names.length;i++){
   var l=c.layer(names[i]);l.property('ADBE Effect Parade').property(1).enabled=false;
   var pre=c.layers.precompose([l.index],names[i]+' full-frame',true);
   var wrapped=c.layer(pre.name);wrapped.property('ADBE Effect Parade').addProperty('ADBE Gaussian Blur 2').property(1).setValue(260);
  }
  var l=c.layer('Title Line 2');var a=l.property('ADBE Text Properties').property('ADBE Text Animators').addProperty('ADBE Text Animator');a.name='Editable base text color';
  a.property('ADBE Text Animator Properties').addProperty('ADBE Text Fill Color').expression='thisComp.layer("HAFEZ CONTROLS").effect("Text Color")(1)';
  a.moveTo(1);
  c.motionGraphicsTemplateName='Hafez-FX Editorial Intro v3';app.project.save(dest);log('SOURCE_SAVED');
  if(!c.exportAsMotionGraphicsTemplate(false,base.fsName))throw Error('MOGRT export failed');log('MOGRT_EXPORTED');c=find();
  var q=app.project.renderQueue.items.add(c);q.timeSpanStart=0;q.timeSpanDuration=6;
  q.outputModule(1).applyTemplate('H.264 - Match Render Settings - 15 Mbps');q.outputModule(1).file=new File(base.fsName+'/Hafez-FX-intro-v3.mp4');
  app.project.save(dest);app.project.renderQueue.render();log('RENDER_DONE '+(q.status===RQItemStatus.DONE));
 }catch(e){log('ERROR line='+e.line+' '+e.toString());}finally{app.endSuppressDialogs(false);}
})();
