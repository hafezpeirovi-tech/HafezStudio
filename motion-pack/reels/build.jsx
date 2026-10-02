/* Original reusable vertical graphics. Run once in an empty After Effects session. */
(function () {
    var base=new File($.fileName).parent,dist=new Folder(base.fsName+'/dist/v2'),src=new Folder(base.fsName+'/source');
    var receipt=new File(base.fsName+'/build-v2-result.json'),projectFile=new File(src.fsName+'/Hafez-Reels-v2.aep');
    function write(s){receipt.encoding='UTF-8';receipt.open('w');receipt.write(s);receipt.close();}
    function esc(s){return String(s).replace(/\\/g,'\\\\').replace(/"/g,'\\"').replace(/[\r\n]/g,' ');}
    if(app.project && (app.project.file || app.project.numItems>0)){write('{"ok":false,"error":"Close the existing AE project before building"}');return;}
    if(projectFile.exists){write('{"ok":false,"error":"Versioned source already exists; build is not overwritten"}');return;}
    dist.create();src.create();
    app.beginSuppressDialogs();
    try {
        app.project.bitsPerChannel=16;
        function col(h){return [parseInt(h.substr(0,2),16)/255,parseInt(h.substr(2,2),16)/255,parseInt(h.substr(4,2),16)/255];}
        function rect(c,name,x,y,w,h,r,color){
            var l=c.layers.addShape();l.name=name;l.transform.position.setValue([x,y]);
            var g=l.property('ADBE Root Vectors Group').addProperty('ADBE Vector Group');
            var shape=g.property('ADBE Vectors Group').addProperty('ADBE Vector Shape - Rect');
            shape.property('ADBE Vector Rect Size').setValue([w,h]);shape.property('ADBE Vector Rect Roundness').setValue(r);
            var f=g.property('ADBE Vectors Group').addProperty('ADBE Vector Graphic - Fill');f.property('ADBE Vector Fill Color').setValue(col(color));
            return l;
        }
        function enter(l,delay,shift){
            var t=l.transform,p=t.position,v=p.value;
            p.setValuesAtTimes([delay,delay+.38],[[v[0],v[1]+shift],v]);
            t.opacity.setValuesAtTimes([delay,delay+.22],[0,100]);
            for(var i=1;i<=p.numKeys;i++)p.setTemporalEaseAtKey(i,[new KeyframeEase(0,75)],[new KeyframeEase(0,75)]);
            l.motionBlur=true;
        }
        function headline(c,y,color){
            var l=c.layers.addBoxText([830,300]);l.name='Headline';
            var p=l.property('Source Text'),d=p.value;
            d.text='گاهی فقط یک مکث لازم است';d.font='AbarHighFaNum-ExtraBold';d.fontSize=64;d.leading=90;d.autoLeading=false;
            d.fillColor=col(color);
            try{d.composerEngine=ComposerEngine.UNIVERSAL_TYPE_ENGINE;d.direction=ParagraphDirection.DIRECTION_RIGHT_TO_LEFT;d.digitSet=DigitSet.FARSI_DIGITS;}catch(_){}
            d.justification=ParagraphJustification.CENTER_JUSTIFY;
            p.setValue(d);l.transform.anchorPoint.expression='var r=sourceRectAtTime(time,false);[r.left+r.width/2,r.top]';l.transform.position.setValue([540,y]);
            if(!p.addToMotionGraphicsTemplateAs(c,'Headline'))throw Error('Cannot expose Headline');
            enter(l,.08,32);return l;
        }
        var names=['editorial','pause-card'];
        for(var n=0;n<names.length;n++){
            var c=app.project.items.addComp(names[n],1080,1920,1,8,30);c.motionGraphicsTemplateName=names[n];c.motionBlur=true;c.shutterAngle=120;
            if(n===0){
                var panel=rect(c,'Ink panel',540,1390,980,450,40,'18221C');enter(panel,0,50);
                var bar=rect(c,'Signal yellow',934,1150,90,12,6,'FFE078');enter(bar,.05,10);
                headline(c,1250,'FFF3D0');
            }else{
                var shadow=rect(c,'Card depth',548,1410,930,460,50,'681C29');enter(shadow,0,65);
                var card=rect(c,'Cream card',530,1365,930,460,50,'FFF0D7');card.transform.rotation.setValuesAtTimes([0,.45],[-7,-2]);enter(card,0,65);
                var rod1=rect(c,'Pause 1',850,1125,38,95,14,'ED354A');var rod2=rect(c,'Pause 2',910,1125,38,95,14,'ED354A');enter(rod1,.08,28);enter(rod2,.15,28);
                headline(c,1250,'531B2B');
            }
            c.time=1;
        }
        app.project.save(projectFile);
        for(var j=1;j<=app.project.numItems;j++){
            var item=app.project.item(j);
            if(!item.layer || !item.exportAsMotionGraphicsTemplate)continue;
            var templateName=item.motionGraphicsTemplateName;
            app.project.save(projectFile);
            item.exportAsMotionGraphicsTemplate(false,dist.fsName);
            var generated=new File(dist.fsName+'/'+templateName+'.mogrt');
            var started=new Date().getTime();
            while((!generated.exists || generated.length===0) && new Date().getTime()-started<120000){$.sleep(500);generated=new File(generated.fsName);}
            if(!generated.exists||generated.length===0)throw Error('Template file missing: '+templateName);
        }
        write('{"ok":true,"templates":["editorial","pause-card"],"width":1080,"height":1920,"duration":8}');
    }catch(e){write('{"ok":false,"error":"'+esc(e.message)+'","line":'+(e.line||0)+'}');}
    finally{if(app.project.file && app.project.file.fsName===projectFile.fsName)app.project.close(CloseOptions.DO_NOT_SAVE_CHANGES);app.endSuppressDialogs(false);}
})();
