const { entrypoints, storage } = require("uxp");
const ppro = require("premierepro");

let panelRoot;

function log(message) {
  const output = panelRoot && panelRoot.querySelector("#log");
  if (!output) return;
  const stamp = new Date().toLocaleTimeString("fa-IR");
  output.textContent += `\n[${stamp}] ${message}`;
  output.scrollTop = output.scrollHeight;
}

function transaction(project, label, actions) {
  const valid = actions.filter(Boolean);
  if (!valid.length) return false;
  return project.lockedAccess(() => project.executeTransaction((compound) => {
    valid.forEach((action) => compound.addAction(action));
  }, label));
}

function parameterMatches(name, needles) {
  const value = String(name || "").trim().toLowerCase();
  return needles.some((needle) => value.includes(needle));
}

async function setMogrtParameters(project, trackItem, cue) {
  const chain = await trackItem.getComponentChain();
  const fontNames = ["font", "typeface", "فونت"];
  const controls = cue.controls || {
    "FA Headline": cue.headline_fa || cue.text || "",
    "EN Kicker": cue.kicker_en || ""
  };
  const aliases = {
    "fa headline": ["fa headline", "persian headline", "headline", "source text", "عنوان", "متن"],
    "en kicker": ["en kicker", "english kicker", "kicker"],
    "fa keyword": ["fa keyword", "keyword"],
    "fa support": ["fa support", "support"],
    "metric value": ["metric value", "value", "number"],
    "fa label": ["fa label", "label"],
    "chapter number": ["chapter number"],
    "fa a": ["fa a"],
    "fa b": ["fa b"],
    "fa a support": ["fa a support"],
    "fa b support": ["fa b support"]
  };
  for (let index = 1; index <= 5; index += 1) aliases[`node ${index}`] = [`node ${index}`];
  const pending = Object.entries(controls).filter(([, value]) => {
    if (Array.isArray(value)) return value.length > 0;
    return value !== null && value !== undefined && String(value).trim() !== "";
  });
  const appliedControls = [];
  let fontApplied = false;

  const componentCount = await chain.getComponentCount();
  for (let componentIndex = 0; componentIndex < componentCount; componentIndex += 1) {
    const component = await chain.getComponentAtIndex(componentIndex);
    const paramCount = await component.getParamCount();
    for (let paramIndex = 0; paramIndex < paramCount; paramIndex += 1) {
      const param = await component.getParam(paramIndex);
      const displayName = param.displayName || "";
      try {
        const normalizedName = String(displayName).trim().toLowerCase();
        const match = pending.find(([controlName]) => {
          const normalizedControl = controlName.toLowerCase();
          const names = aliases[normalizedControl] || [normalizedControl];
          return names.some((name) => normalizedName === name || normalizedName.includes(name));
        });
        if (match && !appliedControls.includes(match[0])) {
          const rawValue = match[1];
          const value = typeof rawValue === "string" ? rawValue : rawValue;
          const keyframe = param.createKeyframe(value);
          transaction(project, "Hermes: Set graphic text", [param.createSetValueAction(keyframe, true)]);
          appliedControls.push(match[0]);
          continue;
        }
        if (!fontApplied && cue.font_family && !String(cue.font_family).toLowerCase().includes("auto") && parameterMatches(displayName, fontNames)) {
          const keyframe = param.createKeyframe(String(cue.font_family || "Abar High Regular"));
          transaction(project, "Hermes: Set graphic font", [param.createSetValueAction(keyframe, true)]);
          fontApplied = true;
        }
      } catch (_) {
        // MOGRT controls are template-specific; unsupported controls are safely skipped.
      }
    }
  }
  return { textApplied: appliedControls.length > 0, appliedControls, fontApplied };
}

function findVideoItem(items) {
  return (items || []).find((item) => typeof item.getComponentChain === "function");
}

