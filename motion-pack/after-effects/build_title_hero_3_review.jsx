/* Build a visible review MOGRT from the user's authored Title Hero 3 layer. */
(function buildTitleHero3Review() {
    app.beginSuppressDialogs();
    app.beginUndoGroup("Build Hafez Title Hero 3 Review");

    if (!app.project || !app.project.file) throw new Error("Open the curated Hafez AEP first");
    var scriptFolder = new File($.fileName).parent;
    var productRoot = scriptFolder.parent.parent;
    var outputFolder = new Folder(productRoot.fsName + "/motion-pack/dist");
    var proofFolder = new Folder(productRoot.fsName + "/proof/ae-elements-audit/title-hero-3-review");
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
    log("START");

    var sourceName = "Hafez Hermes Title Hero 3";
    var reviewName = "Hafez Hermes Title Hero 3 Review 1";

    function findComp(name) {
        for (var i = 1; i <= app.project.numItems; i++) {
            var item = app.project.item(i);
            if (item instanceof CompItem && item.name === name) return item;
        }
        return null;
    }

    function patchExpressions(group, oldName, newName) {
        if (!group) return;
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

    var source = findComp(sourceName);
    if (!source) throw new Error("Missing source comp: " + sourceName);
    log("SOURCE_OK | layers=" + source.numLayers + " | controllers=" + source.motionGraphicsTemplateControllerCount);
    var oldReview = findComp(reviewName);
    if (oldReview) oldReview.remove();

    var review = source.duplicate();
    log("DUPLICATED");
    review.name = reviewName;
    review.motionGraphicsTemplateName = reviewName;
    log("RENAMED");

    var visibleTextCount = 0;
    for (var layerIndex = 1; layerIndex <= review.numLayers; layerIndex++) {
        var layer = review.layer(layerIndex);
        patchExpressions(layer, sourceName, reviewName);
        var layerName = String(layer.name);
        if (layer instanceof TextLayer && layerName.indexOf("HAFEZ EDIT ·") !== 0) {
            layer.enabled = true;
            visibleTextCount++;
            log("ENABLED_AUTHORED_TITLE | " + layerName);
        }
        if (layerName === "HAFEZ · OPTIONAL BACKGROUND") layer.enabled = false;
    }

    if (!visibleTextCount) throw new Error("No authored title layer found");

    // Render evidence before export. These frames verify that the authored
    // animation survives independently of Premiere's template cache.
    var previewTimes = [0, 0.5, 1, 2, 3, 5, 10, 15, 20, 25];
    for (var previewIndex = 0; previewIndex < previewTimes.length; previewIndex++) {
        var time = Math.min(previewTimes[previewIndex], review.duration - review.frameDuration);
        var label = String(time).replace(".", "p");
        try {
            review.saveFrameToPng(time, new File(proofFolder.fsName + "/frame-" + label + ".png"));
            log("PREVIEW_OK | " + time);
        } catch (error) {
            log("PREVIEW_FAILED | " + time + " | " + error.toString());
        }
    }

    var controllerCount = review.motionGraphicsTemplateControllerCount;
    app.project.save(app.project.file);
    var exported = review.exportAsMotionGraphicsTemplate(true, outputFolder.fsName);
    log("DONE | ok=" + exported + " | controllers=" + controllerCount + " | visibleText=" + visibleTextCount);
    logFile.close();
    app.endUndoGroup();
    app.endSuppressDialogs(false);
})();
