/*
 * Minimal typography-origin repair for the authored Subscribe review.
 * True RTL text has a different sourceRect.left from the source's pre-shaped
 * LTR text. Compensate only the subtitle's anchor X, retaining the authored
 * anchor keyframes, position, Y, animation, plate and logo. Not a redesign.
 * This writes only the owned Review 1 asset, never the canonical Subscribe.
 */
(function fixSubscribeReview1SubtitleOrigin() {
    var root = new File($.fileName).parent.parent.parent;
    function pathKey(value) { return String(value).replace(/\\/g, "/").replace(/\/$/, "").toLowerCase(); }
    var ownedPrefix = pathKey(new Folder(root.fsName + "/motion-pack/source").fsName) + "/";
    if (!app.project || !app.project.file || pathKey(app.project.file.fsName).indexOf(ownedPrefix) !== 0 || !/\.aep$/i.test(app.project.file.fsName)) {
        throw new Error("Open the backed-up HafezStudio AEP in motion-pack/source");
    }
    function findComp(name) {
        for (var i = 1; i <= app.project.numItems; i++) {
            var item = app.project.item(i);
            if (item instanceof CompItem && item.name === name) return item;
        }
        return null;
    }
    var original = findComp("Hafez Hermes Subscribe");
    var review = findComp("Hafez Hermes Subscribe Review 1");
    if (!original || !review) throw new Error("Both original and Subscribe Review 1 comps are required");
    var seen = {};
    function findSubtitle(comp, result) {
        if (seen[String(comp.id)]) return;
        seen[String(comp.id)] = true;
        for (var li = 1; li <= comp.numLayers; li++) {
            var layer = comp.layer(li);
            if (layer instanceof TextLayer && String(layer.name).indexOf("HAFEZ EDIT ·") !== 0) {
                var prop = layer.property("ADBE Text Properties").property("ADBE Text Document");
                if (prop.expression.indexOf('layer("HAFEZ EDIT · Channel Subtitle")') >= 0) result.push(layer);
            }
            if (layer instanceof AVLayer && layer.source instanceof CompItem) findSubtitle(layer.source, result);
        }
    }
    var sourceMatches = [], reviewMatches = [];
    findSubtitle(original, sourceMatches);
    seen = {};
    findSubtitle(review, reviewMatches);
    if (sourceMatches.length !== 1 || reviewMatches.length !== 1) throw new Error("Expected one bound subtitle per hierarchy");
    var sourceLayer = sourceMatches[0], layer = reviewMatches[0];
    var anchor = layer.property("ADBE Transform Group").property("ADBE Anchor Point");
    if (anchor.expression && anchor.expression.indexOf("HAFEZ_SUBTITLE_ORIGIN_FIX") < 0) {
        throw new Error("Subtitle has an existing anchor expression; inspect it before changing authored logic");
    }
    // Sample the typography on the completed hold, not on each entrance frame:
    // dynamic glyph bounds during the word animator must not cancel its ease.
    var sampleTime = 2;
    var referenceLeft = Number(sourceLayer.sourceRectAtTime(sampleTime, false).left);
    if (!isFinite(referenceLeft)) throw new Error("Invalid original subtitle glyph origin");
    var proofFolder = new Folder(root.fsName + "/proof/ae-elements-audit/subscribe-review-1");
    if (!proofFolder.exists) proofFolder.create();
    var logFile = new File(proofFolder.fsName + "/subtitle-origin-fix.log");
    logFile.encoding = "UTF-8";
    if (!logFile.open("w")) throw new Error("Cannot write subtitle origin log");
    function log(value) { logFile.writeln(String(value)); logFile.close(); logFile.open("a"); }
    app.beginSuppressDialogs();
    app.beginUndoGroup("Repair Subscribe RTL subtitle origin");
    try {
        var beforeRect = layer.sourceRectAtTime(sampleTime, false);
        var beforeAnchor = anchor.valueAtTime(sampleTime, false);
        log("BEFORE | rectLeft=" + beforeRect.left + " | width=" + beforeRect.width + " | anchor=" + beforeAnchor.join(",") + " | referenceLeft=" + referenceLeft);
        anchor.expression =
            '// HAFEZ_SUBTITLE_ORIGIN_FIX: preserve authored keys and Y.\n' +
            'var r=sourceRectAtTime(' + sampleTime + ',false);\n' +
            'var dx=r.left-(' + referenceLeft + ');\n' +
            'value.length>2?[value[0]+dx,value[1],value[2]]:[value[0]+dx,value[1]];';
        var afterAnchor = anchor.valueAtTime(sampleTime, false);
        if (anchor.expressionError) throw new Error(anchor.expressionError);
        var baseAnchor = anchor.valueAtTime(sampleTime, true);
        var alignedOrigin = Number(beforeRect.left) - Number(afterAnchor[0]);
        var expectedOrigin = referenceLeft - Number(baseAnchor[0]);
        if (Math.abs(alignedOrigin - expectedOrigin) > .01) throw new Error("Subtitle origin correction did not match authored reference");
        log("AFTER | anchor=" + afterAnchor.join(",") + " | correctedOrigin=" + alignedOrigin + " | expectedOrigin=" + expectedOrigin);
        var times = [1.2, 2.2, 3.95, 4.2];
        for (var i = 0; i < times.length; i++) {
            review.saveFrameToPng(times[i], new File(proofFolder.fsName + "/frame-fixed-" + String(times[i]).replace(".", "p") + ".png"));
            log("FRAME_OK | " + times[i]);
        }
        var count = review.motionGraphicsTemplateControllerCount;
        app.project.save(app.project.file);
        if (!review.exportAsMotionGraphicsTemplate(true, new Folder(root.fsName + "/motion-pack/dist").fsName)) throw new Error("Review-only export failed");
        log("DONE | controls=" + count + " | canonicalUnchanged=true");
    } catch (error) {
        log("FAILED | " + error.toString());
        throw error;
    } finally {
        logFile.close();
        app.endUndoGroup();
        app.endSuppressDialogs(false);
    }
})();
