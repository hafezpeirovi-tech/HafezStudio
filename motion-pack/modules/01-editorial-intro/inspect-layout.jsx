(function(){
 var base=new File($.fileName).parent;var file=new File(base.fsName+'/Hafez-Editorial-Intro-v1.aep');
 var out=new File(base.fsName+'/layout-diagnostics.txt');out.encoding='UTF-8';out.open('w');
 function log(s){out.writeln(s);}
 try{
  if(app.project.file && app.project.file.fsName!==file.fsName)throw Error('Unrelated project open');
  if(!app.project.file && app.project.numItems>0)throw Error('Unsaved unrelated project');
  if(!app.project.file)app.open(file);
  var c;for(var i=1;i<=app.project.numItems;i++)if(app.project.item(i).name==='Hafez Editorial Intro v1')c=app.project.item(i);
  for(var j=1;j<=c.numLayers;j++){
   var l=c.layer(j);if(!(l instanceof TextLayer))continue;
   var p=l.property('Source Text'),d=p.value,r=l.sourceRectAtTime(2,false);
   log('LAYER '+l.name);
   try{log('FONT '+d.font);}catch(e){log('FONT_ERROR '+String(e));}
   try{log('BOUNDS '+r.left+' '+r.top+' '+r.width+' '+r.height);}catch(e){log('BOUNDS_ERROR '+String(e));}
   try{log('fontObject substitute='+d.fontObject.isSubstitute+' ps='+d.fontObject.postScriptName);}catch(e){log(String(e));}
   log('sourceExpr='+p.expression+' error='+p.expressionError);
   var fx=l.property('ADBE Effect Parade');for(var k=1;k<=fx.numProperties;k++){var e=fx.property(k);for(var m=1;m<=e.numProperties;m++){var v=e.property(m);if(v.canSetExpression)log(e.name+'/'+v.name+' expr='+v.expression+' err='+v.expressionError);}}
  }
  log('DONE');
 }catch(e){log('ERROR line='+e.line+' '+e.toString());}finally{out.close();}
})();
