"use strict";

const $ = (selector) => document.querySelector(selector);
const ADAPTIVE_MIN = 0;
const ADAPTIVE_MAX = 100;
const ADAPTIVE_DEFAULT = 82;
const state = { cam1: "", cam2: "", config: null, brandTokens: null, running: false, mode: "youtube", view: "director", resources: null, doctor: null, previewPlaying: true, latestPlan: "", currentOutput: "", adaptiveValue: ADAPTIVE_DEFAULT, progress: 0, jobStage: "analyze" };
const PIPELINE_STAGES = [
  { id: "analyze", start: 0, end: 49, label: "تحلیل، سینک و پیاده‌سازی گفتار" },
  { id: "direct", start: 50, end: 64, label: "کارگردانی، ریتم و انتخاب دوربین" },
  { id: "design", start: 65, end: 81, label: "موشن، MOGRT و جانمایی امن" },
  { id: "finish", start: 82, end: 100, label: "صدا، Premiere XML و کنترل نهایی" }
];

function normalizeAdaptiveValue(value, fallback = ADAPTIVE_DEFAULT) {
  const numeric = Number(value);
  if (!Number.isFinite(numeric) || numeric < ADAPTIVE_MIN || numeric > ADAPTIVE_MAX) return fallback;
  return Math.round(numeric);
}

function adaptiveProgress(value = state.adaptiveValue) {
  return ((value - ADAPTIVE_MIN) / (ADAPTIVE_MAX - ADAPTIVE_MIN)) * 100;
}

function renderAdaptiveValue() {
  const input = $("#glowIntensity");
  const output = $("#glowValue");
  if (!input || !output) return;
  const value = normalizeAdaptiveValue(state.adaptiveValue);
  const progress = adaptiveProgress(value);
  state.adaptiveValue = value;
  input.value = String(value);
  input.style.setProperty("--slider-progress", `${progress}%`);
  input.setAttribute("aria-valuetext", `${value}%`);
  output.textContent = `${value}%`;
}

function setAdaptiveValue(value, { updatePreview = true } = {}) {
  state.adaptiveValue = normalizeAdaptiveValue(value);
  if (state.config) {
    state.config.adaptiveValue = state.adaptiveValue;
    state.config.glowIntensity = state.adaptiveValue / 100;
  }
  renderAdaptiveValue();
  if (updatePreview) syncPreviewLook();
}

function persistedAdaptiveValue(config) {
  const explicit = Number(config?.adaptiveValue);
  if (Number.isFinite(explicit) && explicit >= ADAPTIVE_MIN && explicit <= ADAPTIVE_MAX) {
    return normalizeAdaptiveValue(explicit);
  }
  const legacyGlow = Number(config?.glowIntensity);
  if (Number.isFinite(legacyGlow) && legacyGlow >= 0 && legacyGlow <= 1) {
    return normalizeAdaptiveValue(legacyGlow * 100);
  }
  return ADAPTIVE_DEFAULT;
}

function applyBrandTokens(tokens) {
  if (!tokens?.palette) return;
  state.brandTokens = tokens;
  const root = document.documentElement;
  root.dataset.brand = tokens.id || "hafez-premium-neon";
  const paletteMap = {
    "--brand-canvas": "canvas",
    "--brand-surface": "surface",
    "--brand-surface-elevated": "surfaceElevated",
    "--brand-surface-active": "surfaceActive",
    "--brand-positive": "primaryAccent",
    "--brand-positive-soft": "primaryAccentSoft",
    "--brand-negative": "negativeAccent",
    "--brand-text-primary": "textPrimary",
    "--brand-text-secondary": "textSecondary",
    "--brand-border": "borderSubtle"
  };
  Object.entries(paletteMap).forEach(([cssName, tokenName]) => root.style.setProperty(cssName, tokens.palette[tokenName]));
  root.style.setProperty("--brand-radius-card", `${tokens.radius?.card || 40}px`);
  root.style.setProperty("--brand-radius-control", `${tokens.radius?.control || 24}px`);
  root.style.setProperty("--brand-radius-compact", `${tokens.radius?.compact || 16}px`);
  root.style.setProperty("--brand-radius-pill", `${tokens.radius?.pill || 999}px`);
  root.style.setProperty("--brand-glow-radius", `${tokens.glow?.radiusPx || 34}px`);
  root.style.setProperty("--brand-glow-bloom", `${tokens.glow?.bloomPx || 76}px`);
  root.style.setProperty("--brand-glow-alpha", String(tokens.glow?.outerAlpha ?? 0.28));
}

