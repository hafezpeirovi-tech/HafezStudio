/* Hafez Studio Premiere Finisher — ExtendScript compatibility bridge. */
$._hafez = $._hafez || {};

$._hafez.parseJson = function (text) {
    // Premiere's legacy ExtendScript engine does not always provide JSON.
    // Plans and MOGRT text documents are trusted local files/values.
    return eval("(" + String(text).replace(/^\uFEFF/, "") + ")");
};

$._hafez.stringify = function (value) {
    if (value === null) return "null";
    var type = typeof value;
    if (type === "string") {
        return '"' + value
            .replace(/\\/g, "\\\\")
            .replace(/"/g, '\\"')
            .replace(/\r/g, "\\r")
            .replace(/\n/g, "\\n")
            .replace(/\t/g, "\\t") + '"';
    }
    if (type === "number") return isFinite(value) ? String(value) : "null";
    if (type === "boolean") return value ? "true" : "false";
    if (value instanceof Array) {
        var parts = [];
        for (var i = 0; i < value.length; i++) parts.push($._hafez.stringify(value[i]));
        return "[" + parts.join(",") + "]";
    }
    if (type === "object") {
        var fields = [];
        for (var key in value) {
            if (!value.hasOwnProperty(key)) continue;
            var childType = typeof value[key];
            if (childType === "undefined" || childType === "function") continue;
            fields.push($._hafez.stringify(String(key)) + ":" + $._hafez.stringify(value[key]));
        }
        return "{" + fields.join(",") + "}";
    }
    return "null";
};

$._hafez.readJson = function (path) {
    var file = new File(path);
    if (!file.exists) throw new Error("Plan پیدا نشد: " + path);
    file.encoding = "UTF-8";
    file.open("r");
    var text = file.read();
    file.close();
    return $._hafez.parseJson(text);
};

$._hafez.normal = function (value) {
    return String(value || "").toLowerCase().replace(/^\s+|\s+$/g, "");
};

$._hafez.paramAliases = function (name) {
    var aliases = {
        "fa headline": ["fa headline", "persian headline", "headline", "source text", "عنوان", "متن"],
        "en kicker": ["en kicker", "english kicker", "kicker"],
        "fa keyword": ["fa keyword", "keyword"],
        "fa support": ["fa support", "support"],
        "metric value": ["metric value", "value", "number"],
        "fa label": ["fa label", "label"],
        "chapter number": ["chapter number"],
        "layout position": ["layout position"],
        "layout scale": ["layout scale"],
        "max text width": ["max text width"],
        "glow intensity": ["glow intensity"]
    };
    for (var i = 1; i <= 5; i++) aliases["node " + i] = ["node " + i];
    return aliases[$._hafez.normal(name)] || [$._hafez.normal(name)];
};

$._hafez.setParam = function (param, value, fontFamily, coordinateSpace, fontSize) {
    var hasFontSize = typeof fontSize !== "undefined";
    if (hasFontSize && (!(Number(fontSize) > 0) || !isFinite(Number(fontSize)))) return false;
    if (hasFontSize && typeof value !== "string") return false;
    // Premiere's AE Point Control API uses normalized coordinates even though
    // its Effect Controls UI displays pixels. Verified in Premiere 2026:
    // UI [400,260] -> API [0.2083333284,0.2407407463] for a 1920x1080 comp.
    // Sending pixels directly clamps the UI to 32767 and hides live graphics.
    if ($._hafez.normal(param.displayName) === "layout position" && value instanceof Array && value.length === 2) {
        var space = coordinateSpace || [1920, 1080];
        if (!(Number(space[0]) > 0 && Number(space[1]) > 0)) return false;
        try {
            var point = [Number(value[0]) / Number(space[0]), Number(value[1]) / Number(space[1])];
            if (!isFinite(point[0]) || !isFinite(point[1])) return false;
            param.setValue(point, 1);
            var storedPoint = param.getValue();
            return Math.abs(storedPoint[0] - point[0]) < 0.00001 && Math.abs(storedPoint[1] - point[1]) < 0.00001;
        } catch (_) { return false; }
    }
    // AE color controls are packed numbers in getValue(), not RGBA arrays.
    // Adobe's PProPanel sample uses setColorValue(alpha, red, green, blue).
    if (value instanceof Array && value.length === 4) {
        try {
            var rgba = [];
            for (var ci = 0; ci < 4; ci++) rgba.push(Math.round(Math.max(0, Math.min(1, Number(value[ci]))) * 255));
            param.setColorValue(rgba[3], rgba[0], rgba[1], rgba[2], 1);
            var actualColor = param.getColorValue();
            return Math.abs(actualColor[0] - rgba[3]) <= 1 && Math.abs(actualColor[1] - rgba[0]) <= 1 && Math.abs(actualColor[2] - rgba[1]) <= 1 && Math.abs(actualColor[3] - rgba[2]) <= 1;
        } catch (_) { return false; }
    }
    var current;
    try { current = param.getValue(); } catch (_) { current = null; }
    if (typeof value === "string" && typeof current === "string" && current.indexOf("textEditValue") >= 0) {
        try {
            var textDoc = $._hafez.parseJson(current);
            textDoc.textEditValue = value;
            if (textDoc.fontTextRunLength && textDoc.fontTextRunLength.length) textDoc.fontTextRunLength[0] = value.length;
            // Editable text controls often store the font inside the Source Text JSON
            // instead of exposing a separate "Font" MOGRT parameter.  Apply the
            // curator's selected family to every text run while preserving all
            // other author-provided typography settings.
            if (fontFamily && String(fontFamily).toLowerCase().indexOf("auto") < 0) {
                if (textDoc.fontEditValue instanceof Array && textDoc.fontEditValue.length) {
                    for (var fontIndex = 0; fontIndex < textDoc.fontEditValue.length; fontIndex++) {
                        textDoc.fontEditValue[fontIndex] = String(fontFamily);
                    }
                } else {
                    textDoc.fontEditValue = [String(fontFamily)];
                }
            }
            if (hasFontSize) {
                // Premiere exposes editable native typography in Source Text
                // JSON, not as a separate scalar MOGRT control. Do not invent
                // capability flags for templates which did not expose it.
                if (textDoc.capPropFontSizeEdit !== true || !(textDoc.fontSizeEditValue instanceof Array) || !textDoc.fontSizeEditValue.length) return false;
                for (var sizeIndex = 0; sizeIndex < textDoc.fontSizeEditValue.length; sizeIndex++) textDoc.fontSizeEditValue[sizeIndex] = Number(fontSize);
            }
            var textResult = param.setValue($._hafez.stringify(textDoc), 1);
            if (!(textResult === 0 || textResult === true || typeof textResult === "undefined")) return false;
            var storedText = $._hafez.parseJson(param.getValue());
            if (storedText.textEditValue !== value) return false;
            if (fontFamily && String(fontFamily).toLowerCase().indexOf("auto") < 0) {
                if (!storedText.fontEditValue || !storedText.fontEditValue.length) return false;
                for (var storedFontIndex = 0; storedFontIndex < storedText.fontEditValue.length; storedFontIndex++) {
                    if (String(storedText.fontEditValue[storedFontIndex]) !== String(fontFamily)) return false;
                }
            }
            if (hasFontSize) {
                if (!(storedText.fontSizeEditValue instanceof Array) || storedText.fontSizeEditValue.length !== textDoc.fontSizeEditValue.length) return false;
                for (var storedSizeIndex = 0; storedSizeIndex < storedText.fontSizeEditValue.length; storedSizeIndex++) {
                    var storedSize = Number(storedText.fontSizeEditValue[storedSizeIndex]);
                    if (!isFinite(storedSize) || Math.abs(storedSize - Number(fontSize)) > 0.00001 * Math.max(1, Number(fontSize))) return false;
                }
            }
            return true;
        } catch (_) { return false; }
    }
    if (hasFontSize) return false; // A requested font size must target native Source Text.
    try {
        var result = param.setValue(value, 1);
        if (!(result === 0 || result === true || typeof result === "undefined")) return false;
        var storedValue = param.getValue();
        if (typeof value === "number") return isFinite(value) && isFinite(Number(storedValue)) && Math.abs(Number(storedValue) - value) <= 0.00001 * Math.max(1, Math.abs(value));
        if (typeof value === "boolean") return storedValue === value || storedValue === Number(value);
        if (value instanceof Array) {
            if (!storedValue || storedValue.length !== value.length) return false;
            for (var valueIndex = 0; valueIndex < value.length; valueIndex++) {
                if (!isFinite(Number(value[valueIndex])) || !isFinite(Number(storedValue[valueIndex])) || Math.abs(Number(storedValue[valueIndex]) - Number(value[valueIndex])) > 0.00001) return false;
            }
            return true;
        }
        return storedValue === value;
    } catch (_) { return false; }
};

$._hafez.applyControls = function (component, cue) {
    var controls = cue.controls || {};
    var applied = 0;
    cue.appliedText = {};
    cue.appliedControls = {};
    if (!component || !component.properties) return applied;
    for (var p = 0; p < component.properties.numItems; p++) {
        var param = component.properties[p];
        var display = $._hafez.normal(param.displayName);
        for (var key in controls) {
            if (!controls.hasOwnProperty(key)) continue;
            var names = $._hafez.paramAliases(key);
            var match = false;
            for (var n = 0; n < names.length; n++) {
                if (display === names[n]) { match = true; break; }
            }
            var perTextFonts = cue.text_fonts || {};
            var perTextSizes = cue.text_sizes || {};
            var controlFont = perTextFonts.hasOwnProperty(key) ? perTextFonts[key] : cue.font_family;
            var controlSize = perTextSizes.hasOwnProperty(key) ? perTextSizes[key] : undefined;
            if (match && $._hafez.setParam(param, controls[key], controlFont, cue.coordinate_space, controlSize)) {
                applied++;
                cue.appliedControls[key] = true;
                try {
                    var stored = param.getValue();
                    if (typeof stored === "string" && stored.indexOf("textEditValue") >= 0) {
                        if ($._hafez.parseJson(stored).textEditValue === controls[key]) cue.appliedText[key] = true;
                    }
                } catch (_) {}
                break;
            }
        }
    }
    return applied;
};

// Typed vendor controls never go through legacy name aliases. A color and a
// Source Text parameter may both be called "Text 1" in the SAME template.
$._hafez.applyTypedControls = function (component, bindings) {
    if (!component || !component.properties || !(bindings instanceof Array) || !bindings.length) throw new Error("Missing typed MOGRT contract");
    var report = {applied:0, texts:0, controls:[]};
    var used = {};
    for (var b = 0; b < bindings.length; b++) {
        var binding = bindings[b], matches = [];
        for (var p = 0; p < component.properties.numItems; p++) {
            var param = component.properties[p];
            if (String(param.displayName) !== binding.name) continue;
            var value = null, kind = "unknown";
            try { value = param.getValue(); } catch (_) { continue; }
            if (typeof value === "string" && value.indexOf("textEditValue") >= 0) kind = "text";
            else {
                try { var color = param.getColorValue(); if (color && color.length === 4) kind = "color"; } catch (_) {}
                if (kind === "unknown") {
                    if (value instanceof Array) kind = value.length === 2 ? "point" : "vector";
                    else if (typeof value === "boolean") kind = "boolean";
                    else if (typeof value === "number") kind = "scalar";
                }
            }
            // Premiere represents checkbox values as 0/1 in some releases.
            if (kind === binding.kind || (binding.kind === "boolean" && kind === "scalar" && (value === 0 || value === 1))) matches.push({param:param,index:p});
        }
        var occurrence = Number(binding.occurrence || 0);
        if (occurrence < 0 || occurrence % 1 !== 0 || occurrence >= matches.length) throw new Error("Typed parameter not found: " + binding.name + " / " + binding.kind);
        var selected = matches[occurrence], key = "p:" + selected.index;
        if (used[key]) throw new Error("Duplicate typed parameter binding: " + binding.name);
        used[key] = true;
        var ok = false;
        if (binding.kind === "vector" || binding.kind === "point") {
            var proposed = binding.value;
            if (!(proposed instanceof Array) || (binding.kind === "point" && proposed.length !== 2)) throw new Error("Invalid vector/point");
            for (var n = 0; n < proposed.length; n++) if (typeof proposed[n] !== "number" || !isFinite(proposed[n])) throw new Error("Non-finite vector");
            selected.param.setValue(proposed, 1);
            var stored = selected.param.getValue(); ok = !!stored && stored.length === proposed.length;
            for (var j = 0; ok && j < proposed.length; j++) ok = Math.abs(Number(stored[j])-proposed[j]) < 0.0001;
        } else {
            if (binding.kind === "text" && binding.font) {
                var doc = $._hafez.parseJson(selected.param.getValue());
                if (doc.capPropFontEdit !== true) throw new Error("Native font editing is locked: " + binding.name);
            }
            ok = $._hafez.setParam(selected.param, binding.value, binding.font || "", null, binding.fontSize);
        }
        if (!ok) throw new Error("Typed control readback failed: " + binding.name);
        report.applied++; if (binding.kind === "text") report.texts++;
        report.controls.push({index:selected.index,name:binding.name,kind:binding.kind});
    }
    return report;
};

$._hafez.templateName = function (path) {
    return decodeURI(new File(path).name.replace(/\.mogrt$/i, ""));
};

// Explicit native clip scaling, separate from vendor-internal layout values.
// Never infer it from metadata dimensions: Premiere can auto-scale imports.
$._hafez.applyNativeScale = function (item, scale) {
    if (typeof scale !== "number" || !isFinite(scale) || scale <= 0 || scale > 400) throw new Error("Invalid native scale");
    var motion = null;
    for (var c = 0; c < item.components.numItems; c++) {
        if (String(item.components[c].matchName) === "AE.ADBE Motion") motion = item.components[c];
    }
    if (!motion) throw new Error("Native Motion component unavailable");
    var scaleParam = null, uniform = null;
    for (var p = 0; p < motion.properties.numItems; p++) {
        var param = motion.properties[p];
        if (String(param.displayName) === "Scale") scaleParam = param;
        if (String(param.displayName) === "Uniform Scale") uniform = param;
    }
    if (!scaleParam || !uniform) throw new Error("Native scale contract unavailable");
    if ((scaleParam.isTimeVarying && scaleParam.isTimeVarying()) || (uniform.isTimeVarying && uniform.isTimeVarying())) throw new Error("Animated native scale requires manual review");
    if (!$._hafez.setParam(uniform, true) || !$._hafez.setParam(scaleParam, scale)) throw new Error("Native scale readback failed");
};

$._hafez.matchesCueItem = function (item, templateName, start) {
    // Only app-named native graphics on this plan's track and frame may be
    // reused or quarantined. A loose prefix also matched owner suffixes.
    if (templateName.indexOf("Hafez ") !== 0 || !isFinite(Number(start))) return false;
    var itemName = String(item.name);
    if (itemName !== templateName && !(itemName.indexOf(templateName) === 0 && /^ Review [0-9]+$/.test(itemName.substr(templateName.length)))) return false;
    if (!isFinite(Number(item.start.seconds)) || Math.abs(item.start.seconds - Number(start)) >= 0.04) return false;
    try { return !!item.getMGTComponent(); } catch (_) { return false; }
};

$._hafez.disableItem = function (item) {
    item.disabled = true;
    if (!item.disabled) throw new Error("Could not disable failed Hafez graphic; manual review required");
};

// Vendor names are not ownership evidence. Only exact, deterministic names
// assigned at import by this plan may be updated on a retry.
$._hafez.layerItemName = function (layer, cue, layerIndex) {
    if (!layer.typed_controls) return $._hafez.templateName(layer.template_path || cue.template_path);
    var cueId = String(cue.id || "");
    if (!/^[a-zA-Z0-9_-]+$/.test(cueId)) throw new Error("Invalid native cue identity");
    return "Hafez Glass " + cueId + " L" + String(layerIndex);
};

$._hafez.disableCue = function (sequence, cue, plannedMogrtIndex, result) {
    var layers = cue.template_layers && cue.template_layers.length ? cue.template_layers : [cue];
    for (var layerIndex = 0; layerIndex < layers.length; layerIndex++) {
        var layer = layers[layerIndex];
        var trackIndex = Number(layer.track === undefined ? (cue.track === undefined ? plannedMogrtIndex : cue.track) : layer.track);
        if (!isFinite(trackIndex) || trackIndex < 0 || trackIndex % 1 !== 0 || trackIndex >= sequence.videoTracks.numTracks) continue;
        var templateName = $._hafez.layerItemName(layer, cue, layerIndex);
        var track = sequence.videoTracks[trackIndex];
        for (var clipIndex = 0; clipIndex < track.clips.numItems; clipIndex++) {
            var item = track.clips[clipIndex];
            if (!$._hafez.matchesCueItem(item, templateName, cue.start)) continue;
            try {
                $._hafez.disableItem(item);
                result.disabled++;
            } catch (disableError) {
                result.safetyFailures++;
                result.messages.push("SAFETY FAILURE: " + cue.id + " | " + disableError.message);
            }
        }
    }
};

$._hafez.inspectTimeline = function (requestJson) {
    var report = {ok:true, sequence:"", videoTracks:[], firstMogrt:null, mogrts:[]};
    try {
        var sequence = app.project.activeSequence;
        if (!sequence) throw new Error("سکانس فعال پیدا نشد.");
        if (requestJson) {
            var request = $._hafez.parseJson(requestJson);
            if (!request.expected_project_path || !request.expected_sequence_name) throw new Error("Exact inspect target required");
            if (String(app.project.path).replace(/\\/g,"/").toLowerCase() !== String(request.expected_project_path).replace(/\\/g,"/").toLowerCase() || sequence.name !== request.expected_sequence_name) throw new Error("Inspect target mismatch");
            if (request.expected_sequence_id && String(sequence.sequenceID) !== String(request.expected_sequence_id)) throw new Error("Inspect sequence ID mismatch");
        }
        report.sequence = sequence.name;
        report.project = app.project.path;
        report.sequence_id = String(sequence.sequenceID);
        report.frameSize = [sequence.frameSizeHorizontal, sequence.frameSizeVertical];
        report.timebase = String(sequence.timebase);
        for (var t = 0; t < sequence.videoTracks.numTracks; t++) {
            var track = sequence.videoTracks[t];
            report.videoTracks.push({index:t, clips:track.clips.numItems, muted:track.isMuted()});
            if (t < 2 || track.clips.numItems < 1) continue;
            for (var clipIndex = 0; clipIndex < track.clips.numItems; clipIndex++) {
            var item = track.clips[clipIndex];
            var detail = {track:t, name:item.name, start:item.start.seconds, end:item.end.seconds,
                inPoint:item.inPoint.seconds, outPoint:item.outPoint.seconds, disabled:item.disabled, params:[], motion:[], components:[]};
            for (var componentIndex = 0; componentIndex < item.components.numItems; componentIndex++) {
                var motionComponent = item.components[componentIndex];
                detail.components.push({name:String(motionComponent.displayName),matchName:String(motionComponent.matchName)});
                if (String(motionComponent.displayName) !== "Motion" && String(motionComponent.matchName) !== "ADBE Motion") continue;
                for (var mp = 0; mp < motionComponent.properties.numItems; mp++) {
                    var motionParam = motionComponent.properties[mp];
                    try { detail.motion.push({index:mp,name:String(motionParam.displayName),value:motionParam.getValue()}); } catch (_) {}
                }
            }
            try {
                var component = item.getMGTComponent();
                detail.component = !!component;
                if (component && component.properties) {
                    detail.propertyCount = component.properties.numItems;
                    for (var p = 0; p < component.properties.numItems && p < 200; p++) {
                        var param = component.properties[p];
                        var value;
                        try { value = param.getValue(); } catch (_) { value = "<unreadable>"; }
                        var propertyDetail = {name:String(param.displayName || ""), type:typeof value, preview:String(value).substr(0, 2000)};
                        if (/color|accent|surface|border|text primary/i.test(param.displayName)) {
                            try { propertyDetail.color = param.getColorValue(); } catch (_) {}
                        }
                        detail.params.push(propertyDetail);
                    }
                }
            } catch (componentError) {
                detail.componentError = componentError.message;
            }
            if (!report.firstMogrt) report.firstMogrt = detail;
            report.mogrts.push(detail);
            }
        }
    } catch (error) {
        report.ok = false;
        report.error = error.message;
        report.line = error.line || 0;
    }
    return $._hafez.stringify(report);
};

$._hafez.importXmlRequest = function (requestJson) {
    var report = {ok:false, mode:"import_xml", imported:false, activated:false, saved:false, bin:"", sequences:[], messages:[]};
    function pathKey(path) { return String(new File(path).fsName).replace(/\\/g, "/").toLowerCase(); }
    function findBin(parent, name, depth) {
        if (depth > 100) throw new Error("Project bin nesting exceeds safe limit");
        if (!parent || !parent.children) return null;
        for (var i = 0; i < parent.children.numItems; i++) {
            var child = parent.children[i];
            if (child.type !== 2) continue;
            if (String(child.name) === name) return child;
            var nested = findBin(child, name, depth + 1);
            if (nested) return nested;
        }
        return null;
    }
    try {
        var request = $._hafez.parseJson(requestJson);
        if (request.protocol !== "hafez-native-import-v1" || request.mode !== "import_xml") throw new Error("Unsupported native import request");
        if (!request.expected_project_path || !request.xml_path || !request.bin_name || !request.expected_sequence_name) throw new Error("Exact project, XML, bin and sequence are required");
        if (!/\.prproj$/i.test(request.expected_project_path) || !/\.xml$/i.test(request.xml_path)) throw new Error("Expected a Premiere project and XML file");
        var project = app.project;
        if (!project || !project.path || pathKey(project.path) !== pathKey(request.expected_project_path)) throw new Error("Active project does not match the explicitly requested QA project");
        if (!(new File(request.xml_path)).exists) throw new Error("XML file not found");
        var names = request.expected_sequence_names;
        if (!(names instanceof Array) || names.length < 1 || names.length > 20) throw new Error("Expected sequence inventory is required");
        var expected = {}, selectedExpected = false;
        for (var nameIndex = 0; nameIndex < names.length; nameIndex++) {
            var name = String(names[nameIndex]);
            if (!name || expected["name:" + name]) throw new Error("Expected sequence names must be unique");
            expected["name:" + name] = true;
            if (name === request.expected_sequence_name) selectedExpected = true;
        }
        if (!selectedExpected) throw new Error("Target sequence is absent from expected inventory");
        if (findBin(project.rootItem, String(request.bin_name), 0)) throw new Error("Target bin already exists; refusing a duplicate import");
        var before = {}, beforeCount = project.sequences.numSequences;
        if (!isFinite(Number(beforeCount))) throw new Error("Sequence inventory is unavailable");
        for (var index = 0; index < beforeCount; index++) {
            var oldSequence = project.sequences[index];
            var oldId = String(oldSequence.sequenceID || "");
            if (!oldId || before["id:" + oldId]) throw new Error("Existing sequence IDs cannot be verified");
            before["id:" + oldId] = true;
            if (expected["name:" + String(oldSequence.name)]) throw new Error("Expected sequence name already exists: " + oldSequence.name);
        }
        // No existing bin, sequence, timeline or project is renamed or deleted.
        project.rootItem.createBin(String(request.bin_name));
        var bin = findBin(project.rootItem, String(request.bin_name), 0);
        if (!bin) throw new Error("Could not create the isolated import bin");
        report.bin = String(request.bin_name);
        var imported = project.importFiles([new File(request.xml_path).fsName], true, bin, false);
        report.imported = imported === true || imported === 1;
        if (!report.imported) throw new Error("Premiere did not confirm XML import; inspect the isolated bin before retrying");
        if (!app.project || pathKey(app.project.path) !== pathKey(request.expected_project_path)) throw new Error("Active project changed during XML import");
        var newNames = {}, selected = null;
        for (var afterIndex = 0; afterIndex < project.sequences.numSequences; afterIndex++) {
            var candidate = project.sequences[afterIndex];
            var candidateId = String(candidate.sequenceID || "");
            if (!candidateId) throw new Error("Imported sequence has no verifiable ID");
            if (before["id:" + candidateId]) continue;
            var candidateName = String(candidate.name);
            report.sequences.push({id:candidateId, name:candidateName});
            if (!expected["name:" + candidateName] || newNames["name:" + candidateName]) throw new Error("Unexpected or duplicate newly imported sequence: " + candidateName);
            newNames["name:" + candidateName] = true;
            if (candidateName === request.expected_sequence_name) selected = candidate;
        }
        if (report.sequences.length !== names.length || !selected) throw new Error("New sequence inventory does not match the expected XML");
        if (!project.openSequence(selected.sequenceID)) throw new Error("Could not activate the newly imported sequence ID");
        if (!project.activeSequence || String(project.activeSequence.sequenceID) !== String(selected.sequenceID)) throw new Error("Active sequence readback differs from the newly imported sequence");
        report.activated = true;
        report.sequence_id = String(selected.sequenceID);
        report.sequence = String(selected.name);
        report.ok = true;
        report.messages.push("Imported into a new isolated bin and activated the verified new sequence ID. No MOGRTs applied and project not saved.");
    } catch (error) {
        report.messages.push("XML IMPORT FAILED: " + error.message);
        if (report.bin) report.messages.push("The new import bin is preserved for inspection; no existing project content was removed.");
    }
    return $._hafez.stringify(report);
};

$._hafez.applyPlan = function (path, muteGuide) {
    // inserted remains the compatible count of fully verified active items,
    // not the number of import attempts or disabled partial results.
    var result = {ok:false, inserted:0, attempted:0, imported:0, updated:0, disabled:0, safetyFailures:0, textUpdated:0, failed:0, warnings:[], messages:[]};
    try {
        var plan = $._hafez.readJson(path);
        if (plan.protocol !== "hermes-professional-edit-v2") throw new Error("Plan باید V2 باشد.");
        if (plan.style_pack === "glass" && (plan.purpose !== "isolated-native-qa" || !plan.expected_project_path)) throw new Error("Glass production routing awaits font and native QA approval; exact isolated QA project required");
        if (plan.expected_project_path && String(app.project.path).replace(/\\/g,"/").toLowerCase() !== String(plan.expected_project_path).replace(/\\/g,"/").toLowerCase()) throw new Error("Active project does not match the requested plan");
        var sequence = app.project.activeSequence;
        if (!sequence) throw new Error("سکانس فعال پیدا نشد.");
        if (sequence.name !== plan.sequence) throw new Error("سکانس «" + plan.sequence + "» را فعال کن؛ سکانس فعلی با Plan یکسان نیست.");
        if (plan.expected_sequence_id && String(sequence.sequenceID) !== String(plan.expected_sequence_id)) throw new Error("Active sequence ID mismatch");
        var guideIndex = Number(plan.video_tracks.png_guide === undefined ? 2 : plan.video_tracks.png_guide);
        var plannedMogrtIndex = Number(plan.video_tracks.mogrt === undefined ? 3 : plan.video_tracks.mogrt);
        if (plannedMogrtIndex >= sequence.videoTracks.numTracks) {
            throw new Error("Track رزروشده V" + (plannedMogrtIndex + 1) + " برای MOGRT پیدا نشد؛ XML جدید را import کن.");
        }
        var graphics = plan.graphics || [];
        var expectedMogrtCount = 0;
        for (var countIndex = 0; countIndex < graphics.length; countIndex++) {
            var countLayers = graphics[countIndex].template_layers;
            expectedMogrtCount += countLayers && countLayers.length ? countLayers.length : 1;
        }
        for (var i = 0; i < graphics.length; i++) {
            var cue = graphics[i];
            if (cue.review_blocked === true) {
                $._hafez.disableCue(sequence, cue, plannedMogrtIndex, result);
                result.failed++;
                result.messages.push("REVIEW BLOCKED: " + cue.id + " | " + String(cue.review_blocked_reason || cue.review_reason || "Editorial or native QA review required"));
                continue;
            }
            if (cue.layout && cue.layout.collision_free === false) {
                $._hafez.disableCue(sequence, cue, plannedMogrtIndex, result);
                result.failed++;
                result.messages.push("✕ " + cue.id + ": Face collision");
                continue;
            }
            var layers = cue.template_layers && cue.template_layers.length ? cue.template_layers : [cue];
            for (var layerIndex = 0; layerIndex < layers.length; layerIndex++) {
                var layer = layers[layerIndex];
                // ExtendScript var is function-scoped: reset before any early
                // validation can throw, or the previous layer could be disabled.
                var item = null;
                var imported = false;
                result.attempted++;
                try {
                    var templatePath = layer.template_path || cue.template_path;
                    var plannedTrack = layer.track === undefined ? (cue.track === undefined ? plannedMogrtIndex : cue.track) : layer.track;
                    var trackIndex = Number(plannedTrack);
                    if (!isFinite(trackIndex) || trackIndex < 0 || trackIndex % 1 !== 0 || trackIndex >= sequence.videoTracks.numTracks) {
                        throw new Error("Track دوزبانه V" + (trackIndex + 1) + " در سکانس وجود ندارد");
                    }
                    var targetTrack = sequence.videoTracks[trackIndex];
                    var templateName = $._hafez.layerItemName(layer, cue, layerIndex);
                    // A retry updates this plan's matching Hafez clip instead of
                    // stacking duplicate graphics on the same frame.
                    for (var existingIndex = 0; existingIndex < targetTrack.clips.numItems; existingIndex++) {
                        var existingItem = targetTrack.clips[existingIndex];
                        if ($._hafez.matchesCueItem(existingItem, templateName, cue.start)) {
                            if (item) {
                                $._hafez.disableCue(sequence, cue, plannedMogrtIndex, result);
                                item = null;
                                throw new Error("چند MOGRT هم‌زمان پیدا شد؛ بازبینی دستی لازم است");
                            }
                            item = existingItem;
                        }
                    }
                    // Keep incomplete text, default vendor graphics, or stale
                    // unsafe placement off screen throughout a retry.
                    if (item) $._hafez.disableItem(item);
                    if (!(new File(templatePath)).exists) throw new Error("MOGRT پیدا نشد");
                    if (!isFinite(Number(cue.start)) || Number(cue.start) < 0 || !isFinite(Number(cue.end)) || Number(cue.end) <= Number(cue.start)) throw new Error("زمان‌بندی MOGRT معتبر نیست");
                    // The September 2 approved live-text wrapper was archived
                    // while the obsolete vendor capsule kept the canonical name.
                    // Migrate only this plan's exact old Hafez clip; other clips
                    // and later retries remain untouched.
                    if (item && templateName === "Hafez Hermes Glass Insight" &&
                        String(item.name) === "Hafez Hermes Glass Insight") {
                        item.remove(false, false);
                        item = null;
                        result.messages.push("Glass Insight: migrated obsolete capsule to approved Review 7 wrapper.");
                    }
                    if (!item) {
                        item = sequence.importMGT(templatePath, String(Math.round(Number(cue.start) * 254016000000)), trackIndex, 0);
                        if (item) {
                            imported = true; result.imported++;
                            if (layer.typed_controls) item.name = templateName;
                        }
                    }
                    if (!item) throw new Error("Premiere آیتم MOGRT برنگرداند");
                    $._hafez.disableItem(item);
                    var endTime = new Time();
                    endTime.seconds = Number(cue.end);
                    item.end = endTime;
                    if (Math.abs(item.end.seconds - Number(cue.end)) > 0.04) throw new Error("زمان خروج MOGRT اعمال نشد");
                    var component = item.getMGTComponent();
                    var layerCue = {
                        controls: layer.controls || cue.controls || {},
                        font_family: layer.role === "catalog-curated-element" ? (layer.font_family || "") : (layer.font_family || cue.font_family || ""),
                        coordinate_space: (cue.layout || {}).mogrt_coordinate_space || [1920, 1080],
                        text_sizes: {}, text_fonts: {}, appliedText: {}, appliedControls: {}
                    };
                    var typographyMaps = ["text_sizes", "text_fonts"];
                    for (var mapIndex = 0; mapIndex < typographyMaps.length; mapIndex++) {
                        var mapName = typographyMaps[mapIndex];
                        var cueMap = cue[mapName] || {}, layerMap = layer[mapName] || {};
                        for (var cueMapKey in cueMap) if (cueMap.hasOwnProperty(cueMapKey)) layerCue[mapName][cueMapKey] = cueMap[cueMapKey];
                        for (var layerMapKey in layerMap) if (layerMap.hasOwnProperty(layerMapKey)) layerCue[mapName][layerMapKey] = layerMap[layerMapKey];
                    }
                    var typedReport = null;
                    if (layer.typed_controls) {
                        typedReport = $._hafez.applyTypedControls(component, layer.typed_controls);
                        if (typeof layer.native_motion_scale !== "undefined") $._hafez.applyNativeScale(item, layer.native_motion_scale);
                        result.messages.push("Typed controls verified: " + templateName + " | " + typedReport.applied);
                    }
                    var changed = typedReport ? typedReport.applied : $._hafez.applyControls(component, layerCue);
                    var requiredText = (layer.text_controls || cue.text_controls || []).slice(0);
                    // An explicitly sized/font-selected text control is always
                    // required, even when the plan omitted text_controls.
                    for (var requiredMapIndex = 0; requiredMapIndex < typographyMaps.length; requiredMapIndex++) {
                        var requiredMap = layerCue[typographyMaps[requiredMapIndex]];
                        for (var requiredMapKey in requiredMap) if (requiredMap.hasOwnProperty(requiredMapKey)) requiredText.push(requiredMapKey);
                    }
                    var textCount = 0;
                    for (var textKey in layerCue.appliedText) if (layerCue.appliedText.hasOwnProperty(textKey)) textCount++;
                    for (var textIndex = 0; textIndex < requiredText.length; textIndex++) {
                        if (!layerCue.appliedText[requiredText[textIndex]]) throw new Error("متن قابل‌ویرایش تأیید نشد: " + requiredText[textIndex]);
                    }
                    if (typedReport) textCount = typedReport.texts;
                    var verifiedBackground = typedReport && layer.role === "vendor-background" && layer.allow_no_text === true && typedReport.applied > 0;
                    if (textCount < 1 && !verifiedBackground) throw new Error("هیچ متن قابل‌ویرایشی پس از درج تأیید نشد");
                    var requiredControls = layer.required_controls || cue.required_controls || [];
                    for (var requiredIndex = 0; requiredIndex < requiredControls.length; requiredIndex++) {
                        if (!layerCue.appliedControls[requiredControls[requiredIndex]]) throw new Error("کنترل ضروری تأیید نشد: " + requiredControls[requiredIndex]);
                    }
                    for (var controlKey in layerCue.controls) {
                        if (!layerCue.controls.hasOwnProperty(controlKey) || layerCue.appliedControls[controlKey]) continue;
                        var controlName = $._hafez.normal(controlKey);
                        if (controlName === "layout position" || controlName === "layout scale") throw new Error("جای‌گذاری ایمن تأیید نشد: " + controlKey);
                        result.warnings.push(cue.id + "/" + (layer.role || "graphic") + ": unverified optional control: " + controlKey);
                    }
                    // A previously disabled cue is enabled only after this
                    // non-blocked plan re-applies and verifies all required data.
                    item.disabled = false;
                    if (item.disabled) throw new Error("MOGRT تأیید شد اما فعال‌سازی ممکن نشد");
                    result.inserted++;
                    if (!imported) result.updated++;
                    if (textCount > 0) result.textUpdated++;
                } catch (cueError) {
                    if (item) {
                        try {
                            $._hafez.disableItem(item);
                            result.disabled++;
                        } catch (disableError) {
                            result.safetyFailures++;
                            result.messages.push("SAFETY FAILURE: " + cue.id + " | " + disableError.message);
                        }
                    }
                    result.failed++;
                    result.messages.push("✕ " + cue.id + "/" + (layer.role || "graphic") + ": " + cueError.message);
                }
            }
        }
        if (muteGuide && result.failed === 0 && result.inserted === expectedMogrtCount) {
            if (sequence.videoTracks.numTracks > guideIndex) sequence.videoTracks[guideIndex].setMute(1);
            result.messages.push("V" + (guideIndex + 1) + " راهنما Mute شد؛ Track مستقل MOGRT فعال است.");
        }
        result.ok = result.failed === 0 && result.inserted === expectedMogrtCount;
        result.messages.push("پروژه عمداً Save نشد؛ پس از بازبینی خودت ذخیره کن.");
    } catch (error) {
        result.failed++;
        result.messages.push("خطای Finisher: " + error.message);
    }
    return $._hafez.stringify(result);
};
