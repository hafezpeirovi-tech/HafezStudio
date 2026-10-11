param([ValidatePattern('^[0-9]{2}$')][string]$Revision = '01',
      [ValidatePattern('^[0-9]{8}$')][string]$BuildDate = (Get-Date -Format 'yyyyMMdd'))
$ErrorActionPreference = 'Stop'
$editorialRoot = Split-Path -Parent $PSScriptRoot
$editorialEngine = Join-Path $editorialRoot 'engine'
$editorialBuild = Join-Path $editorialEngine "editorial-candidate-$BuildDate-$Revision"
$editorialPython = Join-Path $env:LOCALAPPDATA 'Programs\Python\Python311\python.exe'
if (Test-Path -LiteralPath $editorialBuild) { throw 'Candidate already exists; no overwrite.' }
New-Item -ItemType Directory -Path $editorialBuild | Out-Null
$editorialBefore = @(Get-ChildItem (Join-Path $editorialEngine 'src\hermes_video') -File | Where-Object Extension -in '.py','.jsx' | Get-FileHash -Algorithm SHA256 | Select-Object Path,Hash)
& $editorialPython -m PyInstaller --onedir --name hermes-engine `
  --distpath (Join-Path $editorialBuild 'dist') --workpath (Join-Path $editorialBuild 'work') --specpath $editorialBuild `
  --paths (Join-Path $editorialEngine 'src\hermes_video') `
  --hidden-import autocut --hidden-import glass_storyboard --hidden-import glass_semantic_cards `
  --hidden-import glass_motion_roles `
  --add-data "$(Join-Path $editorialEngine 'models');models" `
  --add-data "$(Join-Path $editorialEngine 'src\hermes_video\subtitle_glossary.txt');." `
  --add-data "$(Join-Path $editorialEngine 'src\hermes_video\editorial_source_export.jsx');." `
  --collect-all faster_whisper --collect-all ctranslate2 --copy-metadata faster-whisper --copy-metadata ctranslate2 `
  --collect-all arabic_reshaper --collect-all bidi `
  --exclude-module ctranslate2.converters --exclude-module torch --exclude-module torchvision --exclude-module torchaudio `
  --exclude-module transformers --exclude-module pandas --exclude-module matplotlib --exclude-module jinja2 `
  (Join-Path $editorialEngine 'src\hermes_video\studio_cli.py')
if ($LASTEXITCODE -ne 0) { throw 'Build failed; installed application unchanged.' }
$editorialAfter = @(Get-ChildItem (Join-Path $editorialEngine 'src\hermes_video') -File | Where-Object Extension -in '.py','.jsx' | Get-FileHash -Algorithm SHA256 | Select-Object Path,Hash)
if (Compare-Object $editorialBefore $editorialAfter -Property Path,Hash) { throw 'Source changed during build; do not deploy.' }
$editorialAfter | ConvertTo-Json | Set-Content -LiteralPath (Join-Path $editorialBuild 'source-hashes.json') -Encoding utf8
Write-Output (Join-Path $editorialBuild 'dist\hermes-engine\hermes-engine.exe')
