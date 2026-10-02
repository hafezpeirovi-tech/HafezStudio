"use strict";
(() => {
  const el = id => document.getElementById(id);
  let output = null, running = false;
  const message = text => { el("reelsMessage").textContent = text; };
  function event(data) {
    if (data.output) output = data.output;
    if (data.message) message(data.message);
    if (data.progress != null) el("reelsProgress").value = data.progress;
    if (data.state) running = data.state === "running";
    el("reelsStart").disabled = running; el("reelsCancel").disabled = !running;
    el("reelsOpen").hidden = !output;
    if (data.result) {
      el("reelsResults").replaceChildren();
      for (const clip of data.result.clips || []) {
        const card = document.createElement("div"); card.className = "reels-result";
        const title = document.createElement("strong"); title.textContent = `${clip.id} · ${(clip.end - clip.start).toFixed(1)} ثانیه`;
        const text = document.createElement("p"); text.textContent = clip.text;
        const reason = document.createElement("small"); reason.textContent = clip.reason;
        card.append(title, text, reason); el("reelsResults").append(card);
      }
    }
  }
  const caught = fn => async () => { try { await fn(); } catch (error) { message(error.message); } };
  el("reelsInputMode").addEventListener("change", () => {
    el("reelsSource").value = ""; el("reelsProjectFields").hidden = el("reelsInputMode").value !== "project";
  });
  el("reelsPickSource").onclick = caught(async () => { const value = el("reelsInputMode").value === "project" ? await window.hermes.reelsFile("project") : await window.hermes.selectVideo(); if(value) el("reelsSource").value = value; });
  for (const [button, kind, target] of [["reelsPickPreset", "preset", "reelsPreset"], ["reelsPickSrt", "srt", "reelsSrt"]]) {
    el(button).onclick = caught(async () => { const value = await window.hermes.reelsFile(kind); if(value) el(target).value = value; });
  }
  el("reelsClearSrt").onclick = () => { el("reelsSrt").value = ""; };
  el("reelsForm").addEventListener("submit", async e => {
    e.preventDefault(); if(running) return;
    const input = { sequence: el("reelsSequence").value.trim(), preset: el("reelsPreset").value,
      srt: el("reelsSrt").value || null, count: Number(el("reelsCount").value),
      min_duration: Number(el("reelsMin").value), max_duration: Number(el("reelsMax").value),
      style: el("reelsStyle").value, selector: el("reelsSelector").value };
    input[el("reelsInputMode").value] = el("reelsSource").value;
    if(!input.video && !input.project) return message("فایل ورودی را انتخاب کن.");
    try { await window.hermes.reelsStart(input); } catch(error) { event({state:"failed",message:error.message}); }
  });
  el("reelsCancel").onclick = caught(() => window.hermes.reelsCancel());
  el("reelsOpen").onclick = caught(() => window.hermes.openPath(output));
  window.hermes.onReelsEvent(event);
  window.hermes.reelsStatus().then(status => {
    el("reelsReadiness").textContent = `موشن: ${status.templates.every(t=>t.ready) ? "قالب‌ها موجودند" : "قالب‌ها هنوز ساخته نشده‌اند"} · Gemini: ${status.aiConfigured ? "تنظیم شده" : "نیازمند تنظیم محلی"}`;
    if(status.last) event({...status.last, state:status.running ? "running" : status.last.state});
  }).catch(error => message(error.message));
})();
