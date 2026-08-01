@echo off
title Furi Trigger Monitor
setlocal
set "ROOT=%~dp0.."
set "LOG=%ROOT%\BepInEx\LogOutput.log"
if not exist "%LOG%" (
    echo LogOutput.log not found at:
    echo %LOG%
    echo.
    echo Start the game Furi once with the mod installed, then run this file again.
    pause
    exit /b 1
)
echo Watching: %LOG%
echo Shows every game trigger in real time. Close this window (or press Ctrl+C) to stop.
echo.
powershell -NoProfile -ExecutionPolicy Bypass -Command "$m=[regex]'\[[^\]]*\]\s*\[TriggerMonitor\]\s*(.*)'; Get-Content -LiteralPath '%LOG%' -Wait -Tail 40 | Where-Object { $_.Contains('[TriggerMonitor]') } | ForEach-Object { $x=$m.Match($_); if ($x.Success) { Write-Host $x.Groups[1].Value } else { Write-Host $_ } }"
pause
