# Music Pack Maker

The music pack maker makes a music pack for the mod.
A music pack has your music for one boss fight.
This document explains how to use the pack maker.

NOTE: The example pack only changes the music of the first fight against The Chain.

## Download the Mod

Get the latest release here:

https://github.com/LeonKraim/Furi-Custom-Music-Mod/releases


## What You Need

- The pack maker. It is one EXE file.
- The game Furi on your computer.
  The pack maker reads the sound banks of the game to make the trigger list.
- Your music track. It can be an MP3, OGG, WAV, or AIF file.

## Make a Pack

1. Open the pack maker.

2. Type the pack name in the field "Pack name".

3. Select the fight in the field "Fight".
   A pack can hold several fights, one for each boss.
   Select "Add fight" to put another boss into the same pack.
   Each fight has its own boss, triggers, and cues.

4. Select the boss in the field "Boss".
   The trigger list shows the triggers of this boss.

5. Select a trigger in the field "Trigger".

6. Select the song for this cue.
   Select "Browse" next to the field "Source track".
   Each cue has its own song.
   This lets the fight switch between different songs at different moments.

7. Type a cue id in the field "Cue id".
   The cue id is a short name for this part of the song.

8. Set the fields "Start (s)" and "End (s)".
   They are the seconds in the source track.
   The pack maker exports this part of the song.

9. Set the fields "BPM" and "Beats/bar".
   They are the tempo of the song.

10. Select the transition.
    "immediate" switches at once.
    "next_beat" switches on the next beat.
    "next_bar" switches on the next bar.

11. For a repeating phase, select "Loop this exported cue".

12. Check the field "Block original sound".
    The pack maker sets it automatically for the selected trigger.
    Keep it ON for music events.
    Set it OFF for attack sounds.
    If it is ON for an attack sound, the attack has no sound.

13. Optional: type "Intro start (s)" and "Intro end (s)".
    The mod plays this part one time at the start of the fight.
    The fade-in takes "Fade-in (s)" seconds.
    Then the rest of the song plays in a loop.
    The rest of the song is from the intro end to the end of the source track.
    To use only the "Start/End" loop, leave the intro fields empty.

14. Optional: select a trigger in the field "Requires trigger".
    The cue fires only after this trigger already fired in the fight.
    This makes sequences: one fight moment plays only after another fight moment.
    Example: a phase-change cue plays only after the phase-2 trigger happened.
    The mod tracks the triggers from the start of the fight.
    The list resets when the fight starts again.

15. Optional: select a trigger in the field "Requires NOT trigger".
    The cue never fires after this trigger already fired in the fight.
    Use it for one-time moments: the cue plays until the trigger happens.
    Example: an intro cue that stops playing once the second phase starts.

16. Select "Add cue".
    The cue appears in the table.

17. Repeat steps 5 to 16 for each fight moment.

18. Select "Build pack".
    The pack maker exports the WAV files.
    This can take some time.

19. The pack is ready.
    The pack folder is in this folder:

    BepInEx\plugins\FuriDynamicMusic\packs\

## Install the Pack

1. Copy the pack folder into this folder:

   BepInEx\plugins\FuriDynamicMusic\packs\

2. Set the config "Active pack" to the pack name.


## Watch the Triggers in Real Time

The file MonitorTriggers.bat shows every trigger the game fires while you play.
The mod writes one line for every event and state change.
This helps you find the right trigger for each fight moment.

1. Start the game with the mod installed.

2. Open MonitorTriggers.bat.
   It shows the triggers in real time.

3. Play the fight.
   Each line shows one event or state.
   Examples:

   EVENT:Play_Law_Music_Arena
   STATE:Law_Path.Law_Path01



## The Words in the Pack Maker

- Trigger. It is one moment in the fight.
  Examples: the start of the fight, a phase change, an attack sound.
- Cue. It is one part of your song.
- Pack. It is the folder with all the cues of one boss fight.
  One pack can hold several boss fights.
  Use "Add fight" in the pack maker to add a fight for another boss.


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

## Watch the Triggers in Real Time

The file MonitorTriggers.bat shows every trigger the game fires while you play.
The mod writes one line for every event and state change.
This helps you find the right trigger for each fight moment.

1. Start the game with the mod installed.
2. Open MonitorTriggers.bat.
   It shows the triggers in real time.
3. Play the fight.
   Each line shows one trigger.
   Examples:

   event:Play_Law_Music_Arena
   state:Law_Path.Law_Path01
