$ErrorActionPreference = 'Stop'

$root = Split-Path -Parent $PSScriptRoot
$output = Join-Path $root 'BepInEx\plugins\FuriDynamicMusic'
New-Item -ItemType Directory -Force -Path $output | Out-Null

$references = @(
    (Join-Path $root 'BepInEx\core\BepInEx.dll'),
    (Join-Path $root 'BepInEx\core\0Harmony.dll'),
    (Join-Path $root 'Furi_Data\Managed\netstandard.dll'),
    (Join-Path $root 'Furi_Data\Managed\UnityEngine.dll'),
    (Join-Path $root 'Furi_Data\Managed\UnityEngine.CoreModule.dll'),
    (Join-Path $root 'Furi_Data\Managed\UnityEngine.AudioModule.dll'),
    (Join-Path $root 'Furi_Data\Managed\UnityEngine.AssetBundleModule.dll'),
    (Join-Path $root 'Furi_Data\Managed\UnityEngine.InputLegacyModule.dll'),
    (Join-Path $root 'Furi_Data\Managed\UnityEngine.IMGUIModule.dll'),
    (Join-Path $root 'Furi_Data\Managed\UnityEngine.JSONSerializeModule.dll'),
    (Join-Path $root 'Furi_Data\Managed\UnityEngine.TextRenderingModule.dll'),
    (Join-Path $root 'Furi_Data\Managed\UnityEngine.UnityWebRequestModule.dll'),
    (Join-Path $root 'Furi_Data\Managed\UnityEngine.UnityWebRequestAudioModule.dll')
)

$referenceArgs = $references | ForEach-Object { '/reference:"{0}"' -f $_ }
$source = Join-Path $PSScriptRoot 'FuriDynamicMusic.cs'
$dll = Join-Path $output 'FuriDynamicMusic.dll.new'
& 'C:\Windows\Microsoft.NET\Framework64\v4.0.30319\csc.exe' /nologo /target:library /langversion:5 /optimize+ /out:$dll $referenceArgs $source
if ($LASTEXITCODE -ne 0) { throw 'Compilation failed.' }
Write-Host "Built $dll"
