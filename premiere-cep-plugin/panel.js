(function () {
  "use strict";
  var applyButton = document.getElementById("apply");
  var logNode = document.getElementById("log");
  var stateNode = document.getElementById("state");
  var planNode = document.getElementById("planName");
  var running = false;

  function log(message) {
    logNode.textContent += "\n" + message;
    logNode.scrollTop = logNode.scrollHeight;
  }

  function evalScript(script, callback) {
    window.__adobe_cep__.evalScript(script, callback || function () {});
  }

  function jsxString(value) {
    return '"' + String(value).replace(/\\/g, "\\\\").replace(/"/g, '\\"') + '"';
  }

  function parseJsonData(data) {
    // CEP can expose an UTF-8 BOM either as U+FEFF or as the three
    // mojibake characters "ï»¿", depending on the host/code page.
    var clean = String(data || "")
      .replace(/^\uFEFF/, "")
      .replace(/^\u00EF\u00BB\u00BF/, "");
    return JSON.parse(clean);
  }

  function extensionPath(relativePath) {
    var root = decodeURI(window.__adobe_cep__.getSystemPath("extension"));
    if (/^file:\/\/\//i.test(root)) root = root.replace(/^file:\/\/\//i, "");
    else if (/^file:\/\//i.test(root)) root = root.replace(/^file:\/\//i, "");
    return String(root).replace(/[\\\/]$/, "") + "/" + relativePath.replace(/^\//, "");
  }

  function writeResult(requestId, payload) {
    var result = {
      request_id: requestId || "manual",
      completed_at: new Date().toISOString(),
      result: payload
    };
    window.cep.fs.writeFile(extensionPath("runtime/last-result.json"), JSON.stringify(result, null, 2));
  }

  function applyPlanPath(path, options) {
    options = options || {};
    if (running) {
      log("یک Finisher دیگر در حال اجراست؛ درخواست تکراری نادیده گرفته شد.");
      return;
    }
    var planRead = window.cep.fs.readFile(path);
    if (planRead.err) { log("خطا در خواندن Plan: " + planRead.err); return; }
    try {
      var plan = parseJsonData(planRead.data);
      if (plan.protocol !== "hermes-professional-edit-v2") throw new Error("Plan باید نسخه V2 باشد.");
      planNode.textContent = path.split(/[\\/]/).pop();
      log("Plan معتبر: " + plan.graphics.length + " موشن");
    } catch (error) {
      log("Plan نامعتبر: " + error.message);
      return;
    }
    running = true;
    applyButton.disabled = true;
    stateNode.textContent = "در حال اجرا";
    var muteEnabled = options.muteGuide === undefined ? document.getElementById("muteGuide").checked : !!options.muteGuide;
    var mute = muteEnabled ? "true" : "false";
    var bridgeCall = [
      "(function(){",
      "try{",
      "$.evalFile(new File(" + jsxString(extensionPath("jsx/hafez.jsx")) + "));",
      "if(typeof $._hafez==='undefined'||typeof $._hafez.applyPlan!=='function')throw new Error('Hafez JSX bridge is not loaded');",
      "return $._hafez.applyPlan(" + jsxString(path) + "," + mute + ");",
      "}catch(e){",
      "return '{\\\"ok\\\":false,\\\"inserted\\\":0,\\\"textUpdated\\\":0,\\\"failed\\\":1,\\\"messages\\\":[\\\"Bridge: '+String(e.message).replace(/\\\"/g,'\\\\\\\"')+' | line '+String(e.line||0)+'\\\"]}';",
      "}",
      "})()"
    ].join("");
    evalScript(bridgeCall, function (raw) {
      running = false;
      applyButton.disabled = false;
      try {
        var result = JSON.parse(raw);
        stateNode.textContent = result.ok ? "کامل شد" : "خطا";
        log("MOGRT: " + result.inserted + " | متن: " + result.textUpdated + " | خطا: " + result.failed);
        if (result.messages) result.messages.forEach(log);
        writeResult(options.requestId, result);
      } catch (error) {
        stateNode.textContent = "خطا";
        log("پاسخ نامعتبر Premiere: " + raw);
        writeResult(options.requestId, {ok:false, inserted:0, textUpdated:0, failed:1, messages:[String(raw)]});
      }
    });
  }

  function consumeAutomationRequest() {
    if (running) return; // Never consume another request during native mutation.
    var queuePath = extensionPath("runtime/active-plan.json");
    var queued = window.cep.fs.readFile(queuePath);
    if (!queued || queued.err || !queued.data) return;
    try {
      var request = parseJsonData(queued.data);
      if (!request.plan_path && !request.request_id) return; // Empty shipped queue.
      if (request.mode && ["apply", "inspect", "import_xml", "finish_glass"].indexOf(request.mode) < 0) throw new Error("حالت درخواست پشتیبانی نمی‌شود.");
      if (request.mode !== "import_xml" && !request.plan_path) throw new Error("plan_path در درخواست وجود ندارد.");
      if (request.mode === "import_xml" && !request.request_id) throw new Error("request_id برای import لازم است.");
      var requestId = String(request.request_id || request.plan_path);
      if (localStorage.getItem("hafez-last-request") === requestId) return;
      localStorage.setItem("hafez-last-request", requestId);
      if (request.mode === "finish_glass") {
        running = true; applyButton.disabled = true; stateNode.textContent = "ساخت بازبینی Glass";
        window.cep.fs.deleteFile(queuePath);
        var glassCall = "$.evalFile(new File(" + jsxString(extensionPath("jsx/hafez.jsx")) + "));" +
          "$.evalFile(new File(" + jsxString(extensionPath("jsx/glass-review.jsx")) + "));" +
          "$._hafez.finishGlassReview(" + jsxString(JSON.stringify(request)) + ")";
        evalScript(glassCall, function (raw) {
          running = false; applyButton.disabled = false;
          try {
            var glassResult = parseJsonData(raw);
            stateNode.textContent = glassResult.ok ? "پروژهٔ بازبینی ذخیره شد" : "نیاز به بررسی";
            if (glassResult.messages) glassResult.messages.forEach(log);
            writeResult(requestId, glassResult);
          } catch (error) { writeResult(requestId, {ok:false,messages:[String(raw)]}); }
        });
        return;
      }
      if (request.mode === "import_xml") {
        running = true;
        applyButton.disabled = true;
        stateNode.textContent = "در حال Import مستقل";
        window.cep.fs.deleteFile(queuePath);
        log("در حال Import XML به Bin مستقل؛ پروژه و شناسه سکانس کنترل می‌شوند…");
        var importCall = "$.evalFile(new File(" + jsxString(extensionPath("jsx/hafez.jsx")) + "));$._hafez.importXmlRequest(" + jsxString(JSON.stringify(request)) + ")";
        evalScript(importCall, function (raw) {
          running = false;
          applyButton.disabled = false;
          try {
            var imported = parseJsonData(raw);
            stateNode.textContent = imported.ok ? "Import تأیید شد" : "خطای Import";
            if (imported.messages) imported.messages.forEach(log);
            writeResult(requestId, imported);
          } catch (error) {
            stateNode.textContent = "خطای Import";
            writeResult(requestId, {ok:false, mode:"import_xml", messages:[String(raw)]});
          }
        });
        return;
      }
      if (request.mode === "inspect") {
        window.cep.fs.deleteFile(queuePath);
        log("در حال بررسی Track و پارامترهای MOGRT…");
        evalScript("$.evalFile(new File(" + jsxString(extensionPath("jsx/hafez.jsx")) + "));$._hafez.inspectTimeline(" + jsxString(JSON.stringify(request)) + ")", function (raw) {
          try {
            var report = parseJsonData(raw);
            log("گزارش Timeline آماده شد.");
            writeResult(requestId, report);
          } catch (error) {
            log("گزارش Timeline نامعتبر بود: " + raw);
            writeResult(requestId, {ok:false, error:String(raw)});
          }
        });
        return;
      }
      log("درخواست Hafez Studio دریافت شد؛ Finisher خودکار شروع می‌شود.");
      window.cep.fs.deleteFile(queuePath);
      applyPlanPath(request.plan_path, {requestId:requestId, muteGuide:request.mute_guide === true});
    } catch (error) {
      running = false;
      applyButton.disabled = false;
      stateNode.textContent = "خطا";
      log("درخواست خودکار نامعتبر: " + error.message);
      writeResult("invalid", {ok:false, inserted:0, textUpdated:0, failed:1, messages:[error.message]});
    }
  }

  applyButton.addEventListener("click", function () {
    var picker = window.cep.fs.showOpenDialog(false, false, "Hafez Premiere Plan را انتخاب کن", "", ["json"]);
    if (!picker || picker.err || !picker.data || !picker.data.length) return;
    applyPlanPath(picker.data[0], {requestId:"manual-" + Date.now()});
  });

  // Runtime jobs/receipts must never be shipped inside a new extension package.
  // CEP filesystem API: Adobe-CEP/CEP-Resources, CEPEngine_extensions.js.
  if (window.cep.fs.readdir(extensionPath("runtime")).err) {
    if (window.cep.fs.makedir(extensionPath("runtime")).err) {
      applyButton.disabled = true;
      stateNode.textContent = "پوشهٔ ارتباط Premiere قابل ساخت نیست";
      return;
    }
  }
  function glassHeartbeat() {
    window.cep.fs.writeFile(extensionPath("runtime/glass-heartbeat.json"),
      JSON.stringify({version:"glass-review-v1",at:Date.now(),running:running}));
  }
  glassHeartbeat();
  window.setInterval(glassHeartbeat, 10000);
  window.setTimeout(consumeAutomationRequest, 700);
  window.setInterval(consumeAutomationRequest, 1500);
})();
