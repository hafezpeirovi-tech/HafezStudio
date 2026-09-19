(function inspectCuratedHermesElements() {
    var project = app.project;
    var lines = [];
    var curated = [];
    var exportFolder = null;

    if (!project) {
        alert("Hafez inspection: no project is open.");
        return;
    }

    for (var index = 1; index <= project.numItems; index += 1) {
        var item = project.item(index);
        if (item instanceof FolderItem && item.name === "HAFEZ CURATED EXPORTS") {
            exportFolder = item;
        }
        if (item instanceof CompItem && item.name.indexOf("Hafez Hermes") === 0) {
            var controlCount = "n/a";
            try {
                controlCount = item.motionGraphicsTemplateControllerCount;
            } catch (controlError) {
                controlCount = "error";
            }
            curated.push(item.name + " | layers=" + item.numLayers + " | controls=" + controlCount);
        }
    }

    lines.push("Hafez curated comps: " + curated.length);
    for (var curatedIndex = 0; curatedIndex < curated.length; curatedIndex += 1) {
        lines.push(curated[curatedIndex]);
    }

    if (exportFolder) {
        lines.push("");
        lines.push("Export folder children: " + exportFolder.numItems);
        for (var childIndex = 1; childIndex <= exportFolder.numItems; childIndex += 1) {
            var child = exportFolder.item(childIndex);
            lines.push(childIndex + ". " + child.name + " [" + child.typeName + "]");
        }
    } else {
        lines.push("");
        lines.push("Export folder: NOT FOUND");
    }

    alert(lines.join("\n"));
}());
