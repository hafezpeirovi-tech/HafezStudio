/* Inspect actual visible text evaluation, in a separate Studio-owned AEP.+ * This is diagnostic: canonical templates and the owner's AEP are unchanged. */
(function () {
    var root = new File($.fileName).parent.parent.parent;
    var dir = new Folder(root.fsName + "/proof/ae-elements-audit/subscribe-runtime");
    if (!dir.exists) dir.create();
    var log = new File(dir.fsName + "/runtime.json");
    log.encoding = "UTF-8";
    var report = {phase:"start", rows:[], changed:[], errors:[]};
    // Reuse the ES3 serializer already shipped with the Adobe bridge. AE may
    // start without a native JSON object before any panels have loaded.
    $.evalFile(new File(root.fsName + "/premiere-cep-plugin/jsx/hafez.jsx"));
    function write() { log.open("w"); log.write($._hafez.stringify(report)); log.close(); }
    function comp(name) {
        for (var i=1; i<=app.project.numItems; i++) {
            var c=app.project.item(i);
            if (c instanceof CompItem && c.name===name) return c;
        }
        return null;
    }
    function walk(c, visited, path) {
        if (visited[c.id]) return;
        visited[c.id]=true;
        for (var i=1;i<=c.numLayers;i++) {
            var l=c.layer(i);
            if (l instanceof TextLayer) {
                var p=l.property("ADBE Text Properties").property("ADBE Text Document");
                var d=p.valueAtTime(3,false);
                var r=l.sourceRectAtTime(3,false);
                report.rows.push({path:path+"/"+l.name, enabled:l.enabled,
                    font:d.font, size:d.fontSize, text:d.text, expression:p.expression,
                    expressionError:p.expressionError, expressionEnabled:p.expressionEnabled,
                    bounds:{left:r.left,top:r.top,width:r.width,height:r.height},
                    inPoint:l.inPoint,outPoint:l.outPoint});
            }
            try { if (l.source instanceof CompItem) walk(l.source,visited,path+"/"+l.name); } catch (_) {}
        }
    }
    write();
    try {
        app.beginSuppressDialogs();
        // Do not discard an existing user's unsaved Adobe session.
        if (app.project && app.project.dirty) throw new Error("Save the open AE project before running this probe");
        var workFile=new File(root.fsName + "/motion-pack/source/Hafez Publication Pass 20260905.aep");
        if (!app.project.file || app.project.file.fsName !== workFile.fsName) {
            app.open(new File(root.fsName + "/motion-pack/source/Hermes Studio Elements - Hafez Curated.aep"));
            app.project.save(workFile);
        }
        var target=comp("Hafez Hermes Subscribe");
        if (!target) throw new Error("Subscribe source missing");
        report.comp={name:target.name,width:target.width,height:target.height,duration:target.duration};
        report.layers=[];
        for (var li=1;li<=target.numLayers;li++) report.layers.push(target.layer(li).name);
        walk(target,{},target.name); report.phase="before-mutation"; write();
        var updates={ChannelName:"Hafez-fx",ChannelSubtitle:"حافظ فیوچرز",CTAText:"سابسکرایب کن"};
        for (var key in updates) {
            var l=target.layer("HAFEZ EDIT · "+key);
            if (!l) { report.errors.push("Missing controller "+key); continue; }
            var p=l.property("ADBE Text Properties").property("ADBE Text Document");
            var d=p.value;
            d.text=updates[key];
            d.font="AbarHighFaNum-Black";
            p.setValue(d);
            report.changed.push(key);
        }
        var controls=target.layer("HAFEZ · CONTROLS").property("ADBE Effect Parade");
        controls.property("Layout Position").property(1).setValue([target.width/2,target.height/2]);
        controls.property("Layout Scale").property(1).setValue(100);
        controls.property("Show Background").property(1).setValue(0);
        report.rows=[]; walk(target,{},target.name);
        report.phase="evaluated"; write();
        target.saveFrameToPng(3,new File(dir.fsName+"/subscribe-runtime.png"));
        report.phase="rendered"; write();
    } catch (e) { report.errors.push(String(e)); report.phase="failed"; write(); }
    app.endSuppressDialogs(false);
})();
