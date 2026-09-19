# Restore Documentation

## Prerequisites
1. **Node.js**: Required to install Electron dependencies.
2. **Python**: Required for the engine.
3. **Adobe Premiere Pro**: Required to utilize the CEP plugins.

## Post-Clone Steps
1. Run 
pm install in the project root to install Electron dependencies.
2. Set up Python virtual environment in .test-deps/ and install dependencies.
3. **CRITICAL**: The AI models and binaries (*.bin, fmpeg.exe) are intentionally excluded from Git. You must manually download or restore untime/models/whisper-fa-ct2/model.bin and place it in the untime folder before running 
pm run start.
