(function(){
 var base=new File($.fileName).parent,expected=new File(base.fsName+'/Hafez-FX-Editorial-Intro-v3.aep');
 var out=new File(base.fsName+'/background-bindings.log');out.encoding='UTF-8';out.open('w');
 if(!app.project.file || app.project.file.fsName!==expected.fsName){out.writeln('BLOCKED');out.close();return;}
 app.beginSuppressDialogs();try{
  var names=['Soft sage ambient light full-frame','Soft teal ambient light full-frame'];var master;
  for(var i=1;i<=app.project.numItems;i++){
   var c=app.project.item(i);if(!(c instanceof CompItem))continue;
   if(c.name==='Hafez Editorial Intro v1')master=c;
   for(var j=0;j<names.length;j++)if(c.name===names[j]){
    var fill=c.layer(1).property('ADBE Root Vectors Group').property(1).property('ADBE Vectors Group').property('ADBE Vector Graphic - Fill').property('ADBE Vector Fill Color');
    fill.expression='comp("SaaS Gradient Background 03").layer("Settings").effect("BG Color 0'+(j+2)+'")(1)';out.writeln('BOUND '+names[j]);
   }
  }
  app.project.save(expected);if(!master.exportAsMotionGraphicsTemplate(true,base.fsName))throw Error('Export failed');out.writeln('EXPORTED');
 }catch(e){out.writeln('ERROR '+e.toString());}finally{out.close();app.endSuppressDialogs(false);}
})();
