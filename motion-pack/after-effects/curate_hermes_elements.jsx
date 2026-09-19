/* Hafez Studio · Curate the user-owned Hermes element library.
 *
 * Runs only after a timestamped backup. The original D:\ project remains
 * untouched: this script immediately saves a curated copy inside HafezStudio,
 * duplicates each selected hierarchy, applies ABAR typography and the
 * Director-UI palette, exposes real Essential Graphics controls, removes
 * Grain, disables baked full-frame backgrounds for overlays, and exports the
 * fourteen catalog MOGRTs.
 */

(function curateHermesElements() {
    app.beginSuppressDialogs();
    app.beginUndoGroup("Curate Hermes Studio Elements");

    var scriptFolder = new File($.fileName).parent;
    var productRoot = scriptFolder && scriptFolder.parent && scriptFolder.parent.parent
        ? scriptFolder.parent.parent
        : (app.project && app.project.file ? app.project.file.parent.parent.parent : null);
    if (!productRoot) throw new Error("Unable to resolve HafezStudio product root");
    var sourceFolder = new Folder(productRoot.fsName + "/motion-pack/source");
    var outputFolder = new Folder(productRoot.fsName + "/motion-pack/dist");
    var proofFolder = new Folder(productRoot.fsName + "/proof/ae-elements-audit");
    var previewFolder = new Folder(proofFolder.fsName + "/curated-previews");
    if (!sourceFolder.exists) sourceFolder.create();
    if (!outputFolder.exists) outputFolder.create();
    if (!proofFolder.exists) proofFolder.create();
    if (!previewFolder.exists) previewFolder.create();

    var logFile = new File(proofFolder.fsName + "/curation-export.log");
    logFile.encoding = "UTF-8";
    logFile.open("w");
    function log(value) {
        var line = (new Date()).toUTCString() + " | " + String(value);
        try { logFile.writeln(line); logFile.flush(); } catch (_) {}
        $.writeln(line);
    }

    function rgb(hex) {
        var raw = String(hex).replace("#", "").substring(0, 6);
        return [
            parseInt(raw.substring(0, 2), 16) / 255,
            parseInt(raw.substring(2, 4), 16) / 255,
            parseInt(raw.substring(4, 6), 16) / 255
        ];
    }

    // Keep the authored geometry/effects, but make every generated template
    // visually native to the current Hafez Studio Director UI.  The legacy
    // source project used a warm beige treatment which became an opaque-looking
    // wash over real footage in Premiere.  These are the app's production
    // tokens from app/styles.css.
    var PALETTE = {
        ink: rgb("#020303"),
        glass: rgb("#0A0C0B"),
        deep: rgb("#111412"),
        cool: rgb("#2FD65B"),
        bronze: rgb("#1AC947"),
        sand: rgb("#55FF72"),
        champagne: rgb("#B6FFC1"),
        white: rgb("#F5F7F5")
    };

    var FONTS = {
        body: "AbarHighFaNum-Regular",
        metadata: "AbarHighFaNum-SemiBold",
        label: "AbarHighFaNum-Bold",
        title: "AbarHighFaNum-ExtraBold",
        impact: "AbarHighFaNum-Black"
    };

    var SPECS = [
        {id:"hermes-glass-pill", source:"Glassmorph Lower third or Title1", target:"Hafez Hermes Glass Pill", slots:["Primary Text"], overlay:true, priority:false},
        {id:"hermes-glass-insight", source:"Glassmorph Lower third or Title2", target:"Hafez Hermes Glass Insight", slots:["Title","Body"], overlay:true, priority:true},
        {id:"hermes-glass-kpi", source:"Glassmorph Lower third or Title3", target:"Hafez Hermes Glass KPI", slots:["Label","Value","Description"], overlay:true, priority:true},
        {id:"hermes-glass-quote", source:"Glassmorph Lower third or Title4", target:"Hafez Hermes Glass Quote", slots:["Quote","Author","Role"], overlay:true, priority:true},
        {id:"hermes-glass-selector", source:"Glassmorph Lower third or Title5", target:"Hafez Hermes Glass Selector", slots:["Title","Option 1","Option 2","Option 3","Option 4","Option 5","Option 6"], overlay:true, priority:false},
        {id:"hermes-subscribe", source:"Subscribe", target:"Hafez Hermes Subscribe", slots:["Channel Name","Channel Subtitle","CTA Text"], overlay:true, priority:true},
        {id:"hermes-price-list", source:"[1. Price List]", sourceComp:"1. Price List", target:"Hafez Hermes Price List", slots:["Plan 1","Price 1","Plan 2","Price 2","Plan 3","Price 3"], overlay:true, priority:false},
        {id:"hermes-revenue-chart", source:"[2. Graphic Revenue]", sourceComp:"2. Graphic Revenue", target:"Hafez Hermes Revenue Chart", slots:["Period","Primary Value","Income","Spend","Axis Labels"], overlay:true, priority:true},
        {id:"hermes-saving-balance", source:"[3. Saving Balance]", sourceComp:"3. Saving Balance", target:"Hafez Hermes Saving Balance", slots:["Value","Label","Action 1","Action 2"], overlay:true, priority:false},
        {id:"hermes-weekly-progress", source:"[4. Progres user]", sourceComp:"4. Progres user", target:"Hafez Hermes Weekly Progress", slots:["Greeting","Total","Rate","Day Values"], overlay:true, priority:false},
        {id:"hermes-user-growth", source:"[5. User Growth]", sourceComp:"5. User Growth", target:"Hafez Hermes User Growth", slots:["Title","Percentage","Label A","Value A","Label B","Value B"], overlay:true, priority:true},
        {id:"hermes-flowchart", source:"Flowchart1", target:"Hafez Hermes Flowchart", slots:["Title","Node 1","Node 2","Node 3","Node 4","Node 5","Node 6"], overlay:false, priority:true},
        {id:"hermes-title-hero-3", sourceIndex:13, target:"Hafez Hermes Title Hero 3", slots:["Title"], overlay:true, priority:true, titleColorOnly:true},
        {id:"hermes-title-hero-2", sourceIndex:14, target:"Hafez Hermes Title Hero 2", slots:["Title"], overlay:true, priority:true, titleColorOnly:true}
    ];

    var stats = {
        targets:0, exported:0, exportFailed:0, textNormalized:0,
        textExposed:0, textStyleControls:0, colorsBound:0, backgroundsDisabled:0,
        grainLayersRemoved:0, grainEffectsRemoved:0, easedProperties:0,
        previews:0
    };

    function findComp(name) {
        for (var index = 1; index <= app.project.numItems; index++) {
            var item = app.project.item(index);
            if (item instanceof CompItem && item.name === name) return item;
        }
        return null;
    }

    function findLayer(c, name) {
        for (var index = 1; index <= c.numLayers; index++) {
            if (c.layer(index).name === name) return c.layer(index);
        }
        return null;
    }

    function safeExpressionName(value) {
        return String(value).replace(/\\/g, "\\\\").replace(/\"/g, "\\\"");
    }

    function deepDuplicateComp(sourceComp, prefix, memo) {
        var key = String(sourceComp.id);
        if (memo[key]) return memo[key];
        var duplicated = sourceComp.duplicate();
        duplicated.name = prefix + " · " + sourceComp.name;
        memo[key] = duplicated;
        for (var layerIndex = 1; layerIndex <= duplicated.numLayers; layerIndex++) {
            var layer = duplicated.layer(layerIndex);
            try {
                if (layer.source instanceof CompItem) {
                    var child = deepDuplicateComp(layer.source, prefix, memo);
                    layer.replaceSource(child, false);
                }
            } catch (_) {}
        }
        return duplicated;
    }

    function makeTarget(master, spec) {
        if (spec.sourceIndex) {
            var titleComp = master.duplicate();
            titleComp.name = spec.target;
            for (var layerIndex = titleComp.numLayers; layerIndex >= 1; layerIndex--) {
                if (layerIndex !== spec.sourceIndex) titleComp.layer(layerIndex).remove();
            }
            return titleComp;
        }
        var masterLayer = findLayer(master, spec.source);
        var sourceComp = masterLayer && masterLayer.source instanceof CompItem
            ? masterLayer.source
            : (spec.sourceComp ? findComp(spec.sourceComp) : null);
        if (!(sourceComp instanceof CompItem)) {
            throw new Error("Missing source layer/comp: " + spec.source + " / " + String(spec.sourceComp || ""));
        }
        var target = deepDuplicateComp(sourceComp, spec.target, {});
        target.name = spec.target;
        return target;
    }

    function roleForText(layer, doc, slot) {
        var probe = (String(layer.name) + " " + String(slot || "")).toLowerCase();
        if (/value|price|percentage|rate|total|number|kpi/.test(probe) || Number(doc.fontSize) >= 90) return "impact";
        if (/title|heading|headline|channel name/.test(probe) || Number(doc.fontSize) >= 58) return "title";
        if (/metadata|role|author|subtitle|axis|day|period/.test(probe) || Number(doc.fontSize) <= 28) return "metadata";
        if (/body|description|quote|support/.test(probe)) return "body";
        return "label";
    }

    function textColorForRole(role) {
        if (role === "impact") return PALETTE.sand;
        if (role === "metadata") return PALETTE.cool;
        if (role === "title") return PALETTE.white;
        return PALETTE.white;
    }

    function normalizeTextLayer(layer, titleColorOnly) {
        try {
            var prop = layer.property("ADBE Text Properties").property("ADBE Text Document");
            var doc = prop.value;
            var role = roleForText(layer, doc, "");
            try { doc.font = FONTS[role]; } catch (_) {}
            doc.applyFill = true;
            doc.fillColor = titleColorOnly ? PALETTE.white : textColorForRole(role);
            prop.setValue(doc);
            stats.textNormalized++;
        } catch (error) {
            log("TEXT_NORMALIZE_FAILED | " + layer.name + " | " + error.toString());
        }
    }

    function removeGrainEffects(layer) {
        try {
            var effects = layer.property("ADBE Effect Parade");
            if (!effects) return;
            for (var index = effects.numProperties; index >= 1; index--) {
                var effect = effects.property(index);
                if (/grain/i.test(String(effect.name) + " " + String(effect.matchName))) {
                    effect.remove();
                    stats.grainEffectsRemoved++;
                }
            }
        } catch (_) {}
    }

    function isFullFrameSolid(layer, c) {
        try {
            if (!layer.source || !(layer.source.mainSource instanceof SolidSource)) return false;
            if (String(layer.name).indexOf("HAFEZ ·") === 0) return false;
            if (layer.adjustmentLayer) return false;
            var masks = layer.property("ADBE Mask Parade");
            if (masks && masks.numProperties > 0) return false;
            var layerName = String(layer.name).replace(/^\s+|\s+$/g, "");
            var isNamedPlate = /^(bg|background|back[ _-]?plate|plate)(?:[ _-]?\d+)?$/i.test(layerName) ||
                /^(?:dark|light|gray|grey|black|white|beige)[ _-].*solid(?:[ _-]?\d+)?$/i.test(layerName);
            if (!isNamedPlate) return false;
            var scale = layer.property("ADBE Transform Group").property("ADBE Scale").value;
            var visibleWidth = layer.source.width * Math.abs(Number(scale[0])) / 100;
            var visibleHeight = layer.source.height * Math.abs(Number(scale[1])) / 100;
            return visibleWidth >= c.width * .85 && visibleHeight >= c.height * .85;
        } catch (_) { return false; }
    }

    function isFullFrameNamedLayer(layer, c) {
        if (!/^(bg|background|back[ _-]?plate|plate)(?:[ _-]?\d+)?$/i.test(String(layer.name).replace(/^\s+|\s+$/g, ""))) return false;
        if (layer.adjustmentLayer) return false;
        try {
            var rect = layer.sourceRectAtTime(0, false);
            return rect.width >= c.width * .78 && rect.height >= c.height * .78;
        } catch (_) { return true; }
    }

    function colorTokenFor(value) {
        var r = Number(value[0]), g = Number(value[1]), b = Number(value[2]);
        var luminance = r * .2126 + g * .7152 + b * .0722;
        if (luminance < .18) return "Glass Surface";
        if (luminance > .80) return "Text Primary";
        if (b > r * 1.12 || b > g * 1.08) return "Cool Accent";
        if (r > b * 1.15) return "Sand Accent";
        return "Champagne Border";
    }

    function bindPropertyTree(group, targetName, controlName) {
        if (!group || !group.numProperties) return;
        for (var index = 1; index <= group.numProperties; index++) {
            var prop = group.property(index);
            try {
                if (prop.propertyType === PropertyType.PROPERTY) {
                    if (prop.propertyValueType === PropertyValueType.COLOR && prop.canSetExpression) {
                        var token = colorTokenFor(prop.value);
                        prop.expression = "comp(\"" + safeExpressionName(targetName) + "\").layer(\"" + controlName + "\").effect(\"" + token + "\")(\"Color\")";
                        stats.colorsBound++;
                    } else if (prop.canSetExpression && /glow intensity/i.test(String(prop.name))) {
                        prop.expression = "value * comp(\"" + safeExpressionName(targetName) + "\").layer(\"" + controlName + "\").effect(\"Glow Intensity\")(\"Slider\") / 100";
                    } else if (prop.canSetExpression && /glow radius/i.test(String(prop.name))) {
                        prop.expression = "value * comp(\"" + safeExpressionName(targetName) + "\").layer(\"" + controlName + "\").effect(\"Glow Radius\")(\"Slider\") / 34";
                    } else if (prop.canSetExpression && prop.matchName === "ADBE Vector Fill Opacity") {
                        prop.expression = "value * comp(\"" + safeExpressionName(targetName) + "\").layer(\"" + controlName + "\").effect(\"Glass Opacity\")(\"Slider\") / 72";
                    }
                } else {
                    bindPropertyTree(prop, targetName, controlName);
                }
            } catch (_) {}
        }
    }

    function bindSolidColor(layer, targetName, controlName) {
        try {
            if (!layer.source || !(layer.source.mainSource instanceof SolidSource)) return;
            var effects = layer.property("ADBE Effect Parade");
            var fill = effects.addProperty("ADBE Fill");
            fill.name = "HAFEZ · SOLID COLOR";
            var token = colorTokenFor(layer.source.mainSource.color);
            fill.property(1).expression = "comp(\"" + safeExpressionName(targetName) + "\").layer(\"" + controlName + "\").effect(\"" + token + "\")(\"Color\")";
            stats.colorsBound++;
        } catch (_) {}
    }

    function easeProperty(prop) {
        try {
            if (!prop || prop.numKeys < 2 || !prop.canVaryOverTime) return;
            var match = String(prop.matchName);
            if (!/(Position|Scale|Rotation|Opacity)/i.test(match)) return;
            for (var keyIndex = 1; keyIndex <= prop.numKeys; keyIndex++) {
                try {
                    prop.setInterpolationTypeAtKey(keyIndex, KeyframeInterpolationType.BEZIER, KeyframeInterpolationType.BEZIER);
                    var value = prop.keyValue(keyIndex);
                    var dimensions = value instanceof Array ? value.length : 1;
                    var incoming = [], outgoing = [];
                    for (var axis = 0; axis < dimensions; axis++) {
                        incoming.push(new KeyframeEase(0, 72));
                        outgoing.push(new KeyframeEase(0, 72));
                    }
                    prop.setTemporalEaseAtKey(keyIndex, incoming, outgoing);
                } catch (_) {}
            }
            stats.easedProperties++;
        } catch (_) {}
    }

    function easeTransforms(layer) {
        try {
            var transform = layer.property("ADBE Transform Group");
            if (!transform) return;
            for (var index = 1; index <= transform.numProperties; index++) easeProperty(transform.property(index));
        } catch (_) {}
    }

    function processHierarchy(c, targetName, controlName, overlayDefault, titleColorOnly, visited) {
        var key = String(c.id);
        if (visited[key]) return;
        visited[key] = true;
        for (var layerIndex = c.numLayers; layerIndex >= 1; layerIndex--) {
            var layer = c.layer(layerIndex);
            if (String(layer.name).indexOf("HAFEZ ·") === 0 || String(layer.name).indexOf("HAFEZ EDIT ·") === 0) continue;
            if (/grain/i.test(String(layer.name))) {
                layer.remove();
                stats.grainLayersRemoved++;
                continue;
            }
            removeGrainEffects(layer);
            if (layer instanceof TextLayer) {
                normalizeTextLayer(layer, titleColorOnly);
                bindPropertyTree(layer.property("ADBE Effect Parade"), targetName, controlName);
            }
            easeTransforms(layer);
            // Overlay MOGRTs must never carry an opaque full-frame plate from the
            // vendor/source comp. A number of the Hermes comps use a light solid
            // rather than a dark, predictably named "Background" layer; allowing
            // those through covers Premiere footage with a sand/beige frame. The
            // The authored optional plate below is the only full-frame background and
            // remains explicitly gated by the Show Background control.
            if (overlayDefault && (isFullFrameSolid(layer, c) || isFullFrameNamedLayer(layer, c))) {
                try { layer.enabled = false; stats.backgroundsDisabled++; } catch (_) {}
            }
            try {
                if (layer.source instanceof CompItem) {
                    processHierarchy(layer.source, targetName, controlName, overlayDefault, titleColorOnly, visited);
                } else if (!(layer instanceof TextLayer)) {
                    bindSolidColor(layer, targetName, controlName);
                    bindPropertyTree(layer.property("ADBE Root Vectors Group"), targetName, controlName);
                    bindPropertyTree(layer.property("ADBE Effect Parade"), targetName, controlName);
                }
            } catch (_) {}
        }
    }

    function addControlEffect(control, target, matchName, name, value) {
        var effect = control.property("ADBE Effect Parade").addProperty(matchName);
        effect.name = name;
        effect.property(1).setValue(value);
        try { effect.property(1).addToMotionGraphicsTemplateAs(target, name); } catch (error) { log("CONTROL_EXPOSE_FAILED | " + target.name + " | " + name + " | " + error.toString()); }
        return effect;
    }

    function addRig(target, overlayDefault) {
        var control = target.layers.addNull();
        control.name = "HAFEZ · CONTROLS";
        control.guideLayer = true;
        addControlEffect(control, target, "ADBE Color Control", "Glass Surface", PALETTE.glass);
        addControlEffect(control, target, "ADBE Color Control", "Sand Accent", PALETTE.sand);
        addControlEffect(control, target, "ADBE Color Control", "Cool Accent", PALETTE.cool);
        addControlEffect(control, target, "ADBE Color Control", "Champagne Border", PALETTE.champagne);
        addControlEffect(control, target, "ADBE Color Control", "Text Primary", PALETTE.white);
        addControlEffect(control, target, "ADBE Color Control", "Background Color", PALETTE.ink);
        addControlEffect(control, target, "ADBE Slider Control", "Glass Opacity", 58);
        addControlEffect(control, target, "ADBE Slider Control", "Glow Intensity", 34);
        addControlEffect(control, target, "ADBE Slider Control", "Glow Radius", 22);
        addControlEffect(control, target, "ADBE Point Control", "Layout Position", [target.width / 2, target.height / 2]);
        addControlEffect(control, target, "ADBE Slider Control", "Layout Scale", 100);
        addControlEffect(control, target, "ADBE Checkbox Control", "Show Background", overlayDefault ? 0 : 1);

        var layout = target.layers.addNull();
        layout.name = "HAFEZ · LAYOUT";
        layout.guideLayer = true;
        try {
            layout.property("ADBE Transform Group").property("ADBE Position").expression =
                "thisComp.layer(\"HAFEZ · CONTROLS\").effect(\"Layout Position\")(\"Point\")";
            layout.property("ADBE Transform Group").property("ADBE Scale").expression =
                "var s=thisComp.layer(\"HAFEZ · CONTROLS\").effect(\"Layout Scale\")(\"Slider\"); [s,s]";
            for (var layerIndex = 1; layerIndex <= target.numLayers; layerIndex++) {
                var child = target.layer(layerIndex);
                if (child === control || child === layout || !(child instanceof AVLayer) || child.parent) continue;
                child.parent = layout;
            }
        } catch (error) {
            log("LAYOUT_RIG_FAILED | " + target.name + " | " + error.toString());
        }

        var background = target.layers.addSolid(PALETTE.ink, "HAFEZ · OPTIONAL BACKGROUND", target.width, target.height, target.pixelAspect, target.duration);
        background.moveToEnd();
        if (overlayDefault) background.enabled = false;
        try {
            var backgroundFill = background.property("ADBE Effect Parade").addProperty("ADBE Fill");
            backgroundFill.name = "HAFEZ · BACKGROUND COLOR";
            backgroundFill.property(1).expression =
                "thisComp.layer(\"HAFEZ · CONTROLS\").effect(\"Background Color\")(\"Color\")";
            background.property("ADBE Transform Group").property("ADBE Opacity").expression =
                "thisComp.layer(\"HAFEZ · CONTROLS\").effect(\"Show Background\")(\"Checkbox\") * 100";
        } catch (_) {}
        return control;
    }

    function collectTextLayers(c, visited, result) {
        var key = String(c.id);
        if (visited[key]) return;
        visited[key] = true;
        for (var layerIndex = 1; layerIndex <= c.numLayers; layerIndex++) {
            var layer = c.layer(layerIndex);
            if (layer instanceof TextLayer && layer.name.indexOf("HAFEZ EDIT ·") !== 0) {
                try {
                    var prop = layer.property("ADBE Text Properties").property("ADBE Text Document");
                    result.push({layer:layer, prop:prop, size:Number(prop.value.fontSize), name:String(layer.name)});
                } catch (_) {}
            }
            try { if (layer.source instanceof CompItem) collectTextLayers(layer.source, visited, result); } catch (_) {}
        }
    }

    function exposeEditableText(target, slots, titleColorOnly, control) {
        var candidates = [];
        collectTextLayers(target, {}, candidates);
        candidates.sort(function(a, b) {
            if (a.size !== b.size) return b.size - a.size;
            return a.name < b.name ? -1 : 1;
        });
        var limit = Math.min(slots.length, candidates.length);
        for (var index = 0; index < limit; index++) {
            var slot = String(slots[index]);
            var source = candidates[index];
            try {
                var controller = target.layers.addText(source.prop.value);
                controller.name = "HAFEZ EDIT · " + slot;
                controller.enabled = false;
                controller.shy = true;
                var controllerProp = controller.property("ADBE Text Properties").property("ADBE Text Document");
                var doc = controllerProp.value;
                var role = roleForText(source.layer, doc, slot);
                try { doc.font = FONTS[role]; } catch (_) {}
                doc.applyFill = true;
                doc.fillColor = titleColorOnly ? PALETTE.white : textColorForRole(role);
                controllerProp.setValue(doc);
                controllerProp.addToMotionGraphicsTemplateAs(target, slot);

                var textColorName = slot + " · Text Color";
                var leadingName = slot + " · Line Spacing";
                var trackingName = slot + " · Tracking";
                var initialLeading = Number(source.prop.value.leading);
                if (!initialLeading || initialLeading < 1) initialLeading = Math.max(1, Number(source.prop.value.fontSize) * 1.2);
                var initialTracking = Number(source.prop.value.tracking);
                if (isNaN(initialTracking)) initialTracking = 0;
                var initialColor = source.prop.value.fillColor || textColorForRole(role);
                addControlEffect(control, target, "ADBE Color Control", textColorName, initialColor);
                addControlEffect(control, target, "ADBE Slider Control", leadingName, initialLeading);
                addControlEffect(control, target, "ADBE Slider Control", trackingName, initialTracking);
                stats.textStyleControls += 3;

                var targetExpressionName = safeExpressionName(target.name);
                var controllerExpressionName = safeExpressionName(controller.name);
                var controlExpressionName = safeExpressionName(control.name);
                source.prop.expression =
                    "var editable = comp(\"" + targetExpressionName + "\").layer(\"" + controllerExpressionName + "\").text.sourceText;\n" +
                    "var rig = comp(\"" + targetExpressionName + "\").layer(\"" + controlExpressionName + "\");\n" +
                    "var style = editable.getStyleAt(0, 0);\n" +
                    "style.setText(editable.toString())" +
                    ".setApplyFill(true)" +
                    ".setFillColor(rig.effect(\"" + safeExpressionName(textColorName) + "\")(\"Color\"))" +
                    ".setAutoLeading(false)" +
                    ".setLeading(Math.max(1, rig.effect(\"" + safeExpressionName(leadingName) + "\")(\"Slider\")))" +
                    ".setTracking(rig.effect(\"" + safeExpressionName(trackingName) + "\")(\"Slider\"));";
                stats.textExposed++;
            } catch (error) {
                log("TEXT_EXPOSE_FAILED | " + target.name + " | " + slot + " | " + error.toString());
            }
        }
    }

    function savePreview(target, spec) {
        if (!spec.priority) return;
        try {
            var previewFile = new File(previewFolder.fsName + "/" + spec.id + ".png");
            target.saveFrameToPng(Math.min(target.duration * .5, Math.max(0, target.duration - .05)), previewFile);
            if (previewFile.exists) stats.previews++;
        } catch (error) {
            log("PREVIEW_FAILED | " + target.name + " | " + error.toString());
        }
    }

    function exportTarget(target, spec) {
        target.motionGraphicsTemplateName = spec.target;
        try { app.project.save(curatedFile); } catch (_) {}
        try {
            var ok = target.exportAsMotionGraphicsTemplate(true, outputFolder.fsName);
            if (ok) { stats.exported++; log("EXPORT_OK | " + spec.id + " | " + spec.target + ".mogrt"); }
            else { stats.exportFailed++; log("EXPORT_FALSE | " + spec.id); }
        } catch (error) {
            stats.exportFailed++;
            log("EXPORT_FAILED | " + spec.id + " | " + error.toString());
        }
    }

    if (!app.project || !app.project.file) throw new Error("A saved After Effects project must be open");
    var originalFile = app.project.file;
    var master = findComp("All Elements");
    if (!master) throw new Error("Missing master comp: All Elements");
    log("SOURCE | " + originalFile.fsName);

    var curatedFile = new File(sourceFolder.fsName + "/Hermes Studio Elements - Hafez Curated.aep");
    app.project.save(curatedFile);
    log("CURATED_COPY | " + curatedFile.fsName);

    var exportFolder = null;
    for (var folderIndex = 1; folderIndex <= app.project.numItems; folderIndex++) {
        var folderItem = app.project.item(folderIndex);
        if (folderItem instanceof FolderItem && folderItem.name === "HAFEZ CURATED EXPORTS") {
            exportFolder = folderItem;
            break;
        }
    }
    if (!exportFolder) exportFolder = app.project.items.addFolder("HAFEZ CURATED EXPORTS");
    var targets = [];
    for (var specIndex = 0; specIndex < SPECS.length; specIndex++) {
        var spec = SPECS[specIndex];
        try {
            if (findComp(spec.target)) {
                log("CURATE_SKIP_EXISTING | " + spec.id);
                continue;
            }
            var target = makeTarget(master, spec);
            target.name = spec.target;
            target.parentFolder = exportFolder;
            target.motionGraphicsTemplateName = spec.target;
            var control = addRig(target, spec.overlay);
            processHierarchy(target, target.name, "HAFEZ · CONTROLS", spec.overlay, !!spec.titleColorOnly, {});
            exposeEditableText(target, spec.slots, !!spec.titleColorOnly, control);
            stats.targets++;
            targets.push({target:target, spec:spec});
            app.project.save(curatedFile);
            log("CURATED_OK | " + spec.id + " | controllers=" + target.motionGraphicsTemplateControllerCount);
        } catch (error) {
            log("CURATE_FAILED | " + spec.id + " | " + error.toString());
        }
    }

    app.project.save(curatedFile);
    for (var targetIndex = 0; targetIndex < targets.length; targetIndex++) {
        var exportComp = findComp(targets[targetIndex].spec.target);
        if (!exportComp) { log("EXPORT_MISSING_COMP | " + targets[targetIndex].spec.id); continue; }
        exportTarget(exportComp, targets[targetIndex].spec);
        var previewComp = findComp(targets[targetIndex].spec.target);
        if (previewComp) savePreview(previewComp, targets[targetIndex].spec);
    }
    app.project.save(curatedFile);

    log("SUMMARY | " + stats.toSource());
    logFile.close();
    app.endUndoGroup();
    app.endSuppressDialogs(false);
})();
