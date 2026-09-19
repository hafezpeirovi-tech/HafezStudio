/* Headless entry point for the overlay patch. */
(function batchPatchCuratedOverlayBackgrounds() {
    var scriptFolder = new File($.fileName).parent;
    var productRoot = scriptFolder.parent.parent;
    var curatedFile = new File(productRoot.fsName + "/motion-pack/source/Hermes Studio Elements - Hafez Curated.aep");
    var patchFile = new File(scriptFolder.fsName + "/patch_curated_overlay_backgrounds.jsx");
    if (!curatedFile.exists) throw new Error("Missing curated project: " + curatedFile.fsName);
    if (!patchFile.exists) throw new Error("Missing overlay patch: " + patchFile.fsName);
    app.beginSuppressDialogs();
    app.open(curatedFile);
    $.evalFile(patchFile);
    app.project.save(curatedFile);
    app.endSuppressDialogs(false);
    app.quit();
})();
