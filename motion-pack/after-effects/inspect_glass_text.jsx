(function () {
    var root = new Folder("C:/Users/1SKY.IR/.n8n/products/HafezStudio");
    var report = new File(root.fsName + "/proof/ae-elements-audit/glass-text-runtime.txt");
    report.encoding = "UTF-8";
    report.open("w");

    function out(value) { report.writeln(String(value)); }
    function arr(value) {
        try { return "[" + value.join(",") + "]"; } catch (_) { return String(value); }
    }
    function propLine(layer, property, label, time) {
        try {
            out(label + "|value=" + arr(property.valueAtTime(time, false)) +
                "|expr=" + property.expressionEnabled + "|expression=" + property.expression);
        } catch (error) { out(label + "|ERROR=" + error.toString()); }
    }
    function walk(group, prefix, time, depth) {
        if (!group || depth > 7) return;
        for (var wi = 1; wi <= group.numProperties; wi++) {
            var child = group.property(wi);
            var childPath = prefix + "/" + child.name + "{" + child.matchName + "}";
            if (child.propertyValueType !== PropertyValueType.NO_VALUE) {
                try {
                    out("ANIM_PROP|" + childPath + "|value=" + arr(child.valueAtTime(time, false)) +
                        "|expr=" + child.expressionEnabled + "|expression=" + child.expression);
                } catch (error) { out("ANIM_PROP_ERROR|" + childPath + "|" + error.toString()); }
            }
            if (child.numProperties) walk(child, childPath, time, depth + 1);
        }
    }

    var comp = null;
    for (var i = 1; i <= app.project.numItems; i++) {
        var item = app.project.item(i);
        if (item instanceof CompItem && item.name === "Hafez Hermes Glass Insight") { comp = item; break; }
    }
    if (!comp) { out("ERROR|missing comp"); report.close(); return; }

    var sample = Math.min(comp.duration / 2, 3);
    out("COMP|" + comp.width + "x" + comp.height + "|duration=" + comp.duration + "|sample=" + sample);
    for (var li = 1; li <= comp.numLayers; li++) {
        var layer = comp.layer(li);
        if (!(layer instanceof TextLayer) || String(layer.name).indexOf("HAFEZ EDIT ·") === 0) continue;
        var doc = layer.property("ADBE Text Properties").property("ADBE Text Document").valueAtTime(sample, false);
        var rect = layer.sourceRectAtTime(sample, false);
        out("TEXT|index=" + layer.index + "|name=" + layer.name + "|enabled=" + layer.enabled +
            "|active=" + layer.activeAtTime(sample) + "|in=" + layer.inPoint + "|out=" + layer.outPoint +
            "|parent=" + (layer.parent ? layer.parent.name : "") + "|blend=" + layer.blendingMode +
            "|font=" + doc.font + "|fontSize=" + doc.fontSize + "|applyFill=" + doc.applyFill +
            "|fill=" + arr(doc.fillColor) + "|justification=" + doc.justification +
            "|rect=" + [rect.left,rect.top,rect.width,rect.height].join(","));
        var tx = layer.property("ADBE Transform Group");
        propLine(layer, tx.property("ADBE Anchor Point"), "ANCHOR", sample);
        propLine(layer, tx.property("ADBE Position"), "POSITION", sample);
        propLine(layer, tx.property("ADBE Scale"), "SCALE", sample);
        propLine(layer, tx.property("ADBE Opacity"), "OPACITY", sample);
        var effects = layer.property("ADBE Effect Parade");
        for (var ei = 1; ei <= effects.numProperties; ei++) {
            var effect = effects.property(ei);
            out("EFFECT|" + effect.name + "|enabled=" + effect.enabled);
            for (var pi = 1; pi <= effect.numProperties; pi++) {
                var property = effect.property(pi);
                if (property.propertyValueType !== PropertyValueType.NO_VALUE) {
                    try { out("EFFECT_PROP|" + effect.name + "/" + property.name + "=" + arr(property.valueAtTime(sample, false))); } catch (_) {}
                }
            }
        }
        var animators = layer.property("ADBE Text Properties").property("ADBE Text Animators");
        out("ANIMATORS|count=" + animators.numProperties);
        walk(animators, layer.name + "/Animators", sample, 0);
    }
    report.close();
})();
