# Furi Wwise Music Pack

This BepInEx plugin replaces every embedded music media item inside a temporary copy of Furi's own `Music_SoundBank.bnk`. It does not play audio through Unity or a separate Windows audio player.

As a result, Furi itself retains responsibility for music volume, master volume, focus muting, pause behavior, mixing, and music-event timing.

## Current pack scope

For the current test mode, the selected pack's `music/1.wav` is inserted into every music slot from:

`BepInEx/plugins/FuriDynamicMusic/packs/<pack-name>/music/1.wav`

This deliberately makes the supplied track play for all Furi music events, including menus and every boss, while Furi's original event/state/transition graph remains in control. The WAV must be standard 16-bit PCM; the supplied track is already compatible.

## Reversibility

On startup, the plugin saves the untouched stock bank to:

`BepInEx/plugins/FuriDynamicMusic/banks/Music_SoundBank.stock.bnk`

It then stages a patched copy only while the plugin is active. On a normal game exit or when the plugin is unloaded, it restores Furi's original bank. If the game is interrupted, the next plugin start restores stock before applying a fresh replacement.

## Build

Run `FuriMusicMod/build.ps1`. The DLL is written to:

`BepInEx/plugins/FuriDynamicMusic/FuriDynamicMusic.dll`
