# Hafez Studio Context

## Purpose
AI-assisted professional video editing frontend for Adobe Premiere Pro and After Effects. Serves as a desktop Electron UI wrapper for the Hermes video automation pipeline.

## Main Technologies
- **Frontend**: HTML/CSS/JS (Electron, React-like data flow via enderer.js)
- **Backend**: Node.js (Electron main process) + Python (engine/)
- **Adobe Integration**: Adobe CEP Extensions (premiere-cep-plugin/)
- **AI Models**: Local inference using CTranslate2 (Whisper) inside untime/.

## Entry Points
- electron/main.js (Electron Main Process)
- pp/index.html & pp/renderer.js (UI)

## Dependencies
- Node.js & npm (electron, electron-builder)
- Python 3 (
umpy, cv2, pydub, ctranslate2 internally)
- Local 
8n integration.

## Technical Stack & Integrations
- **Electron:** Desktop application wrapper for the studio interface.
- **Python Engine:** Backend execution for AI and processing tasks.
- **Premiere Integration:** Integrates with Adobe Premiere for automated editing/rendering.
- **Hermes Relation:** Integrates with the Hermes Video Automation stack for content processing.
- **n8n Relation:** Orchestrated or triggered by local n8n workflows.
- **Excluded AI Models:** Heavy AI models (.bin, .onnx, untime/models) and generated binaries (elease/, win-unpacked/) are strictly excluded from source control.
- **Restore Requirements:** Cloning this repository requires separate manual downloads of the AI models to become fully operational.
