/* Resume-safe exporter for the already-curated Hermes element comps.
 * Always resolves a fresh CompItem after MOGRT export because After Effects
 * invalidates scripting handles while packaging a template.
 */

(function exportCuratedHermesElements() {
    app.beginSuppressDialogs();
    var scriptFolder = new File($.fileName).parent;
    var productRoot = scriptFolder.parent.parent;
    var outputFolder = new Folder(productRoot.fsName + "/motion-pack/dist");
    var previewFolder = new Folder(productRoot.fsName + "/proof/ae-elements-audit/curated-previews");
    if (!outputFolder.exists) outputFolder.create();
    if (!previewFolder.exists) previewFolder.create();

    var specs = [
        {id:"hermes-glass-pill", name:"Hafez Hermes Glass Pill", priority:false},
        {id:"hermes-glass-insight", name:"Hafez Hermes Glass Insight", priority:true},
        {id:"hermes-glass-kpi", name:"Hafez Hermes Glass KPI", priority:true},
        {id:"hermes-glass-quote", name:"Hafez Hermes Glass Quote", priority:true},
        {id:"hermes-glass-selector", name:"Hafez Hermes Glass Selector", priority:false},
        {id:"hermes-subscribe", name:"Hafez Hermes Subscribe", priority:true},
        {id:"hermes-price-list", name:"Hafez Hermes Price List", priority:false},
        {id:"hermes-revenue-chart", name:"Hafez Hermes Revenue Chart", priority:true},
        {id:"hermes-saving-balance", name:"Hafez Hermes Saving Balance", priority:false},
        {id:"hermes-weekly-progress", name:"Hafez Hermes Weekly Progress", priority:false},
        {id:"hermes-user-growth", name:"Hafez Hermes User Growth", priority:true},
        {id:"hermes-flowchart", name:"Hafez Hermes Flowchart", priority:true},
        {id:"hermes-title-hero-3", name:"Hafez Hermes Title Hero 3", priority:true},
        {id:"hermes-title-hero-2", name:"Hafez Hermes Title Hero 2", priority:true}
    ];

    function findComp(name) {
        for (var index = 1; index <= app.project.numItems; index++) {
            var item = app.project.item(index);
            if (item instanceof CompItem && item.name === name) return item;
        }
        return null;
    }

    if (!app.project || !app.project.file) throw new Error("Open the curated saved AEP before exporting");
    var projectFile = app.project.file;
    for (var index = 0; index < specs.length; index++) {
        var spec = specs[index];
        var existing = new File(outputFolder.fsName + "/" + spec.name + ".mogrt");
        if (!existing.exists) {
            var target = findComp(spec.name);
            if (!target) continue;
            target.motionGraphicsTemplateName = spec.name;
            app.project.save(projectFile);
            try { target.exportAsMotionGraphicsTemplate(true, outputFolder.fsName); } catch (_) {}
        }
        if (spec.priority) {
            var preview = new File(previewFolder.fsName + "/" + spec.id + ".png");
            if (!preview.exists) {
                var previewComp = findComp(spec.name);
                if (previewComp) {
                    try { previewComp.saveFrameToPng(Math.min(previewComp.duration * .5, Math.max(0, previewComp.duration - .05)), preview); } catch (_) {}
                }
            }
        }
    }
    app.project.save(projectFile);
    app.endSuppressDialogs(false);
})();
