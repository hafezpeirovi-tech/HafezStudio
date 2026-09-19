/* Scoped authoring job: diagnostic + isolated Review 8; no canonical promotion. */
(function () {
    var folder=new File($.fileName).parent;
    $.evalFile(new File(folder.fsName+"/audit_subscribe_runtime.jsx"));
    $.evalFile(new File(folder.fsName+"/build_glass_insight_review_8.jsx"));
})();
