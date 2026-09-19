/* Open the user-owned source AEP, immediately save a HafezStudio-owned copy,
 * then rebuild/export the curated editable MOGRT catalog.
 *
 * The curation script performs Save As before mutating any project item, so
 * D:/AE proj/Hermes Studio Elements.aep remains unchanged.
 */

(function rebuildCuratedHermesElements() {
    app.beginSuppressDialogs();
    var sourceProject = new File("D:/AE proj/Hermes Studio Elements.aep");
    if (!sourceProject.exists) throw new Error("Missing source AEP: " + sourceProject.fsName);
    app.open(sourceProject);

    var scriptFolder = new File($.fileName).parent;
    var curator = new File(scriptFolder.fsName + "/curate_hermes_elements.jsx");
    if (!curator.exists) throw new Error("Missing curator script: " + curator.fsName);
    $.evalFile(curator);
    app.endSuppressDialogs(false);
})();
