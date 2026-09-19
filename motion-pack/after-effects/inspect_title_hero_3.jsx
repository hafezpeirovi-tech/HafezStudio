(function () {
    var outputRoot = new Folder("C:/Users/1SKY.IR/.n8n/products/HafezStudio/proof/ae-elements-audit/title-hero-3");
    if (!outputRoot.exists) outputRoot.create();

    function writeText(path, value) {
        var file = new File(path);
        file.encoding = "UTF-8";
        if (!file.open("w")) throw new Error("Cannot open " + path);
        file.write(value);
        file.close();
    }

    function findComp(name) {
        for (var i = 1; i <= app.project.numItems; i++) {
            var item = app.project.item(i);
            if (item instanceof CompItem && item.name === name) return item;
        }
        return null;
    }

    function valueAt(prop, time) {
        try { return prop.valueAtTime(time, false); } catch (_) { return null; }
    }

    function textAt(layer, time) {
        try {
            var prop = layer.property("ADBE Text Properties").property("ADBE Text Document");
            var doc = prop.valueAtTime(time, false);
            return {
                text: doc.text,
                font: doc.font,
                fontSize: doc.fontSize,
                leading: doc.leading,
                tracking: doc.tracking,
                fillColor: doc.fillColor,
                expression: prop.expression || ""
            };
        } catch (_) { return null; }
    }

    function layerInfo(layer, comp) {
        var transform = layer.property("ADBE Transform Group");
        var opacity = transform ? transform.property("ADBE Opacity") : null;
        var position = transform ? transform.property("ADBE Position") : null;
        var scale = transform ? transform.property("ADBE Scale") : null;
        var sampleTimes = [0, 0.5, 1, 2, 5, 10, 15, 20, 25, Math.max(0, comp.duration - comp.frameDuration)];
        var samples = [];
        for (var s = 0; s < sampleTimes.length; s++) {
            var t = Math.min(Math.max(0, sampleTimes[s]), Math.max(0, comp.duration - comp.frameDuration));
            samples.push({
                time: t,
                active: layer.activeAtTime(t),
                opacity: opacity ? valueAt(opacity, t) : null,
                position: position ? valueAt(position, t) : null,
                scale: scale ? valueAt(scale, t) : null,
                text: textAt(layer, t)
            });
        }
        var sourceName = null;
        var sourceType = null;
        try {
            sourceName = layer.source ? layer.source.name : null;
            sourceType = layer.source instanceof CompItem ? "comp" : (layer.source ? "footage" : null);
        } catch (_) {}
        return {
            index: layer.index,
            name: layer.name,
            enabled: layer.enabled,
            shy: layer.shy,
            guideLayer: layer.guideLayer,
            adjustmentLayer: layer.adjustmentLayer,
            hasVideo: layer.hasVideo,
            inPoint: layer.inPoint,
            outPoint: layer.outPoint,
            startTime: layer.startTime,
            stretch: layer.stretch,
            sourceName: sourceName,
            sourceType: sourceType,
            samples: samples
        };
    }

    var names = ["Hafez Hermes Title Hero 3", "All element"];
    var report = { project: app.project.file ? app.project.file.fsName : null, comps: [] };
    for (var n = 0; n < names.length; n++) {
        var comp = findComp(names[n]);
        if (!comp) continue;
        var compInfo = {
            name: comp.name,
            width: comp.width,
            height: comp.height,
            duration: comp.duration,
            frameRate: comp.frameRate,
            displayStartTime: comp.displayStartTime,
            layers: []
        };
        for (var i = 1; i <= comp.numLayers; i++) compInfo.layers.push(layerInfo(comp.layer(i), comp));
        report.comps.push(compInfo);
    }
    writeText(outputRoot.fsName + "/inventory.json", JSON.stringify(report, null, 2));

    var target = findComp("Hafez Hermes Title Hero 3");
    if (target) {
        var times = [0, 0.5, 1, 2, 5, 10, 15, 20, 25, Math.max(0, target.duration - target.frameDuration)];
        for (var t = 0; t < times.length; t++) {
            var time = times[t];
            var label = String(time).replace(".", "p");
            try { target.saveFrameToPng(time, new File(outputRoot.fsName + "/frame-" + label + ".png")); } catch (_) {}
        }
    }
    writeText(outputRoot.fsName + "/done.txt", "DONE\n");
})();
