/*
 * Force the actual authored Glass Insight panel—not only its EGP controls—onto
 * the Hafez Director UI palette, then export a fresh AE-authored MOGRT.
 */
(function patchGlassInsightGreen() {
    app.beginSuppressDialogs();
    app.beginUndoGroup("Hafez Glass Insight green palette");

    if (!app.project || !app.project.file) throw new Error("Open the curated Hafez AEP first");
    var scriptFolder = new File($.fileName).parent;
    var productRoot = scriptFolder.parent.parent;
    var outputFolder = new Folder(productRoot.fsName + "/motion-pack/dist");
    var proofFolder = new Folder(productRoot.fsName + "/proof/ae-elements-audit");
    if (!outputFolder.exists) outputFolder.create();
    if (!proofFolder.exists) proofFolder.create();
    var logFile = new File(proofFolder.fsName + "/glass-insight-green-patch.log");
    logFile.encoding = "UTF-8";
    logFile.open("w");
    function log(value) { logFile.writeln((new Date()).toUTCString() + " | " + String(value)); }

    var target = null;
    for (var i = 1; i <= app.project.numItems; i++) {
        var item = app.project.item(i);
        if (item instanceof CompItem && item.name === "Hafez Hermes Glass Insight") {
            target = item;
            break;
        }
    }
    if (!target) throw new Error("Hafez Hermes Glass Insight not found");

    var controlName = "HAFEZ · CONTROLS";
    function tokenExpression(token) {
        return "comp(\"Hafez Hermes Glass Insight\").layer(\"" + controlName + "\").effect(\"" + token + "\")(\"Color\")";
    }
    function sliderExpression(name, multiplier) {
        return "clamp(comp(\"Hafez Hermes Glass Insight\").layer(\"" + controlName + "\").effect(\"" + name + "\")(\"Slider\"),0,100)*" + multiplier;
    }

    function setExpression(prop, expression, label) {
        try {
            if (!prop || !prop.canSetExpression) return false;
            prop.expression = expression;
            log("BOUND | " + label);
            return true;
        } catch (error) {
            log("BIND_FAILED | " + label + " | " + error.toString());
            return false;
        }
    }

    function patchGlowEffect(effect, layerName) {
        var changed = 0;
        try {
            var colorsMode = effect.property("ADBE Glo2-0007");
            if (colorsMode) { colorsMode.setValue(2); changed++; }
        } catch (_) {}
        try { if (setExpression(effect.property("ADBE Glo2-0012"), tokenExpression("Sand Accent"), layerName + "/Glow/Color A")) changed++; } catch (_) {}
        try { if (setExpression(effect.property("ADBE Glo2-0013"), tokenExpression("Cool Accent"), layerName + "/Glow/Color B")) changed++; } catch (_) {}
        return changed;
    }

    function patchProperties(group, layerName, semantic, parentMatch) {
        if (!group || !group.numProperties) return 0;
        var changed = 0;
        for (var index = 1; index <= group.numProperties; index++) {
            var prop = group.property(index);
            var match = String(prop.matchName);
            try {
                if (prop.propertyType === PropertyType.PROPERTY) {
                    if (match === "ADBE Vector Stroke Color") {
                        if (setExpression(prop, tokenExpression("Sand Accent"), layerName + "/Stroke")) changed++;
                    } else if (match === "ADBE Vector Fill Color") {
                        var fillToken = semantic === "glow" ? "Sand Accent" : "Glass Surface";
                        if (setExpression(prop, tokenExpression(fillToken), layerName + "/Fill")) changed++;
                    } else if (match === "ADBE Vector Fill Opacity" && semantic === "panel") {
                        if (setExpression(prop, sliderExpression("Glass Opacity", "0.68"), layerName + "/Glass Opacity")) changed++;
                    } else if (match === "outerGlow/color" || match === "innerGlow/color") {
                        if (setExpression(prop, tokenExpression("Sand Accent"), layerName + "/Layer Glow")) changed++;
                    } else if (match === "ADBE Tint-0001" || match === "ADBE Tint-0002") {
                        if (setExpression(prop, tokenExpression("Glass Surface"), layerName + "/Tint")) changed++;
                    } else if (match === "ADBE Tint-0003" && /displacement/i.test(layerName)) {
                        prop.setValue(72);
                        changed++;
                    } else if (prop.propertyValueType === PropertyValueType.COLOR && /(?:deep glow|glow)/i.test(parentMatch || "")) {
                        if (setExpression(prop, tokenExpression("Sand Accent"), layerName + "/Plugin Glow Color")) changed++;
                    }
                } else {
                    changed += patchProperties(prop, layerName, semantic, (parentMatch ? parentMatch + "/" : "") + match + "/" + prop.name);
                }
            } catch (error) {
                log("PROPERTY_FAILED | " + layerName + "/" + prop.name + " | " + error.toString());
            }
        }
        return changed;
    }

    function patchLayer(layer) {
        var name = String(layer.name);
        var semantic = /(?:glow|accent|rotator)/i.test(name) ? "glow" :
            /(?:panel light|panel|glass|displacement)/i.test(name) ? "panel" : "other";
        var changed = 0;
        var effects = layer.property("ADBE Effect Parade");
        for (var i = 1; effects && i <= effects.numProperties; i++) {
            var effect = effects.property(i);
            try {
                if (String(effect.matchName) === "ADBE Glo2") changed += patchGlowEffect(effect, name);
            } catch (_) {}
        }
        changed += patchProperties(effects, name, semantic, "Effects");
        changed += patchProperties(layer.property("ADBE Root Vectors Group"), name, semantic, "Vectors");
        changed += patchProperties(layer.property("ADBE Layer Styles"), name, semantic, "Styles");
        return changed;
    }

    var changed = 0;
    for (var layerIndex = 1; layerIndex <= target.numLayers; layerIndex++) {
        var layer = target.layer(layerIndex);
        var layerName = String(layer.name);
        if (layerName.indexOf("HAFEZ EDIT ·") === 0 || layerName === controlName || layerName === "HAFEZ · LAYOUT") continue;
        if (/^(?:grid(?:\s*\d+)?|color|links|adjustment layer(?:\s*\d+)?|bg)$/i.test(layerName.replace(/^\s+|\s+$/g, ""))) {
            try { layer.enabled = false; } catch (_) {}
            continue;
        }
        changed += patchLayer(layer);
    }

    function patchEditableTextLayer(textLayer, semantic) {
        // The vendor text was parented to a displacement controller. That is
        // useful inside the stock comp, but makes an exposed absolute Layout
        // Position land outside the glass after Premiere overrides it. Keep
        // the vendor text animator, while detaching only the spatial parent so
        // the live title/body share the same coordinate space as the panel.
        try {
            textLayer.parent = null;
            textLayer.blendingMode = BlendingMode.NORMAL;
            changed++;
            log("DETACHED_TEXT_SPATIAL_PARENT | " + textLayer.name);
        } catch (error) {
            log("TEXT_PARENT_DETACH_FAILED | " + textLayer.name + " | " + error.toString());
        }

        // The vendor range selector ends with Animator Opacity=0 and remains
        // selected after Premiere remaps the template duration, leaving only a
        // faint outline. Replace that timing-fragile selector with layer-level
        // eased motion below; text content/style controls remain fully live.
        try {
            var textAnimators = textLayer.property("ADBE Text Properties").property("ADBE Text Animators");
            while (textAnimators.numProperties > 0) textAnimators.property(1).remove();
            changed++;
            log("REMOVED_TIMING_FRAGILE_TEXT_ANIMATORS | " + textLayer.name);
        } catch (error) {
            log("TEXT_ANIMATOR_REMOVE_FAILED | " + textLayer.name + " | " + error.toString());
        }

        try {
            var sourceText = textLayer.property("ADBE Text Properties").property("ADBE Text Document");
            var sourceDocument = sourceText.value;
            sourceDocument.applyFill = true;
            sourceDocument.fillColor = semantic === "title" ? [0.333333, 1.0, 0.447059] : [0.960784, 0.968627, 0.960784];
            sourceText.setValue(sourceDocument);
            changed++;
            log("SET_NATIVE_TEXT_FILL | " + textLayer.name + " | " + semantic);
        } catch (error) {
            log("NATIVE_TEXT_FILL_FAILED | " + textLayer.name + " | " + error.toString());
        }
        function zeroStyleOpacity(group, styleLabel) {
            if (!group || !group.numProperties) return;
            for (var opacityIndex = 1; opacityIndex <= group.numProperties; opacityIndex++) {
                var opacityProperty = group.property(opacityIndex);
                if (/opacity/i.test(String(opacityProperty.name)) || /opacity/i.test(String(opacityProperty.matchName))) {
                    try {
                        opacityProperty.setValue(0);
                        changed++;
                        log("ZEROED_TEXT_STYLE_OPACITY | " + textLayer.name + " | " + styleLabel + "/" + opacityProperty.name);
                    } catch (opacityError) {
                        log("TEXT_STYLE_OPACITY_ZERO_FAILED | " + textLayer.name + " | " + styleLabel + "/" + opacityProperty.name + " | " + opacityError.toString());
                    }
                }
                if (opacityProperty.numProperties) zeroStyleOpacity(opacityProperty, styleLabel + "/" + opacityProperty.name);
            }
        }
        try {
            var layerStyles = textLayer.property("ADBE Layer Styles");
            if (layerStyles) {
                for (var styleIndex = layerStyles.numProperties; styleIndex >= 1; styleIndex--) {
                    var style = layerStyles.property(styleIndex);
                    var styleMatch = String(style.matchName);
                    var keepStyle = styleMatch === "dropShadow/enabled" || styleMatch === "outerGlow/enabled" || styleMatch === "ADBE Blend Options Group";
                    if (!keepStyle) {
                        zeroStyleOpacity(style, String(style.name));
                    }
                }
            }
        } catch (error) {
            log("TEXT_STYLE_CLEANUP_FAILED | " + textLayer.name + " | " + error.toString());
        }

        var fill = null;
        try { fill = textLayer.property("ADBE Effect Parade").property("ADBE Fill"); } catch (_) {}
        if (fill) {
            var colorToken = semantic === "title" ? "Sand Accent" : "Text Primary";
            try {
                if (setExpression(fill.property("ADBE Fill-0002"), tokenExpression(colorToken), textLayer.name + "/Readable Fill")) changed++;
            } catch (_) {}
            try {
                // The stock template shipped with this at 1%, which made the
                // editable copy look like a watermark inside Premiere.
                var fillOpacity = fill.property("ADBE Fill-0005");
                // Adobe exposes percentage controls inconsistently across
                // effects (some are 0..1, others 0..100). Always use the
                // property's declared maximum so the live type is truly 100%.
                fillOpacity.setValue(fillOpacity.maxValue);
                changed++;
                log("SET_TEXT_FILL_OPACITY | " + textLayer.name + " | value=" + fillOpacity.value + " | max=" + fillOpacity.maxValue);
            } catch (error) {
                log("TEXT_FILL_OPACITY_FAILED | " + textLayer.name + " | " + error.toString());
            }
            try {
                // Source Text exposes its own editable color control in
                // Premiere. Disabling the vendor Fill effect prevents the AE
                // MOGRT renderer from multiplying that live color into a faint
                // outline while preserving every editable text-style control.
                fill.enabled = false;
                changed++;
                log("DISABLED_VENDOR_TEXT_FILL | " + textLayer.name);
            } catch (error) {
                log("VENDOR_TEXT_FILL_DISABLE_FAILED | " + textLayer.name + " | " + error.toString());
            }
        }

        // Layout Position/Scale must move the editable type together with the
        // glass plate. The stock layers use off-centre anchors, which makes
        // RTL text escape the panel. Re-centre each live TextDocument and put
        // it on a deterministic title/body rail inside the glass. Existing
        // scale animation is still preserved through value below.
        var transform = textLayer.property("ADBE Transform Group");
        try {
            transform.property("ADBE Anchor Point").expression =
                "var r=sourceRectAtTime(time,false);[r.left+r.width/2,r.top+r.height/2]";
            changed++;
            log("BOUND_TEXT_CENTER_ANCHOR | " + textLayer.name);
        } catch (error) {
            log("TEXT_CENTER_ANCHOR_FAILED | " + textLayer.name + " | " + error.toString());
        }
        try {
            var yOffset = semantic === "title" ? -92 : 42;
            var xOffset = semantic === "title" ? -30 : 30;
            transform.property("ADBE Position").expression =
                "var c=thisComp.layer(\"" + controlName + "\");" +
                "var p=c.effect(\"Layout Position\")(\"Point\");" +
                "var s=c.effect(\"Layout Scale\")(\"Slider\")/100;" +
                "var xIn=ease(time,inPoint,inPoint+.30," + xOffset + ",0);" +
                "var xOut=ease(time,outPoint-.32,outPoint,0," + (-xOffset * 0.6) + ");" +
                "var q=p+[xIn+xOut," + yOffset + "]*s;" +
                "value.length>2?[q[0],q[1],value[2]]:q";
            changed++;
            log("BOUND_TEXT_LAYOUT_POSITION | " + textLayer.name);
        } catch (error) {
            log("TEXT_LAYOUT_POSITION_FAILED | " + textLayer.name + " | " + error.toString());
        }
        try {
            transform.property("ADBE Scale").expression =
                "var s=thisComp.layer(\"" + controlName + "\").effect(\"Layout Scale\")(\"Slider\")/100;" +
                "var a=ease(time,inPoint,inPoint+.30,96,100);" +
                "var b=ease(time,outPoint-.32,outPoint,100,98);" +
                "value*s*Math.min(a,b)/100";
            changed++;
            log("BOUND_TEXT_LAYOUT_SCALE | " + textLayer.name);
        } catch (error) {
            log("TEXT_LAYOUT_SCALE_FAILED | " + textLayer.name + " | " + error.toString());
        }
        try {
            transform.property("ADBE Opacity").expression =
                "Math.min(ease(time,inPoint,inPoint+.22,0,100),ease(time,outPoint-.28,outPoint,100,0))";
            changed++;
            log("BOUND_TEXT_EASED_OPACITY | " + textLayer.name);
        } catch (error) {
            log("TEXT_EASED_OPACITY_FAILED | " + textLayer.name + " | " + error.toString());
        }
    }

    for (var textLayerIndex = 1; textLayerIndex <= target.numLayers; textLayerIndex++) {
        var editableText = target.layer(textLayerIndex);
        if (!(editableText instanceof TextLayer) || !editableText.enabled || String(editableText.name).indexOf("HAFEZ EDIT ·") === 0) continue;
        patchEditableTextLayer(editableText, /good morning/i.test(String(editableText.name)) ? "title" : "body");
    }

    function removeLayerByName(name) {
        try {
            var existing = target.layer(name);
            if (existing) existing.remove();
        } catch (_) {}
    }

    function addRoundedShape(layerName, fillEnabled, glowEnabled) {
        var layer = target.layers.addShape();
        layer.name = layerName;
        var contents = layer.property("ADBE Root Vectors Group");
        var group = contents.addProperty("ADBE Vector Group");
        group.name = "Hafez Glass Panel";
        var vectors = group.property("ADBE Vectors Group");
        var rectangle = vectors.addProperty("ADBE Vector Shape - Rect");
        rectangle.property("ADBE Vector Rect Size").setValue([720, 380]);
        rectangle.property("ADBE Vector Rect Roundness").setValue(72);

        if (fillEnabled) {
            var fill = vectors.addProperty("ADBE Vector Graphic - Fill");
            fill.property("ADBE Vector Fill Color").expression = tokenExpression("Glass Surface");
            fill.property("ADBE Vector Fill Opacity").expression =
                "clamp(thisComp.layer(\"" + controlName + "\").effect(\"Glass Opacity\")(\"Slider\"),0,100)";
        }

        var stroke = vectors.addProperty("ADBE Vector Graphic - Stroke");
        stroke.property("ADBE Vector Stroke Color").expression = tokenExpression("Sand Accent");
        stroke.property("ADBE Vector Stroke Opacity").setValue(glowEnabled ? 88 : 72);
        stroke.property("ADBE Vector Stroke Width").setValue(glowEnabled ? 3.2 : 2.2);

        var transform = layer.property("ADBE Transform Group");
        transform.property("ADBE Position").expression =
            "thisComp.layer(\"" + controlName + "\").effect(\"Layout Position\")(\"Point\")";
        transform.property("ADBE Scale").expression =
            "var s=thisComp.layer(\"" + controlName + "\").effect(\"Layout Scale\")(\"Slider\");" +
            "var a=ease(time,inPoint,inPoint+.28,92,100);" +
            "var b=ease(time,outPoint-.30,outPoint,100,96);" +
            "var k=Math.min(a,b);[s*k/100,s*k/100]";
        transform.property("ADBE Opacity").expression =
            "Math.min(ease(time,inPoint,inPoint+.22,0,100),ease(time,outPoint-.28,outPoint,100,0))";

        if (glowEnabled) {
            try {
                var glow = layer.property("ADBE Effect Parade").addProperty("ADBE Glo2");
                glow.name = "HAFEZ · GREEN GLOW";
                glow.property("ADBE Glo2-0001").setValue(2);
                glow.property("ADBE Glo2-0002").setValue(42);
                glow.property("ADBE Glo2-0003").expression =
                    "thisComp.layer(\"" + controlName + "\").effect(\"Glow Radius\")(\"Slider\")";
                glow.property("ADBE Glo2-0004").expression =
                    "thisComp.layer(\"" + controlName + "\").effect(\"Glow Intensity\")(\"Slider\")/30";
                glow.property("ADBE Glo2-0007").setValue(1);
            } catch (error) { log("NATIVE_GLOW_FAILED | " + error.toString()); }
        }

        var lastText = null;
        for (var textIndex = 1; textIndex <= target.numLayers; textIndex++) {
            var candidate = target.layer(textIndex);
            if (candidate instanceof TextLayer && candidate.enabled && String(candidate.name).indexOf("HAFEZ EDIT ·") !== 0) {
                if (!lastText || candidate.index > lastText.index) lastText = candidate;
            }
        }
        if (lastText) layer.moveAfter(lastText);
        return layer;
    }

    // The vendor rotator and light passes sample the underlying footage and can
    // turn magenta over skin/blue studio shots. Preserve the displacement and
    // shadow, but replace those four color passes with a controlled Hafez glass
    // plate and an AE-native green glow.
    var legacyColorPasses = ["Panel Light 2", "Panel Light", "Glow Rotator", "Glow 2"];
    for (var legacyIndex = 0; legacyIndex < legacyColorPasses.length; legacyIndex++) {
        try {
            var legacy = target.layer(legacyColorPasses[legacyIndex]);
            if (legacy) {
                legacy.enabled = false;
                log("DISABLED_LEGACY_COLOR_PASS | " + legacy.name);
            }
        } catch (_) {}
    }
    removeLayerByName("HAFEZ · BRAND GLASS");
    removeLayerByName("HAFEZ · BRAND GLOW");
    addRoundedShape("HAFEZ · BRAND GLASS", true, false);
    addRoundedShape("HAFEZ · BRAND GLOW", false, true);

    // Keep editable typography above every displacement/light/shadow pass.
    // The original stack contains several full-panel blend layers; placing the
    // live type at the top prevents those passes from washing it out in the
    // Premiere renderer while retaining the authored reveal animator.
    var editableTextLayers = [];
    for (var collectIndex = 1; collectIndex <= target.numLayers; collectIndex++) {
        var collectLayer = target.layer(collectIndex);
        if (collectLayer instanceof TextLayer && collectLayer.enabled && String(collectLayer.name).indexOf("HAFEZ EDIT ·") !== 0) {
            editableTextLayers.push(collectLayer);
        }
    }
    for (var raiseIndex = editableTextLayers.length - 1; raiseIndex >= 0; raiseIndex--) {
        var raiseLayer = editableTextLayers[raiseIndex];
        if (raiseLayer) {
            try {
                raiseLayer.moveToBeginning();
                changed++;
                log("RAISED_EDITABLE_TEXT | " + raiseLayer.name);
            } catch (error) {
                log("RAISE_EDITABLE_TEXT_FAILED | " + raiseLayer.name + " | " + error.toString());
            }
        }
    }

    // Keep the panel glassy but stop the underlying warm/blue footage from
    // dominating the brand tint. The glow remains authored and animated.
    var controlEffects = target.layer(controlName).property("ADBE Effect Parade");
    try { controlEffects.property("Glass Opacity").property(1).setValue(68); } catch (_) {}
    try { controlEffects.property("Glow Intensity").property(1).setValue(24); } catch (_) {}
    try { controlEffects.property("Glow Radius").property(1).setValue(20); } catch (_) {}
    try { controlEffects.property("Show Background").property(1).setValue(0); } catch (_) {}

    // A versioned EGP name forces Premiere to invalidate its persistent MOGRT
    // render cache; overwriting a file with the same internal template name can
    // otherwise keep showing an older AE render after an application restart.
    target.motionGraphicsTemplateName = target.name + " v7";
    app.project.save(app.project.file);
    var ok = target.exportAsMotionGraphicsTemplate(true, outputFolder.fsName);
    log("DONE | ok=" + ok + " | changed=" + changed);
    logFile.close();
    app.endUndoGroup();
    app.endSuppressDialogs(false);
})();
