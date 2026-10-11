param([ValidatePattern('^[0-9]{8}-[0-9]{2}$')][string]$BuildId = '20261011-01',
      [ValidatePattern('^[0-9]{8}-[0-9]{2}$')][string]$SmokeId = '20261011-02')
$ErrorActionPreference = 'Stop'
$motionRoot = [IO.Path]::GetFullPath((Split-Path -Parent $PSScriptRoot))
$motionResources = Join-Path $motionRoot 'release-upscale-candidate-20260928-01/win-unpacked/resources'
$motionCandidateRoot = Join-Path $motionRoot "engine/editorial-candidate-$BuildId"
$motionCandidate = Join-Path $motionCandidateRoot 'dist/hermes-engine'
$motionActive = Join-Path $motionResources 'engine/hermes-engine'
$motionStage = Join-Path $motionResources "engine/motion-staged-$BuildId"
$motionBackup = Join-Path $motionRoot "backups/motion-engine-$BuildId"
$motionSmoke = Join-Path $motionRoot "proof/motion-release-$SmokeId/smoke.edit.json"
foreach ($motionPath in @($motionCandidate,$motionActive,$motionStage,$motionBackup,$motionSmoke)) {
    if (-not [IO.Path]::GetFullPath($motionPath).StartsWith($motionRoot+[IO.Path]::DirectorySeparatorChar,[StringComparison]::OrdinalIgnoreCase)) { throw 'Target leaves project root.' }
}
if (Get-Process -Name 'Hafez Studio','hermes-engine' -ErrorAction SilentlyContinue) { throw 'App/job is running; no replacement.' }
if ((Test-Path -LiteralPath $motionBackup) -or (Test-Path -LiteralPath $motionStage)) { throw 'Prior activation exists; inspect it, never retry blindly.' }
foreach ($motionEntry in (Get-Content -Raw (Join-Path $motionCandidateRoot 'source-hashes.json') | ConvertFrom-Json)) {
    if ((Get-FileHash -LiteralPath $motionEntry.Path).Hash -ne $motionEntry.Hash) { throw 'Candidate source changed.' }
}
$motionShellHash = (Get-FileHash -LiteralPath (Join-Path $motionResources 'app.asar')).Hash
$motionOldRoot = $env:HERMES_STUDIO_ROOT
try {
    $env:HERMES_STUDIO_ROOT = $motionResources
    & (Join-Path $motionCandidate 'hermes-engine.exe') finalize --manifest $motionSmoke --style glass --glass-review --editorial-glass
    if ($LASTEXITCODE -ne 0) { throw 'Packaged smoke failed; installation untouched.' }
    New-Item -ItemType Directory -Path $motionBackup | Out-Null
    Copy-Item -LiteralPath $motionCandidate -Destination $motionStage -Recurse
    foreach ($motionFile in (Get-ChildItem -LiteralPath $motionCandidate -File -Recurse)) {
        $motionRelative = $motionFile.FullName.Substring($motionCandidate.Length).TrimStart('\','/')
        if ((Get-FileHash -LiteralPath $motionFile.FullName).Hash -ne (Get-FileHash -LiteralPath (Join-Path $motionStage $motionRelative)).Hash) { throw 'Staged engine copy differs.' }
    }
    if (Get-Process -Name 'Hafez Studio','hermes-engine' -ErrorAction SilentlyContinue) { throw 'App/job started during validation; no replacement.' }
    if ((Get-FileHash -LiteralPath (Join-Path $motionResources 'app.asar')).Hash -ne $motionShellHash) { throw 'App shell changed; no replacement.' }
    Move-Item -LiteralPath $motionActive -Destination (Join-Path $motionBackup 'previous-engine')
    try {
        Move-Item -LiteralPath $motionStage -Destination $motionActive
        & (Join-Path $motionActive 'hermes-engine.exe') finalize --manifest $motionSmoke --style glass --glass-review --editorial-glass
        if ($LASTEXITCODE -ne 0) { throw 'Active runtime validation failed.' }
        if ((Get-FileHash -LiteralPath (Join-Path $motionResources 'app.asar')).Hash -ne $motionShellHash) { throw 'Shell identity changed.' }
    } catch {
        if (Test-Path -LiteralPath $motionActive) { Move-Item -LiteralPath $motionActive -Destination (Join-Path $motionBackup 'failed-new-engine') }
        Move-Item -LiteralPath (Join-Path $motionBackup 'previous-engine') -Destination $motionActive
        throw
    }
    [ordered]@{status='activated';at=(Get-Date -Format o);build=$BuildId;engineHash=(Get-FileHash -LiteralPath (Join-Path $motionActive 'hermes-engine.exe')).Hash;shellHash=$motionShellHash;backup=$motionBackup;smoke=$motionSmoke;movieExported=$false} | ConvertTo-Json | Set-Content -LiteralPath (Join-Path $motionBackup 'activation.json') -Encoding utf8
    Write-Output 'ACTIVATED engine only. Same app shell, Upscale and Reels unchanged. Previous engine retained.'
} finally { $env:HERMES_STUDIO_ROOT=$motionOldRoot }
