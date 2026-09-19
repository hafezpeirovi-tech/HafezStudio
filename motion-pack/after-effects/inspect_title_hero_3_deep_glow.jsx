/* Read-only inventory of every Deep Glow instance used by Title Hero 3. */
(function inspectTitleHero3DeepGlow() {
    app.beginSuppressDialogs();

    var productRoot = new File($.fileName).parent.parent.parent;
    var outputFolder = new Folder(productRoot.fsName + "/proof/ae-elements-audit/title-hero-3-deepglow");
    if (!outputFolder.exists) outputFolder.create();

    function writeText(path, value) {
        var file = new File(path);
        file.encoding = "UTF-8";
        if (!file.open("w")) throw new Error("Cannot write " + path);
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

    function safeValue(property) {
        try {
            if (property.propertyValueType === PropertyValueType.NO_VALUE) return null;
            var value = property.value;
            if (value instanceof TextDocument) return { text: value.text };
            if (value instanceof Shape) return "[Shape]";
            if (value instanceof MarkerValue) return "[Marker]";
            return value;
        } catch (_) {
            return "[unavailable]";
        }
    }

    function propertyInfo(property) {
        var result = {
            index: property.propertyIndex,
            name: String(property.name),
            matchName: String(property.matchName),
            propertyType: property.propertyType,
            propertyValueType: null,
            value: null,
            canSetExpression: false,
            expressionEnabled: false,
            expression: ""
        };
        try { result.propertyValueType = property.propertyValueType; } catch (_) {}
        try { result.value = safeValue(property); } catch (_) {}
        try { result.canSetExpression = property.canSetExpression; } catch (_) {}
        try { result.expressionEnabled = property.expressionEnabled; } catch (_) {}
        try { result.expression = property.expression || ""; } catch (_) {}
        return result;
    }

    function walkProperties(group, destination) {
        if (!group || !group.numProperties) return;
        for (var i = 1; i <= group.numProperties; i++) {
            var property = group.property(i);
            if (!property) continue;
            var info = propertyInfo(property);
            if (property.propertyType !== PropertyType.PROPERTY) {
                info.children = [];
                walkProperties(property, info.children);
            }
            destination.push(info);
        }
    }

    function isDeepGlow(effect) {
        var label = (String(effect.name) + " " + String(effect.matchName)).toLowerCase();
        return label.indexOf("pedg2") >= 0 || label.indexOf("deep glow") >= 0 || label.indexOf("deepglow") >= 0;
    }

    var report = {
        project: app.project && app.project.file ? app.project.file.fsName : null,
        roots: [],
        deepGlowEffects: []
    };
    var visited = {};

    function inspectComp(comp, path) {
        if (!comp || visited[comp.id]) return;
        visited[comp.id] = true;
        var rootEntry = { name: comp.name, id: comp.id, path: path, layers: comp.numLayers, controls: {} };
        try {
            var controlLayer = comp.layer("HAFEZ · CONTROLS");
            var controlEffects = controlLayer ? controlLayer.property("ADBE Effect Parade") : null;
            if (controlEffects) {
                var glowRadius = controlEffects.property("Glow Radius");
                var glowIntensity = controlEffects.property("Glow Intensity");
                if (glowRadius) rootEntry.controls.glowRadius = glowRadius.property(1).value;
                if (glowIntensity) rootEntry.controls.glowIntensity = glowIntensity.property(1).value;
            }
        } catch (_) {}
        report.roots.push(rootEntry);

        for (var layerIndex = 1; layerIndex <= comp.numLayers; layerIndex++) {
            var layer = comp.layer(layerIndex);
            var effects = layer.property("ADBE Effect Parade");
            if (effects) {
                for (var effectIndex = 1; effectIndex <= effects.numProperties; effectIndex++) {
                    var effect = effects.property(effectIndex);
                    if (!effect || !isDeepGlow(effect)) continue;
                    var entry = {
                        compName: comp.name,
                        compId: comp.id,
                        compPath: path,
                        layerName: String(layer.name),
                        layerIndex: layer.index,
                        effectName: String(effect.name),
                        effectMatchName: String(effect.matchName),
                        effectIndex: effect.propertyIndex,
                        properties: []
                    };
                    walkProperties(effect, entry.properties);
                    report.deepGlowEffects.push(entry);
                }
            }
            try {
                if (layer.source instanceof CompItem) {
                    inspectComp(layer.source, path + " > " + layer.name + " :: " + layer.source.name);
                }
            } catch (_) {}
        }
    }

    var names = ["Hafez Hermes Title Hero 3 Review 2", "Hafez Hermes Title Hero 3 Review 1", "Hafez Hermes Title Hero 3"];
    for (var n = 0; n < names.length; n++) {
        var comp = findComp(names[n]);
        if (comp) inspectComp(comp, comp.name);
    }

    writeText(outputFolder.fsName + "/inventory.json", JSON.stringify(report, null, 2));
    writeText(outputFolder.fsName + "/done.txt", "DONE\nDeep Glow effects: " + report.deepGlowEffects.length + "\n");
    app.endSuppressDialogs(false);
})();
