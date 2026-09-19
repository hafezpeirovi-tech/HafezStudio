"use strict";

const { app, BrowserWindow, dialog, ipcMain, shell } = require("electron");
const { spawn } = require("child_process");
const fs = require("fs");
const os = require("os");
const path = require("path");
const { findPreparedJob } = require("./job-recovery");
const glassFinisher = require("./glass-finisher");

let mainWindow;
let activeJob = null;

const isPackaged = () => app.isPackaged;
const sourceRoot = () => path.resolve(__dirname, "..");
const resourceRoot = () => isPackaged() ? process.resourcesPath : sourceRoot();
const premiereRuntime = () => path.join(app.getPath("appData"), "Adobe", "CEP", "extensions", "ir.hafez.studio.cep", "runtime");

function userConfigPath() {
  return path.join(app.getPath("userData"), "settings.json");
}

function legacyUserConfigPath() {
  return path.join(app.getPath("appData"), "Hermes Studio", "settings.json");
}

function defaultOutputRoot() {
  return path.join(app.getPath("videos"), "Hafez Studio Outputs");
}

const CONFIG_VERSION = 7;

function brandTokensPath() {
  return path.join(resourceRoot(), "config", "brand-tokens.json");
}

function loadBrandTokens() {
  const fallback = {
    schemaVersion: 1,
    id: "hafez-premium-neon",
    palette: {
      canvas: "#020303", surface: "#0A0C0B", surfaceElevated: "#111412",
      surfaceActive: "#142019", primaryAccent: "#55FF72", primaryAccentSoft: "#2FD65B",
      negativeAccent: "#FF5964", textPrimary: "#FFFFFF", textSecondary: "#9DA5A0",
      borderSubtle: "#FFFFFF0A"
    },
    radius: { card: 40, control: 24, compact: 16, pill: 999 },
    glow: { intensity: 0.72, corePx: 4, radiusPx: 34, bloomPx: 76, outerAlpha: 0.28 },
    motion: { surfaceOpacity: 0.9, borderOpacity: 0.32, highlightGlow: 0.58 },
    rules: { grainAllowed: false, inactiveUsesNegativeAccent: false, templateFamilyLimit: 4 }
  };
  try {
    return { ...fallback, ...JSON.parse(fs.readFileSync(brandTokensPath(), "utf8")) };
  } catch (_) {
    return fallback;
  }
}

function defaultFontPath(role = "body") {
  const localFonts = path.join(process.env.LOCALAPPDATA || "", "Microsoft", "Windows", "Fonts");
  const systemFonts = path.join(process.env.WINDIR || "C:\\Windows", "Fonts");
  const names = role === "title"
    ? ["YekanBakh-ExtraBlack.ttf", "Peyda-ExtraBold.ttf", "IRANSansX-ExtraBold.ttf", "Dana-ExtraBold.ttf", "AbarHigh-ExtraBold.ttf", "tahomabd.ttf"]
    : ["YekanBakh-Regular.ttf", "Peyda-Regular.ttf", "IRANSansX-Regular.ttf", "Dana-Regular.ttf", "AbarHigh-Regular.ttf", "tahoma.ttf"];
  for (const name of names) {
    for (const root of [localFonts, systemFonts]) {
      const candidate = path.join(root, name);
      if (fs.existsSync(candidate)) return candidate;
    }
  }
  return isPackaged()
    ? path.join(process.resourcesPath, "fonts", "Estedad-VF.ttf")
    : path.join(sourceRoot(), "app", "assets", "fonts", "Estedad-VF.ttf");
}

function fontDisplayName(fontPath, role) {
  const name = path.basename(fontPath, path.extname(fontPath));
  if (/^YekanBakh-/i.test(name)) return role === "title" ? "Yekan Bakh ExtraBlack" : "Yekan Bakh Regular";
  if (/^tahomabd$/i.test(name)) return "Tahoma Bold";
  if (/^tahoma$/i.test(name)) return "Tahoma Regular";
  return name || "Auto Persian";
}

