/*
 * Review 8: preserve the approved Review 7 artwork, repair editor controls and
 * make the authored entrance/exit survive a shorter Premiere cue.
 *
 * Run against a backed-up HafezStudio-owned AEP only. This script duplicates
 * the complete Review 7 hierarchy, retargets expression references to those
 * private copies, and exports a NEW Review 8 MOGRT. It neither edits Review 7
 * nor replaces the canonical MOGRT. Native Premiere render QA is still needed
 * before promotion. The Finisher must set Duration Seconds to the cue length;
 * merely trimming this 30-second container is not a responsive-timing test.
 */
(function buildGlassInsightReview8() {
    var scriptFolder = new File($.fileName).parent;
    var productRoot = scriptFolder.parent.parent;
    var ownedFolder = new Folder(productRoot.fsName + "/motion-pack/source");
    function normalizedPath(value) {
        return String(value).replace(/\\/g, "/").replace(/\/$/, "").toLowerCase();
    }
    if (!app.project || !app.project.file) throw new Error("Open the backed-up curated Hafez AEP first");
    var projectPath = normalizedPath(app.project.file.fsName);
    var ownedPrefix = normalizedPath(ownedFolder.fsName) + "/";
    if (projectPath.indexOf(ownedPrefix) !== 0 || !/\.aep$/i.test(projectPath)) {
        throw new Error("Refusing to modify an AEP outside HafezStudio/motion-pack/source");
    }

    var SOURCE = "Hafez Hermes Glass Insight Review 7";
    var TARGET = "Hafez Hermes Glass Insight Review 8";
    var outputFolder = new Folder(productRoot.fsName + "/motion-pack/dist");
    var proofFolder = new Folder(productRoot.fsName + "/proof/ae-elements-audit");
    if (!outputFolder.exists) outputFolder.create();
    if (!proofFolder.exists) proofFolder.create();
    var logFile = new File(proofFolder.fsName + "/glass-insight-review-8-build.log");
    logFile.encoding = "UTF-8";
    if (!logFile.open("w")) throw new Error("Cannot open Review 8 build log");
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
    function quote(value) { return String(value).replace(/\\/g, "\\\\").replace(/\"/g, "\\\""); }
    var source = findComp(SOURCE);
    if (!source) throw new Error("Missing approved source comp: " + SOURCE);
    if (findComp(TARGET)) throw new Error("Review 8 already exists; inspect it instead of silently overwriting it");

    app.beginSuppressDialogs();
    app.beginUndoGroup("Hafez Glass Review 8 editable controls and cue timing");
    var originalProjectFile = app.project.file;
    try {
        // Duplicate every nested comp. Patching the original source rig would
        // otherwise redirect Review 7's controls to Review 8 as a side effect.
        var duplicates = {};
        var pairs = [];
        function duplicateHierarchy(comp) {
            var key = String(comp.id);
            if (duplicates[key]) return duplicates[key];
            var copy = comp.duplicate();
            copy.name = comp === source ? TARGET : "HAFEZ R8 " + key + " · " + comp.name;
            duplicates[key] = copy;
            pairs.push({ original: comp.name, copy: copy });
            for (var li = 1; li <= copy.numLayers; li++) {
                var layer = copy.layer(li);
                if (layer instanceof AVLayer && layer.source instanceof CompItem) {
                    layer.replaceSource(duplicateHierarchy(layer.source), false);
                }
            }
            return copy;
        }
        var wrapper = duplicateHierarchy(source);
        function patchExpressionReferences(group) {
            for (var pi = 1; pi <= group.numProperties; pi++) {
                var prop = group.property(pi);
                if (prop.propertyType !== PropertyType.PROPERTY) {
                    patchExpressionReferences(prop);
                    continue;
                }
                if (!prop.canSetExpression || !prop.expression) continue;
                var expr = prop.expression;
                for (var ni = 0; ni < pairs.length; ni++) {
                    // Exact comp() reference replacement, not arbitrary layer
                    // names or user text. Existing scripts use double quotes.
                    var oldRef = 'comp("' + quote(pairs[ni].original) + '")';
                    var newRef = 'comp("' + quote(pairs[ni].copy.name) + '")';
                    expr = expr.split(oldRef).join(newRef);
                }
                if (expr !== prop.expression) prop.expression = expr;
            }
        }
        for (var ci = 0; ci < pairs.length; ci++) {
            for (var li = 1; li <= pairs[ci].copy.numLayers; li++) patchExpressionReferences(pairs[ci].copy.layer(li));
        }
        log("PRIVATE_HIERARCHY | comps=" + pairs.length);

        var controls = wrapper.layer("HAFEZ · CONTROLS");
        var panel = wrapper.layer("HAFEZ · AUTHORED GLASS / GLOW / SHADOW");
        if (!controls || !panel || !(panel.source instanceof CompItem)) throw new Error("Unexpected Review 7 structure");
        var authoredDuration = Number(panel.source.duration);
        var authoredFrame = Number(panel.source.frameDuration);
        var containerDuration = 30;
        var defaultDuration = Math.min(containerDuration, Math.max(1.6, authoredDuration));
        wrapper.duration = containerDuration;
        wrapper.workAreaStart = 0;
        wrapper.workAreaDuration = defaultDuration;
        wrapper.motionGraphicsTemplateName = TARGET;

        var newNames = [];
        function addControl(name, matchName, value) {
            var effect = controls.property("ADBE Effect Parade").addProperty(matchName);
            effect.name = name;
            effect.property(1).setValue(value);
            newNames.push(name);
        }
        addControl("Duration Seconds", "ADBE Slider Control", defaultDuration);

        // Keep font, size, direction, justification and the owner's text layer
        // animation. The expression starts from the layer's current text style
        // (including Premiere font/size overrides), changing only these three
        // explicitly exposed attributes. There is no baked-font replacement.
        var slots = ["Title", "Body"];
        for (var si = 0; si < slots.length; si++) {
            var slot = slots[si];
            var textLayer = wrapper.layer("HAFEZ EDIT · " + slot.toUpperCase());
            if (!(textLayer instanceof TextLayer)) throw new Error("Missing live " + slot + " layer");
            var sourceText = textLayer.property("ADBE Text Properties").property("ADBE Text Document");
            var doc = sourceText.value;
            var leading = Number(doc.leading);
            if (!isFinite(leading) || leading < 1) leading = Number(doc.fontSize) * 1.18;
            var tracking = Number(doc.tracking);
            if (!isFinite(tracking)) tracking = 0;
            addControl(slot + " · Text Color", "ADBE Color Control", doc.fillColor);
            addControl(slot + " · Line Spacing", "ADBE Slider Control", leading);
            addControl(slot + " · Tracking", "ADBE Slider Control", tracking);
            // Resolve again after effects are added: AE invalidates some
            // Property objects when an indexed group is modified.
            sourceText = wrapper.layer("HAFEZ EDIT · " + slot.toUpperCase()).property("ADBE Text Properties").property("ADBE Text Document");
            sourceText.expression =
                'var rig=thisComp.layer("HAFEZ · CONTROLS");\n' +
                'var editable=text.sourceText;\n' +
                'editable.getStyleAt(0,time).setText(value.toString()).setApplyFill(true)' +
                '.setFillColor(rig.effect("' + quote(slot + " · Text Color") + '")("Color"))' +
                '.setAutoLeading(false)' +
                '.setLeading(Math.max(1,rig.effect("' + quote(slot + " · Line Spacing") + '")("Slider")))' +
                '.setTracking(rig.effect("' + quote(slot + " · Tracking") + '")("Slider"));';
            if (sourceText.expressionError) throw new Error(slot + " style expression: " + sourceText.expressionError);

            textLayer.outPoint = containerDuration;
            var tx = textLayer.property("ADBE Transform Group");
            var animatedNames = ["ADBE Position", "ADBE Scale", "ADBE Opacity"];
            for (var ai = 0; ai < animatedNames.length; ai++) {
                var animated = tx.property(animatedNames[ai]);
                if (!animated.expression || animated.expression.indexOf("outPoint") < 0) {
                    throw new Error("Missing expected Review 7 ease-out expression: " + slot + "/" + animatedNames[ai]);
                }
                animated.expression =
                    'var hafezDuration=Math.max(1.6,Math.min(thisComp.duration,thisComp.layer("HAFEZ · CONTROLS").effect("Duration Seconds")("Slider")));\n' +
                    animated.expression.replace(/\boutPoint\b/g, "hafezDuration");
                if (animated.expressionError) throw new Error(slot + " timing expression: " + animated.expressionError);
            }
            log("LIVE_STYLE_AND_OUTRO | " + slot + " | leading=" + leading + " | tracking=" + tracking);
        }

        // Fixed-speed authored head/tail and time-remapped hold. The original
        // nested composition keeps all glass/shadow/glow effects and curves.
        // A wrapper opacity ease guarantees transparent first/last cue frames
        // even if one vendor render pass has no authored fade-out of its own.
        panel.timeRemapEnabled = true;
        panel.outPoint = containerDuration;
        panel.property("ADBE Time Remapping").expression =
            'var d=Math.max(1.6,Math.min(thisComp.duration,thisComp.layer("HAFEZ · CONTROLS").effect("Duration Seconds")("Slider")));\n' +
            'var sourceEnd=' + authoredDuration + ', head=.65, tail=.48;\n' +
            'var t=Math.max(0,time-inPoint), mapped;\n' +
            'if(t<head){mapped=t;}else if(t>=d-tail){mapped=sourceEnd-tail+(t-(d-tail));}' +
            'else{mapped=head+(t-head)*(sourceEnd-head-tail)/(d-head-tail);}\n' +
            'Math.max(0,Math.min(sourceEnd-' + authoredFrame + ',mapped));';
        panel.property("ADBE Transform Group").property("ADBE Opacity").expression =
            'var d=Math.max(1.6,Math.min(thisComp.duration,thisComp.layer("HAFEZ · CONTROLS").effect("Duration Seconds")("Slider")));' +
            'value*Math.min(ease(time,inPoint,inPoint+.22,0,1),ease(time,d-.28,d,1,0));';
        if (panel.property("ADBE Time Remapping").expressionError) throw new Error("Panel time-remap expression failed");

        for (var ei = 0; ei < newNames.length; ei++) {
            var exposed = controls.property("ADBE Effect Parade").property(newNames[ei]).property(1);
            if (!exposed.addToMotionGraphicsTemplateAs(wrapper, newNames[ei])) {
                throw new Error("Could not expose " + newNames[ei]);
            }
        }
        // Count before export; export can invalidate CompItem handles in AE.
        var count = wrapper.motionGraphicsTemplateControllerCount;
        if (count < 21) throw new Error("Expected Review 7's 14 controls plus 7 new controls, got " + count);
        app.project.save(originalProjectFile);
        var ok = wrapper.exportAsMotionGraphicsTemplate(true, outputFolder.fsName);
        if (!ok) throw new Error("Review 8 export returned false");
        log("DONE | controllers=" + count + " | authoredDuration=" + authoredDuration + " | containerDuration=" + containerDuration + " | defaultDuration=" + defaultDuration);
    } catch (error) {
        log("FAILED | " + error.toString());
        throw error;
    } finally {
        logFile.close();
        app.endUndoGroup();
        app.endSuppressDialogs(false);
    }
})();
