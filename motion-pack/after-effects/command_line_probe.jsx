(function commandLineProbe() {
    var marker = new File("C:/Users/1SKY.IR/.n8n/products/HafezStudio/proof/ae-elements-audit/command-line-probe.log");
    marker.encoding = "UTF-8";
    marker.open("w");
    marker.writeln((new Date()).toUTCString() + " | OK");
    marker.close();
})();