function defaultConfig() {
  return {
    version: CONFIG_VERSION,
    outputRoot: defaultOutputRoot(),
    stylePack: "signal-os",
    performanceProfile: "maximum",
    graphicDensity: "balanced",
    languageMode: "fa-en",
    fontFamily: "auto",
    titleFontPath: defaultFontPath("title"),
    titleFontName: fontDisplayName(defaultFontPath("title"), "title"),
    titleFontWeight: 800,
    bodyFontPath: defaultFontPath("body"),
    bodyFontName: fontDisplayName(defaultFontPath("body"), "body"),
    bodyFontWeight: 400,
    preserveCamera1Audio: true,
    telegramAdapter: "n8n",
    telegramEnabled: true,
    aiProvider: "n8n",
    accent: "neon-green",
    theme: "dark",
    adaptiveValue: 82,
    glowIntensity: 0.82,
    copyMode: "source-faithful",
    revealSpeed: 0.42,
    liftDistance: 50,
    revealBlur: 10,
    faceClearance: 0.16,
    editableMogrtOnly: true
  };
}

function loadConfig() {
  const defaults = defaultConfig();
  for (const candidate of [userConfigPath(), legacyUserConfigPath()]) {
    try {
      const saved = JSON.parse(fs.readFileSync(candidate, "utf8"));
      const merged = { ...defaults, ...saved, version: CONFIG_VERSION };
      const hasAdaptiveValue = Object.prototype.hasOwnProperty.call(saved, "adaptiveValue");
      const savedAdaptiveValue = Number(saved.adaptiveValue);
      const legacyGlowIntensity = Number(saved.glowIntensity);
      if (hasAdaptiveValue) {
        merged.adaptiveValue = Number.isFinite(savedAdaptiveValue) && savedAdaptiveValue >= 0 && savedAdaptiveValue <= 100
          ? Math.round(savedAdaptiveValue)
          : defaults.adaptiveValue;
      } else if (Number.isFinite(legacyGlowIntensity) && legacyGlowIntensity >= 0 && legacyGlowIntensity <= 1) {
        merged.adaptiveValue = Math.round(legacyGlowIntensity * 100);
      } else {
        merged.adaptiveValue = defaults.adaptiveValue;
      }
      merged.glowIntensity = merged.adaptiveValue / 100;
      // Version 2 selected the bundled Estedad variable font.  The compact
      // offline renderer has no RAQM, so migrate that legacy selection to a
      // role-specific static Persian font before the next job starts.
      if (Number(saved.version || 0) < CONFIG_VERSION) {
        for (const role of ["title", "body"]) {
          const key = `${role}FontPath`;
          if (!saved[key] || /Estedad-VF\.ttf$/i.test(saved[key])) {
            merged[key] = defaultFontPath(role);
            merged[`${role}FontName`] = fontDisplayName(merged[key], role);
          }
        }
        if (Number(saved.version || 0) < 4) {
          merged.editableMogrtOnly = true;
        }
        if (Number(saved.version || 0) < 7) {
          merged.copyMode = "source-faithful";
          merged.graphicDensity = "balanced";
        }
      }
      return merged;
    } catch (_) {}
  }
  return defaults;
}

function saveConfig(next) {
  const safe = { ...defaultConfig(), ...next, version: CONFIG_VERSION };
  const adaptiveValue = Number(safe.adaptiveValue);
  safe.adaptiveValue = Number.isFinite(adaptiveValue) && adaptiveValue >= 0 && adaptiveValue <= 100
    ? Math.round(adaptiveValue)
    : 82;
  safe.glowIntensity = safe.adaptiveValue / 100;
  safe.performanceProfile = ["maximum", "adaptive", "balanced"].includes(safe.performanceProfile) ? safe.performanceProfile : "maximum";
  safe.graphicDensity = ["balanced", "dense", "max"].includes(safe.graphicDensity) ? safe.graphicDensity : "max";
  safe.languageMode = ["fa", "fa-en", "auto"].includes(safe.languageMode) ? safe.languageMode : "fa-en";
  safe.titleFontWeight = [600, 700, 800, 900].includes(Number(safe.titleFontWeight)) ? Number(safe.titleFontWeight) : 800;
  safe.bodyFontWeight = [300, 400, 500, 600].includes(Number(safe.bodyFontWeight)) ? Number(safe.bodyFontWeight) : 400;
  // Credentials are intentionally not accepted by this object.
  delete safe.apiKey;
  delete safe.telegramToken;
  fs.mkdirSync(path.dirname(userConfigPath()), { recursive: true });
  fs.writeFileSync(userConfigPath(), JSON.stringify(safe, null, 2), "utf8");
  return safe;
}

