/*
 * Repair the user's authored Subscribe MOGRT without replacing its artwork.
 * Operates only on an owned, backed-up motion-pack/source AEP; duplicates the
 * full source hierarchy and exports a NEW review asset, never the canonical.
 * Real text mutation, native font/size/color edits and timing still require
 * Premiere QA before promotion. Duration Seconds must match the cue length.
 */
(function buildSubscribeReview1() {
    var productRoot = new File($.fileName).parent.parent.parent;
    function pathKey(value) { return String(value).replace(/\\/g, "/").replace(/\/$/, "").toLowerCase(); }
    var ownedPrefix = pathKey(new Folder(productRoot.fsName + "/motion-pack/source").fsName) + "/";
    if (!app.project || !app.project.file || pathKey(app.project.file.fsName).indexOf(ownedPrefix) !== 0 || !/\.aep$/i.test(app.project.file.fsName)) {
        throw new Error("Open the backed-up HafezStudio-owned AEP in motion-pack/source");
    }
    var SOURCE = "Hafez Hermes Subscribe";
    var TARGET = "Hafez Hermes Subscribe Review 1";
    var originalFile = app.project.file;
    var outputFolder = new Folder(productRoot.fsName + "/motion-pack/dist");
    var proofFolder = new Folder(productRoot.fsName + "/proof/ae-elements-audit/subscribe-review-1");
    if (!outputFolder.exists) outputFolder.create();
    if (!proofFolder.exists) proofFolder.create();
    var logFile = new File(proofFolder.fsName + "/build.log");
    logFile.encoding = "UTF-8";
    if (!logFile.open("w")) throw new Error("Cannot open Subscribe review log");
    function log(value) { logFile.writeln((new Date()).toUTCString() + " | " + String(value)); logFile.close(); logFile.open("a"); }
    function findComp(name) {
        for (var i = 1; i <= app.project.numItems; i++) {
            var item = app.project.item(i);
            if (item instanceof CompItem && item.name === name) return item;
        }
        return null;
    }
    function quote(value) { return String(value).replace(/\\/g, "\\\\").replace(/\"/g, "\\\""); }
    var source = findComp(SOURCE);
    if (!source) throw new Error("Missing authored Subscribe comp");
    if (findComp(TARGET)) throw new Error("Subscribe Review 1 already exists; inspect it before another build");
    var slots = [
        { name: "Channel Name", text: "Hafez-fx", font: "AbarHighFaNum-Black", rtl: false },
        { name: "Channel Subtitle", text: "حافظ پیروی", font: "AbarHighFaNum-ExtraBold", rtl: true },
        { name: "CTA Text", text: "سابسکرایب کن", font: "AbarHighFaNum-ExtraBold", rtl: true }
    ];
    function rgb(hex) { return [parseInt(hex.substr(0, 2), 16) / 255, parseInt(hex.substr(2, 2), 16) / 255, parseInt(hex.substr(4, 2), 16) / 255]; }
    var tokens = {
        "Glass Surface": rgb("0A0C0B"), "Sand Accent": rgb("55FF72"),
        "Cool Accent": rgb("2FD65B"), "Champagne Border": rgb("B6FFC1"),
        "Text Primary": rgb("F5F7F5"), "Background Color": rgb("020303"),
        "Channel Name · Text Color": rgb("55FF72"),
        "Channel Subtitle · Text Color": rgb("F5F7F5"),
        "CTA Text · Text Color": rgb("F5F7F5")
    };
    app.beginSuppressDialogs();
    app.beginUndoGroup("Hafez Subscribe Unicode and responsive cue review");
    try {
        var memo = {}, pairs = [];
        function duplicateHierarchy(comp) {
            var key = String(comp.id);
            if (memo[key]) return memo[key];
            var copy = comp.duplicate();
            copy.name = comp === source ? TARGET : "HAFEZ SUB R1 " + key + " · " + comp.name;
            memo[key] = copy;
            pairs.push({ original: comp.name, copy: copy });
            for (var li = 1; li <= copy.numLayers; li++) {
                var layer = copy.layer(li);
                if (layer instanceof AVLayer && layer.source instanceof CompItem) layer.replaceSource(duplicateHierarchy(layer.source), false);
            }
            return copy;
        }
        var review = duplicateHierarchy(source);
        function walkProperties(group, callback) {
            for (var pi = 1; pi <= group.numProperties; pi++) {
                var prop = group.property(pi);
                if (prop.propertyType === PropertyType.PROPERTY) callback(prop);
                else walkProperties(prop, callback);
            }
        }
        for (var ci = 0; ci < pairs.length; ci++) {
            for (var li = 1; li <= pairs[ci].copy.numLayers; li++) {
                walkProperties(pairs[ci].copy.layer(li), function (prop) {
                    if (!prop.canSetExpression || !prop.expression) return;
                    var expr = prop.expression;
                    for (var ni = 0; ni < pairs.length; ni++) {
                        expr = expr.split('comp("' + quote(pairs[ni].original) + '")').join('comp("' + quote(pairs[ni].copy.name) + '")');
                    }
                    if (expr !== prop.expression) prop.expression = expr;
                });
            }
        }
        log("PRIVATE_HIERARCHY | comps=" + pairs.length);
        var rig = review.layer("HAFEZ · CONTROLS");
        if (!rig) throw new Error("Missing authored Hafez rig");
        for (var token in tokens) if (tokens.hasOwnProperty(token)) {
            var control = rig.property("ADBE Effect Parade").property(token);
            if (!control) throw new Error("Missing color control " + token);
            control.property(1).setValue(tokens[token]);
        }
        rig.property("ADBE Effect Parade").property("Show Background").property(1).setValue(0);
        try { review.layer("HAFEZ · OPTIONAL BACKGROUND").enabled = false; } catch (_) {}

        function setUnicodeDocument(prop, slot) {
            var expression = prop.expression;
            if (expression) prop.expression = "";
            var doc = prop.value;
            doc.text = slot.text;
            doc.font = slot.font;
            doc.composerEngine = ComposerEngine.UNIVERSAL_TYPE_ENGINE;
            doc.direction = slot.rtl ? ParagraphDirection.DIRECTION_RIGHT_TO_LEFT : ParagraphDirection.DIRECTION_LEFT_TO_RIGHT;
            try { doc.digitSet = slot.rtl ? DigitSet.FARSI_DIGITS : DigitSet.DEFAULT_DIGITS; } catch (_) {}
            doc.applyFill = true;
            doc.fillColor = tokens[slot.name + " · Text Color"];
            prop.setValue(doc);
            if (expression) prop.expression = expression;
        }
        for (var si = 0; si < slots.length; si++) {
            var controllerLayer = review.layer("HAFEZ EDIT · " + slots[si].name);
            if (!(controllerLayer instanceof TextLayer)) throw new Error("Missing controller " + slots[si].name);
            setUnicodeDocument(controllerLayer.property("ADBE Text Properties").property("ADBE Text Document"), slots[si]);
        }

        // The old curation incorrectly assigned its Fill Color expression to
        // Fill Mask (property 1). Only repair Hafez-owned effects/bindings; the
        // user's other effect parameters, masks and animation remain intact.
        function fillColorProperty(effect) {
            var color = null;
            try { color = effect.property("Color"); } catch (_) {}
            if (color && color.propertyValueType === PropertyValueType.COLOR) return color;
            color = null;
            for (var pi = 1; pi <= effect.numProperties; pi++) {
                var prop = effect.property(pi);
                if (prop.propertyValueType === PropertyValueType.COLOR) {
                    if (color && color !== prop) throw new Error("Ambiguous Fill Color property");
                    color = prop;
                }
            }
            if (!color) throw new Error("Missing actual Fill Color property");
            return color;
        }
        var visible = [], colorRepairs = 0;
        for (var ci = 0; ci < pairs.length; ci++) {
            var comp = pairs[ci].copy;
            for (var li = 1; li <= comp.numLayers; li++) {
                var layer = comp.layer(li);
                var boundSlot = null;
                if (layer instanceof TextLayer && String(layer.name).indexOf("HAFEZ EDIT ·") !== 0) {
                    var text = layer.property("ADBE Text Properties").property("ADBE Text Document");
                    for (var si = 0; si < slots.length; si++) {
                        if (text.expression.indexOf('layer("HAFEZ EDIT · ' + slots[si].name + '")') >= 0) boundSlot = slots[si];
                    }
                    if (boundSlot) {
                        setUnicodeDocument(text, boundSlot);
                        // Preserve the existing style-control expression but
                        // retrieve the current style rather than a time-0 style.
                        text.expression = text.expression.replace(/getStyleAt\(0,\s*0\)/g, "getStyleAt(0,time)");
                        visible.push({ comp: comp, layer: layer, slot: boundSlot });
                    }
                }
                var effects = layer.property("ADBE Effect Parade");
                if (!effects) continue;
                for (var ei = 1; ei <= effects.numProperties; ei++) {
                    var effect = effects.property(ei);
                    if (effect.matchName !== "ADBE Fill") continue;
                    var color = fillColorProperty(effect);
                    var first = effect.property(1);
                    var ownedEffect = String(effect.name).indexOf("HAFEZ ·") === 0;
                    var oldExpression = first.canSetExpression ? String(first.expression || "") : "";
                    var ownedMaskBinding = ownedEffect && oldExpression.indexOf("HAFEZ · CONTROLS") >= 0;
                    if (ownedMaskBinding) {
                        first.expression = "";
                        color.expression = oldExpression;
                        colorRepairs++;
                    } else if (ownedEffect && !color.expression) {
                        var fillToken = /BACKGROUND/.test(effect.name) ? "Background Color" : "Glass Surface";
                        color.expression = 'comp("' + quote(TARGET) + '").layer("HAFEZ · CONTROLS").effect("' + fillToken + '")("Color")';
                        colorRepairs++;
                    }
                    if (boundSlot && color.expression && color.expression.indexOf("HAFEZ · CONTROLS") >= 0) {
                        color.expression = 'comp("' + quote(TARGET) + '").layer("HAFEZ · CONTROLS").effect("' + quote(boundSlot.name + " · Text Color") + '")("Color")';
                    }
                }
            }
        }
        log("UNICODE_BINDINGS | visible=" + visible.length + " | fillRepairs=" + colorRepairs);
        if (visible.length !== 3) throw new Error("Expected exactly three bound visible text layers, got " + visible.length);

        // Keep the authored entry (including its staggered name/subtitle/CTA),
        // map the hold to the actual cue length, then play the authored tail.
        // A final opacity ease ensures that every vendor pass leaves cleanly.
        var containerDuration = 30, defaultDuration = 4.2;
        review.duration = containerDuration;
        review.workAreaStart = 0;
        review.workAreaDuration = defaultDuration;
        var durationControl = rig.property("ADBE Effect Parade").addProperty("ADBE Slider Control");
        durationControl.name = "Duration Seconds";
        durationControl.property(1).setValue(defaultDuration);
        if (!rig.property("ADBE Effect Parade").property("Duration Seconds").property(1).addToMotionGraphicsTemplateAs(review, "Duration Seconds")) {
            throw new Error("Cannot expose Duration Seconds");
        }
        var retimed = 0;
        for (var li = 1; li <= review.numLayers; li++) {
            var layer = review.layer(li);
            if (!(layer instanceof AVLayer) || !(layer.source instanceof CompItem) || !layer.enabled) continue;
            var duration = Number(layer.source.duration), frame = Number(layer.source.frameDuration);
            if (duration < 2.4) throw new Error("Unexpected short authored Subscribe source");
            layer.timeRemapEnabled = true;
            layer.outPoint = containerDuration;
            layer.property("ADBE Time Remapping").expression =
                'var d=Math.max(3.2,Math.min(thisComp.duration,thisComp.layer("HAFEZ · CONTROLS").effect("Duration Seconds")("Slider")));\n' +
                'var sourceEnd=' + duration + ', head=1.7, tail=.6;\n' +
                'var t=Math.max(0,time-inPoint), mapped;\n' +
                'if(t<head){mapped=t;}else if(t>=d-tail){mapped=sourceEnd-tail+(t-(d-tail));}' +
                'else{mapped=head+(t-head)*(sourceEnd-head-tail)/(d-head-tail);}\n' +
                'Math.max(0,Math.min(sourceEnd-' + frame + ',mapped));';
            var opacity = layer.property("ADBE Transform Group").property("ADBE Opacity");
            if (opacity.expression) throw new Error("Unexpected root opacity expression; refusing to replace authored logic");
            opacity.expression =
                'var d=Math.max(3.2,Math.min(thisComp.duration,thisComp.layer("HAFEZ · CONTROLS").effect("Duration Seconds")("Slider")));' +
                'value*Math.min(ease(time,inPoint,inPoint+.18,0,1),ease(time,d-.36,d,1,0));';
            retimed++;
        }
        if (retimed !== 1) throw new Error("Expected one authored Subscribe render layer, got " + retimed);
        review.motionGraphicsTemplateName = TARGET;

        // Fail the build on actual evaluated-text mismatch, not just control
        // labels. These checks are AE evidence, not a claim of Premiere QA.
        for (var vi = 0; vi < visible.length; vi++) {
            var entry = visible[vi];
            var prop = entry.layer.property("ADBE Text Properties").property("ADBE Text Document");
            var evaluated = prop.valueAtTime(2, false);
            if (String(evaluated.text) !== entry.slot.text) throw new Error("Rendered binding mismatch: " + entry.slot.name + " => " + evaluated.text);
            if (prop.expressionError) throw new Error("Text expression failed: " + entry.slot.name + " | " + prop.expressionError);
            if (evaluated.direction !== (entry.slot.rtl ? ParagraphDirection.DIRECTION_RIGHT_TO_LEFT : ParagraphDirection.DIRECTION_LEFT_TO_RIGHT)) {
                throw new Error("Incorrect evaluated text direction: " + entry.slot.name);
            }
            log("EVALUATED_TEXT_OK | " + entry.slot.name + " | " + evaluated.text + " | font=" + evaluated.font + " | size=" + evaluated.fontSize);
        }
        var errors = [];
        for (var ci = 0; ci < pairs.length; ci++) {
            var comp = pairs[ci].copy;
            for (var li = 1; li <= comp.numLayers; li++) {
                var layer = comp.layer(li);
                walkProperties(layer, function (prop) {
                    if (prop.canSetExpression && prop.expression && prop.expressionError) errors.push(prop.name + ": " + prop.expressionError);
                });
            }
        }
        if (errors.length) throw new Error("Expression errors: " + errors.join(" | "));
        var count = review.motionGraphicsTemplateControllerCount;
        if (count < 25) throw new Error("Expected 24 existing controls plus duration, got " + count);
        var previewTimes = [0, 1.2, 2.2, 3.95, 4.2];
        for (var pi = 0; pi < previewTimes.length; pi++) {
            var time = previewTimes[pi];
            review.saveFrameToPng(time, new File(proofFolder.fsName + "/frame-" + String(time).replace(".", "p") + ".png"));
            log("FRAME_OK | " + time);
        }
        app.project.save(originalFile);
        if (!review.exportAsMotionGraphicsTemplate(true, outputFolder.fsName)) throw new Error("Subscribe review export returned false");
        log("DONE | controls=" + count + " | defaultDuration=" + defaultDuration + " | containerDuration=" + containerDuration);
    } catch (error) {
        log("FAILED | " + error.toString());
        throw error;
    } finally {
        logFile.close();
        app.endUndoGroup();
        app.endSuppressDialogs(false);
    }
})();