const youtubeViewCopy = {
  director: { kicker: "YOUTUBE · AI VIDEO OPERATING SYSTEM", title: "YouTube Director" },
  motion: { kicker: "YOUTUBE · MOTION DESIGN SYSTEM", title: "Motion Design" },
  audio: { kicker: "YOUTUBE · VOICE FINISHING SYSTEM", title: "Voice Lab" },
  integrations: { kicker: "YOUTUBE · LOCAL INTEGRATIONS", title: "Integrations" },
  settings: { kicker: "HAFEZ STUDIO · CONFIGURATION", title: "Settings" }
};

const modeCopy = {
  reels: {
    kicker: "REELS · PHASE 02",
    title: "Reels Studio",
    icon: "layout",
    phase: "PHASE 02 · NEXT",
    copy: "پس از تأیید کامل پایپ‌لاین YouTube، موتور عمودی و ریتم مخصوص ریلز در این بخش فعال می‌شود.",
    steps: ["9:16 Reframe", "Hook First", "Fast Captions", "Loop Ending"]
  },
  podcast: {
    kicker: "PODCAST · PHASE 03",
    title: "Podcast Studio",
    icon: "podcast",
    phase: "PHASE 03 · LATER",
    copy: "بعد از نهایی‌شدن YouTube و Reels، تدوین چندنفره، میکس گفت‌وگو و نسخه صوتی پادکست اینجا اضافه می‌شود.",
    steps: ["Speaker Cut", "Multi Mic", "Audio Story", "Chapters"]
  }
};

function iconMarkup(name, className = "thin-icon") {
  return `<svg class="${className}" aria-hidden="true"><use href="#i-${name}"></use></svg>`;
}

function fileName(value) {
  if (!value) return "برای انتخاب کلیک کن";
  return value.split(/[\\/]/).pop();
}

