/* Write a sanitized structural audit of the priority comp so opaque nested
 * plates can be identified without changing the project.
 */
(function auditGlassInsightHierarchy() {
    var productRoot = new File($.fileName).parent.parent.parent;
    var output = new File(productRoot.fsName + "/proof/ae-elements-audit/glass-insight-hierarchy.tsv");
    output.encoding = "UTF-8";
    output.open("w");
    output.writeln("depth\tcomp\tindex\tlayer\tenabled\tadjustment\tsourceType\tsourceSize\tvisibleSize\topacity\tblend\tmasks\teffects");

    function findComp(name) {
        for (var index = 1; index <= app.project.numItems; index++) {
            var item = app.project.item(index);
            if (item instanceof CompItem && item.name === name) return item;
        }
        return null;
    }

    function clean(value) {
        return String(value).replace(/[\t\r\n]+/g, " ");
    }

    function walk(comp, depth, visited) {
        var key = String(comp.id);
        if (visited[key]) return;
        visited[key] = true;
        for (var layerIndex = 1; layerIndex <= comp.numLayers; layerIndex++) {
            var layer = comp.layer(layerIndex);
            var sourceType = "none";
            var sourceSize = "";
            var visibleSize = "";
            try {
                if (layer.source instanceof CompItem) sourceType = "comp";
                else if (layer.source && layer.source.mainSource instanceof SolidSource) sourceType = "solid";
                else if (layer.source) sourceType = "footage";
                if (layer.source) sourceSize = layer.source.width + "x" + layer.source.height;
                if (layer.source) {
                    var scale = layer.property("ADBE Transform Group").property("ADBE Scale").value;
                    visibleSize = Math.round(layer.source.width * Math.abs(Number(scale[0])) / 100) + "x" +
                        Math.round(layer.source.height * Math.abs(Number(scale[1])) / 100);
                }
            } catch (_) {}
            var opacity = "";
            try { opacity = layer.property("ADBE Transform Group").property("ADBE Opacity").value; } catch (_) {}
            var masks = 0;
            try { masks = layer.property("ADBE Mask Parade").numProperties; } catch (_) {}
            var effects = 0;
            try { effects = layer.property("ADBE Effect Parade").numProperties; } catch (_) {}
            output.writeln([
                depth,
                clean(comp.name),
                layerIndex,
                clean(layer.name),
                layer.enabled,
                layer.adjustmentLayer,
                sourceType,
                sourceSize,
                visibleSize,
                opacity,
                clean(layer.blendingMode),
                masks,
                effects
            ].join("\t"));
            try {
                if (layer.source instanceof CompItem) walk(layer.source, depth + 1, visited);
            } catch (_) {}
        }
    }

    var comp = findComp("Hafez Hermes Glass Insight");
    if (!comp) throw new Error("Priority Glass Insight comp not found");
    walk(comp, 0, {});
    output.close();
})();