async function applyPlan() {
  const button = panelRoot.querySelector("#applyPlan");
  button.disabled = true;
  try {
    const file = await storage.localFileSystem.getFileForOpening({ types: ["json"] });
    if (!file) {
      log("انتخاب فایل لغو شد.");
      return;
    }

    const plan = JSON.parse(await file.read());
    if (!["hermes-professional-edit-v1", "hermes-professional-edit-v2"].includes(plan.protocol)) {
      throw new Error("این فایل، Hafez Premiere Plan معتبر نیست.");
    }

    if (plan.protocol === "hermes-professional-edit-v2") {
      const collisions = (plan.graphics || []).filter((cue) => cue.layout && cue.layout.collision_free === false);
      const overflow = (plan.graphics || []).filter((cue) => {
        const maxLines = Number(cue.layout?.max_lines || 3);
        const textLines = String(cue.controls?.["FA Headline"] || cue.text || "").split(/\r?\n/).length;
        const nodeOverflow = Object.entries(cue.controls || {}).some(([name, value]) => /^Node \d+$/i.test(name) && String(value).split(/\r?\n/).length > 2);
        return textLines > maxLines || nodeOverflow;
      });
      if (collisions.length || overflow.length) {
        throw new Error(`Quality Gate رد شد: برخورد با صورت ${collisions.length}، سرریز متن ${overflow.length}.`);
      }
    }

    const project = await ppro.Project.getActiveProject();
    const sequence = project && await project.getActiveSequence();
    if (!project || !sequence) throw new Error("پروژه و سکانس فعال Premiere پیدا نشد.");

    if (sequence.name !== plan.sequence) {
      log(`هشدار: سکانس فعال «${sequence.name}» است؛ Plan برای «${plan.sequence}» ساخته شده.`);
    }

    const editor = ppro.SequenceEditor.getEditor(sequence);
    const mogrtTrackIndex = Number(plan.video_tracks?.mogrt ?? 3);
    let inserted = 0;
    let textUpdated = 0;
    let failed = 0;
    const expectedMogrtCount = (plan.graphics || []).reduce((total, cue) => {
      const layers = Array.isArray(cue.template_layers) && cue.template_layers.length ? cue.template_layers : [cue];
      return total + layers.length;
    }, 0);

    log(`شروع جایگذاری ${expectedMogrtCount} لایه MOGRT از ${plan.graphics.length} Cue…`);
    for (const cue of plan.graphics) {
      const layers = Array.isArray(cue.template_layers) && cue.template_layers.length ? cue.template_layers : [cue];
      for (const layer of layers) {
        const layerCue = { ...cue, ...layer, controls: layer.controls || cue.controls || {} };
        try {
          const at = ppro.TickTime.createWithSeconds(Number(cue.start));
          const cueTrackIndex = Number(layerCue.track ?? mogrtTrackIndex);
          const insertedItems = await editor.insertMogrtFromPath(
            layerCue.template_path,
            at,
            cueTrackIndex,
            0
          );
          const item = findVideoItem(insertedItems);
          if (!item) throw new Error("آیتم ویدیویی MOGRT برنگشت");

          const end = ppro.TickTime.createWithSeconds(Number(cue.end));
          transaction(project, "Hermes: Set MOGRT duration", [item.createSetEndAction(end)]);
          const result = await setMogrtParameters(project, item, layerCue);
          inserted += 1;
          if (result.textApplied) textUpdated += 1;
          log(`✓ ${cue.id}/${layerCue.role || "graphic"}: ${String(cue.text).slice(0, 52)}`);
        } catch (error) {
          failed += 1;
          log(`✕ ${cue.id}/${layerCue.role || "graphic"}: ${error.message || error}`);
        }
      }
    }

    if (inserted === expectedMogrtCount && failed === 0 && panelRoot.querySelector("#muteFallback").checked) {
      try {
        const pngTrack = await sequence.getVideoTrack(Number(plan.video_tracks?.png_guide ?? plan.video_tracks?.png_fallback ?? 2));
        await pngTrack.setMute(true);
        log("راهنمای Legacy PNG خاموش شد؛ MOGRTها فعال ماندند.");
      } catch (error) {
        log(`هشدار: Mute لایه PNG انجام نشد (${error.message || error}).`);
      }
    }

    log(`تمام شد — MOGRT: ${inserted} | متن تنظیم‌شده: ${textUpdated} | خطا: ${failed}`);
    if (failed || inserted !== expectedMogrtCount) log("Finisher ناقص بود؛ XML جدید هیچ PNG پنهانی را جایگزین MOGRT نمی‌کند.");
  } catch (error) {
    log(`خطای اجرا: ${error.message || error}`);
  } finally {
    button.disabled = false;
  }
}

entrypoints.setup({
  panels: {
    hermesFinisher: {
      create(rootNode) {
        panelRoot = rootNode;
        rootNode.appendChild(document.body);
        rootNode.querySelector("#applyPlan").addEventListener("click", applyPlan);
        rootNode.querySelector("#clearLog").addEventListener("click", () => {
          rootNode.querySelector("#log").textContent = "گزارش پاک شد.";
        });
      },
      show(rootNode) {
        panelRoot = rootNode;
      }
    }
  }
});
