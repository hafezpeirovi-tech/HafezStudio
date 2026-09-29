$ErrorActionPreference = 'Stop'
$editorialRoot = Split-Path -Parent $PSScriptRoot
$editorialResources = Join-Path $editorialRoot 'release-upscale-candidate-20260928-01/win-unpacked/resources'
$editorialBackup = Join-Path $editorialRoot 'backups/editorial-release-20260929-01'
$editorialCandidate = Join-Path $editorialRoot 'engine/editorial-candidate-20260928-02/dist/hermes-engine'
if (Get-Process -Name 'Hafez Studio','hermes-engine' -ErrorAction SilentlyContinue) { throw 'Close Hafez Studio and let its jobs finish before staging.' }
if (Test-Path -LiteralPath $editorialBackup) { throw 'Backup already exists; inspect the prior attempt.' }
foreach ($entry in (Get-Content -Raw (Join-Path $editorialRoot 'engine/editorial-candidate-20260928-02/source-hashes.json') | ConvertFrom-Json)) {
    if ((Get-FileHash -LiteralPath $entry.Path).Hash -ne $entry.Hash) { throw "Candidate source changed: $($entry.Path)" }
}
New-Item -ItemType Directory -Path $editorialBackup | Out-Null
Copy-Item -LiteralPath (Join-Path $editorialResources 'app.asar') -Destination $editorialBackup
Copy-Item -LiteralPath (Join-Path $editorialResources 'app.asar.unpacked') -Destination $editorialBackup -Recurse
Copy-Item -LiteralPath (Join-Path $editorialResources 'engine/hermes-engine') -Destination $editorialBackup -Recurse
$editorialModule = Join-Path $editorialResources 'motion-pack/modules/01-editorial-intro'
if (Test-Path -LiteralPath $editorialModule) { throw 'Unexpected existing Editorial module; no overwrite.' }
New-Item -ItemType Directory -Path $editorialModule | Out-Null
foreach ($name in @('Hafez-FX-Editorial-Intro-v3.aep','Hafez-FX Editorial Intro v4.mogrt')) {
    $source = Join-Path $editorialRoot "motion-pack/modules/01-editorial-intro/$name"
    Copy-Item -LiteralPath $source -Destination $editorialModule
    if ((Get-FileHash -LiteralPath $source).Hash -ne (Get-FileHash -LiteralPath (Join-Path $editorialModule $name)).Hash) { throw 'Template copy hash mismatch.' }
}
# Stage the complete runtime next to the old engine; activation is a separate step.
Copy-Item -LiteralPath $editorialCandidate -Destination (Join-Path $editorialResources 'engine/editorial-staged') -Recurse
Write-Output 'Backed up existing shell/engine; staged candidate and verified local authoring prerequisites. Existing application routing remains unchanged.'
