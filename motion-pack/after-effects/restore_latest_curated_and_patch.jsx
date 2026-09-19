/* Restore the latest fully editable curated AEP saved before the broad QA
 * filter, re-enable the authored effect carriers, keep only BG disabled, and
 * run the production overlay exporter.
 */
(function restoreLatestCuratedAndPatch() {
    app.beginSuppressDialogs();
    var productRoot = new File($.fileName).parent.parent.parent;
    var latestSource = new File(productRoot.fsName + "/backups/mogrt-overlay-fix-20260902-170000/Hermes Studio Elements - accidental-wide-filter.aep");
    if (!latestSource.exists) throw new Error("Latest curated recovery file not found: " + latestSource.fsName);
    app.open(latestSource);

    function findComp(name) {
        for (var index = 1; index <= app.project.numItems; index++) {
            var item = app.project.item(index);
            if (item instanceof CompItem && item.name === name) return item;
        }
        return null;
    }

    var target = findComp("Hafez Hermes Glass Insight");
    if (!target) throw new Error("Priority Glass Insight comp not found");
    var preserve = {
        "Grid": true,
        "Grid 2": true,
        "Adjustment Layer 2": true,
        "Links": true,
        "Color": true
    };
    for (var layerIndex = 1; layerIndex <= target.numLayers; layerIndex++) {
        var layer = target.layer(layerIndex);
        if (preserve[String(layer.name)]) layer.enabled = true;
        if (String(layer.name).toLowerCase() === "bg") layer.enabled = false;
    }

    var curatedTarget = new File(productRoot.fsName + "/motion-pack/source/Hermes Studio Elements - Hafez Curated.aep");
    app.project.save(curatedTarget);

    var patchScript = new File(productRoot.fsName + "/motion-pack/after-effects/patch_curated_overlay_backgrounds.jsx");
    if (!patchScript.exists) throw new Error("Overlay patch script not found: " + patchScript.fsName);
    $.evalFile(patchScript);
})();
