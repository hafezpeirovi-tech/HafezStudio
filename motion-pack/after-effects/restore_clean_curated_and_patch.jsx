/* Recover the curated AEP from the pre-QA backup, while preserving the current
 * generated copy for rollback, then apply the precise overlay-plate patch.
 */
(function restoreCleanCuratedAndPatch() {
    var productRoot = new File($.fileName).parent.parent.parent;
    var recoveryFolder = new Folder(productRoot.fsName + "/backups/mogrt-overlay-fix-20260902-170000");
    if (!recoveryFolder.exists) recoveryFolder.create();

    var currentRecovery = new File(recoveryFolder.fsName + "/Hermes Studio Elements - accidental-wide-filter.aep");
    if (app.project && app.project.file) app.project.save(currentRecovery);

    var cleanSource = new File(productRoot.fsName + "/backups/premiere-mogrt-text-fix-20260902-153757/motion-pack/source/Hermes Studio Elements - Hafez Curated.aep");
    if (!cleanSource.exists) throw new Error("Clean curated backup not found: " + cleanSource.fsName);
    app.open(cleanSource);

    var curatedTarget = new File(productRoot.fsName + "/motion-pack/source/Hermes Studio Elements - Hafez Curated.aep");
    app.project.save(curatedTarget);

    var patchScript = new File(productRoot.fsName + "/motion-pack/after-effects/patch_curated_overlay_backgrounds.jsx");
    if (!patchScript.exists) throw new Error("Overlay patch script not found: " + patchScript.fsName);
    $.evalFile(patchScript);
})();
