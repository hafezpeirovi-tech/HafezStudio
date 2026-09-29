$ErrorActionPreference='Stop'
& (Get-Process -Id $PID).Path -NoProfile -File 'C:\Users\1SKY.IR\.n8n\security\hermes-local-guard\Test-HermesSession.ps1' -Category HERMES_CONFIG_WRITE
if ($LASTEXITCODE -ne 0) { throw 'Local authorization required' }
$bindingRoot=[IO.Path]::GetFullPath((Split-Path -Parent $PSScriptRoot))
$bindingExtension=Join-Path $env:APPDATA 'Adobe\CEP\extensions\ir.hafez.studio.cep'
$bindingResources=Join-Path $bindingRoot 'release-upscale-candidate-20260928-01\win-unpacked\resources\premiere-cep-plugin'
$bindingBackup=Join-Path $bindingRoot 'backups\premiere-target-binding-20260929-01\deployed'
if (Test-Path -LiteralPath $bindingBackup) { throw 'Deployment backup exists; inspect before retry' }
if (Test-Path -LiteralPath (Join-Path $bindingExtension 'runtime\active-plan.json')) { throw 'Native queue occupied' }
$bindingHeartbeat=Get-Content -Raw -LiteralPath (Join-Path $bindingExtension 'runtime\glass-heartbeat.json') | ConvertFrom-Json
if ($bindingHeartbeat.running) { throw 'Native finisher busy' }
New-Item -ItemType Directory -Path $bindingBackup | Out-Null
foreach ($bindingName in @('hafez.jsx','glass-review.jsx')) {
    $bindingSource=Join-Path $bindingRoot ('premiere-cep-plugin\jsx\'+$bindingName)
    foreach ($bindingTarget in @($bindingExtension,$bindingResources)) {
        $bindingLabel=if ($bindingTarget -eq $bindingExtension) {'installed-'} else {'resources-'}
        $bindingDestination=Join-Path $bindingTarget ('jsx\'+$bindingName)
        Copy-Item -LiteralPath $bindingDestination -Destination (Join-Path $bindingBackup ($bindingLabel+$bindingName))
        Copy-Item -LiteralPath $bindingSource -Destination $bindingDestination -Force
        if ((Get-FileHash -LiteralPath $bindingDestination).Hash -ne (Get-FileHash -LiteralPath $bindingSource).Hash) { throw 'Installed file differs from source' }
    }
}
Write-Output 'Verified: installed CEP and same-app packaged resources updated. Runtime queue, engine, UI and Upscale unchanged.'
