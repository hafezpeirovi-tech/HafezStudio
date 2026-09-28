/* Request is serialized by compile_editorial_intro.py; never execute text from media. */
(function (job) {
    var folder = new Folder(job.output), receipt = new File(folder.fsName + '/ae-receipt.json');
    var src = new File(job.source_aep), previous = app.project.file;
    function quote(s) { return '"'+String(s).replace(/\\/g,'\\\\').replace(/"/g,'\\"').replace(/\r/g,'\\r').replace(/\n/g,'\\n').replace(/\t/g,'\\t')+'"'; }
    function result(ok, detail) {
        receipt.encoding = 'UTF-8'; receipt.open('w');
        receipt.write('{"ok":'+(ok?'true':'false')+',"job_id":'+quote(job.job_id)+',"portrait":'+quote(new File(job.portrait).fsName.replace(/\\/g,'/'))+',"detail":'+quote(detail)+'}');
        receipt.close();
    }
    // Never save/close a different project or discard unsaved user changes.
    if (app.project.dirty || (previous && previous.fsName !== src.fsName && (!job.previous_project || previous.fsName !== new File(job.previous_project).fsName)) || (!previous && app.project.numItems)) {
        result(false, 'Open the saved Editorial source project without unsaved changes first.'); return;
    }
    if (new File(job.project).exists || new File(folder.fsName+'/'+job.job_id+'.mogrt').exists) {
        result(false, 'Output already exists; do not repeat a native mutation.'); return;
    }
    app.beginSuppressDialogs();
    try {
        app.open(src);
        var comp = null;
        for (var i=1;i<=app.project.numItems;i++) {
            var item=app.project.item(i);
            if (item instanceof CompItem && item.name==='Hafez Editorial Intro v1') comp=item;
        }
        if (!comp) throw Error('Missing verified master comp');
        var portrait=comp.layer('Replace Portrait Video');
        portrait.source.replace(new File(job.portrait));
        portrait.startTime=0; portrait.inPoint=0; portrait.audioEnabled=false;
        comp.frameRate=job.fps[0]/job.fps[1]; comp.duration=job.duration;
        for (var l=1;l<=comp.numLayers;l++) if(comp.layer(l).outPoint>=5.99) comp.layer(l).outPoint=job.duration;
        var values={'Brand':'HAFEZ-FX','Title Line 1':job.title_lines[0],'Title Line 2':job.title_lines[1],
                    'Subtitle':'','Topic Label':'','English Eyebrow':''};
        for (var name in values) {
            var prop=comp.layer(name).property('ADBE Text Properties').property('ADBE Text Document');
            var doc=prop.value; doc.text=values[name]; prop.setValue(doc);
        }
        // An empty optional label must not leave a decorative empty pill.
        // An editor can add text later and the same eased panel reappears.
        comp.layer('Topic panel').transform.opacity.expression='thisComp.layer("Topic Label").text.sourceText.toString().replace(/\\s/g,"").length ? value : 0';
        comp.motionGraphicsTemplateName=job.job_id;
        app.project.save(new File(job.project));
        if (!comp.exportAsMotionGraphicsTemplate(false,folder.fsName)) throw Error('MOGRT export failed');
        // AE export invalidates some scripting references; resolve the comp again.
        comp=null;
        for(var j=1;j<=app.project.numItems;j++) {
            var exportedItem=app.project.item(j);
            if(exportedItem instanceof CompItem && exportedItem.name==='Hafez Editorial Intro v1') comp=exportedItem;
        }
        if(!comp) throw Error('Master comp unavailable after export');
        if(job.preview) {
            for(var q=1;q<=app.project.renderQueue.numItems;q++) {
                var old=app.project.renderQueue.item(q);
                if(old.status===RQItemStatus.QUEUED) old.render=false;
            }
            var render=app.project.renderQueue.items.add(comp);
            render.timeSpanStart=0; render.timeSpanDuration=job.duration;
            render.outputModule(1).applyTemplate('H.264 - Match Render Settings - 15 Mbps');
            render.outputModule(1).file=new File(folder.fsName+'/Editorial-Preview.mp4');
            app.project.save(new File(job.project)); app.project.renderQueue.render();
            if(render.status!==RQItemStatus.DONE) throw Error('Preview did not finish');
        }
        app.project.save(new File(job.project));
        result(true,'Exported current-media native MOGRT; Premiere verification still required.');
    } catch(error) { result(false,String(error)+' line '+error.line); }
    finally { app.endSuppressDialogs(false); }
})(HAFEZ_EDITORIAL_JOB);
