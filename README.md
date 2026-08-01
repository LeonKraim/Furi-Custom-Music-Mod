## Furi Dynamic Music Mod

The mod makes the game Furi play your music.
It replaces the original music of the boss fights with your own music.

### The Project Has Two Parts

- The mod. It is the file "FuriDynamicMusic.dll".
  It runs in the game with BepInEx.

- The music pack maker. It makes music packs.
  It is one EXE file, or the file "FuriMusicEditor.py".

### How It Works

- A music pack has your music for one boss fight.
- The pack has a manifest and WAV files.
- The mod reads the pack when the game starts.
- In a fight, the game sends a trigger for each fight moment.
  Examples: the start of the fight, a phase change, an attack sound.
- The mod plays the music of the matching trigger.

### The Files in This Repository

- "FuriDynamicMusic.cs". It is the source code of the mod.
- "FuriMusicEditor.py". It is the source code of the music pack maker.
- "build.ps1". It builds the mod.
- "LICENSE.md". It is the license.
- The folder "Example Pack". It is an example of a music pack.

### Requirements

- The game Furi on your computer.
- BepInEx 5 installed into the game folder.
- ffmpeg.exe. The pack maker uses it to export WAV files.
- Your music track. It can be an MP3, OGG, WAV, or AIF file.

### The Documents Use Simplified Technical English

All instructions in this repository use ASD-STE100.
This is the Simplified Technical English standard.
It makes the instructions clear for all users.

### License

The mod, the pack maker, and the example packs use the "Furi Dynamic Music
Mod License". See the file "LICENSE.md".
The license requires credit to the Author, open-source Source, and a
revenue share for commercial use.

### Current Version

- Mod version: 4.1.1
- Pack schema version: 1
