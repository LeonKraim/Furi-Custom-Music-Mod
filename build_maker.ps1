$ErrorActionPreference = 'Continue'

# Builds FuriMusicPackMaker.exe (one-file, no console) and bundles ffmpeg.exe
# so users do not have to install ffmpeg separately.

$scriptDir = $PSScriptRoot
$vendorDir = Join-Path $scriptDir 'vendor'
$distDir = Join-Path $scriptDir 'dist'
$workDir = Join-Path $scriptDir 'build'
$specFile = Join-Path $scriptDir 'FuriMusicPackMaker.spec'
$editor = Join-Path $scriptDir 'FuriMusicEditor.py'

# 1. Make sure we have an ffmpeg.exe to bundle.
$ffmpeg = Join-Path $vendorDir 'ffmpeg.exe'
if (-not (Test-Path $ffmpeg)) {
    $system = Get-Command ffmpeg.exe -ErrorAction SilentlyContinue
    if ($system) {
        New-Item -ItemType Directory -Force -Path $vendorDir | Out-Null
        Copy-Item -Force $system.Source $ffmpeg
        Write-Host "Copied system ffmpeg to $ffmpeg"
    } else {
        throw "ffmpeg.exe not found. Put ffmpeg.exe into the folder 'vendor' next to this script."
    }
}
Write-Host "Bundling ffmpeg: $ffmpeg"

# 2. Make sure PyInstaller is available.
python -m pip show pyinstaller *> $null
if ($LASTEXITCODE -ne 0) {
    Write-Host 'Installing PyInstaller...'
    python -m pip install pyinstaller
    if ($LASTEXITCODE -ne 0) { throw 'Failed to install PyInstaller.' }
}

# 3. Clean previous build output.
foreach ($path in @($distDir, $workDir)) {
    if (Test-Path $path) { Remove-Item -Recurse -Force $path }
}
if (Test-Path $specFile) { Remove-Item -Force $specFile }

# 4. Build the EXE with ffmpeg inside.
python -m PyInstaller --onefile --windowed --name FuriMusicPackMaker `
    --distpath $distDir --workpath $workDir --specpath $scriptDir `
    --add-binary "$ffmpeg;." $editor 2>&1 | ForEach-Object { Write-Host $_ }

if ($LASTEXITCODE -ne 0) { throw 'PyInstaller build failed.' }

Write-Host ''
Write-Host "Built: $(Join-Path $distDir 'FuriMusicPackMaker.exe')"
Write-Host 'ffmpeg.exe is bundled into the EXE. No separate ffmpeg install is needed.'
