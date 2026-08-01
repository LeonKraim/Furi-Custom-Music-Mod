# Music Pack Maker

The music pack maker makes a music pack for the mod.
A music pack has your music for one boss fight.
This document explains how to use the pack maker.

NOTE: The example pack only changes the music of the first fight against The Chain.

## Download the Mod

Get the latest release here:

https://github.com/LeonKraim/Furi-Custom-Music-Mod/releases

Each release has 2 files:

- FuriMusicMod.zip. The mod itself.
  The install guide is below.
- FuriMusicPackMaker.exe. The pack maker.
  It has ffmpeg inside, so no separate ffmpeg install is needed.

## What You Need

- The pack maker. It is one EXE file.
- The game Furi on your computer.
  The pack maker reads the sound banks of the game to make the trigger list.
- ffmpeg.exe. The pack maker uses it to export WAV files.
- Your music track. It can be an MP3, OGG, WAV, or AIF file.

NOTE: The pack maker finds ffmpeg automatically.
If it cannot find ffmpeg, select the file with "Browse".
NOTE: The pack maker finds the game folder automatically.
If it cannot find the game, select the game folder with "Browse".

## The Words in the Pack Maker

- Trigger. It is one moment in the fight.
  Examples: the start of the fight, a phase change, an attack sound.
- Cue. It is one part of your song.
- Pack. It is the folder with all the cues of one boss fight.

## Make a Pack

1. Open the pack maker.

2. Type the pack name in the field "Pack name".

3. Select the source track.
   Select "Browse" next to the field "Source track".

4. Select the boss in the field "Boss".
   The trigger list shows the triggers of this boss.

5. Select a trigger in the field "Trigger".

6. Type a cue id in the field "Cue id".
   The cue id is a short name for this part of the song.

7. Set the fields "Start (s)" and "End (s)".
   They are the seconds in the source track.
   The pack maker exports this part of the song.

8. Set the fields "BPM" and "Beats/bar".
   They are the tempo of the song.

9. Select the transition.
   "immediate" switches at once.
   "next_beat" switches on the next beat.
   "next_bar" switches on the next bar.

10. For a repeating phase, select "Loop this exported cue".

11. Check the field "Block original sound".
    The pack maker sets it automatically for the selected trigger.
    Keep it ON for music events.
    Set it OFF for attack sounds.
    If it is ON for an attack sound, the attack has no sound.

12. Optional: type "Intro start (s)" and "Intro end (s)".
    The mod plays this part one time at the start of the fight.
    The fade-in takes "Fade-in (s)" seconds.
    Then the rest of the song plays in a loop.
    The rest of the song is from the intro end to the end of the source track.
    To use only the "Start/End" loop, leave the intro fields empty.

13. Select "Add cue".
    The cue appears in the table.

14. Repeat steps 5 to 13 for each fight moment.

15. Select "Build pack".
    The pack maker exports the WAV files.
    This can take some time.

16. The pack is ready.
    The pack folder is in this folder:

    BepInEx\plugins\FuriDynamicMusic\packs\

## Install the Pack

1. Copy the pack folder into this folder:

   BepInEx\plugins\FuriDynamicMusic\packs\

2. Set the config "Active pack" to the pack name.


## Notes

- The mod reads the pack when the game starts.
  If you change a pack, build it again and copy it again.
- One pack is for one boss fight.
  Make one pack for each boss.


# Install the Furi Dynamic Music Mod

The mod makes the game Furi play your music.
The music comes from a music pack.
This document explains how to install the mod.

## The Release ZIP File

The ZIP file has one folder: "BepInEx".
The mod file is in this path inside the ZIP:

    BepInEx\plugins\FuriDynamicMusic\FuriDynamicMusic.dll

## Find the Game Folder

1. Open Steam.

2. Select the game Furi in your library.

3. Select "Properties".

4. Select "Installed Files".

5. Select "Browse".
   The game folder opens.
   The game folder has the file "Furi.exe".

## Install BepInEx

Do this step only if the game folder has no folder "BepInEx".

1. Go to the GitHub page of BepInEx.

2. Download "BepInEx 5.4.x" for Windows x64.

3. Open the ZIP file.

4. Copy the folder "BepInEx" into the game folder.

5. Start the game one time.
   BepInEx creates its files.

6. Close the game.

## Install the Mod

1. Close the game.

2. Open the release ZIP file of the mod.

3. Copy the folder "BepInEx" into the game folder.
   If the computer asks, select "Yes" to replace the files.

4. Start the game.
   The mod is now active.
