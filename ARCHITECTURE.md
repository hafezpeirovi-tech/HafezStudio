# Architecture

## Electron Application
The main.js file handles IPC bridging, config loading, and system tray logic. enderer.js handles the UI and user intent tracking, utilizing a local state machine (director vs preview mode).

## Local Bridge
HafezStudio talks to the local Hermes instance and 
8n workflows via an internal API. The renderer exposes window.hermes logic to communicate with external CEP plugins.

## Premiere CEP Integration
The premiere-cep-plugin/ directory is copied directly to the Adobe CEP extensions folder on the host machine. This plugin uses hafez.jsx (ExtendScript) to communicate with Premiere Pro and the Electron app simultaneously.

## Engine
Python components in engine/ are responsible for heavy lifting: AI transcription, pacing calculations, and segment geometry.
