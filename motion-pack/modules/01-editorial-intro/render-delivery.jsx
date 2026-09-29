(function(){
 var base=new File($.fileName).parent,src=new File(base.fsName+'/Hafez-FX-Editorial-Intro-v3.aep');
 var out=new File(base.fsName+'/delivery-render.log');out.encoding='UTF-8';
 function log(s){out.open('a');out.writeln(s);out.close();}
 if(!app.project.file || app.project.file.fsName!==src.fsName || new File(base.fsName+'/Hafez-FX-Intro-Preview.mp4').exists){log('BLOCKED: unexpected source or existing output');return;}
 app.beginSuppressDialogs();try{
  var c=null;for(var i=1;i<=app.project.numItems;i++)if(app.project.item(i) instanceof CompItem && app.project.item(i).name==='Hafez Editorial Intro v1')c=app.project.item(i);
  if(!c)throw Error('Missing comp');
  for(var j=1;j<=app.project.renderQueue.numItems;j++){var old=app.project.renderQueue.item(j);if(old.status===RQItemStatus.QUEUED)old.render=false;}
  var q=app.project.renderQueue.items.add(c);q.timeSpanStart=0;q.timeSpanDuration=6;
  q.outputModule(1).applyTemplate('H.264 - Match Render Settings - 15 Mbps');
  q.outputModule(1).file=new File(base.fsName+'/Hafez-FX-Intro-Preview.mp4');
  app.project.renderQueue.render();log('RENDER_DONE '+(q.status===RQItemStatus.DONE));
  app.project.save(src);
 }catch(e){log('ERROR '+e.toString());}finally{app.endSuppressDialogs(false);}
})();
