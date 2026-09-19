/* Patch already-curated Hafez MOGRT comps without rebuilding the source tree.
 *
 * Premiere QA found that some vendor comps use an unnamed, light, full-frame
 * solid.  Those plates survived the first dark-background-only filter and hid
 * both the footage and the editable text.  Overlay templates must keep only
 * masked/scaled graphic solids; the explicit HAFEZ optional background remains
 * the sole full-frame plate controlled by Show Background.
 */
(function patchCuratedOverlayBackgrounds() {
    app.beginSuppressDialogs();
    app.beginUndoGroup("Patch Hafez overlay backgrounds");

    if (!app.project || !app.project.file) throw new Error("Open the curated Hafez AEP first");
    var scriptFolder = new File($.fileName).parent;
    var productRoot = scriptFolder.parent.parent;
    var outputFolder = new Folder(productRoot.fsName + "/motion-pack/dist");
    var proofFolder = new Folder(productRoot.fsName + "/proof/ae-elements-audit");
    if (!outputFolder.exists) outputFolder.create();
    if (!proofFolder.exists) proofFolder.create();

    var logFile = new File(proofFolder.fsName + "/overlay-background-patch.log");
    logFile.encoding = "UTF-8";
    logFile.open("w");
    function log(value) {
        var line = (new Date()).toUTCString() + " | " + String(value);
        try { logFile.writeln(line); logFile.flush(); } catch (_) {}
        $.writeln(line);
    }

    function findComp(name) {
        for (var index = 1; index <= app.project.numItems; index++) {
            var item = app.project.item(index);
            if (item instanceof CompItem && item.name === name) return item;
        }
        return null;
    }

    function isOpaqueFullFrameSolid(layer, c) {
        try {
            if (!layer.source || !(layer.source.mainSource instanceof SolidSource)) return false;
            if (String(layer.name).indexOf("HAFEZ ·") === 0) return false;
            if (layer.adjustmentLayer) return false;
            var masks = layer.property("ADBE Mask Parade");
            if (masks && masks.numProperties > 0) return false;
            // Full-frame solids are also commonly used as adjustment, grid,
            // tint and link-effect carriers.  Preserve those authored layers;
            // only remove a layer whose name explicitly identifies a plate.
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

    function patchHierarchy(c, visited) {
        var key = String(c.id);
        if (visited[key]) return 0;
        visited[key] = true;
        var disabled = 0;
        for (var index = c.numLayers; index >= 1; index--) {
            var layer = c.layer(index);
            var isAuthoredOptionalPlate = String(layer.name) === "HAFEZ · OPTIONAL BACKGROUND";
            if (isAuthoredOptionalPlate || isOpaqueFullFrameSolid(layer, c)) {
                try {
                    layer.enabled = false;
                    disabled++;
                    log("DISABLED_PLATE | " + c.name + " | " + layer.name);
                } catch (_) {}
            }
            try {
                if (layer.source instanceof CompItem) disabled += patchHierarchy(layer.source, visited);
            } catch (_) {}
        }
        return disabled;
    }

    function disableTopLevelFootageCarriers(c) {
        var disabled = 0;
        for (var index = c.numLayers; index >= 1; index--) {
            var layer = c.layer(index);
            var name = String(layer.name).replace(/^\s+|\s+$/g, "");
            // These vendor layers colorize or draw a grid across the whole
            // composition.  They look correct over the vendor demo plate but
            // contaminate arbitrary user footage.  The actual glass panel,
            // panel lights, shadow, displacement and authored glow remain.
            if (/^(?:grid(?:\s*\d+)?|color|links|adjustment layer(?:\s*\d+)?)$/i.test(name)) {
                try {
                    layer.enabled = false;
                    disabled++;
                    log("DISABLED_FOOTAGE_CARRIER | " + c.name + " | " + layer.name);
                } catch (_) {}
            }
        }
        return disabled;
    }

    function syncDirectorPalette(c) {
        var control = null;
        try { control = c.layer("HAFEZ · CONTROLS"); } catch (_) {}
        if (!control) return 0;
        var colors = {
            "Glass Surface": [10 / 255, 12 / 255, 11 / 255],
            "Sand Accent": [85 / 255, 255 / 255, 114 / 255],
            "Cool Accent": [47 / 255, 214 / 255, 91 / 255],
            "Champagne Border": [182 / 255, 255 / 255, 193 / 255],
            "Text Primary": [245 / 255, 247 / 255, 245 / 255],
            "Background Color": [2 / 255, 3 / 255, 3 / 255]
        };
        var changed = 0;
        var effects = control.property("ADBE Effect Parade");
        for (var index = 1; effects && index <= effects.numProperties; index++) {
            var effect = effects.property(index);
            var effectName = String(effect.name);
            try {
                if (colors[effectName]) {
                    effect.property(1).setValue(colors[effectName]);
                    changed++;
                } else if (/\u00b7 Text Color$/i.test(effectName)) {
                    var accentText = /(?:kicker|label|badge|eyebrow|tag|chapter|metric)/i.test(effectName);
                    effect.property(1).setValue(accentText ? colors["Sand Accent"] : colors["Text Primary"]);
                    changed++;
                } else if (effectName === "Glass Opacity") {
                    effect.property(1).setValue(58);
                    changed++;
                } else if (effectName === "Glow Intensity") {
                    effect.property(1).setValue(34);
                    changed++;
                } else if (effectName === "Glow Radius") {
                    effect.property(1).setValue(22);
                    changed++;
                } else if (effectName === "Show Background") {
                    effect.property(1).setValue(0);
                    changed++;
                }
            } catch (_) {}
        }
        log("SYNCED_DIRECTOR_PALETTE | " + c.name + " | controls=" + changed);
        return changed;
    }

    function promoteTextAboveAdjustments(c, visited) {
        var key = String(c.id);
        if (visited[key]) return 0;
        visited[key] = true;
        var moved = 0;
        var firstAdjustment = null;
        var textLayers = [];
        for (var index = 1; index <= c.numLayers; index++) {
            var layer = c.layer(index);
            if (!firstAdjustment && layer.enabled && layer.adjustmentLayer) firstAdjustment = layer;
            if (layer instanceof TextLayer && String(layer.name).indexOf("HAFEZ EDIT ·") !== 0) textLayers.push(layer);
            try {
                if (layer.source instanceof CompItem) moved += promoteTextAboveAdjustments(layer.source, visited);
            } catch (_) {}
        }
        if (!firstAdjustment) return moved;
        // A global adjustment above editable text changes the selected Premiere
        // swatch after the fact. Keep all authored effects, but render text after
        // those adjustments so its exposed color remains color-accurate.
        for (var textIndex = 0; textIndex < textLayers.length; textIndex++) {
            try {
                if (textLayers[textIndex].index > firstAdjustment.index) {
                    textLayers[textIndex].moveBefore(firstAdjustment);
                    moved++;
                    log("PROMOTED_TEXT | " + c.name + " | " + textLayers[textIndex].name);
                }
            } catch (_) {}
        }
        return moved;
    }

    var targetNames = [
        "Hafez Hermes Glass Pill",
        "Hafez Hermes Glass Insight",
        "Hafez Hermes Glass KPI",
        "Hafez Hermes Glass Quote",
        "Hafez Hermes Glass Selector",
        "Hafez Hermes Subscribe",
        "Hafez Hermes Price List",
        "Hafez Hermes Revenue Chart",
        "Hafez Hermes Saving Balance",
        "Hafez Hermes Weekly Progress",
        "Hafez Hermes User Growth",
        "Hafez Hermes Title Hero 3",
        "Hafez Hermes Title Hero 2"
    ];
    var exported = 0;
    for (var targetIndex = 0; targetIndex < targetNames.length; targetIndex++) {
        var target = findComp(targetNames[targetIndex]);
        if (!target) {
            log("MISSING | " + targetNames[targetIndex]);
            continue;
        }
        // AE may invalidate a CompItem reference after MOGRT export. Keep the
        // stable name before exporting so post-export logging cannot dereference
        // an invalid host object.
        var targetName = target.name;
        var disabled = patchHierarchy(target, {});
        disabled += disableTopLevelFootageCarriers(target);
        var paletteControls = syncDirectorPalette(target);
        var promoted = promoteTextAboveAdjustments(target, {});
        target.motionGraphicsTemplateName = targetName;
        app.project.save(app.project.file);
        var ok = target.exportAsMotionGraphicsTemplate(true, outputFolder.fsName);
        log((ok ? "EXPORT_OK" : "EXPORT_FALSE") + " | " + targetName + " | disabled=" + disabled + " | palette=" + paletteControls + " | promoted=" + promoted);
        if (ok) exported++;
    }

    log("DONE | exported=" + exported);
    logFile.close();
    app.endUndoGroup();
    app.endSuppressDialogs(false);
})();
