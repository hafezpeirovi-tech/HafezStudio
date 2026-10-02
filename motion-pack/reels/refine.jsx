/* Adjust only the generated Hafez Reels source; run in an isolated AE instance. */
(function(){
    var base=new File($.fileName).parent,source=new File(base.fsName+'/source/Hafez-Reels-v2.aep');
    var receipt=new File(base.fsName+'/refine-result.json');
    function result(text){receipt.encoding='UTF-8';receipt.open('w');receipt.write(text);receipt.close();}
    if(app.project && (app.project.file || app.project.numItems)){result('{"ok":false,"error":"Instance must be empty"}');return;}
    app.beginSuppressDialogs();
    try{
        app.open(source);var preview=new Folder(base.fsName+'/preview');preview.create();
        for(var i=1;i<=app.project.numItems;i++){
            var c=app.project.item(i);if(!c.layer || !c.exportAsMotionGraphicsTemplate)continue;
            var layer=c.layer('Headline');
            var textProperty=layer.property('Source Text'),doc=textProperty.value;
            try{doc.composerEngine=ComposerEngine.UNIVERSAL_TYPE_ENGINE;doc.direction=ParagraphDirection.DIRECTION_RIGHT_TO_LEFT;}catch(_){}
            doc.justification=ParagraphJustification.CENTER_JUSTIFY;textProperty.setValue(doc);
            layer.transform.anchorPoint.expression='var r=sourceRectAtTime(time,false);[r.left+r.width/2,r.top]';
            layer.transform.position.setValuesAtTimes([.08,.46],[[540,1282],[540,1250]]);
            c.time=1;
        }
        app.project.save(source);
        var exported=0;
        for(var j=1;j<=app.project.numItems;j++){
            var comp=app.project.item(j);if(!comp.layer || !comp.exportAsMotionGraphicsTemplate)continue;
            var exportFolder=new Folder(base.fsName+'/dist/v2');
            var templateName=comp.motionGraphicsTemplateName;
            app.project.save(source);
            comp.exportAsMotionGraphicsTemplate(true,exportFolder.fsName);
            var file=new File(exportFolder.fsName+'/'+templateName+'.mogrt'),started=new Date().getTime();
            // Recent AE releases return before the file is written. Keep the source open.
            while((!file.exists || file.length===0) && new Date().getTime()-started<120000){$.sleep(500);file=new File(file.fsName);}
            if(!file.exists || file.length===0)throw Error('Exported file missing after timeout');
            exported++;
        }
        if(exported!==2)throw Error('Expected two compositions; exported '+exported+'; project items '+app.project.numItems);
        result('{"ok":true,"exported":'+exported+'}');
    }catch(e){result('{"ok":false,"line":'+(e.line||0)+',"error":"'+String(e.message).replace(/\\/g,'\\\\').replace(/"/g,'\\"').replace(/[\r\n]/g,' ')+'"}');}
    finally{if(app.project.file && app.project.file.fsName===source.fsName)app.project.close(CloseOptions.DO_NOT_SAVE_CHANGES);app.endSuppressDialogs(false);}
})();
