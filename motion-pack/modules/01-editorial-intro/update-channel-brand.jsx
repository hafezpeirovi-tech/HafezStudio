(function(){
 var base=new File($.fileName).parent;
 var expected=new File(base.fsName+'/Hafez-Editorial-Intro-v1.aep');
 var report=new File(base.fsName+'/channel-brand.log');report.encoding='UTF-8';
 function log(s){report.open('a');report.writeln(s);report.close();}
 if(!app.project.file || app.project.file.fsName!==expected.fsName){log('BLOCKED: unrelated project');return;}
 function comp(){for(var i=1;i<=app.project.numItems;i++)if(app.project.item(i) instanceof CompItem && app.project.item(i).name==='Hafez Editorial Intro v1')return app.project.item(i);throw Error('Missing comp');}
 app.beginSuppressDialogs();
 try{
  var c=comp();var p=c.layer('Brand').property('Source Text');var d=p.value;d.text='HAFEZ-FX';p.setValue(d);
  app.project.save(expected);log('BRAND '+p.value.text);
  if(!c.exportAsMotionGraphicsTemplate(true,base.fsName))throw Error('Export failed');
  log('MOGRT_EXPORTED');c=comp();
  for(var j=1;j<=app.project.renderQueue.numItems;j++)app.project.renderQueue.item(j).render=false;
  var q=app.project.renderQueue.items.add(c);q.timeSpanStart=0;q.timeSpanDuration=6;
  q.outputModule(1).applyTemplate('H.264 - Match Render Settings - 15 Mbps');
  q.outputModule(1).file=new File(base.fsName+'/Hafez-FX-intro-preview.mp4');
  app.project.save(expected);app.project.renderQueue.render();
  log('RENDER_DONE '+(q.status===RQItemStatus.DONE));
 }catch(e){log('ERROR '+e.toString());}finally{app.endSuppressDialogs(false);}
})();
