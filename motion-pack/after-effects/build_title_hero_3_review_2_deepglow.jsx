/*
 * Build Title Hero 3 Review 2 with Premiere controls wired to the actual
 * Deep Glow 2 Radius and Exposure properties.
 */
(function buildTitleHero3Review2DeepGlow() {
    app.beginSuppressDialogs();
    app.beginUndoGroup("Build Hafez Title Hero 3 Review 2 Deep Glow");

    if (!app.project || !app.project.file) throw new Error("Open the curated Hafez AEP first");
    var scriptFolder = new File($.fileName).parent;
    var productRoot = scriptFolder.parent.parent;
    var outputFolder = new Folder(productRoot.fsName + "/motion-pack/dist");
    var proofFolder = new Folder(productRoot.fsName + "/proof/ae-elements-audit/title-hero-3-review-2-deepglow");
    if (!outputFolder.exists) outputFolder.create();
    if (!proofFolder.exists) proofFolder.create();

    var logFile = new File(proofFolder.fsName + "/build.log");
    logFile.encoding = "UTF-8";
    logFile.open("w");
    function log(value) {
        logFile.writeln((new Date()).toUTCString() + " | " + String(value));
        logFile.close();
        logFile.open("a");
    }

    function findComp(name) {
        for (var i = 1; i <= app.project.numItems; i++) {
            var item = app.project.item(i);
            if (item instanceof CompItem && item.name === name) return item;
        }
        return null;
    }

    function patchExpressions(group, oldName, newName) {
        if (!group || !group.numProperties) return;
        for (var i = 1; i <= group.numProperties; i++) {
            var property = group.property(i);
            if (!property) continue;
            if (property.propertyType === PropertyType.PROPERTY) {
                try {
                    if (property.canSetExpression && property.expression) {
                        property.expression = property.expression.split(oldName).join(newName);
                    }
                } catch (_) {}
            } else {
                patchExpressions(property, oldName, newName);
            }
        }
    }

    function findEffectProperty(effect, matchName, fallbackName) {
        for (var i = 1; i <= effect.numProperties; i++) {
            var property = effect.property(i);
            if (!property) continue;
            if (String(property.matchName) === matchName || String(property.name) === fallbackName) return property;
        }
        return null;
    }

    function controlProperty(controlLayer, effectName) {
        var effects = controlLayer.property("ADBE Effect Parade");
        var effect = effects ? effects.property(effectName) : null;
        return effect ? effect.property(1) : null;
    }

    function setControl(controlLayer, effectName, value) {
        var property = controlProperty(controlLayer, effectName);
        if (!property) throw new Error("Missing control: " + effectName);
        property.setValue(value);
    }

    function renderFrame(comp, time, name) {
        try {
            comp.saveFrameToPng(time, new File(proofFolder.fsName + "/" + name + ".png"));
            log("PREVIEW_OK | " + name + " | " + time);
        } catch (error) {
            log("PREVIEW_FAILED | " + name + " | " + error.toString());
        }
    }

    log("START");
    var sourceName = "Hafez Hermes Title Hero 3 Review 1";
    var reviewName = "Hafez Hermes Title Hero 3 Review 2";
    var controlName = "HAFEZ · CONTROLS";
    var source = findComp(sourceName) || findComp("Hafez Hermes Title Hero 3");
    if (!source) throw new Error("Missing Title Hero 3 source comp");

    var oldReview = findComp(reviewName);
    if (oldReview) oldReview.remove();

    var review = source.duplicate();
    review.name = reviewName;
    review.motionGraphicsTemplateName = reviewName;
    log("DUPLICATED | source=" + source.name + " | controllers=" + review.motionGraphicsTemplateControllerCount);

    var controlLayer = review.layer(controlName);
    if (!controlLayer) throw new Error("Missing control layer: " + controlName);
    setControl(controlLayer, "Glow Radius", 200);
    setControl(controlLayer, "Glow Intensity", 20);

    var deepGlowCount = 0;
    for (var layerIndex = 1; layerIndex <= review.numLayers; layerIndex++) {
        var layer = review.layer(layerIndex);
        patchExpressions(layer, source.name, reviewName);
        var layerName = String(layer.name);
        if (layer instanceof TextLayer && layerName.indexOf("HAFEZ EDIT ·") !== 0) layer.enabled = true;
        if (layerName === "HAFEZ · OPTIONAL BACKGROUND") layer.enabled = false;

        var effects = layer.property("ADBE Effect Parade");
        if (!effects) continue;
        for (var effectIndex = 1; effectIndex <= effects.numProperties; effectIndex++) {
            var effect = effects.property(effectIndex);
            if (!effect || String(effect.matchName) !== "PEDG2") continue;
            var radius = findEffectProperty(effect, "PEDG2-0017", "Radius");
            var exposure = findEffectProperty(effect, "PEDG2-0018", "Exposure");
            if (!radius || !exposure) throw new Error("Deep Glow 2 is missing Radius or Exposure");

            // Keep useful base values even if expressions are disabled manually.
            radius.setValue(200);
            exposure.setValue(0.2);
            radius.expression = "thisComp.layer(\"" + controlName + "\").effect(\"Glow Radius\")(\"Slider\")";
            exposure.expression = "thisComp.layer(\"" + controlName + "\").effect(\"Glow Intensity\")(\"Slider\") / 100";
            deepGlowCount++;
            log("BOUND_DEEP_GLOW | layer=" + layer.name + " | radius=" + radius.value + " | exposure=" + exposure.value);
        }
    }
    if (!deepGlowCount) throw new Error("No Deep Glow 2 effect found in review comp");

    // Render three states from the same frame. Distinct renders prove the two
    // Premiere controls now reach the plug-in rather than being decorative UI.
    var previewTime = Math.min(1.0, review.duration - review.frameDuration);
    setControl(controlLayer, "Glow Radius", 200);
    setControl(controlLayer, "Glow Intensity", 20);
    renderFrame(review, previewTime, "frame-default-r200-e020");
    setControl(controlLayer, "Glow Radius", 35);
    setControl(controlLayer, "Glow Intensity", 3);
    renderFrame(review, previewTime, "frame-low-r035-e003");
    setControl(controlLayer, "Glow Radius", 360);
    setControl(controlLayer, "Glow Intensity", 75);
    renderFrame(review, previewTime, "frame-high-r360-e075");
    setControl(controlLayer, "Glow Radius", 200);
    setControl(controlLayer, "Glow Intensity", 20);

    app.project.save(app.project.file);
    // Some third-party effects invalidate the ExtendScript CompItem handle
    // during save. Rehydrate it before opening Essential Graphics/exporting.
    review = findComp(reviewName);
    if (!review) throw new Error("Review comp became unavailable after save");
    var controllerCountBeforeExport = review.motionGraphicsTemplateControllerCount;
    log("EXPORT_START | name=" + review.motionGraphicsTemplateName + " | folder=" + outputFolder.fsName);
    var exported = false;
    try {
        review.openInEssentialGraphics();
        exported = review.exportAsMotionGraphicsTemplate(true, outputFolder.fsName);
        log("EXPORT_RETURNED | ok=" + exported);
    } catch (exportError) {
        log("EXPORT_FAILED | " + exportError.toString() + " | line=" + exportError.line);
        throw exportError;
    }
    log("DONE | ok=" + exported + " | deepGlow=" + deepGlowCount + " | controllers=" + controllerCountBeforeExport);
    logFile.close();
    app.endUndoGroup();
    app.endSuppressDialogs(false);
})();
