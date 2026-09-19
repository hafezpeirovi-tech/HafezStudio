/* Render controlled diagnostic frames to identify the remaining opaque plate
 * without sacrificing authored grid, tint, link or adjustment effects.
 */
(function diagnoseGlassInsightLayers() {
    app.beginSuppressDialogs();
    var productRoot = new File($.fileName).parent.parent.parent;
    var outputFolder = new Folder(productRoot.fsName + "/proof/ae-elements-audit/glass-insight-layer-diagnostics");
    if (!outputFolder.exists) outputFolder.create();

    function findComp(name) {
        for (var itemIndex = 1; itemIndex <= app.project.numItems; itemIndex++) {
            var item = app.project.item(itemIndex);
            if (item instanceof CompItem && item.name === name) return item;
        }
        return null;
    }

    var comp = findComp("Hafez Hermes Glass Insight");
    if (!comp) throw new Error("Priority Glass Insight comp not found");
    var names = ["BG", "Grid", "Grid 2", "Adjustment Layer 2", "Links", "Color", "HAFEZ · OPTIONAL BACKGROUND"];
    var layers = {};
    var originalStates = {};
    for (var layerIndex = 1; layerIndex <= comp.numLayers; layerIndex++) {
        var layer = comp.layer(layerIndex);
        var name = String(layer.name);
        for (var nameIndex = 0; nameIndex < names.length; nameIndex++) {
            if (name === names[nameIndex]) {
                layers[name] = layer;
                originalStates[name] = layer.enabled;
            }
        }
    }

    function setStates(disabledNames) {
        for (var stateIndex = 0; stateIndex < names.length; stateIndex++) {
            var stateName = names[stateIndex];
            if (!layers[stateName]) continue;
            var disabled = false;
            for (var disabledIndex = 0; disabledIndex < disabledNames.length; disabledIndex++) {
                if (stateName === disabledNames[disabledIndex]) disabled = true;
            }
            layers[stateName].enabled = !disabled;
        }
    }

    function render(label, disabledNames) {
        setStates(disabledNames);
        comp.saveFrameToPng(2.0, new File(outputFolder.fsName + "/" + label + ".png"));
    }

    render("00-baseline-all-enabled", []);
    render("01-bg-off", ["BG"]);
    render("02-bg-grid-off", ["BG", "Grid"]);
    render("03-bg-grid-grid2-off", ["BG", "Grid", "Grid 2"]);
    render("04-bg-adjustment-off", ["BG", "Adjustment Layer 2"]);
    render("05-bg-links-off", ["BG", "Links"]);
    render("06-bg-color-off", ["BG", "Color"]);
    render("07-bg-grid-grid2-adjustment-off", ["BG", "Grid", "Grid 2", "Adjustment Layer 2"]);
    render("08-only-hafez-and-authored-content", names);
    render("09-bg-and-optional-background-off", ["BG", "HAFEZ · OPTIONAL BACKGROUND"]);
    render("10-all-carriers-and-optional-background-off", names);

    for (var restoreIndex = 0; restoreIndex < names.length; restoreIndex++) {
        var restoreName = names[restoreIndex];
        if (layers[restoreName]) layers[restoreName].enabled = originalStates[restoreName];
    }
    app.endSuppressDialogs(false);
})();
