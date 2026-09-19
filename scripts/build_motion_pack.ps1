param(
    [ValidateSet('full', 'hero-only', 'chapter-only', 'glass-titles-only')]
    [string]$Mode = 'full'
)

$ErrorActionPreference = 'Stop'
$ProductRoot = Split-Path -Parent $PSScriptRoot
$Output = Join-Path $ProductRoot 'motion-pack\dist'
$Script = Join-Path $ProductRoot 'motion-pack\after-effects\build_hafez_motion_pack.jsx'
$FontControlPatcher = Join-Path $ProductRoot 'scripts\enable_mogrt_font_controls.py'
$AfterFx = 'C:\Program Files\Adobe\Adobe After Effects 2026\Support Files\AfterFX.com'
$AfterFxGui = 'C:\Program Files\Adobe\Adobe After Effects 2026\Support Files\AfterFX.exe'
if (-not (Test-Path -LiteralPath $AfterFx)) { throw 'Adobe After Effects 2026 command-line host was not found.' }
New-Item -ItemType Directory -Path $Output -Force | Out-Null
$env:HERMES_MOGRT_OUT = $Output
$env:HERMES_MOGRT_MODE = $Mode
$BuildStarted = Get-Date
if (-not (Get-Process -Name 'AfterFX' -ErrorAction SilentlyContinue)) {
    # Adobe's script host requires an interactive desktop session. Launch the
    # JSX directly; the artifact poll below remains the source of truth.
    & $AfterFxGui -r $Script
} else {
    & $AfterFxGui -r $Script
}

$ExpectedName = switch ($Mode) {
    'hero-only' { 'Hafez Bilingual Hero Highlight.mogrt' }
    'chapter-only' { 'Hafez Chapter Billboard.mogrt' }
    'glass-titles-only' { 'Hafez Fullscreen Glass Chapter.mogrt' }
    default { 'Hafez Subject Occlusion Keyword.mogrt' }
}
$Expected = Join-Path $Output $ExpectedName
$deadline = (Get-Date).AddMinutes(5)
do {
    Start-Sleep -Milliseconds 500
    $artifact = Get-Item -LiteralPath $Expected -ErrorAction SilentlyContinue
} while ((-not $artifact -or $artifact.LastWriteTime -lt $BuildStarted) -and (Get-Date) -lt $deadline)
if (-not $artifact -or $artifact.LastWriteTime -lt $BuildStarted) {
    throw "After Effects did not export the expected MOGRT: $ExpectedName"
}
$PythonCandidates = @(
    $env:HERMES_PYTHON,
    (Join-Path $env:LOCALAPPDATA 'Programs\Python\Python311\python.exe'),
    (Join-Path $ProductRoot 'runtime\python\python.exe')
) | Where-Object { $_ -and (Test-Path -LiteralPath $_) }
$PythonExecutable = $PythonCandidates | Select-Object -First 1
if (-not $PythonExecutable) { throw 'A Python 3 runtime is required to finalize MOGRT font controls.' }
$FontControlTargets = switch ($Mode) {
    'hero-only' { @((Join-Path $Output 'Hafez Bilingual Hero Highlight.mogrt')) }
    'chapter-only' { @((Join-Path $Output 'Hafez Chapter Billboard.mogrt')) }
    'glass-titles-only' {
        @(
            (Join-Path $Output 'Hafez Bilingual Hero Highlight.mogrt'),
            (Join-Path $Output 'Hafez Fullscreen Glass Focus.mogrt'),
            (Join-Path $Output 'Hafez Fullscreen Glass Prism.mogrt'),
            (Join-Path $Output 'Hafez Fullscreen Glass Chapter.mogrt')
        )
    }
    default {
        @(Get-ChildItem -LiteralPath $Output -Filter 'Hafez *.mogrt' |
            Where-Object { $_.BaseName -notmatch ' v\d+$' } |
            ForEach-Object { $_.FullName })
    }
}
$ExistingFontControlTargets = @($FontControlTargets | Where-Object { Test-Path -LiteralPath $_ })
if ($ExistingFontControlTargets.Count -gt 0) {
    & $PythonExecutable $FontControlPatcher @ExistingFontControlTargets
    if ($LASTEXITCODE -ne 0) { throw 'MOGRT font-control post-processing failed.' }
}
Write-Output $Output
