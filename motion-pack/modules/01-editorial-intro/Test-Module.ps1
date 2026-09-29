$ErrorActionPreference = 'Stop'
$checks = 0
function Assert-Module($Condition, $Message) {
  if (-not $Condition) { throw $Message }
  $script:checks++
}
$receipt = Get-Content -Raw -LiteralPath (Join-Path $PSScriptRoot 'native-apply-receipt-v4.json') | ConvertFrom-Json
Assert-Module ($receipt.result.ok -and $receipt.result.inserted -eq 2 -and $receipt.result.failed -eq 0) 'Native apply did not pass'
$inspection = Get-Content -Raw -LiteralPath (Join-Path $PSScriptRoot 'native-inspect-v4.json') | ConvertFrom-Json
Assert-Module ($inspection.result.mogrts.Count -eq 2) 'Expected two native v4 graphics'
$expectedFonts = @('AbarHighFaNum-ExtraBold', 'AbarHighFaNum-Bold')
$expectedSizes = @(102,92)
$expectedSpacing = @(132,120)
for ($i=0; $i -lt 2; $i++) {
  $graphic=$inspection.result.mogrts[$i]
  Assert-Module ($graphic.component -and -not $graphic.disabled -and $graphic.propertyCount -eq 20) 'Missing/enabled native component or controls'
  Assert-Module ($graphic.start -eq (6*$i) -and $graphic.end -eq (6*($i+1))) 'Unexpected timeline interval'
  foreach ($label in @('Title Line 1','Title Line 2')) {
    $property=$graphic.params | Where-Object name -eq $label
    $document=$property.preview | ConvertFrom-Json
    Assert-Module ($document.capPropFontEdit -and $document.capPropFontSizeEdit -and $document.fontEditValue[0] -eq $expectedFonts[$i] -and $document.fontSizeEditValue[0] -eq $expectedSizes[$i]) 'Font or size readback mismatch'
  }
  $spacing=$graphic.params | Where-Object name -eq 'Title Line Spacing'
  Assert-Module ([double]$spacing.preview -eq $expectedSpacing[$i]) 'Line spacing readback mismatch'
}
Add-Type -AssemblyName System.IO.Compression.FileSystem
$archive=[IO.Compression.ZipFile]::OpenRead((Join-Path $PSScriptRoot 'Hafez-FX Editorial Intro v4.mogrt'))
try {
  $reader=[IO.StreamReader]::new($archive.GetEntry('definition.json').Open())
  try {$definition=$reader.ReadToEnd() | ConvertFrom-Json} finally {$reader.Dispose()}
  $spacing=$definition.clientControls | Where-Object {$_.uiName.strDB[0].str -eq 'Title Line Spacing'}
  Assert-Module ($spacing.min -eq 80 -and $spacing.max -eq 220 -and $spacing.value -eq 132) 'Exported slider range regressed'
  $brand=$definition.clientControls | Where-Object {$_.uiName.strDB[0].str -eq 'Brand'}
  Assert-Module ($brand.value.strDB[0].str -eq 'HAFEZ-FX') 'Exported channel brand regressed'
  $texts=@($definition.clientControls | Where-Object type -eq 6)
  Assert-Module ($texts.Count -eq 6 -and @($texts | Where-Object {-not $_.fonteditinfo.capPropFontEdit -or -not $_.fonteditinfo.capPropFontSizeEdit}).Count -eq 0) 'Editable typography capability missing'
} finally {$archive.Dispose()}
Assert-Module ((Get-Item -LiteralPath (Join-Path $PSScriptRoot 'Hafez-FX-Intro-Editable-Test.prproj')).Length -gt 1000) 'Saved Premiere project missing'
Assert-Module ((Get-Item -LiteralPath (Join-Path $PSScriptRoot 'Hafez-FX-Intro-Preview.mp4')).Length -gt 1000) 'Preview missing'
"PASS: $checks artifact/recorded-native-evidence checks. This does not rerun Premiere or the full application."
