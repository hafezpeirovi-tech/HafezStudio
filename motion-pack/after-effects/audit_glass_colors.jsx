/* Read-only color/effect audit for the curated Glass Insight comp. */
(function auditGlassColors() {
    app.beginSuppressDialogs();
    if (!app.project || !app.project.file) throw new Error("Open the curated Hafez AEP first");

    var scriptFolder = new File($.fileName).parent;
    var productRoot = scriptFolder.parent.parent;
    var report = new File(productRoot.fsName + "/proof/ae-elements-audit/glass-insight-color-audit.txt");
    report.encoding = "UTF-8";
    report.open("w");

    function line(value) {
        report.writeln(String(value));
    }

    function valueText(value) {
        if (value instanceof Array) {
            var parts = [];
            for (var i = 0; i < value.length; i++) parts.push(Number(value[i]).toFixed(4));
            return "[" + parts.join(",") + "]";
        }
        return String(value);
    }

    function auditProperties(group, prefix) {
        if (!group || !group.numProperties) return;
        for (var i = 1; i <= group.numProperties; i++) {
            var prop = group.property(i);
            var path = prefix + "/" + prop.name + "{" + prop.matchName + "}";
            try {
                if (prop.propertyType === PropertyType.PROPERTY) {
                    var color = prop.propertyValueType === PropertyValueType.COLOR;
                    var nameLooksColor = /(color|colour|tint|glow|fill|stroke|hue|saturation)/i.test(String(prop.name) + " " + String(prop.matchName));
                    if (color || nameLooksColor) {
                        line("PROP|" + path + "|enabled=" + prop.enabled + "|canExpr=" + prop.canSetExpression + "|expr=" + (prop.expressionEnabled ? prop.expression : "") + "|value=" + valueText(prop.value));
                    }
                } else {
                    auditProperties(prop, path);
                }
            } catch (error) {
                line("ERROR|" + path + "|" + error.toString());
            }
        }
    }

    function auditComp(comp, prefix, visited) {
        var key = String(comp.id);
        if (visited[key]) return;
        visited[key] = true;
        line("COMP|" + prefix + comp.name + "|layers=" + comp.numLayers);
        for (var i = 1; i <= comp.numLayers; i++) {
            var layer = comp.layer(i);
            var layerPath = prefix + comp.name + "/" + layer.name;
            var sourceInfo = "";
            try {
                if (layer.source instanceof CompItem) sourceInfo = "comp:" + layer.source.name;
                else if (layer.source && layer.source.mainSource instanceof SolidSource) sourceInfo = "solid:" + valueText(layer.source.mainSource.color);
                else if (layer.source) sourceInfo = "source:" + layer.source.name;
            } catch (_) {}
            line("LAYER|" + layerPath + "|enabled=" + layer.enabled + "|adjustment=" + layer.adjustmentLayer + "|" + sourceInfo);
            auditProperties(layer.property("ADBE Effect Parade"), layerPath + "/Effects");
            auditProperties(layer.property("ADBE Root Vectors Group"), layerPath + "/Vectors");
            auditProperties(layer.property("ADBE Layer Styles"), layerPath + "/Styles");
            try {
                if (layer.source instanceof CompItem) auditComp(layer.source, prefix + comp.name + ">", visited);
            } catch (_) {}
        }
    }

    var target = null;
    for (var index = 1; index <= app.project.numItems; index++) {
        var item = app.project.item(index);
        if (item instanceof CompItem && item.name === "Hafez Hermes Glass Insight") {
            target = item;
            break;
        }
    }
    if (!target) throw new Error("Hafez Hermes Glass Insight not found");
    auditComp(target, "", {});
    report.close();
    app.endSuppressDialogs(false);
})();
