param(
    [string]$Version = "0.4.0",
    [string]$RepoRoot = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path,
    [string]$ToolsRoot = "",
    [string]$ReleaseRoot = "",
    [string]$PythonExe = ""
)

$ErrorActionPreference = "Stop"

if (-not $ToolsRoot) {
    throw "ToolsRoot is required (folder containing repak, UAssetCLI, and dotnet10)."
}
if (-not $ReleaseRoot) {
    $ReleaseRoot = Join-Path $env:TEMP "RoNCT-build-v$Version"
}

$repo = [IO.Path]::GetFullPath($RepoRoot)
$tools = [IO.Path]::GetFullPath($ToolsRoot)
$release = [IO.Path]::GetFullPath($ReleaseRoot)

if (-not (Test-Path (Join-Path $repo "run_gui.py"))) {
    throw "RepoRoot does not look like the RoNCT repository: $repo"
}
foreach ($required in @(
    (Join-Path $tools "repak\repak.exe"),
    (Join-Path $tools "UAssetCLI\UAssetCLI\UAssetCLI.dll"),
    (Join-Path $tools "dotnet10\dotnet.exe")
)) {
    if (-not (Test-Path $required)) {
        throw "Missing bundled tool: $required"
    }
}

$dist = Join-Path $release "dist"
$work = Join-Path $release "work"
$package = Join-Path $release "RoNCT-v$Version-win64"

New-Item -ItemType Directory -Force -Path $release, $dist, $work | Out-Null
if (Test-Path (Join-Path $dist "ReadyOrNot-ModCompatTester")) {
    Remove-Item -LiteralPath (Join-Path $dist "ReadyOrNot-ModCompatTester") -Recurse -Force
}
if (Test-Path (Join-Path $dist "ReadyOrNot-ModCompatTester.exe")) {
    Remove-Item -LiteralPath (Join-Path $dist "ReadyOrNot-ModCompatTester.exe") -Force
}

Write-Host "Building executable with PyInstaller..."
if (-not $PythonExe) {
    $PythonExe = (Get-Command python).Source
}
& $PythonExe -m PyInstaller `
    (Join-Path $repo "packaging\RoNCT.spec") `
    --noconfirm --clean `
    --distpath $dist --workpath $work
if ($LASTEXITCODE -ne 0) {
    throw "PyInstaller failed with exit code $LASTEXITCODE."
}

Write-Host "Staging release package..."
if (Test-Path $package) {
    Remove-Item -LiteralPath $package -Recurse -Force
}
New-Item -ItemType Directory -Force -Path `
    $package, `
    (Join-Path $package "assets"), `
    (Join-Path $package "tools\repak"), `
    (Join-Path $package "tools\uassetcli"), `
    (Join-Path $package "tools\dotnet") | Out-Null

$appSource = Join-Path $dist "ReadyOrNot-ModCompatTester"
Copy-Item (Join-Path $appSource "*") $package -Recurse
Copy-Item (Join-Path $repo "README.md") $package
Copy-Item (Join-Path $repo "CHANGELOG.md") $package
Copy-Item (Join-Path $repo "LICENSE") (Join-Path $package "LICENSE.txt")
Copy-Item (Join-Path $repo "THIRD_PARTY_NOTICES.txt") $package
Copy-Item (Join-Path $repo "assets\logo.png") (Join-Path $package "assets\logo.png")

Copy-Item (Join-Path $tools "repak\repak.exe") (Join-Path $package "tools\repak")
Copy-Item (Join-Path $tools "repak\oo2core_9_win64.dll") (Join-Path $package "tools\repak")
Copy-Item (Join-Path $tools "repak\LICENSE-APACHE") (Join-Path $package "tools\repak")
Copy-Item (Join-Path $tools "repak\LICENSE-MIT") (Join-Path $package "tools\repak")
Copy-Item (Join-Path $tools "repak\README.md") (Join-Path $package "tools\repak")

$uassetSource = Join-Path $tools "UAssetCLI\UAssetCLI"
Get-ChildItem -LiteralPath $uassetSource -File | ForEach-Object {
    Copy-Item $_.FullName (Join-Path $package "tools\uassetcli")
}

Copy-Item (Join-Path $tools "dotnet10\dotnet.exe") (Join-Path $package "tools\dotnet")
Copy-Item (Join-Path $tools "dotnet10\LICENSE.txt") (Join-Path $package "tools\dotnet")
Copy-Item (Join-Path $tools "dotnet10\ThirdPartyNotices.txt") (Join-Path $package "tools\dotnet")
Copy-Item (Join-Path $tools "dotnet10\host") (Join-Path $package "tools\dotnet\host") -Recurse
Copy-Item (Join-Path $tools "dotnet10\shared") (Join-Path $package "tools\dotnet\shared") -Recurse

$zipPath = Join-Path $dist "RoNCT-v$Version-win64.zip"
if (Test-Path $zipPath) {
    Remove-Item -LiteralPath $zipPath -Force
}
Add-Type -AssemblyName System.IO.Compression.FileSystem
[System.IO.Compression.ZipFile]::CreateFromDirectory($package, $zipPath)

Write-Host "Release ZIP: $zipPath"