function appendLog(line, kind = "") {
  const cleanLine = String(line || "").replace(/\x1B(?:[@-Z\\-_]|\[[0-?]*[ -\/]*[@-~])/g, "").replace(/[\u0000-\u0008\u000B\u000C\u000E-\u001F\u007F]/g, "").trim();
  if (!cleanLine) return;
  const item = document.createElement("div");
  item.className = kind === "stderr" ? "warning" : kind;
  item.textContent = cleanLine;
  $("#console").appendChild(item);
  while ($("#console").children.length > 80) $("#console").firstElementChild.remove();
  $("#console").scrollTop = $("#console").scrollHeight;
}

function clampProgress(value) {
  const numeric = Number(value);
  return Number.isFinite(numeric) ? Math.max(0, Math.min(100, Math.round(numeric))) : state.progress;
}

function stageForProgress(progress) {
  return PIPELINE_STAGES.find((item) => progress <= item.end)?.id || "finish";
}

function renderJobProgress({ progress = state.progress, stage = "", message = "", jobState = "" } = {}) {
  const normalized = clampProgress(progress);
  const stageId = PIPELINE_STAGES.some((item) => item.id === stage) ? stage : stageForProgress(normalized);
  state.progress = normalized;
  state.jobStage = stageId;
  if (jobState) document.body.dataset.jobState = jobState;

  const activeStage = PIPELINE_STAGES.find((item) => item.id === stageId) || PIPELINE_STAGES[0];
  const failed = document.body.dataset.jobState === "failed";
  const completedJob = document.body.dataset.jobState === "completed";
  document.querySelectorAll(".director-pipeline .stage").forEach((node) => {
    const item = PIPELINE_STAGES.find((candidate) => candidate.id === node.dataset.stage);
    const complete = completedJob || normalized >= item.end;
    const active = !completedJob && node.dataset.stage === stageId && normalized > 0;
    node.classList.toggle("complete", complete);
    node.classList.toggle("active", active && !failed);
    node.classList.toggle("failed", active && failed);
    const localProgress = complete ? 100 : active ? ((normalized - item.start) / Math.max(1, item.end - item.start)) * 100 : 0;
    node.style.setProperty("--stage-progress", `${Math.max(0, Math.min(100, localProgress))}%`);
  });
  document.querySelectorAll(".director-pipeline .connector").forEach((node) => {
    const item = PIPELINE_STAGES.find((candidate) => candidate.id === node.dataset.connector);
    node.classList.toggle("complete", completedJob || normalized >= item.end);
  });

  $("#progressBar").style.width = `${normalized}%`;
  $("#progressValue").textContent = `${normalized}%`;
  $("#progressTrack").setAttribute("aria-valuenow", String(normalized));
  $("#currentStageLabel").textContent = failed ? (message || "تدوین به‌دلیل خطا متوقف شد") : (message || activeStage.label);
}

function closeCustomSelects(except = null) {
  document.querySelectorAll(".select-shell.open").forEach((shell) => {
    if (shell === except) return;
    shell.classList.remove("open");
    shell.querySelector(".select-trigger")?.setAttribute("aria-expanded", "false");
  });
}

function setupCustomSelects() {
  document.querySelectorAll(".director-settings select").forEach((select) => {
    if (select.dataset.enhanced === "true") return;
    select.dataset.enhanced = "true";
    select.classList.add("native-select");
    const shell = document.createElement("div");
    shell.className = "select-shell";
    select.parentNode.insertBefore(shell, select);
    shell.appendChild(select);
    const trigger = document.createElement("button");
    trigger.type = "button";
    trigger.className = "select-trigger";
    trigger.setAttribute("aria-haspopup", "listbox");
    trigger.setAttribute("aria-expanded", "false");
    const value = document.createElement("span");
    const chevron = document.createElement("i");
    chevron.textContent = "⌄";
    trigger.append(value, chevron);
    const menu = document.createElement("div");
    menu.className = "select-menu";
    menu.setAttribute("role", "listbox");

    const sync = () => {
      value.textContent = select.selectedOptions[0]?.textContent || "";
      menu.querySelectorAll("button").forEach((button) => {
        const selected = button.dataset.value === select.value;
        button.classList.toggle("selected", selected);
        button.setAttribute("aria-selected", String(selected));
      });
    };
    Array.from(select.options).forEach((option) => {
      const button = document.createElement("button");
      button.type = "button";
      button.setAttribute("role", "option");
      button.dataset.value = option.value;
      button.innerHTML = `<span></span><i>✓</i>`;
      button.querySelector("span").textContent = option.textContent;
      button.addEventListener("click", () => {
        select.value = option.value;
        select.dispatchEvent(new Event("change", { bubbles: true }));
        sync();
        closeCustomSelects();
      });
      menu.appendChild(button);
    });
    trigger.addEventListener("click", (event) => {
      event.stopPropagation();
      const opening = !shell.classList.contains("open");
      closeCustomSelects(shell);
      shell.classList.toggle("open", opening);
      trigger.setAttribute("aria-expanded", String(opening));
    });
    select.addEventListener("change", sync);
    shell.append(trigger, menu);
    sync();
  });
  document.addEventListener("click", () => closeCustomSelects());
  document.addEventListener("keydown", (event) => { if (event.key === "Escape") closeCustomSelects(); });
}

function selectView(view) {
  const copy = youtubeViewCopy[view];
  if (!copy) return;
  state.view = view;
  document.body.dataset.view = view;
  document.querySelectorAll(".nav").forEach((button) => button.classList.toggle("active", button.dataset.view === view));
  if (state.mode !== "youtube") return;
  $("#plannedWorkspace").hidden = true;
  document.querySelectorAll(".studio-view").forEach((panel) => { panel.hidden = panel.dataset.youtubeView !== view; });
  $("#workspaceKicker").textContent = copy.kicker;
  $("#workspaceTitle").textContent = copy.title;
}

function selectMode(mode) {
  state.mode = mode;
  document.querySelectorAll(".mode").forEach((button) => button.classList.toggle("active", button.dataset.mode === mode));
  const youtube = mode === "youtube";
  if (youtube) {
    selectView(state.view);
    return;
  }
  document.body.dataset.view = "planned";
  document.querySelectorAll(".studio-view").forEach((panel) => { panel.hidden = true; });
  $("#plannedWorkspace").hidden = false;
  const copy = modeCopy[mode];
  $("#workspaceKicker").textContent = copy.kicker;
  $("#workspaceTitle").textContent = copy.title;
  $("#plannedIcon").innerHTML = iconMarkup(copy.icon, "thin-icon planned-icon");
  $("#plannedPhase").textContent = copy.phase;
  $("#plannedTitle").textContent = copy.title;
  $("#plannedCopy").textContent = copy.copy;
  $("#plannedWorkspace .planned-steps").innerHTML = copy.steps.map((step) => `<span>${step}</span>`).join("");
}

function updateDirectorReadiness() {
  const ready = [state.cam1, state.cam2].filter(Boolean).length;
  const value = $("#directorReadinessValue");
  const copy = $("#directorReadinessCopy");
  if (value) value.textContent = String(ready);
  if (copy) {
    copy.textContent = ready === 2
      ? "هر دو دوربین آماده‌اند؛ تدوین می‌تواند شروع شود."
      : ready === 1
        ? "یک فایل آماده است؛ دوربین دوم را هم انتخاب کن."
        : "دو فایل دوربین را انتخاب کن تا پروژه آمادهٔ تدوین شود.";
  }
}

function uiConfig() {
  return {
    ...state.config,
    stylePack: $("#stylePack").value,
    performanceProfile: $("#performanceProfile").value,
    graphicDensity: $("#graphicDensity").value,
    languageMode: $("#languageMode").value,
    titleFontPath: state.config.titleFontPath || "",
    titleFontName: state.config.titleFontName || "Auto Persian Display",
    titleFontWeight: Number($("#titleFontWeight").value),
    bodyFontPath: state.config.bodyFontPath || "",
    bodyFontName: state.config.bodyFontName || "Auto Persian Text",
    bodyFontWeight: Number($("#bodyFontWeight").value),
    theme: document.documentElement.dataset.theme || "dark",
    adaptiveValue: state.adaptiveValue,
    glowIntensity: state.adaptiveValue / 100,
    copyMode: $("#copyMode")?.value || "source-faithful",
    revealSpeed: Number($("#revealSpeed")?.value || 42) / 100,
    liftDistance: Number($("#liftDistance")?.value || 50),
    revealBlur: Number($("#revealBlur")?.value || 10),
    faceClearance: Number($("#faceClearance")?.value || 16) / 100,
    editableMogrtOnly: $("#editableMogrtOnly")?.checked !== false
  };
}

function applyTheme(theme) {
  const normalized = theme === "light" ? "light" : "dark";
  document.documentElement.dataset.theme = normalized;
  const button = $("#themeButton");
  if (button) {
    button.querySelector(".theme-icon").innerHTML = iconMarkup(normalized === "dark" ? "sun" : "moon");
    button.querySelector(".theme-light").textContent = normalized === "dark" ? "روشن" : "تیره";
    button.title = normalized === "dark" ? "فعال‌کردن حالت روشن" : "فعال‌کردن حالت تیره";
  }
}

function applyConfig(config) {
  state.config = config;
  applyTheme(config.theme);
  $("#stylePack").value = config.stylePack;
  $("#performanceProfile").value = config.performanceProfile || "maximum";
  $("#graphicDensity").value = config.graphicDensity;
  $("#languageMode").value = config.languageMode;
  setAdaptiveValue(persistedAdaptiveValue(config), { updatePreview: false });
  $("#settingsOutput").value = config.outputRoot || "";
  $("#settingsTheme").value = config.theme === "light" ? "light" : "dark";
  $("#titleFontWeight").value = String(config.titleFontWeight || 800);
  $("#bodyFontWeight").value = String(config.bodyFontWeight || 400);
  if ($("#copyMode")) $("#copyMode").value = config.copyMode || "source-faithful";
  if ($("#revealSpeed")) $("#revealSpeed").value = String(Math.round((config.revealSpeed || 0.42) * 100));
  if ($("#liftDistance")) $("#liftDistance").value = String(config.liftDistance || 50);
  if ($("#revealBlur")) $("#revealBlur").value = String(config.revealBlur ?? 10);
  if ($("#faceClearance")) $("#faceClearance").value = String(Math.round((config.faceClearance || 0.16) * 100));
  if ($("#editableMogrtOnly")) $("#editableMogrtOnly").checked = config.editableMogrtOnly !== false;
  document.querySelectorAll(".preview-title-font").forEach((item) => { item.style.fontWeight = String(config.titleFontWeight || 800); });
  document.querySelectorAll(".preview-body-font").forEach((item) => { item.style.fontWeight = String(config.bodyFontWeight || 400); });
  showFontSelection("title", { path: config.titleFontPath, name: config.titleFontName || "Auto Persian Display" });
  showFontSelection("body", { path: config.bodyFontPath, name: config.bodyFontName || "Auto Persian Text" });
  syncPreviewLook();
  loadPreviewFont("title", config.titleFontPath);
  loadPreviewFont("body", config.bodyFontPath);
}

function restartPreview() {
  const stage = $("#previewStage");
  stage.classList.remove("is-playing");
  void stage.offsetWidth;
  stage.classList.add("is-playing");
  state.previewPlaying = true;
  $("#previewPlay").textContent = "توقف";
}

function syncPreviewLook() {
  const stage = $("#previewStage");
  if (!stage) return;
  const profile = $("#stylePack").value || "signal-os";
  stage.classList.remove("profile-signal-os", "profile-neural-glass", "profile-luxury-tech");
  stage.classList.add(`profile-${profile === "glass" ? "neural-glass" : profile}`);
  stage.dataset.density = $("#graphicDensity").value;
  stage.dataset.language = $("#languageMode").value;
  const glow = state.adaptiveValue;
  stage.style.setProperty("--preview-glow", String(glow / 100));
  const revealSpeed = Number($("#revealSpeed")?.value || 42);
  const liftDistance = Number($("#liftDistance")?.value || 50);
  const revealBlur = Number($("#revealBlur")?.value || 10);
  stage.style.setProperty("--reveal-speed", `${revealSpeed / 100}s`);
  stage.style.setProperty("--lift-distance", `${liftDistance}px`);
  stage.style.setProperty("--reveal-blur", `${revealBlur}px`);
  $("#previewGlow").value = String(glow);
  $("#previewGlowValue").textContent = `${glow}%`;
  if ($("#revealSpeedValue")) $("#revealSpeedValue").textContent = `${(revealSpeed / 100).toFixed(2)}s`;
  if ($("#liftDistanceValue")) $("#liftDistanceValue").textContent = `${liftDistance}px`;
  if ($("#revealBlurValue")) $("#revealBlurValue").textContent = `${revealBlur}px`;
  if ($("#faceClearanceValue")) $("#faceClearanceValue").textContent = `${$("#faceClearance")?.value || 16}%`;
  document.querySelectorAll(".profile-card").forEach((card) => {
    const active = card.dataset.profile === profile;
    card.classList.toggle("active", active);
    card.querySelector("em").textContent = active ? "ACTIVE" : "VIEW";
  });
}

function selectPreviewSection(section) {
  document.querySelectorAll(".preview-section").forEach((button) => button.classList.toggle("active", button.dataset.previewSection === section));
  document.querySelectorAll(".preview-panel").forEach((panel) => { panel.hidden = panel.dataset.previewPanel !== section; });
  if (section !== "rhythm") $("#previewStage").classList.remove("rhythm-mode");
}

function showFontSelection(role, selection) {
  const name = selection?.name || "Auto Persian";
  const path = selection?.path || "";
  $(`#${role}FontName`).textContent = name;
  $(`#${role}FontPath`).textContent = path ? fileName(path) : "فونت پیش‌فرض قابل‌حمل";
  $(`#${role}FontPath`).title = path;
  if (state.config) {
    state.config[`${role}FontName`] = name;
    state.config[`${role}FontPath`] = path;
  }
  updateFontCompatibility();
}

async function loadPreviewFont(role, fontPath) {
  if (!fontPath) return;
  try {
    const payload = await window.hermes.loadFont(fontPath);
    if (!payload?.dataUrl) return;
    const family = `HafezPreview${role === "title" ? "Title" : "Body"}`;
    const face = new FontFace(family, `url(${payload.dataUrl})`);
    await face.load();
    document.fonts.add(face);
    document.querySelectorAll(role === "title" ? ".preview-title-font" : ".preview-body-font").forEach((item) => { item.style.fontFamily = `"${family}", Estedad, sans-serif`; });
  } catch (error) {
    $("#fontCompatibility small").textContent = `پیش‌نمایش فونت بارگذاری نشد: ${error.message || error}`;
  }
}

function updateFontCompatibility() {
  if (!state.config || !$("#fontCompatibility")) return;
  const paths = [state.config.titleFontPath, state.config.bodyFontPath].filter(Boolean);
  const installed = paths.length > 0 && paths.every((value) => /[\\/]Windows[\\/]Fonts[\\/]|[\\/]Microsoft[\\/]Windows[\\/]Fonts[\\/]/i.test(value));
  $("#fontCompatibility b").textContent = installed ? "Adobe Font Ready + Exact PNG" : "Exact PNG Output";
  $("#fontCompatibility small").textContent = installed ? "فونت‌های انتخابی در پوشه فونت ویندوز هستند و برای Adobe آماده‌اند." : "PNG دقیق است؛ برای ویرایش Font داخل MOGRT همان فونت را روی سیستم Adobe نصب کن.";
}

async function runDoctor() {
  $("#engineStatus").textContent = "در حال بررسی…";
  const report = await window.hermes.doctor();
  state.doctor = report;
  const yesNo = (value) => value ? "READY" : "—";
  $("#engineStatus").textContent = report.ok && report.asr?.ok ? "Engine و ASR آماده‌اند" : "Engine نیاز به بررسی دارد";
  $("#premiereStatus").textContent = yesNo(report.adobe?.premiere);
  $("#aeStatus").textContent = yesNo(report.adobe?.afterEffects);
  $("#gpuStatus").textContent = report.gpu?.label || "AUTO";
  $("#settingsEngine").textContent = report.ok ? "READY" : "CHECK REQUIRED";
  if (!report.ok) appendLog(report.error || "Engine doctor failed", "stderr");
  return report;
}

function setIntegrationStatus(selector, ready, readyText = "READY") {
  const item = $(selector);
  item.textContent = ready ? readyText : "OFFLINE";
  item.classList.toggle("ready", Boolean(ready));
}

async function refreshIntegrations() {
  const report = await runDoctor();
  const bridge = await window.hermes.getIntegrations();
  setIntegrationStatus("#integrationPremiere", report.adobe?.premiere);
  setIntegrationStatus("#integrationAE", report.adobe?.afterEffects);
  setIntegrationStatus("#integrationN8n", bridge.n8n, "LOCAL READY");
  setIntegrationStatus("#integrationTelegram", bridge.telegramBridge, "OWNER GATE");
}

function setRunning(running, terminalState = "ready") {
  state.running = running;
  document.body.dataset.jobState = running ? "running" : terminalState;
  $("#startButton").disabled = running;
  $("#cancelButton").disabled = !running;
  $("#jobBadge").textContent = running ? "PROCESSING" : terminalState === "failed" ? "ERROR" : terminalState === "completed" ? "DONE" : "READY";
}

async function initialize() {
  applyBrandTokens(await window.hermes.getBrandTokens());
  applyConfig(await window.hermes.getConfig());
  state.resources = await window.hermes.getResourcePaths();
  setupCustomSelects();
  await runDoctor();
  selectMode("youtube");
  selectView("director");
  updateDirectorReadiness();
  renderJobProgress({ progress: 0, stage: "analyze", message: "آماده برای شروع", jobState: "ready" });
}

$("#cam1Picker").addEventListener("click", async () => {
  const value = await window.hermes.selectVideo();
  if (value) { state.cam1 = value; $("#cam1Path").textContent = fileName(value); $("#cam1Path").title = value; updateDirectorReadiness(); }
});
document.querySelectorAll(".mode").forEach((button) => button.addEventListener("click", () => selectMode(button.dataset.mode)));
document.querySelectorAll(".nav").forEach((button) => button.addEventListener("click", () => {
  if (state.mode !== "youtube") selectMode("youtube");
  selectView(button.dataset.view);
  if (button.dataset.view === "integrations") refreshIntegrations();
  if (button.dataset.view === "motion") restartPreview();
}));
$("#cam2Picker").addEventListener("click", async () => {
  const value = await window.hermes.selectVideo();
  if (value) { state.cam2 = value; $("#cam2Path").textContent = fileName(value); $("#cam2Path").title = value; updateDirectorReadiness(); }
});
$("#doctorButton").addEventListener("click", runDoctor);
$("#themeButton").addEventListener("click", async () => {
  const next = document.documentElement.dataset.theme === "light" ? "dark" : "light";
  applyTheme(next);
  $("#settingsTheme").value = next;
  state.config = await window.hermes.saveConfig(uiConfig());
});
$("#openOutput").addEventListener("click", () => window.hermes.openPath(state.currentOutput || uiConfig().outputRoot));
$("#openMotionPack").addEventListener("click", () => window.hermes.openPath(state.resources.motionPack));
$("#showAfterEffectsSource").addEventListener("click", () => window.hermes.showPath(state.resources.afterEffectsSource));
$("#openVoiceOutput").addEventListener("click", () => window.hermes.openPath(state.currentOutput || uiConfig().outputRoot));
$("#refreshIntegrations").addEventListener("click", refreshIntegrations);
$("#showPremierePlugin").addEventListener("click", () => window.hermes.openPath(state.resources.premierePlugin));
$("#openPlan").addEventListener("click", () => {
  if (state.latestPlan) window.hermes.showPath(state.latestPlan);
});
$("#chooseOutput").addEventListener("click", async () => {
  const outputRoot = await window.hermes.selectOutput();
  if (outputRoot) $("#settingsOutput").value = outputRoot;
});
$("#settingsTheme").addEventListener("change", (event) => applyTheme(event.target.value));
$("#saveSettings").addEventListener("click", async () => {
  const config = { ...uiConfig(), outputRoot: $("#settingsOutput").value || state.config.outputRoot, theme: $("#settingsTheme").value };
  applyTheme(config.theme);
  state.config = await window.hermes.saveConfig(config);
  $("#settingsNotice").textContent = "تنظیمات ذخیره شد.";
  $("#settingsNotice").classList.add("success");
});
$("#stylePack").addEventListener("change", syncPreviewLook);
$("#graphicDensity").addEventListener("change", syncPreviewLook);
$("#languageMode").addEventListener("change", syncPreviewLook);
$("#glowIntensity").addEventListener("input", (event) => setAdaptiveValue(event.target.value));

document.querySelectorAll(".preview-section").forEach((button) => button.addEventListener("click", () => selectPreviewSection(button.dataset.previewSection)));
document.querySelectorAll(".profile-card").forEach((button) => button.addEventListener("click", () => {
  $("#stylePack").value = button.dataset.profile;
  syncPreviewLook();
  restartPreview();
}));
document.querySelectorAll(".motion-choice").forEach((button) => button.addEventListener("click", () => {
  document.querySelectorAll(".motion-choice").forEach((item) => item.classList.toggle("active", item === button));
  $("#previewStage").dataset.motion = button.dataset.motion;
  $("#previewStage").classList.remove("rhythm-mode", "is-before");
  restartPreview();
}));
$("#previewPlay").addEventListener("click", () => {
  state.previewPlaying = !state.previewPlaying;
  $("#previewStage").classList.toggle("is-playing", state.previewPlaying);
  $("#previewPlay").textContent = state.previewPlaying ? "توقف" : "پخش";
});
$("#previewReplay").addEventListener("click", restartPreview);
$("#previewBefore").addEventListener("click", () => {
  const before = $("#previewStage").classList.toggle("is-before");
  $("#previewBefore").textContent = before ? "نمایش بعد" : "قبل / بعد";
});
$("#previewScrub").addEventListener("input", (event) => {
  const seconds = Number(event.target.value) * 0.06;
  $("#previewTime").textContent = `00:${seconds.toFixed(1).padStart(4, "0")} / 00:06.0`;
  $("#previewStage .preview-timeline i").style.width = `${event.target.value}%`;
});
$("#previewGlow").addEventListener("input", (event) => {
  setAdaptiveValue(event.target.value);
});
for (const id of ["revealSpeed", "liftDistance", "revealBlur", "faceClearance"]) {
  $(`#${id}`)?.addEventListener("input", () => { syncPreviewLook(); restartPreview(); });
}
$("#copyMode")?.addEventListener("change", () => { if (state.config) state.config.copyMode = $("#copyMode").value; });
$("#editableMogrtOnly")?.addEventListener("change", () => { if (state.config) state.config.editableMogrtOnly = $("#editableMogrtOnly").checked; });
$("#playRhythm").addEventListener("click", () => {
  $("#previewStage").dataset.motion = "statement";
  $("#previewStage").classList.add("rhythm-mode");
  $("#previewStage").classList.remove("is-before");
  restartPreview();
});

async function chooseFont(role) {
  const selection = await window.hermes.selectFont();
  if (!selection) return;
  showFontSelection(role, selection);
  await loadPreviewFont(role, selection.path);
}
$("#chooseTitleFont").addEventListener("click", () => chooseFont("title"));
$("#chooseBodyFont").addEventListener("click", () => chooseFont("body"));
$("#titleFontWeight").addEventListener("change", (event) => { document.querySelectorAll(".preview-title-font").forEach((item) => { item.style.fontWeight = event.target.value; }); });
$("#bodyFontWeight").addEventListener("change", (event) => { document.querySelectorAll(".preview-body-font").forEach((item) => { item.style.fontWeight = event.target.value; }); });
$("#saveTypography").addEventListener("click", async () => {
  state.config = await window.hermes.saveConfig(uiConfig());
  $("#saveTypography").textContent = "ذخیره شد ✓";
  setTimeout(() => { $("#saveTypography").textContent = "ذخیره تایپوگرافی این ویدیو"; }, 1600);
});
$("#startButton").addEventListener("click", async () => {
  if (!state.cam1 || !state.cam2) { appendLog("هر دو فایل دوربین را انتخاب کن.", "stderr"); return; }
  setRunning(true);
  $("#console").textContent = "";
  $("#jobSummary").hidden = true;
  renderJobProgress({ progress: 2, stage: "analyze", message: "راه‌اندازی موتور تدوین…", jobState: "running" });
  try {
    state.config = await window.hermes.saveConfig(uiConfig());
    const result = await window.hermes.startJob({ cam1: state.cam1, cam2: state.cam2, config: state.config });
    state.currentOutput = result.outputDir || "";
    appendLog(`Job ${result.jobId} started · PID ${result.pid}`);
    if (state.currentOutput) appendLog(`Project output · ${state.currentOutput}`);
  } catch (error) {
    appendLog(error.message || String(error), "error");
    setRunning(false, "failed");
    renderJobProgress({ message: error.message || "شروع Job ناموفق بود", jobState: "failed" });
  }
});
$("#cancelButton").addEventListener("click", () => window.hermes.cancelJob());

window.hermes.onJobLog(({ line, kind }) => {
  appendLog(line, kind);
  const matches = line.match(/HERMES_PROGRESS\s+(\d+)/);
  if (matches) renderJobProgress({ progress: Number(matches[1]) });
});
window.hermes.onJobProgress(({ progress, stage, message, outputDir }) => {
  if (outputDir) state.currentOutput = outputDir;
  renderJobProgress({ progress, stage, message, jobState: "running" });
});
window.hermes.onJobState((event) => {
  if (event.outputDir) state.currentOutput = event.outputDir;
  if (event.state === "running") {
    setRunning(true);
    renderJobProgress({ progress: Math.max(2, state.progress), stage: "analyze", message: "موتور تدوین در حال اجراست…", jobState: "running" });
    return;
  }
  const completed = event.state === "completed";
  setRunning(false, completed ? "completed" : "failed");
  renderJobProgress({
    progress: completed ? 100 : state.progress,
    stage: completed ? "finish" : state.jobStage,
    message: completed ? (event.summary?.nativeReviewReady ? "پروژهٔ Glass با MOGRT و زیرنویس ذخیره شد؛ بازبینی لازم است" : "فایل‌های تدوین آمادهٔ ورود و بازبینی در Premiere شدند") : (event.message || `توقف در مرحله ${state.jobStage}`),
    jobState: completed ? "completed" : "failed"
  });
  if (event.summary) {
    const summary = event.summary;
    state.latestPlan = summary.nativeProject || summary.plan || "";
    $("#openPlan").textContent = summary.nativeProject ? "نمایش پروژهٔ بازبینی Premiere" : "نمایش برنامهٔ Premiere / MOGRT";
    $("#summarySubtitles").textContent = String(summary.subtitleCues || 0);
    $("#summaryGraphics").textContent = String(summary.graphics || 0);
    $("#summaryPunches").textContent = String(summary.punchIns || 0);
    $("#summaryCameras").textContent = String(summary.cameraSwitches || 0);
    const summaryDetails = Object.entries(summary.graphicKinds || {}).map(([kind, count]) => `${kind}: ${count}`);
    if (summary.blockedGraphics) {
      summaryDetails.push(`${summary.blockedGraphics} پیشنهاد مسدود؛ نیازمند بازبینی متن/چیدمان در Premiere Plan`);
    }
    $("#summaryKinds").textContent = summaryDetails.join(" · ");
    $("#jobSummary").hidden = false;
  }
  appendLog(completed ? (event.summary?.nativeReviewReady ? "پروژهٔ بازبینی ذخیره شد؛ فونت، کامپوزیت، محتوا و صدا را پیش از انتشار بررسی کن. فیلم خروجی گرفته نشد." : "خروجی ساخته شد؛ درج MOGRT با Finisher و بازبینی متن/تصویر در Premiere هنوز لازم است.") : (event.message || `Job failed · code ${event.code ?? "?"}`), completed ? "success" : "error");
  if (completed && event.summary?.copyReviewRequired) {
    appendLog(`${event.summary.copyReviewRequired} عنوان دارای متن نامطمئن است؛ فیلد … را پیش از انتشار بررسی کن.`, "warning");
  }
  if (completed && event.summary?.blockedGraphics) {
    appendLog(`${event.summary.blockedGraphics} پیشنهاد گرافیکی به‌دلیل نیاز به بازبینی متن، خوانایی یا جای‌گذاری مسدود است و در شمارندهٔ موشن آماده حساب نشده؛ دلیل هر مورد در Premiere Plan ثبت شده است.`, "warning");
  }
});

initialize();