function findPython() {
  const candidates = [];
  if (process.env.HERMES_ENGINE_EXE) candidates.push({ exe: process.env.HERMES_ENGINE_EXE, args: [] });
  if (isPackaged()) {
    candidates.push({ exe: path.join(process.resourcesPath, "engine", "hermes-engine", "hermes-engine.exe"), args: [] });
  }
  if (process.env.HERMES_PYTHON) candidates.push({ exe: process.env.HERMES_PYTHON, args: [] });
  candidates.push(
    {
      exe: path.join(process.env.LOCALAPPDATA || "", "Programs", "Python", "Python311", "python.exe"),
      args: [path.join(sourceRoot(), "engine", "src", "hermes_video", "studio_cli.py")]
    },
    { exe: "python", args: [path.join(sourceRoot(), "engine", "src", "hermes_video", "studio_cli.py")] }
  );
  return candidates.find((item) => item.exe === "python" || fs.existsSync(item.exe)) || candidates[candidates.length - 1];
}

function engineInvocation(command, commandArgs = []) {
  const runtime = findPython();
  const baseArgs = runtime.args.length ? runtime.args : [];
  return { exe: runtime.exe, args: [...baseArgs, command, ...commandArgs] };
}

function emit(channel, data) {
  if (mainWindow && !mainWindow.isDestroyed()) mainWindow.webContents.send(channel, data);
}

function safeProjectSlug(videoPath) {
  const sourceName = path.basename(videoPath || "project", path.extname(videoPath || ""));
  const slug = sourceName.normalize("NFKC").replace(/[^\p{L}\p{N}]+/gu, "-").replace(/^-+|-+$/g, "").slice(0, 54);
  return slug || "Hafez-Project";
}

function createProjectOutput(baseRoot, cam1Path, jobId) {
  const now = new Date();
  const stamp = [
    now.getFullYear(),
    String(now.getMonth() + 1).padStart(2, "0"),
    String(now.getDate()).padStart(2, "0"),
    "-",
    String(now.getHours()).padStart(2, "0"),
    String(now.getMinutes()).padStart(2, "0"),
    String(now.getSeconds()).padStart(2, "0")
  ].join("");
  const projectDir = path.join(baseRoot, `${stamp}-${safeProjectSlug(cam1Path)}-${jobId.slice(-5)}`);
  fs.mkdirSync(projectDir, { recursive: false });
  return projectDir;
}

function performanceEnvironment(profile) {
  const logicalCores = Math.max(1, os.cpus().length);
  const normalized = ["maximum", "adaptive", "balanced"].includes(profile) ? profile : "maximum";
  const cpuThreads = normalized === "maximum"
    ? logicalCores
    : normalized === "adaptive"
      ? Math.max(2, logicalCores - 2)
      : Math.max(2, Math.ceil(logicalCores / 2));
  const asrWorkers = normalized === "maximum" ? Math.max(1, Math.min(4, Math.floor(logicalCores / 6))) : 1;
  return {
    HERMES_PERFORMANCE_PROFILE: normalized,
    HERMES_CPU_THREADS: String(cpuThreads),
    HERMES_ASR_WORKERS: String(asrWorkers),
    HERMES_FFMPEG_THREADS: normalized === "balanced" ? String(cpuThreads) : "0",
    HERMES_CUDA_PREFERRED: normalized === "balanced" ? "0" : "1",
    OMP_NUM_THREADS: String(cpuThreads),
    MKL_NUM_THREADS: String(cpuThreads),
    OPENBLAS_NUM_THREADS: String(cpuThreads),
    NUMEXPR_MAX_THREADS: String(cpuThreads)
  };
}

