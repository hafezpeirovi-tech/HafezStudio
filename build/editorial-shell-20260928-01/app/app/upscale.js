"use strict";
(() => {
  const el = id => document.getElementById(id);
  let busy = false, externalRunning = false, installed = false, previewReady = false, output = "", engines = {};
  function controls() {
    el("upPreview").disabled = busy || !installed || !el("upInput").value;
    el("upFull").disabled = busy || !installed || !el("upInput").value;
    el("upCancel").disabled = !busy || externalRunning;
    ["upChoose", "upEngine", "upResolution", "upStart", "upConfirm"].forEach(id => el(id).disabled = busy);
    el("upOpen").disabled = !output;
  }
  function invalidate() {
    previewReady = false; el("upConfirm").checked = false;
    el("upComparison").hidden = el("upCompareLabel").hidden = true;
    controls();
  }
  async function refresh() {
    try {
      const info = await window.hermes.upscaleStatus();
      engines = info.engines || {}; installed = engines[el('upEngine').value]?.installed ?? info.installed; busy = info.running;
      externalRunning = info.externalRunning;
      if (externalRunning) el("upStatus").textContent = "آزمون Upscale از پردازش دیگری در حال اجراست. پس از پایان، بررسی نصب را بزن؛ این پنجره پردازش دیگری را متوقف نمی‌کند.";
      el("upInstalled").textContent = (engines[el('upEngine').value]?.label || 'WebSR') + (installed ? ' · آماده؛ کیفیت خروجی را بازبینی کن.' : ' · نصب کامل نیست.');
    } catch (error) { el("upInstalled").textContent = error.message; }
    controls();
  }
  async function start(mode) {
    if (mode === "preview") { previewReady = false; el("upConfirm").checked = false; }
    busy = true; output = ""; controls();
    el("upStatus").textContent = "آماده‌سازی و کنترل ورودی…";
    el("upProgress").removeAttribute("value");
    try {
      const result = await window.hermes.upscaleStart({ input: el("upInput").value,
        resolution: Number(el("upResolution").value), start: Number(el("upStart").value),
        mode, engine: el('upEngine').value, qualityConfirmed: el("upConfirm").checked });
      output = result.jobDir;
    } catch (error) { busy = false; el("upStatus").textContent = error.message; el("upProgress").value = 0; }
    controls();
  }
  el("upChoose").onclick = async () => {
    const file = await window.hermes.selectVideo();
    if (file) { el("upInput").value = file; invalidate(); }
  };
  el("upResolution").onchange = invalidate;
  el('upEngine').onchange = () => { invalidate(); refresh(); };
  el("upStart").onchange = invalidate;
  el("upConfirm").onchange = controls;
  el("upRefresh").onclick = refresh;
  el("upPreview").onclick = () => start("preview");
  el("upFull").onclick = () => start("full");
  el("upCancel").onclick = async () => {
    try { const accepted = await window.hermes.upscaleCancel(); el("upStatus").textContent = accepted ? "در حال توقف پردازش…" : "پردازش فعالی متعلق به این پنجره نیست."; }
    catch (error) { el("upStatus").textContent = error.message; }
  };
  el("upOpen").onclick = () => window.hermes.openPath(output);
  window.hermes.onUpscaleEvent(event => {
    if (event.jobDir) output = event.jobDir;
    if (event.progress !== undefined) el("upProgress").value = event.progress;
    if (event.message || event.error) el("upStatus").textContent = event.error || event.message;
    if (event.etaSeconds) el("upStatus").textContent += ` · تخمین باقی‌مانده: ${Math.ceil(event.etaSeconds / 60)} دقیقه`;
    if (event.stage === "completed") {
      if (event.preview) previewReady = true;
      el("upStatus").textContent = `پردازش تمام شد (${Math.round(event.seconds)} ثانیه). برای تأیید کیفیت، حرکت و جزئیات را بازبینی کن.`;
      if (event.image) { el("upComparison").src = event.image; el("upComparison").hidden = el("upCompareLabel").hidden = false; }
    }
    if (["idle", "failed", "cancelled"].includes(event.stage)) { busy = event.stage === "failed"; }
    controls();
  });
  refresh();
})();
