$ErrorActionPreference = 'Stop'
$ProductRoot = Split-Path -Parent $PSScriptRoot
$Node = Join-Path $env:ProgramFiles 'nodejs\node.exe'
$NpmCli = Join-Path $env:ProgramFiles 'nodejs\node_modules\npm\bin\npm-cli.js'
if (-not (Test-Path -LiteralPath $Node) -or -not (Test-Path -LiteralPath $NpmCli)) {
  throw 'Node.js and its bundled npm CLI are required.'
}
function Invoke-Npm {
  & $Node $NpmCli @args
  if ($LASTEXITCODE -ne 0) { throw "npm failed with exit code $LASTEXITCODE" }
}
Push-Location $ProductRoot
try {
  if (-not (Test-Path -LiteralPath (Join-Path $ProductRoot 'node_modules'))) { Invoke-Npm install }
  Invoke-Npm run check
  Invoke-Npm run dist:win
} finally {
  Pop-Location
}
