$ErrorActionPreference = 'Stop'
$editorialRoot = [IO.Path]::GetFullPath((Split-Path -Parent $PSScriptRoot))
$editorialResources = Join-Path $editorialRoot 'release-upscale-candidate-20260928-01/win-unpacked/resources'
$editorialBackup = Join-Path $editorialRoot 'backups/editorial-release-20260929-01'
$editorialOld = Join-Path $editorialResources 'engine/hermes-engine'
$editorialStage = Join-Path $editorialResources 'engine/editorial-staged'
$editorialRetained = Join-Path $editorialBackup 'active-engine-before-switch'
$editorialShell = Join-Path $editorialRoot 'build/editorial-shell-20260928-01/app.asar'
$editorialManifest = Join-Path $editorialRoot 'proof/editorial-release-smoke-20260929-01/smoke.edit.editorial.json'
foreach ($target in @($editorialOld,$editorialStage,$editorialRetained,$editorialResources)) {
    if (-not [IO.Path]::GetFullPath($target).StartsWith($editorialRoot+[IO.Path]::DirectorySeparatorChar,[StringComparison]::OrdinalIgnoreCase)) { throw 'Target leaves project root.' }
}
if (Get-Process -Name 'Hafez Studio','hermes-engine' -ErrorAction SilentlyContinue) { throw 'Application or job is still running.' }
if (Test-Path -LiteralPath $editorialRetained) { throw 'Activation already attempted; inspect first.' }
if (-not (Test-Path -LiteralPath $editorialManifest)) { throw 'Packaged smoke compilation has not succeeded.' }
if ((Get-FileHash -LiteralPath (Join-Path $editorialResources 'app.asar')).Hash -ne (Get-FileHash -LiteralPath (Join-Path $editorialBackup 'app.asar')).Hash) { throw 'Installed shell changed since backup.' }
$env:HERMES_STUDIO_ROOT=$editorialResources
$editorialPlan=(Get-Content -Raw -LiteralPath $editorialManifest | ConvertFrom-Json).outputs.professional_plan
& (Join-Path $editorialStage 'hermes-engine.exe') glass-validate --qa --plan $editorialPlan
if ($LASTEXITCODE -ne 0) { throw 'Packaged validation failed; application not activated.' }
Copy-Item -LiteralPath $editorialShell -Destination (Join-Path $editorialResources 'app.asar.editorial-new')
Move-Item -LiteralPath $editorialOld -Destination $editorialRetained
try {
    Move-Item -LiteralPath $editorialStage -Destination $editorialOld
    Move-Item -LiteralPath (Join-Path $editorialResources 'app.asar.editorial-new') -Destination (Join-Path $editorialResources 'app.asar') -Force
    if ((Get-FileHash -LiteralPath $editorialShell).Hash -ne (Get-FileHash -LiteralPath (Join-Path $editorialResources 'app.asar')).Hash) { throw 'Shell verification failed.' }
    $editorialReceipt=[ordered]@{status='activated';at=(Get-Date -Format o);resources=$editorialResources;backup=$editorialBackup;smokeManifest=$editorialManifest;engineHash=(Get-FileHash -LiteralPath (Join-Path $editorialOld 'hermes-engine.exe')).Hash;shellHash=(Get-FileHash -LiteralPath $editorialShell).Hash;finalMovieExported=$false}
    $editorialReceipt | ConvertTo-Json | Set-Content -LiteralPath (Join-Path $editorialBackup 'activation.json') -Encoding utf8
    Write-Output 'ACTIVATED same desktop installation. Prior engine and shell retained in backup. Upscale/runtime/models unchanged.'
} catch {
    if (Test-Path -LiteralPath $editorialOld) { Move-Item -LiteralPath $editorialOld -Destination (Join-Path $editorialBackup 'failed-new-engine') }
    Move-Item -LiteralPath $editorialRetained -Destination $editorialOld
    Copy-Item -LiteralPath (Join-Path $editorialBackup 'app.asar') -Destination (Join-Path $editorialResources 'app.asar') -Force
    throw
}
