$ErrorActionPreference = 'Stop'
$ProductRoot = Split-Path -Parent $PSScriptRoot
$EngineRoot = Join-Path $ProductRoot 'engine'
$Python = if ($env:HERMES_PYTHON) { $env:HERMES_PYTHON } else { Join-Path $env:LOCALAPPDATA 'Programs\Python\Python311\python.exe' }
if (-not (Test-Path -LiteralPath $Python)) { throw "Python 3.11 not found. Set HERMES_PYTHON." }

$Dist = Join-Path $EngineRoot 'dist'
$Work = Join-Path $EngineRoot '.build'
New-Item -ItemType Directory -Path $Dist -Force | Out-Null
New-Item -ItemType Directory -Path $Work -Force | Out-Null

& $Python -m PyInstaller `
  --noconfirm `
  --clean `
  --onedir `
  --name hermes-engine `
  --distpath $Dist `
  --workpath (Join-Path $Work 'pyinstaller') `
  --specpath $Work `
  --paths (Join-Path $EngineRoot 'src\hermes_video') `
  --hidden-import autocut `
  --add-data "$(Join-Path $EngineRoot 'models');models" `
  --add-data "$(Join-Path $EngineRoot 'src\hermes_video\subtitle_glossary.txt');." `
  --collect-all faster_whisper `
  --collect-all ctranslate2 `
  --copy-metadata faster-whisper `
  --copy-metadata ctranslate2 `
  --collect-all arabic_reshaper `
  --collect-all bidi `
  --exclude-module ctranslate2.converters `
  --exclude-module torch `
  --exclude-module torchvision `
  --exclude-module torchaudio `
  --exclude-module transformers `
  --exclude-module pandas `
  --exclude-module matplotlib `
  --exclude-module jinja2 `
  (Join-Path $EngineRoot 'src\hermes_video\studio_cli.py')

if ($LASTEXITCODE -ne 0) { throw "PyInstaller failed with exit code $LASTEXITCODE" }

$EngineExe = Join-Path $Dist 'hermes-engine\hermes-engine.exe'
if (-not (Test-Path -LiteralPath $EngineExe)) { throw 'PyInstaller did not produce the engine executable.' }
Write-Output $EngineExe
