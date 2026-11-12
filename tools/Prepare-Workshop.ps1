# Run on Windows with DayZ Tools installed. This script never logs into Steam.
[CmdletBinding()]
param(
    [Parameter(Mandatory = $true)][string]$DayZToolsPath,
    [string]$SigningDirectory = (Join-Path $env:LOCALAPPDATA 'WolfGamingZA\Signing'),
    [ValidatePattern('^[A-Za-z0-9_-]+$')][string]$Authority = 'WolfGamingZA_DogTags',
    [ValidatePattern('^[0-9]+$')][string]$PublishedFileId = '0',
    [ValidateSet('Private', 'FriendsOnly', 'Public')][string]$Visibility = 'Private'
)

Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'
$Repository = Split-Path -Parent $PSScriptRoot
$Source = Join-Path $Repository 'WGZA_DogTags'
$Tools = (Resolve-Path -LiteralPath $DayZToolsPath).Path

function Find-DayZTool([string]$Name) {
    $ToolMatches = @(Get-ChildItem -LiteralPath $Tools -Filter $Name -File -Recurse)
    if ($ToolMatches.Count -ne 1) { throw "Expected exactly one $Name under $Tools. Check the DayZ Tools installation." }
    return $ToolMatches[0].FullName
}

function Invoke-CheckedTool([string]$Executable, [string[]]$Arguments) {
    & $Executable @Arguments | Out-Host
    if ($LASTEXITCODE -ne 0) { throw "Native tool failed: $Executable (exit $LASTEXITCODE). Do not upload this build." }
}

function Write-Utf8([string]$Path, [string]$Text) {
    [System.IO.File]::WriteAllText($Path, $Text, (New-Object System.Text.UTF8Encoding($false)))
}

$AddonBuilder = Find-DayZTool 'AddonBuilder.exe'
$CreateKey = Find-DayZTool 'DSCreateKey.exe'
$SignFile = Find-DayZTool 'DSSignFile.exe'
if (!(Test-Path -LiteralPath (Join-Path $Source 'config.cpp'))) { throw 'Addon source is missing. Extract the entire Workshop kit first.' }

