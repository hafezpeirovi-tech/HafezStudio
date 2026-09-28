(function(){
 var base=new File($.fileName).parent;
 var out=new File(base.fsName+'/render.log');out.encoding='UTF-8';
 function log(s){out.open('a');out.writeln(s);out.close();}
 var expected=new File(base.fsName+'/Hafez-Editorial-Intro-v1.aep');
 if(!app.project.file || app.project.file.fsName!==expected.fsName){log('BLOCKED: wrong project');return;}
 try{
  var c=null;for(var i=1;i<=app.project.numItems;i++)if(app.project.item(i).name==='Hafez Editorial Intro v1')c=app.project.item(i);
  if(!c)throw Error('Missing module comp');
  for(var l=1;l<=c.numLayers;l++){var layer=c.layer(l);if(layer instanceof TextLayer)log('FONT '+layer.name+' '+layer.property('Source Text').value.font);}
  for(var rq=1;rq<=app.project.renderQueue.numItems;rq++)app.project.renderQueue.item(rq).render=false;
  var q=app.project.renderQueue.items.add(c);q.timeSpanStart=0;q.timeSpanDuration=6;
  var om=q.outputModule(1);log('TEMPLATES '+om.templates.join(' | '));
  om.applyTemplate('H.264 - Match Render Settings - 15 Mbps');om.file=new File(base.fsName+'/native-preview.mp4');
  c.time=2;app.project.save(expected);
  app.project.renderQueue.render();log('VIDEO_STATUS '+q.status);
 }catch(e){log('ERROR '+e.toString()+' line '+e.line);}
})();
