/* Hafez Studio · Signal OS MOGRT generator for After Effects 2026.
 * Generates original, editable motion templates; no third-party template is embedded.
 */

(function buildHafezMotionPack() {
    app.beginUndoGroup("Build Hafez Signal OS");

    var outputValue = $.getenv("HERMES_MOGRT_OUT");
    // A second AfterFX.com process cannot pass new environment variables to an
    // already-running After Effects instance. Resolve a portable default from
    // the JSX location so unattended builds never open a folder dialog.
    var scriptFolder = new File($.fileName).parent;
    var outputFolder = outputValue ? new Folder(outputValue) : new Folder(scriptFolder.parent.fsName + "/dist");
    if (!outputFolder.exists) outputFolder.create();
    // Optional local build selector keeps small template fixes fast without
    // weakening the normal full-pack build. Remove the file for a full build.
    var buildModeValue = $.getenv("HERMES_MOGRT_MODE");
    var buildMode = buildModeValue ? String(buildModeValue).toLowerCase() : "full";
    var buildModeFile = new File(scriptFolder.fsName + "/build-mode.txt");
    if (!buildModeValue && buildModeFile.exists) {
        try {
            buildModeFile.open("r");
            buildMode = String(buildModeFile.read()).replace(/^\s+|\s+$/g, "").toLowerCase() || "full";
            buildModeFile.close();
        } catch (_) { buildMode = "full"; }
    }

    if (!app.project) app.newProject();
    var project = app.project;
    // After Effects requires the source project to be saved before a comp can
    // be exported as a Motion Graphics Template. Saving here also prevents a
    // headless build from waiting forever on the "save project" dialog.
    var projectFile = new File(outputFolder.fsName + "/Hafez-Signal-OS-Source.aep");
    project.save(projectFile);
    var W = 1920, H = 1080, FPS = 30, DURATION = 6;
    function readBrandTokens() {
        var fallback = {
            palette: {canvas:"#020303",surface:"#0A0C0B",surfaceElevated:"#111412",primaryAccent:"#55FF72",primaryAccentSoft:"#2FD65B",negativeAccent:"#FF5964",textPrimary:"#FFFFFF",textSecondary:"#9DA5A0"},
            radius: {card:40,control:24}, glow: {intensity:.72,radiusPx:34}, motion: {borderOpacity:.32}
        };
        try {
            var tokenFile = new File(scriptFolder.parent.parent.fsName + "/config/brand-tokens.json");
            if (!tokenFile.exists) return fallback;
            tokenFile.encoding = "UTF-8";
            tokenFile.open("r");
            var payload = eval("(" + tokenFile.read() + ")");
            tokenFile.close();
            return payload || fallback;
        } catch (_) { return fallback; }
    }
    function readMotionStyle() {
        var fallback = {material:{surfaceOpacity:.72,innerLightOpacity:.36,borderOpacity:.56,backgroundDimOpacity:.91,ambientGlowOpacity:.32,rimLightOpacity:.74,shadowBlurPx:52,shadowOffsetPx:14}};
        try {
            var styleFile = new File(scriptFolder.parent.parent.fsName + "/config/motion-style-contract.json");
            if (!styleFile.exists) return fallback;
            styleFile.encoding = "UTF-8";
            styleFile.open("r");
            var payload = eval("(" + styleFile.read() + ")");
            styleFile.close();
            return payload || fallback;
        } catch (_) { return fallback; }
    }
    function hexRgb(value) {
        var raw = String(value || "#FFFFFF").replace("#", "").substring(0, 6);
        return [parseInt(raw.substring(0,2),16)/255,parseInt(raw.substring(2,4),16)/255,parseInt(raw.substring(4,6),16)/255];
    }
    var BRAND = readBrandTokens();
    var MOTION_STYLE = readMotionStyle();
    var MATERIAL = MOTION_STYLE.material || {};
    var P = BRAND.palette;
    // Source Text controls are exposed to Premiere. The selected fonts must be
    // installed on the Adobe workstation; Hafez Studio's PNG fallback always
    // preserves the exact title/body font chosen in the desktop app.
    // Use PostScript names of fonts that ship with the Hafez Studio setup.
    // A missing font can make editable Source Text render blank in Premiere,
    // even though the MOGRT itself imports successfully.
    var TITLE_FONT = $.getenv("HERMES_MOGRT_TITLE_FONT") || "YekanBakh-ExtraBlack";
    var BODY_FONT = $.getenv("HERMES_MOGRT_BODY_FONT") || "YekanBakh-Regular";
    // Relaxe remains the intended editorial face and is rendered by Hafez's
    // deterministic preview. After Effects 2026 crashes while loading the
    // supplied TTF, so the editable host-safe Source Text defaults to Arial
    // Bold until the font package is replaced by an Adobe-compatible build.
    var ENGLISH_DISPLAY_FONT = $.getenv("HERMES_MOGRT_ENGLISH_FONT") || "Arial-BoldMT";
    // Keep Latin microcopy and numeric UI labels crisp. Yekan Bakh is the
    // Persian display face; its Latin metrics are not intended for compact HUD
    // labels and can collapse when animated with tracking.
    var LATIN_FONT = $.getenv("HERMES_MOGRT_LATIN_FONT") || "Arial-BoldMT";
    var C = {
        ink: hexRgb(P.canvas),
        glass: hexRgb(P.surface),
        elevated: hexRgb(P.surfaceElevated),
        white: hexRgb(P.textPrimary),
        cyan: hexRgb(P.primaryAccent),
        violet: hexRgb(P.primaryAccentSoft),
        amber: hexRgb(P.primaryAccentSoft),
        danger: hexRgb(P.negativeAccent),
        muted: hexRgb(P.textSecondary)
    };

    function comp(name) {
        // MOGRT export may refresh the active project object. Always resolve
        // it from app.project instead of retaining a stale ExtendScript handle.
        var item = app.project.items.addComp(name, W, H, 1, DURATION, FPS);
        item.motionGraphicsTemplateName = name;
        return item;
    }

    function isRtlText(value) {
        return /[\u0600-\u06FF]/.test(String(value));
    }

    function resolveFont(value, requestedFont) {
        var chosen = requestedFont || BODY_FONT;
        if (!isRtlText(value) && chosen === TITLE_FONT) return LATIN_FONT;
        return chosen;
    }

    function configureTextDocument(doc, value) {
        var rtl = isRtlText(value);
        try { doc.composerEngine = ComposerEngine.UNIVERSAL_TYPE_ENGINE; } catch (_) {}
        try {
            doc.direction = rtl ? ParagraphDirection.DIRECTION_RIGHT_TO_LEFT : ParagraphDirection.DIRECTION_LEFT_TO_RIGHT;
        } catch (_) {}
        try { doc.digitSet = rtl ? DigitSet.FARSI_DIGITS : DigitSet.DEFAULT_DIGITS; } catch (_) {}
        try { doc.autoKernType = AutoKernType.METRIC_KERN; } catch (_) {}
        try { doc.fauxBold = false; } catch (_) {}
        // Connected Persian glyphs must not inherit negative tracking. It can
        // visually stack letters even after a range animation has completed.
        if (rtl) doc.tracking = 0;
    }

    function textLayer(c, name, value, size, pos, color, fontName) {
        var layer = c.layers.addText(value);
        layer.name = name;
        var prop = layer.property("ADBE Text Properties").property("ADBE Text Document");
        var doc = prop.value;
        doc.fontSize = size;
        var actualFont = resolveFont(value, fontName);
        try { doc.font = actualFont; } catch (_) {}
        doc.fillColor = color || C.white;
        doc.applyFill = true;
        doc.applyStroke = false;
        doc.justification = ParagraphJustification.CENTER_JUSTIFY;
        configureTextDocument(doc, value);
        prop.setValue(doc);
        layer.property("ADBE Transform Group").property("ADBE Position").setValue(pos);
        add2026Typography(layer, c, actualFont, value);
        return layer;
    }

    function boxTextLayer(c, name, value, size, pos, boxSize, color, fontName) {
        var layer = c.layers.addBoxText(boxSize, value);
        layer.name = name;
        var prop = layer.property("ADBE Text Properties").property("ADBE Text Document");
        var doc = prop.value;
        doc.fontSize = size;
        var actualFont = resolveFont(value, fontName);
        try { doc.font = actualFont; } catch (_) {}
        doc.fillColor = color || C.white;
        doc.applyFill = true;
        doc.applyStroke = false;
        doc.justification = ParagraphJustification.CENTER_JUSTIFY;
        doc.autoLeading = false;
        doc.leading = size * 1.28;
        try { doc.boxVerticalAlignment = BoxVerticalAlignment.CENTER; } catch (_) {}
        configureTextDocument(doc, value);
        prop.setValue(doc);
        layer.property("ADBE Transform Group").property("ADBE Position").setValue(pos);
        add2026Typography(layer, c, actualFont, value);
        return layer;
    }

    function add2026Typography(layer, c, fontName, content) {
        // 2026 system: purposeful tracking compression plus native variable
        // weight when the selected font exposes a wght axis. Everything is
        // guarded so a static Persian font remains a valid, editable fallback.
        var bodyRole = /(Support|Micro|Label|Node Text)/i.test(layer.name) || (fontName === BODY_FONT && fontName !== TITLE_FONT);
        var rtl = isRtlText(content);
        try {
            var textProps = layer.property("ADBE Text Properties");
            var animators = textProps.property("ADBE Text Animators");
            var trackingAnimator = animators.addProperty("ADBE Text Animator");
            trackingAnimator.name = "2026 · Adaptive Tracking";
            var tracking = trackingAnimator.property("ADBE Text Animator Properties").addProperty("ADBE Text Tracking Amount");
            tracking.setValueAtTime(0, rtl ? 0 : (bodyRole ? 18 : 48));
            tracking.setValueAtTime(.58, 0);
            tracking.setValueAtTime(DURATION - .35, 0);
        } catch (_) {}
        try {
            var source = layer.property("ADBE Text Properties").property("ADBE Text Document");
            var fontObject = source.value.fontObject;
            var axes = fontObject && fontObject.designAxesData ? fontObject.designAxesData : [];
            var weightAxis = null;
            for (var axisIndex = 0; axisIndex < axes.length; axisIndex++) {
                if (String(axes[axisIndex].tag).toLowerCase() === "wght") { weightAxis = axes[axisIndex]; break; }
            }
            if (weightAxis) {
                var variableAnimator = layer.property("ADBE Text Properties").property("ADBE Text Animators").addProperty("ADBE Text Animator");
                variableAnimator.name = "2026 · Variable Weight";
                var variableWeight = variableAnimator.property("ADBE Text Animator Properties").addVariableFontAxis("wght");
                var low = Math.max(weightAxis.min, bodyRole ? 340 : 520);
                var high = Math.min(weightAxis.max, bodyRole ? 520 : 900);
                variableWeight.setValueAtTime(0, low);
                variableWeight.setValueAtTime(.72, high);
                variableWeight.setValueAtTime(DURATION - .35, high);
                try { variableWeight.addToMotionGraphicsTemplateAs(c, layer.name + " · Weight Axis"); } catch (_) {}
                try {
                    var spacing = layer.property("ADBE Text Properties").property("ADBE Text More Options").property("ADBE Text Variable Font Spacing");
                    if (spacing) spacing.setValue(1);
                } catch (_) {}
            }
        } catch (_) {}
    }

    function rectangle(c, name, size, pos, fill, opacity, stroke, strokeWidth, radius) {
        var layer = c.layers.addShape();
        layer.name = name;
        var root = layer.property("ADBE Root Vectors Group");
        var group = root.addProperty("ADBE Vector Group");
        group.name = name + " Shape";
        var vectors = group.property("ADBE Vectors Group");
        var rect = vectors.addProperty("ADBE Vector Shape - Rect");
        rect.property("ADBE Vector Rect Size").setValue(size);
        rect.property("ADBE Vector Rect Roundness").setValue(radius || 40);
        var fillProp = vectors.addProperty("ADBE Vector Graphic - Fill");
        fillProp.property("ADBE Vector Fill Color").setValue(fill || C.glass);
        fillProp.property("ADBE Vector Fill Opacity").setValue(opacity == null ? 72 : opacity);
        if (stroke) {
            var strokeProp = vectors.addProperty("ADBE Vector Graphic - Stroke");
            strokeProp.property("ADBE Vector Stroke Color").setValue(stroke);
            strokeProp.property("ADBE Vector Stroke Width").setValue(strokeWidth || 2);
            strokeProp.property("ADBE Vector Stroke Opacity").setValue(88);
        }
        layer.property("ADBE Transform Group").property("ADBE Position").setValue(pos);
        return layer;
    }

    function ellipse(c, name, size, pos, fill, opacity) {
        var layer = c.layers.addShape();
        layer.name = name;
        var root = layer.property("ADBE Root Vectors Group");
        var group = root.addProperty("ADBE Vector Group");
        group.name = name + " Shape";
        var vectors = group.property("ADBE Vectors Group");
        var shape = vectors.addProperty("ADBE Vector Shape - Ellipse");
        shape.property("ADBE Vector Ellipse Size").setValue(size);
        var fillProp = vectors.addProperty("ADBE Vector Graphic - Fill");
        fillProp.property("ADBE Vector Fill Color").setValue(fill || C.cyan);
        fillProp.property("ADBE Vector Fill Opacity").setValue(opacity == null ? 32 : opacity);
        layer.property("ADBE Transform Group").property("ADBE Position").setValue(pos);
        return layer;
    }

    function line(c, name, start, end, color, width) {
        var shape = c.layers.addShape();
        shape.name = name;
        var root = shape.property("ADBE Root Vectors Group");
        var group = root.addProperty("ADBE Vector Group");
        var path = group.property("ADBE Vectors Group").addProperty("ADBE Vector Shape - Group");
        var geometry = new Shape();
        geometry.vertices = [start, end];
        geometry.inTangents = [[0,0],[0,0]];
        geometry.outTangents = [[0,0],[0,0]];
        geometry.closed = false;
        path.property("ADBE Vector Shape").setValue(geometry);
        var stroke = group.property("ADBE Vectors Group").addProperty("ADBE Vector Graphic - Stroke");
        stroke.property("ADBE Vector Stroke Color").setValue(color || C.cyan);
        stroke.property("ADBE Vector Stroke Width").setValue(width || 3);
        return shape;
    }

    function glow(layer, radius, opacity) {
        // Three native bloom passes approximate Deep Glow without a paid
        // dependency.  Text duplicates remain linked to the editable source.
        var radii = [Math.max(4, (radius || 24) * .34), radius || 24, (radius || 24) * 2.25];
        var strengths = [(opacity || 38) * .70, (opacity || 38) * .42, (opacity || 38) * .20];
        var last = null;
        for (var pass = 0; pass < 3; pass++) {
            var duplicate = layer.duplicate();
            duplicate.name = layer.name + " · Bloom " + (pass + 1);
            duplicate.moveAfter(layer);
            duplicate.blendingMode = BlendingMode.ADD;
            var bloomOpacity = duplicate.property("ADBE Transform Group").property("ADBE Opacity");
            if (bloomOpacity.numKeys > 0) bloomOpacity.expression = "value * " + (strengths[pass] / 100);
            else bloomOpacity.setValue(strengths[pass]);
            try {
                if (layer instanceof TextLayer) {
                    duplicate.property("ADBE Text Properties").property("ADBE Text Document").expression =
                        "thisComp.layer(\"" + layer.name.replace(/\"/g, "\\\"") + "\").text.sourceText";
                }
            } catch (_) {}
            try {
                var blur = duplicate.property("ADBE Effect Parade").addProperty("ADBE Gaussian Blur 2");
                blur.property("ADBE Gaussian Blur 2-0001").setValue(radii[pass]);
                blur.property("ADBE Gaussian Blur 2-0003").setValue(true);
            } catch (_) {}
            last = duplicate;
        }
        return last;
    }

    function easy(prop) {
        try {
            // AE's temporal influence model is the native approximation of
            // Hafez UI cubic-bezier entry [0.16,.84,.22,1] and exit
            // [.4,0,.2,1]. The exact curves remain in the shared motion JSON.
            var easeIn = new KeyframeEase(0, 78);
            var easeOut = new KeyframeEase(0, 84);
            for (var k = 1; k <= prop.numKeys; k++) prop.setTemporalEaseAtKey(k, [easeIn], [easeOut]);
        } catch (_) {}
    }

    function wordLift(layer, delay, duration, lift, blurAmount) {
        // Text Animator range is based on WORDS, producing the requested
        // bottom-to-top + blur + opacity reveal with a natural stagger.
        try {
            var animators = layer.property("ADBE Text Properties").property("ADBE Text Animators");
            var animator = animators.addProperty("ADBE Text Animator");
            animator.name = "Hafez · Word Lift Reveal";
            var props = animator.property("ADBE Text Animator Properties");
            props.addProperty("ADBE Text Position 3D").setValue([0, lift == null ? 50 : lift, 0]);
            props.addProperty("ADBE Text Opacity").setValue(0);
            try { props.addProperty("ADBE Text Blur").setValue([blurAmount == null ? 10 : blurAmount, blurAmount == null ? 10 : blurAmount]); } catch (_) {}
            var selector = animator.property("ADBE Text Selectors").addProperty("ADBE Text Selector");
            selector.name = "Word Stagger";
            try { selector.property("ADBE Text Selector Advanced").property("ADBE Text Range Type2").setValue(3); } catch (_) {}
            // The animator makes its selected range invisible/blurred/offset.
            // Keep End at 100 and move Start from 0 to 100 so words are
            // progressively removed from the hidden range and revealed.
            var start = selector.property("ADBE Text Percent Start");
            var end = selector.property("ADBE Text Percent End");
            end.setValue(100);
            start.setValueAtTime(delay, 0);
            start.setValueAtTime(delay + (duration || .72), 100);
            easy(start);
            var layerOpacity = layer.property("ADBE Transform Group").property("ADBE Opacity");
            layerOpacity.setValueAtTime(DURATION - .25, 100);
            layerOpacity.setValueAtTime(DURATION, 0);
            easy(layerOpacity);
            layer.motionBlur = true;
            layer.continuouslyRasterize = true;
        } catch (_) {
            animateIn(layer, delay, lift || 50);
        }
    }

    function animateIn(layer, delay, offsetY) {
        var transform = layer.property("ADBE Transform Group");
        var opacity = transform.property("ADBE Opacity");
        var scale = transform.property("ADBE Scale");
        var position = transform.property("ADBE Position");
        var finalPos = position.value;
        opacity.setValueAtTime(delay, 0);
        opacity.setValueAtTime(delay + .52, 100);
        scale.setValueAtTime(delay, [98.5,98.5]);
        scale.setValueAtTime(delay + .42, [100.7,100.7]);
        scale.setValueAtTime(delay + .58, [100,100]);
        position.setValueAtTime(delay, [finalPos[0], finalPos[1] + (offsetY || 28)]);
        position.setValueAtTime(delay + .58, finalPos);
        opacity.setValueAtTime(DURATION - .4, 100);
        opacity.setValueAtTime(DURATION, 0);
        easy(opacity); easy(scale); easy(position);
    }

    function addSlider(control, c, name, value) {
        var effect = control.property("ADBE Effect Parade").addProperty("ADBE Slider Control");
        effect.name = name;
        effect.property(1).setValue(value);
        try { effect.property(1).addToMotionGraphicsTemplateAs(c, name); } catch (_) {}
        return effect;
    }

    function addPoint(control, c, name, value) {
        var effect = control.property("ADBE Effect Parade").addProperty("ADBE Point Control");
        effect.name = name;
        effect.property(1).setValue(value);
        try { effect.property(1).addToMotionGraphicsTemplateAs(c, name); } catch (_) {}
        return effect;
    }

    function addColor(control, c, name, value) {
        var effect = control.property("ADBE Effect Parade").addProperty("ADBE Color Control");
        effect.name = name;
        effect.property(1).setValue(value);
        try { effect.property(1).addToMotionGraphicsTemplateAs(c, name); } catch (_) {}
        return effect;
    }

    function layoutRig(c, defaultPosition, defaultScale) {
        var control = c.layers.addNull();
        control.name = "HAFEZ · LAYOUT CONTROLS";
        addPoint(control, c, "Layout Position", defaultPosition || [960, 540]);
        addSlider(control, c, "Layout Scale", defaultScale || 100);
        addSlider(control, c, "Max Text Width", 720);
        control.guideLayer = true;
        return control;
    }

    function bindLayout(layer, control, referencePoint) {
        var ref = referencePoint || [960, 540];
        try {
            layer.property("ADBE Transform Group").property("ADBE Position").expression =
                "value + thisComp.layer(\"" + control.name + "\").effect(\"Layout Position\")(\"Point\") - [" + ref[0] + "," + ref[1] + "]";
            layer.property("ADBE Transform Group").property("ADBE Scale").expression =
                "value * thisComp.layer(\"" + control.name + "\").effect(\"Layout Scale\")(\"Slider\") / 100";
        } catch (_) {}
    }

    function exposeText(layer, c, label) {
        try { layer.property("ADBE Text Properties").property("ADBE Text Document").addToMotionGraphicsTemplateAs(c, label); } catch (_) {}
    }

    function brandRig(c) {
        var control = c.layers.addNull();
        control.name = "HAFEZ · BRAND TOKENS";
        addColor(control,c,"Canvas Color",C.ink);
        addColor(control,c,"Primary Accent",C.cyan);
        addColor(control,c,"Negative Accent",C.danger);
        addColor(control,c,"Surface Color",C.glass);
        addColor(control,c,"Surface Elevated",C.elevated);
        addColor(control,c,"Text Primary",C.white);
        addColor(control,c,"Text Secondary",C.muted);
        addSlider(control,c,"Glow Intensity",Math.round(Number(BRAND.glow.intensity || .72)*100));
        addSlider(control,c,"Glow Radius",Number(BRAND.glow.radiusPx || 34));
        addSlider(control,c,"Glass Opacity",Math.round(Number(MATERIAL.surfaceOpacity || .72)*100));
        addSlider(control,c,"Inner Light",Math.round(Number(MATERIAL.innerLightOpacity || .36)*100));
        addSlider(control,c,"Background Dim",Math.round(Number(MATERIAL.backgroundDimOpacity || .91)*100));
        addSlider(control,c,"Ambient Glow",Math.round(Number(MATERIAL.ambientGlowOpacity || .32)*100));
        addSlider(control,c,"Corner Radius",Number(BRAND.radius.card || 40));
        addSlider(control,c,"Border Opacity",Math.round(Number(BRAND.motion.borderOpacity || .32)*100));
        control.guideLayer = true;
        return control;
    }

    function walkProperties(root, callback) {
        if (!root || !root.numProperties) return;
        for (var propertyIndex=1;propertyIndex<=root.numProperties;propertyIndex++) {
            var child = root.property(propertyIndex);
            if (!child) continue;
            callback(child);
            if (child.numProperties) walkProperties(child,callback);
        }
    }

    function bindBrand(c, control) {
        var controlRef = "thisComp.layer(\"" + control.name + "\")";
        for (var layerIndex=1;layerIndex<=c.numLayers;layerIndex++) {
            var layer = c.layer(layerIndex);
            if (!layer || layer === control || /LAYOUT CONTROLS/.test(layer.name)) continue;
            var lower = String(layer.name).toLowerCase();
            var negative = /(negative|danger|error|slow|risk)/.test(lower);
            var muted = /(support|micro|secondary|subtitle)/.test(lower);
            var highlight = /(kicker|metric|number|index|rail|accent|connector|edge|keyword)/.test(lower);
            var panel = /(panel|card|dock|box|statement|hud|node|glass)/.test(lower);
            var inner = /inner light/.test(lower);
            var shadow = /shadow/.test(lower);
            var canvas = /fullscreen canvas/.test(lower);
            var ambient = /ambient bloom/.test(lower);
            var refraction = /refraction/.test(lower);
            try {
                if (canvas) layer.property("ADBE Transform Group").property("ADBE Opacity").expression = controlRef + ".effect(\"Background Dim\")(\"Slider\")";
                if (ambient) layer.property("ADBE Transform Group").property("ADBE Opacity").expression = "value * " + controlRef + ".effect(\"Ambient Glow\")(\"Slider\") / 32";
            } catch (_) {}
            try {
                if (layer instanceof TextLayer) {
                    var fill = layer.property("ADBE Effect Parade").addProperty("ADBE Fill");
                    fill.name = "Hafez · Token Text Fill";
                    var textControl = negative ? "Negative Accent" : (highlight ? "Primary Accent" : (muted ? "Text Secondary" : "Text Primary"));
                    fill.property("ADBE Fill-0002").expression = controlRef + ".effect(\"" + textControl + "\")(\"Color\")";
                }
            } catch (_) {}
            try {
                walkProperties(layer.property("ADBE Root Vectors Group"),function(prop){
                    if (prop.matchName === "ADBE Vector Fill Color") {
                        var fillControl = (canvas || shadow) ? "Canvas Color" : (refraction ? "Text Primary" : (inner ? "Surface Elevated" : (panel ? "Surface Color" : (negative ? "Negative Accent" : "Primary Accent"))));
                        prop.expression = controlRef + ".effect(\"" + fillControl + "\")(\"Color\")";
                        if (panel && !inner && !refraction) prop.propertyGroup(1).property("ADBE Vector Fill Opacity").expression = controlRef + ".effect(\"Glass Opacity\")(\"Slider\")";
                        if (inner) prop.propertyGroup(1).property("ADBE Vector Fill Opacity").expression = controlRef + ".effect(\"Inner Light\")(\"Slider\")";
                    } else if (prop.matchName === "ADBE Vector Stroke Color") {
                        var strokeControl = negative ? "Negative Accent" : (highlight ? "Primary Accent" : "Text Primary");
                        prop.expression = controlRef + ".effect(\"" + strokeControl + "\")(\"Color\")";
                    } else if (prop.matchName === "ADBE Vector Rect Roundness" && panel) {
                        prop.expression = controlRef + ".effect(\"Corner Radius\")(\"Slider\")";
                    } else if (prop.matchName === "ADBE Vector Stroke Opacity") {
                        prop.expression = highlight ? ("Math.max(58," + controlRef + ".effect(\"Border Opacity\")(\"Slider\"))") : (controlRef + ".effect(\"Border Opacity\")(\"Slider\")");
                    }
                });
            } catch (_) {}
            if (/· bloom/.test(lower)) {
                try {
                    var pass = /bloom 1/.test(lower) ? .70 : (/bloom 2/.test(lower) ? .42 : .20);
                    layer.property("ADBE Transform Group").property("ADBE Opacity").expression = "value * " + pass + " * " + controlRef + ".effect(\"Glow Intensity\")(\"Slider\") / 72";
                    walkProperties(layer.property("ADBE Effect Parade"),function(effectProp){
                        if (effectProp.matchName === "ADBE Gaussian Blur 2-0001") {
                            effectProp.expression = controlRef + ".effect(\"Glow Radius\")(\"Slider\") * " + (pass === .70 ? .34 : (pass === .42 ? 1 : 2.25));
                        }
                    });
                } catch (_) {}
            }
        }
    }

    function finish(c) {
        var brandControl = brandRig(c);
        bindBrand(c, brandControl);
        // Adding the comp and its controls marks the AEP dirty. MOGRT export
        // checks the current saved state, so persist immediately before every
        // export to keep both GUI and unattended builds dialog-free.
        try { app.project.save(projectFile); } catch (_) {}
        try { c.exportAsMotionGraphicsTemplate(true, outputFolder.fsName); } catch (error) { $.writeln(c.name + ": " + error.toString()); }
    }

    function liquidGlass(c, name, size, pos, accent, radius) {
        var shadow = rectangle(c, name + " · Shadow", [size[0] + 38, size[1] + 38], [pos[0], pos[1] + Number(MATERIAL.shadowOffsetPx || 14)], C.ink, 58, null, 0, (radius || 36) + 10);
        try {
            var shadowBlur = shadow.property("ADBE Effect Parade").addProperty("ADBE Gaussian Blur 2");
            shadowBlur.property("ADBE Gaussian Blur 2-0001").setValue(Number(MATERIAL.shadowBlurPx || 52));
            shadowBlur.property("ADBE Gaussian Blur 2-0003").setValue(true);
        } catch (_) {}
        var panel = rectangle(c, name, size, pos, C.glass, Math.round(Number(MATERIAL.surfaceOpacity || .72) * 100), accent || C.cyan, 2.4, radius || 36);
        var inner = rectangle(c, name + " · Inner Light", [size[0] - 12, size[1] - 12], [pos[0], pos[1] - 2], C.elevated, Math.round(Number(MATERIAL.innerLightOpacity || .36) * 100), C.white, 1.3, Math.max(12, (radius || 36) - 5));
        inner.blendingMode = BlendingMode.SCREEN;
        var refraction = rectangle(c, name + " · Refraction Band", [size[0] - 58, Math.max(36, size[1] * .16)], [pos[0], pos[1] - size[1] * .29], C.white, 9, null, 0, Math.max(14, (radius || 36) - 10));
        refraction.blendingMode = BlendingMode.SCREEN;
        try {
            var refractionBlur = refraction.property("ADBE Effect Parade").addProperty("ADBE Gaussian Blur 2");
            refractionBlur.property("ADBE Gaussian Blur 2-0001").setValue(18);
            refractionBlur.property("ADBE Gaussian Blur 2-0003").setValue(true);
        } catch (_) {}
        var shine = line(c, name + " · Spectral Edge", [-size[0] * .32, 0], [size[0] * .32, 0], accent || C.cyan, 3);
        shine.property("ADBE Transform Group").property("ADBE Position").setValue([pos[0], pos[1] - size[1] / 2 + 6]);
        glow(shine, 30, Math.round(Number(MATERIAL.rimLightOpacity || .74) * 100));
        var rim = rectangle(c, name + " · Accent Edge", [size[0] + 4,size[1] + 4], pos, C.cyan, 0, accent || C.cyan, 1.4, (radius || 36) + 2);
        animateIn(rim,.11,0);
        glow(rim,28,46);
        return [shadow, panel, inner, refraction, shine, rim];
    }

    function ambientBloom(c, name, size, pos, color, opacity, blurRadius) {
        var bloom = ellipse(c, name + " · Ambient Bloom", size, pos, color || C.cyan, 100);
        bloom.blendingMode = BlendingMode.ADD;
        bloom.property("ADBE Transform Group").property("ADBE Opacity").setValue(opacity == null ? 32 : opacity);
        try {
            var blur = bloom.property("ADBE Effect Parade").addProperty("ADBE Gaussian Blur 2");
            blur.property("ADBE Gaussian Blur 2-0001").setValue(blurRadius || 170);
            blur.property("ADBE Gaussian Blur 2-0003").setValue(true);
        } catch (_) {}
        return bloom;
    }

    function fullScreenEnvironment(c, accent, bias) {
        var layers = [];
        layers.push(rectangle(c, "Fullscreen Canvas", [W + 8, H + 8], [W/2,H/2], C.ink, 100, null, 0, 0));
        layers.push(ambientBloom(c, "Primary", [980,760], bias === "left" ? [360,250] : [1510,250], accent || C.cyan, 32, 175));
        layers.push(ambientBloom(c, "Secondary", [760,600], bias === "left" ? [1580,900] : [360,900], C.violet, 18, 190));
        layers.push(ambientBloom(c, "Glass Refraction", [720,430], [960,540], accent || C.cyan, 13, 118));
        for (var gx = 160; gx < W; gx += 160) {
            var vertical = line(c, "Backdrop Grid V " + gx, [0,-H/2], [0,H/2], C.elevated, 1);
            vertical.property("ADBE Transform Group").property("ADBE Position").setValue([gx,H/2]);
            vertical.property("ADBE Transform Group").property("ADBE Opacity").setValue(11);
            layers.push(vertical);
        }
        for (var gy = 135; gy < H; gy += 135) {
            var horizontal = line(c, "Backdrop Grid H " + gy, [-W/2,0], [W/2,0], C.elevated, 1);
            horizontal.property("ADBE Transform Group").property("ADBE Position").setValue([W/2,gy]);
            horizontal.property("ADBE Transform Group").property("ADBE Opacity").setValue(9);
            layers.push(horizontal);
        }
        var frame = rectangle(c, "Fullscreen Safe Frame", [W-112,H-112], [W/2,H/2], C.ink, 0, C.white, 1, 34);
        layers.push(frame);
        return layers;
    }

    function bindMany(layers, control, reference) {
        for (var i = 0; i < layers.length; i++) if (layers[i]) bindLayout(layers[i], control, reference);
    }

    function fullscreenGlassFocusV1() {
        var c = comp("Hafez Fullscreen Glass Focus"); c.motionBlur = true;
        fullScreenEnvironment(c, C.cyan, "right");
        var ref = [960,540], rig = layoutRig(c, ref, 100);
        var glass = liquidGlass(c, "Focus Liquid Glass", [1160,430], ref, C.cyan, 46);
        var rail = line(c, "Focus Accent Rail", [-420,0], [420,0], C.cyan, 4);
        rail.property("ADBE Transform Group").property("ADBE Position").setValue([960,336]);
        var kicker = textLayer(c, "EN Micro Kicker", "HAFEZ · KEY MOMENT", 20, [960,402], C.cyan, LATIN_FONT);
        var en = boxTextLayer(c, "EN Display Title", "THE WORKFLOW", 112, [960,526], [1060,175], C.white, ENGLISH_DISPLAY_FONT);
        var fa = boxTextLayer(c, "FA Semantic Subtitle", "سیگنال از تریدینگ‌ویو به هوش مصنوعی می‌رسد.", 42, [960,664], [990,88], C.muted, BODY_FONT);
        bindMany(glass.concat([rail,kicker,en,fa]),rig,ref);
        animateIn(glass[0],.02,18);animateIn(glass[1],.05,18);animateIn(glass[2],.08,12);animateIn(glass[3],.10,8);animateIn(glass[4],.12,0);
        animateIn(rail,.14,0);wordLift(kicker,.17,.30,22,6);wordLift(en,.20,.64,42,9);wordLift(fa,.32,.68,30,7);
        glow(rail,34,68);glow(en,18,16);
        exposeText(kicker,c,"EN Micro Kicker");exposeText(en,c,"EN Display Title");exposeText(fa,c,"FA Semantic Subtitle");
        finish(c);
    }

    function fullscreenGlassPrismV1() {
        var c = comp("Hafez Fullscreen Glass Prism"); c.motionBlur = true;
        fullScreenEnvironment(c, C.cyan, "left");
        var ref = [790,550], rig = layoutRig(c, ref, 100);
        var glass = liquidGlass(c, "Prism Liquid Glass", [1320,420], ref, C.cyan, 48);
        var vertical = line(c,"Prism Accent Spine",[0,-138],[0,138],C.cyan,5);
        vertical.property("ADBE Transform Group").property("ADBE Position").setValue([188,550]);
        var kicker = textLayer(c,"EN Micro Kicker","HAFEZ · CORE INSIGHT",20,[790,414],C.cyan,LATIN_FONT);
        var en = boxTextLayer(c,"EN Statement Title","AUTOMATE THE DECISION",76,[815,535],[1140,150],C.white,ENGLISH_DISPLAY_FONT);
        var fa = boxTextLayer(c,"FA Statement Subtitle","تصمیم‌گیری سریع‌تر، دقیق‌تر و قابل تکرار می‌شود.",40,[815,672],[1080,86],C.muted,BODY_FONT);
        bindMany(glass.concat([vertical,kicker,en,fa]),rig,ref);
        animateIn(glass[0],.02,20);animateIn(glass[1],.05,20);animateIn(glass[2],.08,14);animateIn(glass[3],.10,8);animateIn(glass[4],.12,0);
        animateIn(vertical,.14,0);wordLift(kicker,.17,.30,20,6);wordLift(en,.20,.70,46,10);wordLift(fa,.34,.70,30,7);
        glow(vertical,40,74);glow(en,16,14);
        exposeText(kicker,c,"EN Micro Kicker");exposeText(en,c,"EN Statement Title");exposeText(fa,c,"FA Statement Subtitle");
        finish(c);
    }

    function fullscreenGlassChapterV1() {
        var c = comp("Hafez Fullscreen Glass Chapter"); c.motionBlur = true;
        fullScreenEnvironment(c, C.cyan, "right");
        var ref = [960,540], rig = layoutRig(c, ref, 100);
        var glass = liquidGlass(c,"Chapter Portal Glass",[1220,500],ref,C.cyan,52);
        var divider = line(c,"Chapter Accent Divider",[0,-138],[0,138],C.cyan,3);
        divider.property("ADBE Transform Group").property("ADBE Position").setValue([730,548]);
        var number = textLayer(c,"Chapter Number","03",190,[520,548],C.cyan,LATIN_FONT);
        var kicker = textLayer(c,"EN Micro Kicker","HAFEZ · CHAPTER",20,[1110,400],C.cyan,LATIN_FONT);
        var en = boxTextLayer(c,"EN Chapter Title","THE SIGNAL ENGINE",78,[1110,535],[800,165],C.white,ENGLISH_DISPLAY_FONT);
        var fa = boxTextLayer(c,"FA Chapter Subtitle","ورود سیگنال به موتور تحلیل هوشمند",38,[1110,680],[760,82],C.muted,BODY_FONT);
        bindMany(glass.concat([divider,number,kicker,en,fa]),rig,ref);
        animateIn(glass[0],.02,18);animateIn(glass[1],.05,18);animateIn(glass[2],.08,12);animateIn(glass[3],.10,8);animateIn(glass[4],.12,0);
        wordLift(number,.16,.44,36,8);animateIn(divider,.20,0);wordLift(kicker,.20,.30,20,6);wordLift(en,.24,.66,44,9);wordLift(fa,.36,.68,28,7);
        glow(number,34,34);glow(divider,32,68);
        exposeText(number,c,"Chapter Number");exposeText(kicker,c,"EN Micro Kicker");exposeText(en,c,"EN Chapter Title");exposeText(fa,c,"FA Chapter Subtitle");
        finish(c);
    }

    function wordLiftStatementV2() {
        var c = comp("Hafez Word Lift Statement"); c.motionBlur = true;
        var ref = [1500, 220], rig = layoutRig(c, ref, 88);
        var glass = liquidGlass(c, "Liquid Glass Statement", [650, 235], ref, C.cyan, 42);
        var kicker = textLayer(c, "EN Kicker", "KEY INSIGHT", 22, [1500, 150], C.cyan, TITLE_FONT);
        var fa = boxTextLayer(c, "FA Headline", "این کار واقعاً زمانبره، ولی می‌شه خودکارش کرد.", 48, [1500, 242], [550, 128], C.white, TITLE_FONT);
        bindMany(glass.concat([kicker, fa]), rig, ref);
        animateIn(glass[0], .04, 16); animateIn(glass[1], .07, 16); animateIn(glass[2], .09, 12); animateIn(glass[3], .12, 0);
        wordLift(kicker, .16, .38, 28, 8); wordLift(fa, .20, .82, 50, 10); glow(fa, 18, 18);
        exposeText(kicker, c, "EN Kicker"); exposeText(fa, c, "FA Headline"); finish(c);
    }

    function bilingualHeroHighlightV1() {
        // The vendor highlight is used only as a timing reference. Every
        // visible layer below is original Hafez UI material and remains fully
        // editable in Premiere through one coherent MOGRT.
        var c = comp("Hafez Bilingual Hero Highlight"); c.motionBlur = true;
        var ref = [1500, 220], rig = layoutRig(c, ref, 88);
        var glass = liquidGlass(c, "Hero Liquid Glass", [680, 250], ref, C.cyan, 40);
        var rail = line(c, "Hero Accent Rail", [-286, 0], [286, 0], C.cyan, 3);
        rail.property("ADBE Transform Group").property("ADBE Position").setValue([1500, 128]);
        var en = textLayer(c, "EN Display Title", "THE WORKFLOW", 100, [1500, 195], C.white, ENGLISH_DISPLAY_FONT);
        var fa = boxTextLayer(c, "FA Semantic Subtitle", "سیگنال از تریدینگ‌ویو به هوش مصنوعی می‌رسد.", 40, [1500, 282], [590, 72], C.muted, BODY_FONT);
        bindMany(glass.concat([rail, en, fa]), rig, ref);
        animateIn(glass[0], .03, 14); animateIn(glass[1], .06, 14);
        animateIn(glass[2], .09, 10); animateIn(glass[3], .12, 0);
        animateIn(rail, .14, 0);
        wordLift(en, .17, .62, 42, 9);
        wordLift(fa, .30, .68, 30, 7);
        glow(rail, 22, 38);
        exposeText(en, c, "EN Display Title");
        exposeText(fa, c, "FA Semantic Subtitle");
        finish(c);
    }

    function faceSafeCornerNoteV2() {
        var c = comp("Hafez Face Safe Corner Note"); c.motionBlur = true;
        var ref = [1545, 190], rig = layoutRig(c, ref, 88);
        var glass = liquidGlass(c, "Corner Glass", [560, 205], ref, C.violet, 36);
        var index = textLayer(c, "Beat Index", "●  FOCUS", 19, [1545, 130], C.cyan, TITLE_FONT);
        var fa = boxTextLayer(c, "FA Headline", "نکته‌ی اصلی دقیقاً همین‌جاست.", 44, [1545, 218], [470, 105], C.white, TITLE_FONT);
        bindMany(glass.concat([index, fa]), rig, ref);
        animateIn(glass[0], .04, 18); animateIn(glass[1], .08, 18); animateIn(glass[2], .10, 12); animateIn(glass[3], .12, 0);
        wordLift(index, .17, .30, 22, 7); wordLift(fa, .21, .68, 50, 10); glow(glass[3], 24, 52);
        exposeText(index, c, "EN Kicker"); exposeText(fa, c, "FA Headline"); finish(c);
    }

    function bigNumberRevealV2() {
        var c = comp("Hafez Big Number Reveal"); c.motionBlur = true;
        var ref = [1540, 260], rig = layoutRig(c, ref, 90);
        var glass = liquidGlass(c, "Metric Glass", [540, 350], ref, C.violet, 44);
        var en = textLayer(c, "EN Kicker", "EXECUTION LATENCY", 20, [1540, 140], C.cyan, TITLE_FONT);
        var number = textLayer(c, "Metric Value", "10 ms", 126, [1540, 250], C.white, TITLE_FONT);
        var label = boxTextLayer(c, "FA Label", "اختلافی که نتیجه رو عوض می‌کنه.", 35, [1540, 365], [450, 82], C.white, BODY_FONT);
        bindMany(glass.concat([en, number, label]), rig, ref);
        animateIn(glass[0], .03, 22); animateIn(glass[1], .06, 22); animateIn(glass[2], .08, 15); animateIn(glass[3], .10, 0);
        wordLift(en, .14, .30, 24, 7); wordLift(number, .18, .52, 58, 12); wordLift(label, .30, .62, 42, 9); glow(number, 40, 34);
        exposeText(number, c, "Metric Value"); exposeText(label, c, "FA Label"); exposeText(en, c, "EN Kicker"); finish(c);
    }

    function compactFlowchartV2() {
        var c = comp("Hafez Compact Flowchart"); c.motionBlur = true;
        var ref = [340, 550], rig = layoutRig(c, ref, 86);
        var back = liquidGlass(c, "Process Glass", [560, 760], ref, C.cyan, 46);
        var kicker = textLayer(c, "EN Kicker", "THE WORKFLOW", 22, [340, 242], C.cyan, TITLE_FONT);
        var title = boxTextLayer(c, "FA Headline", "مسیر کار از سیگنال تا نتیجه", 40, [340, 315], [470, 92], C.white, TITLE_FONT);
        var labels = ["سیگنال در تریدینگ‌ویو", "ارسال به مدل لوکال هرمس", "اجرا در متاتریدر", "نمایش نتیجه در تلگرام"];
        var all = back.concat([kicker, title]);
        for (var i = 0; i < 4; i++) {
            var y = 410 + i * 126;
            var card = rectangle(c, "Node Card " + (i + 1), [450, 98], [340, y], [7/255,13/255,28/255], 78, i === 3 ? C.amber : C.cyan, 2, 26);
            var idx = textLayer(c, "Node Index " + (i + 1), "0" + (i + 1), 23, [172, y], i === 3 ? C.amber : C.cyan, LATIN_FONT);
            var label = boxTextLayer(c, "Node Text " + (i + 1), labels[i], 29, [370, y + 6], [350, 72], C.white, BODY_FONT);
            all.push(card); all.push(idx); all.push(label);
            animateIn(card, .16 + i * .14, 28); wordLift(idx, .22 + i * .14, .24, 22, 7); wordLift(label, .24 + i * .14, .42, 38, 9);
            exposeText(label, c, "Node " + (i + 1));
            if (i < 3) {
                var connector = line(c, "Connector " + (i + 1), [0,-13], [0,13], C.violet, 4);
                connector.property("ADBE Transform Group").property("ADBE Position").setValue([340, y + 63]);
                glow(connector, 15, 40); all.push(connector); animateIn(connector, .31 + i * .14, 0);
            }
        }
        bindMany(all, rig, ref); animateIn(back[0], .02, 18); animateIn(back[1], .05, 18); animateIn(back[2], .07, 12); animateIn(back[3], .09, 0);
        wordLift(kicker, .10, .30, 24, 7); wordLift(title, .14, .58, 44, 10);
        exposeText(title, c, "FA Headline"); exposeText(kicker, c, "EN Kicker"); finish(c);
    }

    function glassHudMetricV2() {
        var c = comp("Hafez Glass HUD Metric"); c.motionBlur = true;
        var ref = [1550, 230], rig = layoutRig(c, ref, 88);
        var glass = liquidGlass(c, "HUD Liquid Glass", [560, 315], ref, C.cyan, 40);
        var en = textLayer(c, "EN Kicker", "LIVE SYSTEM METRIC", 20, [1550, 125], C.cyan, TITLE_FONT);
        var value = textLayer(c, "Metric Value", "94%", 105, [1550, 235], C.white, TITLE_FONT);
        var label = boxTextLayer(c, "FA Label", "دقت تحلیل در اجرای واقعی", 34, [1550, 335], [450, 70], C.white, BODY_FONT);
        var rail = line(c, "Metric Rail", [-190,0], [190,0], C.violet, 6); rail.property("ADBE Transform Group").property("ADBE Position").setValue([1550,390]);
        bindMany(glass.concat([en, value, label, rail]), rig, ref);
        animateIn(glass[0],.03,18);animateIn(glass[1],.06,18);animateIn(glass[2],.08,12);animateIn(glass[3],.10,0);
        wordLift(en,.13,.30,24,7);wordLift(value,.18,.55,52,11);wordLift(label,.28,.55,38,9);animateIn(rail,.32,0);glow(value,34,30);glow(rail,22,50);
        exposeText(value,c,"Metric Value");exposeText(label,c,"FA Label");exposeText(en,c,"EN Kicker");finish(c);
    }

    function splitCompareV2() {
        var c = comp("Hafez Split Compare"); c.motionBlur = true;
        var ref = [960, 840], rig = layoutRig(c, ref, 96);
        var glass = liquidGlass(c, "Compare Dock", [1180, 300], ref, C.violet, 44);
        var en = textLayer(c, "EN Kicker", "BEFORE / AFTER", 20, [960,725], C.cyan, TITLE_FONT);
        var title = boxTextLayer(c, "FA Headline", "فرقِ اجرای دستی با اجرای هوشمند", 42, [960,780], [1000,80], C.white, TITLE_FONT);
        var a = boxTextLayer(c,"FA A","اجرای دستی",38,[700,865],[420,64],C.white,TITLE_FONT);
        var b = boxTextLayer(c,"FA B","اجرای هوشمند",38,[1220,865],[420,64],C.white,TITLE_FONT);
        var as = boxTextLayer(c,"FA A Support","کند و وابسته به واکنش",27,[700,930],[420,56],C.muted,BODY_FONT);
        var bs = boxTextLayer(c,"FA B Support","سریع، دقیق و قابل تکرار",27,[1220,930],[420,56],C.muted,BODY_FONT);
        var divider = line(c,"Compare Divider",[0,-78],[0,78],C.cyan,3);divider.property("ADBE Transform Group").property("ADBE Position").setValue([960,890]);
        bindMany(glass.concat([en,title,a,b,as,bs,divider]),rig,ref);
        animateIn(glass[0],.03,20);animateIn(glass[1],.06,20);animateIn(glass[2],.08,12);animateIn(glass[3],.10,0);
        wordLift(en,.12,.28,22,7);wordLift(title,.16,.56,40,9);wordLift(a,.25,.42,38,9);wordLift(b,.34,.42,38,9);wordLift(as,.33,.42,28,8);wordLift(bs,.42,.42,28,8);animateIn(divider,.30,0);glow(divider,20,42);
        exposeText(title,c,"FA Headline");exposeText(en,c,"EN Kicker");exposeText(a,c,"FA A");exposeText(b,c,"FA B");exposeText(as,c,"FA A Support");exposeText(bs,c,"FA B Support");finish(c);
    }

    function chapterBillboardV2() {
        var c = comp("Hafez Chapter Billboard"); c.motionBlur = true;
        // The artwork itself sits at the lower safe-zone. Keeping the layout
        // control's reference identical prevents animateIn() from applying the
        // requested offset twice when expressions are evaluated.
        var ref = [960, 940], rig = layoutRig(c, ref, 84);
        var glass = liquidGlass(c, "Chapter Dock", [1160, 270], ref, C.cyan, 44);
        var number = textLayer(c,"Chapter Number","03",126,[520,940],C.violet,TITLE_FONT);
        var en = textLayer(c,"EN Kicker","CHAPTER · DECISION ENGINE",20,[1015,860],C.cyan,TITLE_FONT);
        var fa = boxTextLayer(c,"FA Headline","چطور یک تصمیم حرفه‌ای ساخته می‌شه؟",54,[1060,965],[760,135],C.white,TITLE_FONT);
        bindMany(glass.concat([number,en,fa]),rig,ref);animateIn(glass[0],.02,18);animateIn(glass[1],.05,18);animateIn(glass[2],.07,12);animateIn(glass[3],.09,0);
        wordLift(number,.10,.42,58,12);wordLift(en,.16,.30,22,7);wordLift(fa,.20,.76,50,10);glow(number,42,38);
        exposeText(number,c,"Chapter Number");exposeText(fa,c,"FA Headline");exposeText(en,c,"EN Kicker");finish(c);
    }

    function decisionDepthV2() {
        var c = comp("Hafez Decision Depth Typography"); c.motionBlur = true;
        var ref = [430, 210], rig = layoutRig(c, ref, 86);
        var ghost = textLayer(c,"Depth Ghost","DECISION",118,[430,235],C.violet,TITLE_FONT);ghost.property("ADBE Transform Group").property("ADBE Opacity").setValue(18);
        var en = textLayer(c,"EN Kicker","THE CORE IDEA",20,[430,110],C.cyan,TITLE_FONT);
        var fa = boxTextLayer(c,"FA Headline","تصمیم درست",82,[430,235],[720,160],C.white,TITLE_FONT);
        var support = boxTextLayer(c,"FA Support","وقتی داده روشنه، تصمیم هم روشن می‌شه.",31,[430,350],[680,80],C.white,BODY_FONT);
        bindMany([ghost,en,fa,support],rig,ref);animateIn(ghost,.02,65);wordLift(en,.12,.30,24,7);wordLift(fa,.17,.72,50,10);wordLift(support,.34,.64,40,9);glow(fa,38,32);
        exposeText(en,c,"EN Kicker");exposeText(fa,c,"FA Headline");exposeText(support,c,"FA Support");finish(c);
    }

    function subjectOcclusionKeywordV2() {
        var c = comp("Hafez Subject Occlusion Keyword"); c.motionBlur = true;
        var ref = [420, 210], rig = layoutRig(c, ref, 84);
        var rail = line(c,"Depth Rail",[-300,0],[300,0],C.violet,5);rail.property("ADBE Transform Group").property("ADBE Position").setValue([420,330]);
        var en = textLayer(c,"EN Kicker","BEHIND THE SUBJECT",20,[420,105],C.cyan,TITLE_FONT);
        var fa = boxTextLayer(c,"FA Headline","تصمیم",118,[420,230],[720,210],C.white,TITLE_FONT);
        var support = boxTextLayer(c,"FA Support","تأکید عمقی با فضای امن سوژه",28,[420,390],[650,70],C.muted,BODY_FONT);
        bindMany([rail,en,fa,support],rig,ref);animateIn(rail,.05,0);wordLift(en,.13,.30,24,7);wordLift(fa,.18,.70,58,12);wordLift(support,.35,.52,36,8);glow(fa,46,38);glow(rail,24,48);
        exposeText(en,c,"EN Kicker");exposeText(fa,c,"FA Headline");exposeText(support,c,"FA Support");finish(c);
    }

    function neuralStatement() {
        var c = comp("Hafez Neural Statement");
        var panel = rectangle(c, "Glass Panel", [1120,300], [1210,790], C.glass, 78, C.cyan, 2, 42);
        glow(panel, 30, 25);
        var accent = rectangle(c, "Accent Rail", [9,216], [1732,790], C.cyan, 100, null, 0, 5);
        glow(accent, 22, 52);
        var kicker = textLayer(c, "EN Kicker", "SIGNAL GENERATION", 27, [1230,700], C.cyan, TITLE_FONT);
        var fa = textLayer(c, "FA Headline", "این الگوریتم سیگنال‌های معاملاتی را تولید می‌کند.", 62, [1200,806], C.white, TITLE_FONT);
        var micro = textLayer(c, "EN Micro", "HAFEZ · INTELLIGENT SYSTEM", 18, [1220,900], C.muted, BODY_FONT);
        animateIn(panel, .08, 20); animateIn(accent, .16, 10); animateIn(kicker, .23, 18); animateIn(fa, .29, 24); animateIn(micro, .38, 16);
        exposeText(kicker, c, "EN Kicker"); exposeText(fa, c, "FA Headline"); exposeText(micro, c, "EN Micro"); finish(c);
    }

    function kineticKeyword() {
        var c = comp("Hafez Kinetic Keyword");
        var rail = line(c, "Energy Line", [-360,0], [360,0], C.violet, 5);
        rail.property("ADBE Transform Group").property("ADBE Position").setValue([960,596]); glow(rail, 34, 55);
        var en = textLayer(c, "EN Kicker", "THE CORE IDEA", 25, [960,430], C.cyan, TITLE_FONT);
        var fa = textLayer(c, "FA Keyword", "سرعت اجرای معامله", 116, [960,545], C.white, TITLE_FONT);
        var sub = textLayer(c, "FA Support", "چند میلی‌ثانیه می‌تواند نتیجه را تغییر دهد.", 39, [960,676], C.muted, BODY_FONT);
        animateIn(rail, .04, 0); animateIn(en, .13, 18); animateIn(fa, .2, 42); animateIn(sub, .32, 20);
        exposeText(en, c, "EN Kicker"); exposeText(fa, c, "FA Keyword"); exposeText(sub, c, "FA Support"); finish(c);
    }

    function hudMetric() {
        var c = comp("Hafez HUD Metric");
        var panel = rectangle(c, "HUD Panel", [570,330], [1520,305], C.glass, 72, C.violet, 2, 35); glow(panel, 26, 27);
        var number = textLayer(c, "Metric Value", "12 ms", 112, [1520,280], C.white, TITLE_FONT);
        var label = textLayer(c, "FA Label", "تاخیر اجرای سفارش", 38, [1520,390], C.white, BODY_FONT);
        var en = textLayer(c, "EN Kicker", "EXECUTION LATENCY", 21, [1520,160], C.cyan, TITLE_FONT);
        animateIn(panel, .08, -24); animateIn(en, .15, 16); animateIn(number, .22, 34); animateIn(label, .31, 20);
        exposeText(number, c, "Metric Value"); exposeText(label, c, "FA Label"); exposeText(en, c, "EN Kicker"); finish(c);
    }

    function flowchart() {
        var c = comp("Hafez Flowchart 4 Step");
        var title = textLayer(c, "FA Headline", "مسیر اجرای سیستم", 55, [960,215], C.white, TITLE_FONT);
        var kicker = textLayer(c, "EN Kicker", "AUTOMATION FLOW", 24, [960,145], C.cyan, TITLE_FONT);
        exposeText(title, c, "FA Headline"); exposeText(kicker, c, "EN Kicker");
        var labels = ["دریافت داده", "تحلیل الگوریتم", "تولید سیگنال", "اجرای معامله"];
        for (var i=0; i<4; i++) {
            var x = 360 + i*400;
            var panel = rectangle(c, "Node " + (i+1), [300,155], [x,570], C.glass, 79, i===3?C.amber:C.cyan, 2, 28);
            var index = textLayer(c, "Node Index " + (i+1), "0"+(i+1), 21, [x,522], i===3?C.amber:C.cyan, TITLE_FONT);
            var label = textLayer(c, "Node Text " + (i+1), labels[i], 31, [x,585], C.white, BODY_FONT);
            animateIn(panel, .18+i*.16, 28); animateIn(index, .24+i*.16, 20); animateIn(label, .28+i*.16, 20);
            exposeText(label, c, "Node " + (i+1));
            if (i<3) { var connector=line(c,"Connector "+(i+1),[x+155,570],[x+245,570],C.violet,4); glow(connector,18,42); animateIn(connector,.35+i*.16,0); }
        }
        animateIn(kicker,.05,14); animateIn(title,.1,22); finish(c);
    }

    function chapterHero() {
        var c = comp("Hafez Chapter Hero");
        var number = textLayer(c, "Chapter Number", "03", 220, [365,500], C.violet, TITLE_FONT); glow(number,42,38);
        var lineLayer = line(c,"Chapter Rail",[-380,0],[380,0],C.cyan,5); lineLayer.property("ADBE Transform Group").property("ADBE Position").setValue([1100,625]); glow(lineLayer,28,45);
        var fa = textLayer(c, "FA Headline", "الگوریتم چگونه تصمیم می‌گیرد؟", 78, [1150,500], C.white, TITLE_FONT);
        var en = textLayer(c, "EN Kicker", "CHAPTER · DECISION ENGINE", 25, [1140,405], C.cyan, TITLE_FONT);
        animateIn(number,.05,35);animateIn(en,.17,18);animateIn(fa,.23,32);animateIn(lineLayer,.35,0);
        exposeText(number,c,"Chapter Number");exposeText(fa,c,"FA Headline");exposeText(en,c,"EN Kicker");finish(c);
    }

    function compareAB() {
        var c=comp("Hafez Compare AB");
        var title=textLayer(c,"FA Headline","تفاوت اجرای دستی و خودکار",58,[960,190],C.white,TITLE_FONT);
        var en=textLayer(c,"EN Kicker","MANUAL vs AUTOMATED",24,[960,120],C.cyan,TITLE_FONT);
        var left=rectangle(c,"Card A",[670,390],[560,620],C.glass,77,C.danger,2,38);var right=rectangle(c,"Card B",[670,390],[1360,620],C.glass,77,C.cyan,2,38);
        var a=textLayer(c,"FA A","اجرای دستی",57,[560,560],C.white,TITLE_FONT);var b=textLayer(c,"FA B","اجرای الگوریتمی",57,[1360,560],C.white,TITLE_FONT);
        var as=textLayer(c,"FA A Support","کند و وابسته به واکنش انسان",31,[560,685],C.muted,BODY_FONT);var bs=textLayer(c,"FA B Support","سریع، دقیق و قابل تکرار",31,[1360,685],C.muted,BODY_FONT);
        animateIn(en,.04,12);animateIn(title,.1,20);animateIn(left,.19,28);animateIn(right,.28,28);animateIn(a,.27,20);animateIn(b,.36,20);animateIn(as,.34,16);animateIn(bs,.43,16);
        exposeText(title,c,"FA Headline");exposeText(en,c,"EN Kicker");exposeText(a,c,"FA A");exposeText(b,c,"FA B");exposeText(as,c,"FA A Support");exposeText(bs,c,"FA B Support");finish(c);
    }

    var buildLog = new File(outputFolder.fsName + "/Hafez-Signal-OS-Build.log");
    function writeLog(message) {
        try {
            buildLog.open("a");
            buildLog.writeln(new Date().toUTCString() + " | " + message);
            buildLog.close();
        } catch (_) {}
    }
    app.beginSuppressDialogs();
    try {
        writeLog("build started (" + buildMode + ")");
        if (buildMode === "hero-only") {
            bilingualHeroHighlightV1(); writeLog("Hafez Bilingual Hero Highlight built");
        } else if (buildMode === "chapter-only") {
            chapterBillboardV2(); writeLog("Hafez Chapter Billboard built");
        } else if (buildMode === "glass-titles-only") {
            fullscreenGlassFocusV1(); writeLog("Hafez Fullscreen Glass Focus built");
            fullscreenGlassPrismV1(); writeLog("Hafez Fullscreen Glass Prism built");
            fullscreenGlassChapterV1(); writeLog("Hafez Fullscreen Glass Chapter built");
        } else {
            neuralStatement(); writeLog("Hafez Neural Statement built");
            kineticKeyword(); writeLog("Hafez Kinetic Keyword built");
            hudMetric(); writeLog("Hafez HUD Metric built");
            flowchart(); writeLog("Hafez Flowchart 4 Step built");
            chapterHero(); writeLog("Hafez Chapter Hero built");
            compareAB(); writeLog("Hafez Compare AB built");
            fullscreenGlassFocusV1(); writeLog("Hafez Fullscreen Glass Focus built");
            fullscreenGlassPrismV1(); writeLog("Hafez Fullscreen Glass Prism built");
            fullscreenGlassChapterV1(); writeLog("Hafez Fullscreen Glass Chapter built");
            bilingualHeroHighlightV1(); writeLog("Hafez Bilingual Hero Highlight built");
            wordLiftStatementV2(); writeLog("Hafez Word Lift Statement built");
            faceSafeCornerNoteV2(); writeLog("Hafez Face Safe Corner Note built");
            bigNumberRevealV2(); writeLog("Hafez Big Number Reveal built");
            compactFlowchartV2(); writeLog("Hafez Compact Flowchart built");
            glassHudMetricV2(); writeLog("Hafez Glass HUD Metric built");
            splitCompareV2(); writeLog("Hafez Split Compare built");
            chapterBillboardV2(); writeLog("Hafez Chapter Billboard built");
            decisionDepthV2(); writeLog("Hafez Decision Depth Typography built");
            subjectOcclusionKeywordV2(); writeLog("Hafez Subject Occlusion Keyword built");
        }
        app.project.save(projectFile);
        writeLog("build complete (" + buildMode + ")");
    } catch (error) {
        writeLog("ERROR line " + (error.line || "?") + ": " + error.toString());
    }
    app.endSuppressDialogs(false);
    app.endUndoGroup();
    $.writeln("Hafez Signal OS motion pack generated in: " + outputFolder.fsName);
})();
