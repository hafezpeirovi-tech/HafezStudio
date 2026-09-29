$ErrorActionPreference = 'Stop'
$moduleDir = $PSScriptRoot
$source = Join-Path $moduleDir 'Hafez-FX Editorial Intro v3.mogrt'
$destination = Join-Path $moduleDir 'Hafez-FX Editorial Intro v4.mogrt'
if (Test-Path -LiteralPath $destination) { throw 'Destination already exists' }
Copy-Item -LiteralPath $source -Destination $destination
Add-Type -AssemblyName System.IO.Compression.FileSystem
$archive = [IO.Compression.ZipFile]::Open($destination, [IO.Compression.ZipArchiveMode]::Update)
try {
  $entry = $archive.GetEntry('definition.json')
  $reader = [IO.StreamReader]::new($entry.Open())
  try { $definition = $reader.ReadToEnd() | ConvertFrom-Json } finally { $reader.Dispose() }
  $definition.capsuleID = [guid]::NewGuid().ToString()
  $definition.capsuleName = 'Hafez-FX Editorial Intro v4'
  $definition.capsuleNameLocalized.strDB[0].str = $definition.capsuleName
  $ranges = @{ 'Title Line Spacing' = @(80,220); 'Title Scale' = @(50,140); 'Portrait Zoom' = @(100,160) }
  foreach ($control in $definition.clientControls) {
    $label = $control.uiName.strDB[0].str
    if ($ranges.ContainsKey($label)) { $control.min = $ranges[$label][0]; $control.max = $ranges[$label][1] }
    if ($label -eq 'Brand') { $control.value.strDB[0].str = 'HAFEZ-FX' }
  }
  foreach ($locale in $definition.sourceInfoLocalized.PSObject.Properties) {
    foreach ($control in $locale.Value.capsuleparams.capParams) {
      $label = $control.capPropUIName
      if ($ranges.ContainsKey($label)) { $control.capPropMin = $ranges[$label][0]; $control.capPropMax = $ranges[$label][1] }
      if ($label -eq 'Brand') { $control.capPropDefault = 'HAFEZ-FX'; $control.textEditValue = 'HAFEZ-FX'; $control.fontTextRunLength = @(8) }
    }
  }
  $entry.Delete()
  $writer = [IO.StreamWriter]::new($archive.CreateEntry('definition.json').Open(), [Text.UTF8Encoding]::new($false))
  try { $writer.Write(($definition | ConvertTo-Json -Depth 100 -Compress)) } finally { $writer.Dispose() }
} finally { $archive.Dispose() }
Write-Output $destination
