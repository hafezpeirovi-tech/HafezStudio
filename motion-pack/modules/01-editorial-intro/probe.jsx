(function () {
    var out = new File('C:/Users/1SKY.IR/.n8n/products/HafezStudio/motion-pack/modules/01-editorial-intro/ae-probe.txt');
    out.encoding = 'UTF-8';
    out.open('w');
    out.writeln('After Effects ' + app.version);
    out.writeln('items=' + (app.project ? app.project.numItems : 0));
    out.writeln('savedProject=' + Boolean(app.project && app.project.file));
    out.close();
})();
