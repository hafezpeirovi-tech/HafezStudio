param([ValidatePattern('^[0-9]{2}$')][string]$Revision = '01')
$ErrorActionPreference = 'Stop'
$semanticRoot = Split-Path -Parent $PSScriptRoot
$semanticEngine = Join-Path $semanticRoot 'engine'
$semanticBuild = Join-Path $semanticEngine "semantic-candidate-20260923-$Revision"
$semanticPython = 'C:\Users\1SKY.IR\AppData\Local\Programs\Python\Python311\python.exe'
if (Test-Path -LiteralPath $semanticBuild) { throw 'Candidate exists; no in-place overwrite.' }
New-Item -ItemType Directory -Path $semanticBuild | Out-Null
$semanticBefore = @(Get-ChildItem (Join-Path $semanticEngine 'src\hermes_video') -Filter '*.py' | Get-FileHash -Algorithm SHA256 | Select-Object Path,Hash)
& $semanticPython -m PyInstaller --onedir --name hermes-engine `
  --distpath (Join-Path $semanticBuild 'dist') `
  --workpath (Join-Path $semanticBuild 'work') `
  --specpath $semanticBuild `
  --paths (Join-Path $semanticEngine 'src\hermes_video') `
  --hidden-import autocut --hidden-import glass_storyboard --hidden-import glass_semantic_cards `
  --add-data "$(Join-Path $semanticEngine 'models');models" `
  --add-data "$(Join-Path $semanticEngine 'src\hermes_video\subtitle_glossary.txt');." `
  --collect-all faster_whisper --collect-all ctranslate2 `
  --copy-metadata faster-whisper --copy-metadata ctranslate2 `
  --collect-all arabic_reshaper --collect-all bidi `
  --exclude-module ctranslate2.converters --exclude-module torch --exclude-module torchvision `
  --exclude-module torchaudio --exclude-module transformers --exclude-module pandas `
  --exclude-module matplotlib --exclude-module jinja2 `
  (Join-Path $semanticEngine 'src\hermes_video\studio_cli.py')
if ($LASTEXITCODE -ne 0) { throw 'Build failed; installed release remains unchanged.' }
$semanticAfter = @(Get-ChildItem (Join-Path $semanticEngine 'src\hermes_video') -Filter '*.py' | Get-FileHash -Algorithm SHA256 | Select-Object Path,Hash)
if (Compare-Object $semanticBefore $semanticAfter -Property Path,Hash) { throw 'Source changed during build; do not deploy this candidate.' }
$semanticAfter | ConvertTo-Json | Set-Content -LiteralPath (Join-Path $semanticBuild 'source-hashes.json') -Encoding utf8
Write-Output (Join-Path $semanticBuild 'dist\hermes-engine\hermes-engine.exe')
