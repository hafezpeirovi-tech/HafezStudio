/*
 * Production-review wrapper for the authored Hermes Glass Insight comp.
 * The original glass/glow/shadow render stays intact as a nested comp, while
 * clean live text layers and all editor-facing controls live in this wrapper.
 */
(function buildGlassInsightReview() {
    app.beginSuppressDialogs();
    app.beginUndoGroup("Build Hafez Glass Insight Review MOGRT");

    if (!app.project || !app.project.file) throw new Error("Open the curated Hafez AEP first");
    var scriptFolder = new File($.fileName).parent;
    var productRoot = scriptFolder.parent.parent;
    var outputFolder = new Folder(productRoot.fsName + "/motion-pack/dist");
    var proofFolder = new Folder(productRoot.fsName + "/proof/ae-elements-audit");
    if (!outputFolder.exists) outputFolder.create();
    if (!proofFolder.exists) proofFolder.create();
    var logFile = new File(proofFolder.fsName + "/glass-insight-review-build.log");
    logFile.encoding = "UTF-8";
    logFile.open("w");
    function log(value) { logFile.writeln((new Date()).toUTCString() + " | " + String(value)); }

    var sourceName = "Hafez Hermes Glass Insight";
    var wrapperName = "Hafez Hermes Glass Insight Review 7";
    var source = null;
    var existingWrapper = null;
    for (var itemIndex = 1; itemIndex <= app.project.numItems; itemIndex++) {
        var item = app.project.item(itemIndex);
        if (!(item instanceof CompItem)) continue;
        if (item.name === sourceName) source = item;
        if (item.name === wrapperName) existingWrapper = item;
    }
    if (!source) throw new Error("Missing source comp: " + sourceName);
    if (existingWrapper) existingWrapper.remove();

    // The wrapper owns typography; the nested authored comp owns glass,
    // displacement, glow and shadow.
    for (var sourceLayerIndex = 1; sourceLayerIndex <= source.numLayers; sourceLayerIndex++) {
        var sourceLayer = source.layer(sourceLayerIndex);
        if (sourceLayer instanceof TextLayer && String(sourceLayer.name).indexOf("HAFEZ EDIT ·") !== 0) {
            sourceLayer.enabled = false;
            log("DISABLED_LOCKED_VENDOR_TEXT | " + sourceLayer.name);
        }
    }

    // These vendor carrier layers are full-size sampling rectangles. They are
    // useful inside the stock demo composition, but in Premiere they leave a
    // second green plate over the speaker. The HAFEZ BRAND GLASS/GLOW layers
    // already provide the intended plate, border and glow at the safe position.
    var fullFrameCarriers = ["Displacement Effect", "Panel Shadow"];
    for (var carrierIndex = 0; carrierIndex < fullFrameCarriers.length; carrierIndex++) {
        try {
            var carrier = source.layer(fullFrameCarriers[carrierIndex]);
            if (carrier) {
                carrier.enabled = false;
                log("DISABLED_FULL_FRAME_CARRIER | " + carrier.name);
            }
        } catch (error) { log("DISABLE_CARRIER_FAILED | " + fullFrameCarriers[carrierIndex] + " | " + error.toString()); }
    }

    // Move every root-level vendor render pass as one authored group. Without
    // this, the replacement Hafez plate moves to the safe area while the stock
    // displacement/shadow carrier remains centered over the speaker's face.
    var sourceGroup = null;
    try { sourceGroup = source.layer("HAFEZ · SOURCE GROUP"); } catch (_) {}
    if (!sourceGroup) {
        sourceGroup = source.layers.addNull();
        sourceGroup.name = "HAFEZ · SOURCE GROUP";
        sourceGroup.enabled = false;
        sourceGroup.shy = true;
        sourceGroup.property("ADBE Transform Group").property("ADBE Position").setValue([source.width / 2, source.height / 2]);
        sourceGroup.property("ADBE Transform Group").property("ADBE Scale").setValue([100, 100]);
    }
    var groupCandidates = [];
    for (var groupIndex = 1; groupIndex <= source.numLayers; groupIndex++) {
        var groupLayer = source.layer(groupIndex);
        var groupName = String(groupLayer.name);
        if (groupLayer === sourceGroup || groupName === "HAFEZ · CONTROLS" || groupName === "HAFEZ · LAYOUT") continue;
        if (groupLayer instanceof TextLayer || !groupLayer.enabled || groupLayer.parent) continue;
        if (groupName.indexOf("HAFEZ · BRAND") === 0 || groupName.indexOf("HAFEZ · OPTIONAL BACKGROUND") === 0) continue;
        groupCandidates.push(groupLayer);
    }
    for (var parentIndex = 0; parentIndex < groupCandidates.length; parentIndex++) {
        try {
            groupCandidates[parentIndex].parent = sourceGroup;
            log("GROUPED_VENDOR_PASS | " + groupCandidates[parentIndex].name);
        } catch (error) { log("GROUP_VENDOR_PASS_FAILED | " + groupCandidates[parentIndex].name + " | " + error.toString()); }
    }
    sourceGroup.property("ADBE Transform Group").property("ADBE Position").expression =
        "thisComp.layer(\"HAFEZ · CONTROLS\").effect(\"Layout Position\")(\"Point\")";
    sourceGroup.property("ADBE Transform Group").property("ADBE Scale").expression =
        "var s=thisComp.layer(\"HAFEZ · CONTROLS\").effect(\"Layout Scale\")(\"Slider\");[s,s]";

    var wrapper = app.project.items.addComp(
        wrapperName,
        source.width,
        source.height,
        source.pixelAspect,
        source.duration,
        source.frameRate
    );

    var panelLayer = wrapper.layers.add(source);
    panelLayer.name = "HAFEZ · AUTHORED GLASS / GLOW / SHADOW";
    panelLayer.startTime = 0;
    panelLayer.inPoint = 0;
    panelLayer.outPoint = wrapper.duration;

    var controls = wrapper.layers.addNull();
    controls.name = "HAFEZ · CONTROLS";
    controls.enabled = false;
    controls.shy = true;
    var effects = controls.property("ADBE Effect Parade");

    function addColor(name, value) {
        var effect = effects.addProperty("ADBE Color Control");
        effect.name = name;
        effect.property(1).setValue(value);
        return effect.property(1);
    }
    function addSlider(name, value) {
        var effect = effects.addProperty("ADBE Slider Control");
        effect.name = name;
        effect.property(1).setValue(value);
        return effect.property(1);
    }
    function addPoint(name, value) {
        var effect = effects.addProperty("ADBE Point Control");
        effect.name = name;
        effect.property(1).setValue(value);
        return effect.property(1);
    }
    function addCheckbox(name, value) {
        var effect = effects.addProperty("ADBE Checkbox Control");
        effect.name = name;
        effect.property(1).setValue(value);
        return effect.property(1);
    }

    var exposed = [];
    exposed.push({ name: "Background Color", property: addColor("Background Color", [0.007843, 0.011765, 0.011765]) });
    exposed.push({ name: "Text Primary", property: addColor("Text Primary", [0.960784, 0.968627, 0.960784]) });
    exposed.push({ name: "Champagne Border", property: addColor("Champagne Border", [0.713725, 1.0, 0.756863]) });
    exposed.push({ name: "Cool Accent", property: addColor("Cool Accent", [0.184314, 0.839216, 0.356863]) });
    exposed.push({ name: "Sand Accent", property: addColor("Sand Accent", [0.333333, 1.0, 0.447059]) });
    exposed.push({ name: "Glass Surface", property: addColor("Glass Surface", [0.039216, 0.047059, 0.043137]) });
    exposed.push({ name: "Glow Radius", property: addSlider("Glow Radius", 20) });
    exposed.push({ name: "Glow Intensity", property: addSlider("Glow Intensity", 24) });
    exposed.push({ name: "Glass Opacity", property: addSlider("Glass Opacity", 68) });
    exposed.push({ name: "Show Background", property: addCheckbox("Show Background", 0) });
    exposed.push({ name: "Layout Scale", property: addSlider("Layout Scale", 88) });
    exposed.push({ name: "Layout Position", property: addPoint("Layout Position", [500, 315]) });

    // Bridge wrapper controls to the already-authored source effects. The
    // source graphics therefore retain their original AE render but are driven
    // by the same controls Premiere exposes on this wrapper.
    var sourceControls = source.layer("HAFEZ · CONTROLS");
    if (sourceControls) {
        var sourceEffects = sourceControls.property("ADBE Effect Parade");
        for (var bridgeIndex = 0; bridgeIndex < exposed.length; bridgeIndex++) {
            var bridge = exposed[bridgeIndex];
            var sourceEffect = sourceEffects.property(bridge.name);
            if (!sourceEffect) continue;
            var sourceProperty = sourceEffect.property(1);
            var propertyAccessor = "(1)";
            if (bridge.name === "Layout Position") propertyAccessor = "(\"Point\")";
            else if (/Color|Primary|Border|Accent|Surface/.test(bridge.name)) propertyAccessor = "(\"Color\")";
            else if (bridge.name === "Show Background") propertyAccessor = "(\"Checkbox\")";
            else propertyAccessor = "(\"Slider\")";
            try {
                sourceProperty.expression = "comp(\"" + wrapperName + "\").layer(\"HAFEZ · CONTROLS\").effect(\"" + bridge.name + "\")" + propertyAccessor;
                log("BRIDGED | " + bridge.name);
            } catch (error) { log("BRIDGE_FAILED | " + bridge.name + " | " + error.toString()); }
        }
    }

    function addLiveText(name, value, fontName, fontSize, color, yOffset, xOffset, inDelay) {
        var layer = wrapper.layers.addText(value);
        layer.name = name;
        layer.inPoint = inDelay;
        layer.outPoint = wrapper.duration;
        layer.blendingMode = BlendingMode.NORMAL;
        var sourceText = layer.property("ADBE Text Properties").property("ADBE Text Document");
        var doc = sourceText.value;
        doc.font = fontName;
        doc.fontSize = fontSize;
        doc.applyFill = true;
        doc.fillColor = color;
        doc.applyStroke = false;
        doc.justification = ParagraphJustification.CENTER_JUSTIFY;
        doc.autoLeading = false;
        doc.leading = Math.round(fontSize * 1.18);
        var rtl = /[\u0600-\u06FF]/.test(String(value));
        try { doc.composerEngine = ComposerEngine.UNIVERSAL_TYPE_ENGINE; } catch (_) {}
        try {
            doc.direction = rtl ? ParagraphDirection.DIRECTION_RIGHT_TO_LEFT : ParagraphDirection.DIRECTION_LEFT_TO_RIGHT;
        } catch (_) {}
        try { doc.digitSet = rtl ? DigitSet.FARSI_DIGITS : DigitSet.DEFAULT_DIGITS; } catch (_) {}
        if (rtl) doc.tracking = 0;
        sourceText.setValue(doc);

        var transform = layer.property("ADBE Transform Group");
        transform.property("ADBE Anchor Point").expression =
            "var r=sourceRectAtTime(time,false);[r.left+r.width/2,r.top+r.height/2]";
        transform.property("ADBE Position").expression =
            "var c=thisComp.layer(\"HAFEZ · CONTROLS\");" +
            "var p=c.effect(\"Layout Position\")(\"Point\");" +
            "var s=c.effect(\"Layout Scale\")(\"Slider\")/100;" +
            "var xIn=ease(time,inPoint,inPoint+.30," + xOffset + ",0);" +
            "var xOut=ease(time,outPoint-.32,outPoint,0," + (-xOffset * 0.6) + ");" +
            "var q=p+[xIn+xOut," + yOffset + "]*s;" +
            "value.length>2?[q[0],q[1],value[2]]:q";
        transform.property("ADBE Scale").expression =
            "var s=thisComp.layer(\"HAFEZ · CONTROLS\").effect(\"Layout Scale\")(\"Slider\")/100;" +
            "var a=ease(time,inPoint,inPoint+.30,96,100);" +
            "var b=ease(time,outPoint-.32,outPoint,100,98);" +
            "value*s*Math.min(a,b)/100";
        transform.property("ADBE Opacity").expression =
            "Math.min(ease(time,inPoint,inPoint+.22,0,100),ease(time,outPoint-.28,outPoint,100,0))";
        return sourceText;
    }

    var body = addLiveText(
        "HAFEZ EDIT · BODY",
        "من یک ورک‌فلو ساختم\rکه سیگنال را از تریدینگ‌ویو\rبه هوش مصنوعی می‌فرستد.",
        "AbarHighFaNum-SemiBold",
        40,
        [0.960784, 0.968627, 0.960784],
        42,
        30,
        0.18
    );
    var title = addLiveText(
        "HAFEZ EDIT · TITLE",
        "THE WORKFLOW",
        "AbarHighFaNum-ExtraBold",
        56,
        [0.333333, 1.0, 0.447059],
        -92,
        -30,
        0
    );

    try { body.addToMotionGraphicsTemplateAs(wrapper, "Body"); } catch (error) { log("EXPOSE_BODY_FAILED | " + error.toString()); }
    try { title.addToMotionGraphicsTemplateAs(wrapper, "Title"); } catch (error) { log("EXPOSE_TITLE_FAILED | " + error.toString()); }
    for (var exposeIndex = 0; exposeIndex < exposed.length; exposeIndex++) {
        try {
            // Adding the live text layers can invalidate earlier Property
            // handles in AE 2026. Resolve the control again by name here.
            var liveControl = controls.property("ADBE Effect Parade").property(exposed[exposeIndex].name).property(1);
            liveControl.addToMotionGraphicsTemplateAs(wrapper, exposed[exposeIndex].name);
        }
        catch (error) { log("EXPOSE_CONTROL_FAILED | " + exposed[exposeIndex].name + " | " + error.toString()); }
    }

    wrapper.motionGraphicsTemplateName = wrapperName;
    var controllerCount = wrapper.motionGraphicsTemplateControllerCount;
    app.project.save(app.project.file);
    var ok = wrapper.exportAsMotionGraphicsTemplate(true, outputFolder.fsName);
    // exportAsMotionGraphicsTemplate may invalidate the live CompItem handle in
    // recent AE builds, so keep the count before exporting.
    log("DONE | ok=" + ok + " | controllers=" + controllerCount);
    logFile.close();
    app.endUndoGroup();
    app.endSuppressDialogs(false);
})();
