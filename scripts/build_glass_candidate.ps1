param([ValidatePattern('^[0-9]{2}$')][string]$Revision = '01')
$ErrorActionPreference = 'Stop'
$candidateProductRoot = Split-Path -Parent $PSScriptRoot
$candidateEngineRoot = Join-Path $candidateProductRoot 'engine'
$candidateBuildRoot = Join-Path $candidateEngineRoot "glass-candidate-20260913-$Revision"
$candidateOutputRoot = Join-Path $candidateProductRoot "release-glass-candidate-20260913-$Revision"
$candidatePython = 'C:\Users\1SKY.IR\AppData\Local\Programs\Python\Python311\python.exe'
$candidateNode = 'C:\Program Files\nodejs\node.exe'
if ((Test-Path -LiteralPath $candidateBuildRoot) -or (Test-Path -LiteralPath $candidateOutputRoot)) { throw 'Candidate already exists; no overwrite or rebuild in place.' }
New-Item -ItemType Directory -Path $candidateBuildRoot | Out-Null
& $candidatePython -m PyInstaller --onedir --name hermes-engine `
  --distpath (Join-Path $candidateBuildRoot 'dist') `
  --workpath (Join-Path $candidateBuildRoot 'work') `
  --specpath $candidateBuildRoot `
  --paths (Join-Path $candidateEngineRoot 'src\hermes_video') `
  --hidden-import autocut `
  --add-data "$(Join-Path $candidateEngineRoot 'models');models" `
  --add-data "$(Join-Path $candidateEngineRoot 'src\hermes_video\subtitle_glossary.txt');." `
  --collect-all faster_whisper --collect-all ctranslate2 `
  --copy-metadata faster-whisper --copy-metadata ctranslate2 `
  --collect-all arabic_reshaper --collect-all bidi `
  --exclude-module ctranslate2.converters --exclude-module torch --exclude-module torchvision `
  --exclude-module torchaudio --exclude-module transformers --exclude-module pandas `
  --exclude-module matplotlib --exclude-module jinja2 `
  (Join-Path $candidateEngineRoot 'src\hermes_video\studio_cli.py')
if ($LASTEXITCODE -ne 0) { throw 'Candidate engine build failed; original release unchanged.' }
Push-Location $candidateProductRoot
$candidatePriorRevision = $env:HAFEZ_GLASS_CANDIDATE_REVISION
try {
  $env:HAFEZ_GLASS_CANDIDATE_REVISION = $Revision
  & $candidateNode 'node_modules\electron-builder\out\cli\cli.js' --win dir --x64 --config 'build\glass-candidate.cjs' --publish never
  if ($LASTEXITCODE -ne 0) { throw 'Candidate app build failed; original release unchanged.' }
} finally { $env:HAFEZ_GLASS_CANDIDATE_REVISION = $candidatePriorRevision; Pop-Location }
Write-Output (Join-Path $candidateOutputRoot 'win-unpacked\Hafez Studio.exe')