# Persist signing identity outside the checkout, staging folder and upload content.
$SigningDirectory = [System.IO.Path]::GetFullPath($SigningDirectory)
$RepositoryPath = [System.IO.Path]::GetFullPath($Repository).TrimEnd('\') + '\'
if (($SigningDirectory.TrimEnd('\') + '\').StartsWith($RepositoryPath, [System.StringComparison]::OrdinalIgnoreCase)) {
    throw 'SigningDirectory must be outside this extracted kit/repository.'
}
New-Item -ItemType Directory -Path $SigningDirectory -Force | Out-Null
$PrivateKey = Join-Path $SigningDirectory ($Authority + '.biprivatekey')
$PublicKey = Join-Path $SigningDirectory ($Authority + '.bikey')
$HasPrivate = Test-Path -LiteralPath $PrivateKey
$HasPublic = Test-Path -LiteralPath $PublicKey
if ($HasPrivate -ne $HasPublic) { throw 'Only half of the signing key pair exists. Restore the matching pair; existing files will not be replaced.' }
if (!$HasPrivate) {
    Push-Location -LiteralPath $SigningDirectory
    try { Invoke-CheckedTool $CreateKey @($Authority) }
    finally { Pop-Location }
}
if (!(Test-Path -LiteralPath $PrivateKey) -or !(Test-Path -LiteralPath $PublicKey)) { throw 'Signing tool did not create the expected key pair.' }

$BuildId = (Get-Date -Format 'yyyyMMdd-HHmmss') + '-' + [guid]::NewGuid().ToString('N').Substring(0, 6)
$BuildRoot = Join-Path $Repository ('dist\workshop\' + $BuildId)
$Content = Join-Path $BuildRoot 'content'
$Addons = Join-Path $Content 'Addons'
$Keys = Join-Path $Content 'Keys'
New-Item -ItemType Directory -Path $Addons -Force | Out-Null
New-Item -ItemType Directory -Path $Keys -Force | Out-Null
$Include = Join-Path $BuildRoot 'include.txt'
Write-Utf8 $Include '*.c;*.layout;*.paa;*.p3d;*.rvmat;*.xml;*.csv;*.ogg;*.imageset'

# Official packing/binarization, not the portable source-PBO development packer.
Invoke-CheckedTool $AddonBuilder @($Source, $Addons, '-clear', ('-include=' + $Include))
$Pbo = Join-Path $Addons 'WGZA_DogTags.pbo'
if (!(Test-Path -LiteralPath $Pbo) -or (Get-Item -LiteralPath $Pbo).Length -eq 0) { throw 'Addon Builder did not produce a PBO.' }
Invoke-CheckedTool $SignFile @($PrivateKey, $Pbo)
$Signatures = @(Get-ChildItem -LiteralPath $Addons -Filter 'WGZA_DogTags.pbo.*.bisign' -File)
if ($Signatures.Count -ne 1 -or $Signatures[0].Length -eq 0) { throw 'Expected one nonempty PBO signature. Do not upload this build.' }
Copy-Item -LiteralPath $PublicKey -Destination $Keys
Copy-Item -LiteralPath (Join-Path $Repository 'packaging\mod.cpp') -Destination $Content
if ($PublishedFileId -ne '0') {
    Write-Utf8 (Join-Path $Content 'meta.cpp') ("protocol = 1;`npublishedid = $PublishedFileId;`nname = ""WolfGamingZA Dog Tags"";`n")
}
Copy-Item -LiteralPath (Join-Path $Repository 'server') -Destination $Content -Recurse
Copy-Item -LiteralPath (Join-Path $Repository 'assets\wgza_tag_preview.png') -Destination (Join-Path $BuildRoot 'preview.png')
if (@(Get-ChildItem -LiteralPath $Content -Filter '*.biprivatekey' -File -Recurse).Count -ne 0) { throw 'Private key in upload content; refusing to prepare upload.' }

$VisibilityNumber = @{ Public = '0'; FriendsOnly = '1'; Private = '2' }[$Visibility]
$ContentVdf = $Content.Replace('\', '/')
$PreviewVdf = (Join-Path $BuildRoot 'preview.png').Replace('\', '/')
$Vdf = @"
"workshopitem"
{
    "appid"           "221100"
    "publishedfileid" "$PublishedFileId"
    "contentfolder"   "$ContentVdf"
    "previewfile"     "$PreviewVdf"
    "visibility"      "$VisibilityNumber"
    "title"           "WolfGamingZA Dog Tags - Development"
    "description"     "Original WolfGamingZA survivor identity mod. Development build requiring multiplayer testing. Uses temporary vanilla item geometry; preview is an original design concept. Load on both server and client."
    "changenote"      "Official DayZ Tools build with a PBO signature and public server key."
}
"@
$VdfPath = Join-Path $BuildRoot 'workshop_build_item.vdf'
Write-Utf8 $VdfPath $Vdf
$Manifest = @(Get-ChildItem -LiteralPath $Content -File -Recurse | Sort-Object FullName | ForEach-Object {
    (Get-FileHash -LiteralPath $_.FullName -Algorithm SHA256).Hash.ToLowerInvariant() + '  ' + $_.FullName.Substring($Content.Length + 1).Replace('\', '/')
}) -join "`n"
Write-Utf8 (Join-Path $BuildRoot 'SHA256SUMS') ($Manifest + "`n")
Write-Host "Signed upload content: $Content"
Write-Host "Workshop build file: $VdfPath"
Write-Host "Visibility: $Visibility. No upload or game test has been performed."
Write-Host 'Keep the private signing key backed up outside the mod and GitHub.'
Write-Host 'Test with matching server/client files and verifySignatures=2 before public release.'