function runEngine(command, args, jobId = null, options = {}) {
  if (activeJob) throw new Error("یک Job در حال اجراست.");
  const invocation = engineInvocation(command, args);
  const engineRoot = resourceRoot();
  const outputDir = options.outputDir || "";
  const child = spawn(invocation.exe, invocation.args, {
    cwd: engineRoot,
    windowsHide: true,
    env: {
      ...process.env,
      PYTHONUTF8: "1",
      PYTHONIOENCODING: "utf-8",
      PYTHONUNBUFFERED: "1",
      HERMES_PRESERVE_CAMERA1_AUDIO: "1",
      HERMES_STUDIO_ROOT: engineRoot,
      HERMES_RUNTIME_ROOT: path.join(engineRoot, "runtime"),
      HERMES_STUDIO_CONFIG: userConfigPath(),
      HERMES_BRAND_TOKENS: brandTokensPath(),
      HERMES_MOTION_PACK: path.join(engineRoot, "motion-pack", "dist"),
      ...performanceEnvironment(options.performanceProfile)
    }
  });
  const jobState = { child, jobId, outputDir, startedAt: Date.now(), result: null, ended: false, buffers: { stdout: "", stderr: "" } };
  activeJob = jobState;
  emit("job:state", { state: "running", jobId, pid: child.pid, outputDir });

  const processLine = (kind, rawLine) => {
    const line = String(rawLine).replace(/\x1B(?:[@-Z\\-_]|\[[0-?]*[ -\/]*[@-~])/g, "").trim();
    if (!line) return;
    if (outputDir) {
      try { fs.appendFileSync(path.join(outputDir, "job.log"), `${new Date().toISOString()} [${kind}] ${line}\n`, "utf8"); }
      catch (_) { /* A logging failure must not crash a running edit. */ }
    }
    const stageMatch = line.match(/^HERMES_STAGE\s+(analyze|direct|design|finish)\s+(\d{1,3})(?:\s+(.*))?$/);
    if (stageMatch) {
      emit("job:progress", { jobId, outputDir, stage: stageMatch[1], progress: Math.min(options.glassReview ? 88 : 100, Number(stageMatch[2])), message: stageMatch[3] || "" });
      return;
    }
    const progressMatch = line.match(/^HERMES_PROGRESS\s+(\d{1,3})$/);
    if (progressMatch) {
      emit("job:progress", { jobId, outputDir, progress: Math.min(options.glassReview ? 88 : 100, Number(progressMatch[1])) });
      return;
    }
    if (kind === "stdout" && line.startsWith("{")) {
      try {
        const payload = JSON.parse(line);
        if (payload.event === "completed") jobState.result = payload;
        return;
      } catch (_) {
        // Human-readable engine output can legitimately begin with a brace.
      }
    }
    emit("job:log", { kind: line.startsWith("HERMES_ERROR") ? "error" : kind, line, jobId, at: Date.now() });
  };
  const forward = (kind) => (chunk) => {
    const parts = (jobState.buffers[kind] + String(chunk)).split(/\r\n|\n|\r/);
    jobState.buffers[kind] = parts.pop() || "";
    parts.forEach((line) => processLine(kind, line));
  };
  const flushBuffers = () => {
    for (const kind of ["stdout", "stderr"]) {
      if (jobState.buffers[kind]) processLine(kind, jobState.buffers[kind]);
      jobState.buffers[kind] = "";
    }
  };
  child.stdout.on("data", forward("stdout"));
  child.stderr.on("data", forward("stderr"));
  child.on("error", (error) => {
    if (jobState.ended) return;
    jobState.ended = true;
    emit("job:state", { state: "failed", jobId, outputDir, message: error.message });
    if (activeJob === jobState) activeJob = null;
  });
  child.on("close", async (code) => {
    flushBuffers();
    if (jobState.ended) return;
    jobState.ended = true;
    let nativeError = "";
    if (code === 0 && jobState.result && options.glassReview) {
      jobState.nativePhase = true;
      try {
        let lastProgress = 0;
        const native = await glassFinisher.finish({summary:jobState.result.summary, outputDir, runtime:premiereRuntime(), jobId}, (message) => {
          if (Date.now() - lastProgress < 10000) return;
          lastProgress = Date.now();
          emit("job:progress", {jobId, outputDir, stage:"finish", progress:92, message});
        });
        jobState.result.summary = {...jobState.result.summary, nativeReviewReady:true, nativeProject:native.project,
          nativeSequenceId:native.sequence_id, nativeReceipt:native.receiptPath, premiereFinisherRequired:false,
          nativeCaptions:true, compositingReviewRequired:native.compositing_review_required, publicationReady:false};
      } catch (error) { nativeError = error.message; }
    }
    emit("job:state", {
      state: code === 0 && jobState.result && !nativeError ? "completed" : "failed",
      message: nativeError || undefined,
      jobId,
      outputDir,
      code,
      elapsedMs: Date.now() - jobState.startedAt,
      result: jobState.result,
      summary: jobState.result?.summary || null
    });
    if (activeJob === jobState) activeJob = null;
  });
  return { pid: child.pid, jobId, outputDir };
}

function createWindow() {
  mainWindow = new BrowserWindow({
    width: 1672,
    height: 941,
    minWidth: 1120,
    minHeight: 720,
    backgroundColor: "#020303",
    icon: path.join(sourceRoot(), "app", "assets", "hafez-monogram-on-dark.png"),
    titleBarStyle: "hiddenInset",
    show: false,
    webPreferences: {
      preload: path.join(__dirname, "preload.js"),
      contextIsolation: true,
      nodeIntegration: false,
      sandbox: true
    }
  });
  mainWindow.loadFile(path.join(sourceRoot(), "app", "index.html"));
  mainWindow.once("ready-to-show", () => mainWindow.show());
}

ipcMain.handle("config:get", () => loadConfig());
ipcMain.handle("config:save", (_, config) => saveConfig(config));
ipcMain.handle("brand:get-tokens", () => loadBrandTokens());
ipcMain.handle("resource:paths", () => {
  const root = resourceRoot();
  return {
    motionPack: path.join(root, "motion-pack", "dist"),
    afterEffectsSource: path.join(root, "motion-pack", "source", "Hermes Studio Elements - Hafez Curated.aep"),
    premierePlugin: path.join(root, "premiere-cep-plugin"),
    premiereUxpPlugin: path.join(root, "premiere-plugin")
  };
});
ipcMain.handle("system:integrations", async () => {
  try {
    const response = await fetch("http://127.0.0.1:5678/healthz", { signal: AbortSignal.timeout(2500) });
    return { n8n: response.ok, telegramBridge: response.ok };
  } catch (_) {
    return { n8n: false, telegramBridge: false };
  }
});
ipcMain.handle("file:video", async () => {
  const result = await dialog.showOpenDialog(mainWindow, {
    properties: ["openFile"],
    filters: [{ name: "Video", extensions: ["mp4", "mov", "mxf", "mkv", "avi"] }]
  });
  return result.canceled ? null : result.filePaths[0];
});
function fontPayload(fontPath) {
  if (!fontPath || !fs.existsSync(fontPath) || !fs.statSync(fontPath).isFile()) return null;
  const extension = path.extname(fontPath).toLowerCase();
  if (![".ttf", ".otf"].includes(extension)) throw new Error("فقط فایل‌های TTF و OTF پشتیبانی می‌شوند.");
  if (fs.statSync(fontPath).size > 24 * 1024 * 1024) throw new Error("حجم فایل فونت بیش از حد مجاز است.");
  const mime = extension === ".otf" ? "font/otf" : "font/ttf";
  return { path: fontPath, name: path.basename(fontPath, extension), dataUrl: `data:${mime};base64,${fs.readFileSync(fontPath).toString("base64")}` };
}
ipcMain.handle("file:font", async () => {
  const result = await dialog.showOpenDialog(mainWindow, {
    properties: ["openFile"],
    filters: [{ name: "OpenType Fonts", extensions: ["ttf", "otf"] }]
  });
  return result.canceled ? null : fontPayload(result.filePaths[0]);
});
ipcMain.handle("font:load", (_, fontPath) => fontPayload(fontPath));
ipcMain.handle("folder:output", async () => {
  const result = await dialog.showOpenDialog(mainWindow, { properties: ["openDirectory", "createDirectory"] });
  return result.canceled ? null : result.filePaths[0];
});
ipcMain.handle("system:doctor", () => {
  const invocation = engineInvocation("doctor", ["--json"]);
  return new Promise((resolve) => {
    const engineRoot = resourceRoot();
    const child = spawn(invocation.exe, invocation.args, {
      cwd: engineRoot,
      windowsHide: true,
      env: {
        ...process.env,
        PYTHONUTF8: "1",
        PYTHONIOENCODING: "utf-8",
        HERMES_STUDIO_ROOT: engineRoot,
        HERMES_RUNTIME_ROOT: path.join(engineRoot, "runtime"),
      HERMES_STUDIO_CONFIG: userConfigPath(),
      HERMES_BRAND_TOKENS: brandTokensPath(),
      HERMES_MOTION_PACK: path.join(engineRoot, "motion-pack", "dist")
      }
    });
    let stdout = "";
    let stderr = "";
    child.stdout.on("data", (chunk) => { stdout += chunk; });
    child.stderr.on("data", (chunk) => { stderr += chunk; });
    child.on("error", (error) => resolve({ ok: false, error: error.message }));
    child.on("close", (code) => {
      try { resolve(JSON.parse(stdout)); }
      catch (_) { resolve({ ok: false, code, error: stderr || stdout || "Engine unavailable" }); }
    });
  });
});
ipcMain.handle("job:start", (_, payload) => {
  if (activeJob) throw new Error("یک Job در حال اجراست.");
  const config = saveConfig(payload.config || {});
  const glassReview = config.stylePack === "glass";
  // Fail before spending time on ASR if the native consumer is unavailable.
  if (glassReview) glassFinisher.preflight(premiereRuntime());
  fs.mkdirSync(config.outputRoot, { recursive: true });
  const jobId = `HS-${Date.now().toString(36).toUpperCase()}`;
  const prepared = findPreparedJob(config.outputRoot, payload.cam1, payload.cam2, config.stylePack);
  const outputDir = prepared?.outputDir || createProjectOutput(config.outputRoot, payload.cam1, jobId);
  if (!prepared) fs.writeFileSync(path.join(outputDir, "project.json"), JSON.stringify({
    schemaVersion: 1,
    jobId,
    createdAt: new Date().toISOString(),
    sources: [path.basename(payload.cam1), path.basename(payload.cam2)],
    performanceProfile: config.performanceProfile,
    graphicDensity: config.graphicDensity,
    languageMode: config.languageMode,
    stylePack: config.stylePack
  }, null, 2), "utf8");
  const args = [
    ...(prepared ? ["--manifest", prepared.manifestPath] : ["--cam1", payload.cam1, "--cam2", payload.cam2, "--output", outputDir]),
    "--job-id", jobId,
    "--style", config.stylePack,
    ...(glassReview ? ["--glass-review"] : []),
    "--density", config.graphicDensity,
    "--language", config.languageMode,
    "--performance", config.performanceProfile,
    "--title-font", config.titleFontPath,
    "--title-font-name", config.titleFontName,
    "--title-weight", String(config.titleFontWeight),
    "--body-font", config.bodyFontPath,
    "--body-font-name", config.bodyFontName,
    "--body-weight", String(config.bodyFontWeight),
    "--glow-intensity", String(config.glowIntensity),
    "--copy-mode", String(config.copyMode || "source-faithful")
  ];
  return runEngine(prepared ? "finalize" : "run", args, jobId, { outputDir, performanceProfile: config.performanceProfile, glassReview });
});
ipcMain.handle("job:cancel", () => {
  if (!activeJob) return false;
  if (activeJob.nativePhase) throw new Error("درج بومی Premiere در حال اجراست؛ قطع یا تکرار درخواست می‌تواند نتیجه را نامطمئن کند. منتظر پاسخ پنل بمان.");
  activeJob.child.kill();
  return true;
});
ipcMain.handle("path:open", (_, target) => shell.openPath(target));
ipcMain.handle("path:show", (_, target) => shell.showItemInFolder(target));

app.whenReady().then(() => {
  createWindow();
  app.on("activate", () => { if (BrowserWindow.getAllWindows().length === 0) createWindow(); });
});
app.on("window-all-closed", () => { if (process.platform !== "darwin") app.quit(); });
