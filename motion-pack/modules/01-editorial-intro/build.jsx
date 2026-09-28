/* Independent Module 01. Originals and existing Adobe projects are never saved over. */
(function () {
    var base = new Folder(new File($.fileName).parent.fsName);
    var root = base.parent.parent.parent;
    var sourceProject = new File(base.fsName + '/Hafez-Editorial-Intro-v1.aep');
    var logFile = new File(base.fsName + '/build.log');
    logFile.encoding = 'UTF-8';
    function log(s) { logFile.open('a'); logFile.writeln(new Date().toUTCString()+' | '+s); logFile.close(); }
    function col(h) { return [parseInt(h.substr(0,2),16)/255,parseInt(h.substr(2,2),16)/255,parseInt(h.substr(4,2),16)/255]; }
    function find(name) { for(var i=1;i<=app.project.numItems;i++) if(app.project.item(i) instanceof CompItem && app.project.item(i).name===name) return app.project.item(i); throw Error('Missing comp '+name); }
    if(app.project && (app.project.file || app.project.numItems>0)) {
        if(!app.project.file || app.project.file.fsName!==sourceProject.fsName) {log('BLOCKED: unrelated open project');return;}
        log('BLOCKED: source already open; close this module before rebuilding');return;
    }
    if(sourceProject.exists) {log('BLOCKED: versioned output already exists');return;}
    app.beginSuppressDialogs();
    try {
        log('START');
        app.open(new File(root.fsName+'/proof/editorial-glass-styleframes-20260928/background/mogrt.aep'));
        // This is an extracted COPY of the supplied Qss template, never its original.
        app.project.bitsPerChannel=16;
        try {app.project.linearBlending=false;} catch (_) {}
        var bg=find('SaaS Gradient Background 03');
        var settings=bg.layer('Settings').property('ADBE Effect Parade');
        var colors=['0A1110','335944','192E2E','0C1712','101E19'];
        for(var ci=1;ci<=5;ci++)settings.property('BG Color 0'+ci).property(1).setValue(col(colors[ci-1]));
        settings.property('Noise').property(1).setValue(0);
        settings.property('Dust Effect_01').property(1).setValue(0);
        settings.property('Papper Texture_01').property(1).setValue(0);
        var c=app.project.items.addComp('Hafez Editorial Intro v1',1920,1080,1,6,30);
        c.motionGraphicsTemplateName=c.name;
        c.motionBlur=true;c.shutterAngle=120;
        var bgLayer=c.layers.add(bg);bgLayer.name='Qss supplied gradient';bgLayer.transform.scale.setValue([50,50]);
        var control=c.layers.addNull();control.name='HAFEZ CONTROLS';control.enabled=false;
        function expose(p,label) {if(!p.addToMotionGraphicsTemplateAs(c,label))throw Error('Cannot expose '+label);}
        function ctrl(name,type,value) {var e=control.property('ADBE Effect Parade').addProperty(type);e.name=name;e.property(1).setValue(value);expose(e.property(1),name);return e.property(1);}
        ctrl('Text Color','ADBE Color Control',col('F3F7F4'));
        ctrl('Accent Color','ADBE Color Control',col('80E9B0'));
        ctrl('Secondary Text Color','ADBE Color Control',col('B8C9BF'));
        ctrl('Panel Tint','ADBE Color Control',col('14241B'));
        ctrl('Panel Opacity','ADBE Slider Control',72);
        ctrl('Title Line Spacing','ADBE Slider Control',132);
        ctrl('Title Scale','ADBE Slider Control',100);
        ctrl('Portrait Zoom','ADBE Slider Control',100);
        for(var bi=1;bi<=5;bi++)expose(settings.property('BG Color 0'+bi).property(1),'Background Color '+bi);
        function colorExpr(name){return 'thisComp.layer("HAFEZ CONTROLS").effect("'+name+'")(1)';}
        function animate(l,delay,shift) {
            var o=l.transform.opacity;o.setValuesAtTimes([delay,delay+.42,5.58,6],[0,100,100,0]);
            for(var k=1;k<=o.numKeys;k++)o.setTemporalEaseAtKey(k,[new KeyframeEase(0,78)],[new KeyframeEase(0,78)]);
            if(shift){var p=l.transform.position;var v=p.value;p.setValuesAtTimes([delay,delay+.55,5.5,6],[[v[0],v[1]+shift],v,v,[v[0],v[1]-14]]);for(var j=1;j<=p.numKeys;j++)p.setTemporalEaseAtKey(j,[new KeyframeEase(0,78)],[new KeyframeEase(0,78)]);}
            l.motionBlur=true;
        }
        function rect(name,x,y,w,h,r,color,opacity){
            var l=c.layers.addShape();l.name=name;l.transform.position.setValue([x+w/2,y+h/2]);
            var g=l.property('ADBE Root Vectors Group').addProperty('ADBE Vector Group');
            var shape=g.property('ADBE Vectors Group').addProperty('ADBE Vector Shape - Rect');shape.property('ADBE Vector Rect Size').setValue([w,h]);shape.property('ADBE Vector Rect Roundness').setValue(r);
            var fill=g.property('ADBE Vectors Group').addProperty('ADBE Vector Graphic - Fill');fill.property('ADBE Vector Fill Color').setValue(col(color));fill.property('ADBE Vector Fill Opacity').setValue(opacity);
            return l;
        }
        function text(name,value,size,x,y,color,weight,latin){
            var l=c.layers.addText(value);l.name=name;var p=l.property('Source Text'),d=p.value;
            d.font=latin?'ArialMT':('AbarHighFaNum-'+weight);d.fontSize=size;d.fillColor=col(color);d.applyStroke=false;
            d.justification=ParagraphJustification.RIGHT_JUSTIFY;
            try {d.composerEngine=ComposerEngine.UNIVERSAL_TYPE_ENGINE;d.direction=latin?ParagraphDirection.DIRECTION_LEFT_TO_RIGHT:ParagraphDirection.DIRECTION_RIGHT_TO_LEFT;d.digitSet=DigitSet.FARSI_DIGITS;}catch(_){}
            d.tracking=latin?110:0;p.setValue(d);l.transform.position.setValue([x,y]);
            var fx=l.property('ADBE Effect Parade').addProperty('ADBE Fill');fx.property('ADBE Fill-0002').expression=colorExpr(color==='80E9B0'?'Accent Color':color==='F3F7F4'?'Text Color':'Secondary Text Color');
            expose(p,name);return l;
        }
        // Replaceable live portrait, no rasterized title or UI screenshot.
        var footage=app.project.importFile(new ImportOptions(new File(base.fsName+'/portrait-demo.mp4')));
        var portrait=c.layers.add(footage);portrait.name='Replace Portrait Video';portrait.audioEnabled=false;
        portrait.transform.scale.expression='var z=thisComp.layer("HAFEZ CONTROLS").effect("Portrait Zoom")(1);[68.52,68.52]*z/100';
        portrait.transform.position.setValue([1482.5,525]);
        var matte=rect('Portrait rounded matte',1135,155,695,740,30,'FFFFFF',100);
        portrait.setTrackMatte(matte,TrackMatteType.ALPHA);
        if(!portrait.addToMotionGraphicsTemplateAs(c,'Portrait Video / Replace Media'))throw Error('Media replacement unavailable');
        animate(portrait,0,0);
        // Subtle frame, keeping the photo/video independent of editable typography.
        var frame=rect('Portrait edge',1135,155,695,740,30,'FFFFFF',0);
        var fg=frame.property('ADBE Root Vectors Group').property(1).property('ADBE Vectors Group');
        var stroke=fg.addProperty('ADBE Vector Graphic - Stroke');stroke.property('ADBE Vector Stroke Color').setValue(col('C9E7D0'));stroke.property('ADBE Vector Stroke Opacity').setValue(24);stroke.property('ADBE Vector Stroke Width').setValue(1);
        animate(frame,0,0);
        var brand=text('Brand','HAFEZ / STUDIO',20,300,91,'B8C9BF','Regular',true);animate(brand,.02,0);
        var kicker=text('English Eyebrow','THE BETTER QUESTION',23,990,307,'B8C9BF','Regular',true);animate(kicker,.08,12);
        var t1=text('Title Line 1','فقط استراتژی',102,990,438,'F3F7F4','ExtraBold',false);animate(t1,.12,24);
        var t2=text('Title Line 2','کافی نیست.',102,990,570,'80E9B0','ExtraBold',false);animate(t2,.20,24);
        t1.transform.scale.expression='var s=thisComp.layer("HAFEZ CONTROLS").effect("Title Scale")(1);[s,s]';
        t2.transform.scale.expression=t1.transform.scale.expression;
        t2.transform.position.expression='value+[0,thisComp.layer("HAFEZ CONTROLS").effect("Title Line Spacing")(1)-132]';
        var rule=rect('Divider',110,625,880,1,0,'D7EFE2',18);animate(rule,.24,0);
        var sub=text('Subtitle','داده، احتمال و نقش احساسات',32,990,695,'B8C9BF','Regular',false);animate(sub,.28,16);
        var pill=rect('Topic panel',740,755,250,64,32,'14241B',72);
        var panelFill=pill.property('ADBE Root Vectors Group').property(1).property('ADBE Vectors Group').property('ADBE Vector Graphic - Fill');
        panelFill.property('ADBE Vector Fill Color').expression=colorExpr('Panel Tint');
        panelFill.property('ADBE Vector Fill Opacity').expression='thisComp.layer("HAFEZ CONTROLS").effect("Panel Opacity")(1)';animate(pill,.32,0);
        var topic=text('Topic Label','موضوع این قسمت',24,960,798,'B8C9BF','Regular',false);animate(topic,.34,0);
        // A protected intro/outro permits duration changes without stretching the reveal.
        var mi=new MarkerValue('IN');mi.duration=.75;mi.protectedRegion=true;c.markerProperty.setValueAtTime(0,mi);
        var mo=new MarkerValue('OUT');mo.duration=.5;mo.protectedRegion=true;c.markerProperty.setValueAtTime(5.5,mo);
        c.time=2;c.openInViewer();
        app.project.save(sourceProject);
        log('SOURCE_SAVED controls='+c.motionGraphicsTemplateControllerCount);
        c.saveFrameToPng(2,new File(base.fsName+'/native-frame.png'));
        log('STILL_REQUESTED exists='+new File(base.fsName+'/native-frame.png').exists);
        var ok=c.exportAsMotionGraphicsTemplate(false,base.fsName);
        log('MOGRT_EXPORT '+ok);
        if(!ok)throw Error('MOGRT export returned false');
        c=find('Hafez Editorial Intro v1');
        var q=app.project.renderQueue.items.add(c);q.timeSpanStart=0;q.timeSpanDuration=6;
        q.outputModule(1).file=new File(base.fsName+'/native-preview.avi');
        app.project.save(sourceProject);
        log('READY_FOR_RENDER');
    } catch(e) {log('ERROR line='+e.line+' '+e.toString());}
    finally {app.endSuppressDialogs(false);}
})();
