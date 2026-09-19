(function () {
    var dist = new Folder("C:/Users/1SKY.IR/.n8n/products/HafezStudio/motion-pack/dist/qa-v4");
    if (!dist.exists) {
        dist.create();
    }

    var targets = [
        { name: "Hafez Chapter Billboard v6", time: 3.0, file: "chapter-billboard-v6.png" },
        { name: "Hafez Compact Flowchart v4", time: 3.0, file: "compact-flowchart-v4.png" },
        { name: "Hafez Word Lift Statement v4", time: 3.0, file: "word-lift-v4.png" },
        { name: "Hafez Word Lift Statement v4", time: 0.30, file: "word-lift-v4-030.png" },
        { name: "Hafez Word Lift Statement v4", time: 0.50, file: "word-lift-v4-050.png" },
        { name: "Hafez Word Lift Statement v4", time: 0.70, file: "word-lift-v4-070.png" },
        { name: "Hafez Word Lift Statement v4", time: 0.90, file: "word-lift-v4-090.png" },
        { name: "Hafez Face Safe Corner Note v4", time: 3.0, file: "face-safe-note-v4.png" }
    ];

    function findComp(name) {
        for (var i = 1; i <= app.project.numItems; i++) {
            var item = app.project.item(i);
            if (item instanceof CompItem && item.name === name) {
                return item;
            }
        }
        return null;
    }

    var report = [];
    for (var t = 0; t < targets.length; t++) {
        var target = targets[t];
        var comp = findComp(target.name);
        if (!comp) {
            report.push("MISSING: " + target.name);
            continue;
        }
        var output = new File(dist.fsName + "/" + target.file);
        comp.saveFrameToPng(target.time, output);
        report.push("OK: " + target.name + " -> " + output.fsName);
    }

    var log = new File(dist.fsName + "/qa-render.log");
    log.encoding = "UTF-8";
    log.open("w");
    log.write(report.join("\n"));
    log.close();
})();
