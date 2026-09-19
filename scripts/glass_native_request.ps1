param([Parameter(Mandatory=$true)][string]$RequestPath,[switch]$Collect,[ValidateSet('sample','timeline')][string]$Target='sample')
$ErrorActionPreference='Stop'
& (Get-Process -Id $PID).Path -NoProfile -File 'C:\Users\1SKY.IR\.n8n\security\hermes-local-guard\Test-HermesSession.ps1' -Category HERMES_CONFIG_WRITE
if($LASTEXITCODE -ne 0){throw 'Local authorization unavailable'}
$glassProof=[IO.Path]::GetFullPath((Join-Path $PSScriptRoot '..\proof\glass-pack-20260913-01'))
if($Target -eq 'timeline'){$glassProof=[IO.Path]::GetFullPath((Join-Path $PSScriptRoot '..\proof\glass-timeline-20260913-03'))}
$glassRequestFile=(Resolve-Path -LiteralPath $RequestPath).Path
if(!$glassRequestFile.StartsWith($glassProof+[IO.Path]::DirectorySeparatorChar,[StringComparison]::OrdinalIgnoreCase)){throw 'Request outside isolated Glass QA'}
$glassRequest=Get-Content -LiteralPath $glassRequestFile -Raw|ConvertFrom-Json
$glassExpected=Join-Path $glassProof 'Hafez-Glass-Pack-Review-20260913.prproj'
$glassSequence='Glass Pack - Native Review - 20260913'
if($Target -eq 'timeline'){$glassExpected=Join-Path $glassProof 'Hafez-Glass-Timeline-Review.prproj';$glassSequence='Hafez Glass — Automatic Timeline Review'}
if($glassRequest.expected_project_path -cne $glassExpected -or $glassRequest.expected_sequence_name -cne $glassSequence){throw 'Unexpected native target'}
$glassRuntime='C:\Users\1SKY.IR\AppData\Roaming\Adobe\CEP\extensions\ir.hafez.studio.cep\runtime'
$glassQueue=Join-Path $glassRuntime 'active-plan.json'
$glassLast=Join-Path $glassRuntime 'last-result.json'
$glassReceipt=$glassRequestFile.Replace('.request.json','.result.json')
$glassSubmitted=$glassRequestFile.Replace('.request.json','.submitted.json')
function Write-GlassExclusive($Path,$Bytes){$stream=[IO.File]::Open($Path,[IO.FileMode]::CreateNew,[IO.FileAccess]::Write,[IO.FileShare]::None);try{$stream.Write($Bytes,0,$Bytes.Length)}finally{$stream.Dispose()}}
if(Test-Path -LiteralPath $glassReceipt){throw 'Receipt exists; no resend'}
if(!$Collect){
 if((Test-Path -LiteralPath $glassQueue) -or (Test-Path -LiteralPath $glassSubmitted)){throw 'Occupied or uncertain request; collect only'}
 if(Test-Path -LiteralPath $glassLast){$old=Get-Content -LiteralPath $glassLast -Raw|ConvertFrom-Json;if($old.request_id -ceq $glassRequest.request_id){throw 'Already completed'}}
 Write-GlassExclusive $glassSubmitted ([Text.Encoding]::UTF8.GetBytes((@{request_id=$glassRequest.request_id;submitted_at=[DateTimeOffset]::UtcNow.ToString('o')}|ConvertTo-Json)))
 Write-GlassExclusive $glassQueue ([IO.File]::ReadAllBytes($glassRequestFile))
}
$glassDeadline=(Get-Date).AddSeconds(25)
do{
 if(Test-Path -LiteralPath $glassLast){
  $raw=Get-Content -LiteralPath $glassLast -Raw
  try{$result=$raw|ConvertFrom-Json}catch{$result=$null}
  if($result -and $result.request_id -ceq $glassRequest.request_id){
   Write-GlassExclusive $glassReceipt ([Text.UTF8Encoding]::new($false).GetBytes($raw))
   [pscustomobject]@{request=$result.request_id;ok=$result.result.ok;receipt=$glassReceipt;messages=$result.result.messages}|ConvertTo-Json -Depth 5
   if(!$result.result.ok){exit 1};exit 0
  }
 }
 Start-Sleep -Milliseconds 350
}while((Get-Date) -lt $glassDeadline)
throw 'Pending: preserve dispatch and collect, do not resend.'
