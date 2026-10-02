@echo off
setlocal
cd /d "%~dp0"
if not exist "node_modules\electron\dist\electron.exe" (
  echo Hafez Studio development runtime is missing. Install project dependencies first.
  pause
  exit /b 1
)
start "" "node_modules\electron\dist\electron.exe" . --reels --disable-gpu
