(function(){
 var base=new File($.fileName).parent;
 var expected=new File(base.fsName+'/Hafez-Editorial-Intro-v1.aep');
 var report=new File(base.fsName+'/pause.log');report.encoding='UTF-8';
 function log(s){report.open('a');report.writeln(new Date().toUTCString()+' '+s);report.close();}
 if(!app.project.file || app.project.file.fsName!==expected.fsName){log('NO_ACTION: unrelated or no open project');return;}
 try{
  if(app.project.renderQueue.rendering){app.project.renderQueue.stopRendering();log('OUR_RENDER_STOPPED');}
  app.project.save(expected);log('OUR_MODULE_SAVED');
  app.project.close(CloseOptions.DO_NOT_SAVE_CHANGES);log('OUR_MODULE_CLOSED');
 }catch(e){log('ERROR '+e.toString());}
})();
