# PythonSH v0.7.8

PythonSH is a GPLv3 Python/PyQt6 inoffical reimplementation and expansion inspired by the original Java SoundHelix project.

The original SoundHelix project is a Java framework for algorithmic random music composition with XML configuration and MIDI output. This Python version keeps the core ideas—seeded composition, configurable harmony, arrangement engines, sequence-like track roles, random song names and MIDI export—but removes the Java runtime dependency and adds a Windows-focused PyQt6 GUI.

Example Output (v.4.9 / commit d0b79c2):

https://github.com/user-attachments/assets/4627ff79-b327-45cb-ac00-ba589ec109fe

Example Output (v.7.9 / commit 2cdb77c ; using Midi-Import Preset with 80% Adaptation Rate / Synth, Melody, Pop Style):

https://github.com/user-attachments/assets/212716bd-2344-423a-8c95-98bd59c96fad

(btw. you can copy a seed to reproduce the same song but make changes to the used instruments and volumes of each midi channel in the finetune tab or add more channels with extra functions. In this example case the output filename was "Electric and Machine_seed1666653313.mid")

Prompt Mode:

<img width="1343" height="513" alt="v7_8_prompt-mode" src="https://github.com/user-attachments/assets/e9ed8f2d-d954-460d-b47f-6a36401a57ce" />

Parameter Mode:

<img width="1345" height="863" alt="v7_8_parameter-mode" src="https://github.com/user-attachments/assets/300b2b73-212a-47d6-9370-5db29728427a" />

## What is included

- PyQt6 Windows GUI, no tkinter.
- Pure-Python Standard MIDI File writer, no Java required.
- SoundHelix-style deterministic random song titles when the song-title field is left blank.
- Preset system inspired by the original XML examples:
  - Original XML Popcorn Expansion, now closer to the Java XML/log output
  - PythonSoundHelix Popcorn Expansion, a shorter enhanced variant
  - Legacy XML Piano Expansion
  - Legacy XML Guitar Expansion
  - Extended Pop
  - Arcade Byte Bubbles
  - public-domain-inspired motif examples: Ode, Elise, Canon and Toccata
  - new genre/style presets: Synthwave, House, Drum and Bass, Ambient, Matrix/Cyber, Funk, LoFi and Orchestral.
  - AlgoMusic legacy-inspired Techno/House presets based on the public Aminet metadata and screenshot-informed pattern concepts for Thomas Schürger's Amiga AlgoMusic.
- Editable track table with roles: drum, bass, chord, arpeggio, melody, pad, counter and texture.
- Per-track instrument dropdowns using General MIDI program names.
- Optional per-instrument loudness normalization. It moves normal notes toward a similar average level while preserving strong accents, fills and highlighted song moments.
- Auto octave/range guard for melody, counter, arpeggio and texture voices, reducing overly high/piercing generated lines while preserving the musical motif.
- Optional WAV rendering through a built-in lightweight synth. No SoundFont is required.
- Optional MP3 rendering when `ffmpeg` is installed and available in `PATH`; MP3 rendering is enabled by default and gracefully skipped when ffmpeg is missing.
- Options tab with theme switching: Dark, Light, Hell, Matrix, Ocean, Avatar, Amiga MUI and MagicWB.
- English/German GUI language switching with tooltips for important controls.
- Seed control and random seed mode; GUI presets now default to randomizing the seed on every generation.
- Key, mode, chord progression, harmonic rhythm and structure controls.
- Humanization, swing, motif memory, variation, LFO expression and call/response controls.
- MIDI export plus JSON result/project export and chord-sheet export.
- History tab with thumbs-up/thumbs-down ratings.
- Simple rating memory: positively rated generations can nudge future randomized generations.
- Original XML inspector tab for the bundled GPLv3 SoundHelix XML examples.
- Windows installer and Nuitka onefile/no-console compile script.

## Start on Windows

1. Extract the ZIP.
2. Run `install_windows.bat` once.
3. Run `run_windows.bat` afterwards.

Generated MIDI/WAV/MP3 files are written to `output/`.

## MP3 export note

WAV export works with the bundled Python dependencies. MP3 export additionally needs `ffmpeg` in the Windows PATH. If ffmpeg is missing or too old for a specific encoder option, the app keeps the WAV and writes a warning to the log instead of crashing or printing raw ffmpeg errors to the console.

## Build EXE on Windows

Run:

```bat
compile_windows_nuitka.bat
```

The result should appear as:

```text
dist\PythonSoundHelix.exe
```

## Command-line generation without GUI

```bat
.venv\Scripts\python.exe PythonSoundHelix.py --nogui --preset "PythonSoundHelix Extended Pop" --random-seed --normalize --render-wav
```

## License

GPLv3. See `COPYING`.

The bundled XML files in `resources/original_soundhelix_examples/` are copied from the supplied SoundHelix source archive and are also treated as GPLv3 reference material.

## Notes about example melodies

The public-domain-inspired examples use short transformed interval contours and generator variation. They are not bundled recordings and are not intended as exact covers. The new genre presets and `Arcade Byte Bubbles` are original generator templates designed to provide catchy, recognizable test material without using commercial melodies.

## v0.7.x

- look at docs/version_info.md for a detailed changelog

## v0.4.9 Seed / Popcorn contour pass

- Added a **Seed variation** control in the Generate tab. Different randomized seeds now change melodic phrase order, weak-note details and arpeggio row ordering more audibly.
- Improved the Popcorn-inspired preset behavior: the template now uses a contour-based synthetic pulse bank instead of being flattened into generic chord tones on strong beats. This is designed to be recognizable as a derivative/tribute style without embedding an exact copyrighted melody.
- Added `--seed-variation 0..100` for CLI generation.
- Arpeggio ordering now reacts to the seed at phrase/bar level, so repeated generations with the same parameters are less structurally identical.

## v0.4.8 AlgoMusic pattern-row pass

- Added AlgoMusic-inspired presets:
  - **AlgoMusic Legacy Techno House**
  - **AlgoMusic 040 Acid Jam**
  - **AlgoMusic Ambient House**
  - **AlgoMusic Techno Pattern Rows**
- Renamed the former ambient-house preset to remove `MUI` from the musical preset name; MUI remains only as a GUI/theme reference.
- Added screenshot-informed digit/dash melody-row logic and symbol-based drum-row logic inspired by the visible AlgoMusic Techno pattern screens.
- Added tracker/Amiga-style generator patterns: `amiga four`, `tracker hats`, `acid pulse`, `random gate`, `tracker arp`, `algomusic drums` and `digit progression`.
- Added melody templates: `AlgoMusic tracker pulse`, `AlgoMusic house chord riff`, `AlgoMusic random walk` and `AlgoMusic digit progression`.
- Added **Amiga MUI** and **MagicWB** GUI themes.
- Added `resources/algomusic_reference/AlgoMusic_Aminet_Notes.txt` documenting the public Aminet facts used as inspiration.
- The AlgoMusic additions are newly written Python logic; no Amiga binary/header/example code is bundled.

## v0.4.4 Popcorn compatibility pass

- Reworked **Original XML Popcorn Expansion** toward the original Java SoundHelix-Popcorn XML/log output.
- Uses 137 BPM, 288 bars, 12 ticks per beat and 36 structural activity sections, matching the original console trace shape.
- Uses the original Am/G/F/C/Em/D duration-bearing harmony pattern instead of falling back to a generic pop progression.
- Adds a separate **PythonSoundHelix Popcorn Expansion** preset for the shorter, more modern enhanced version.
- The classic Popcorn preset uses MIDI-only generation by default to avoid unexpectedly rendering an eight-minute WAV/MP3; audio can still be rendered with the Render/Play button.

## v0.4.1 hotfix

- The main generation button is now labeled **Generate Song** because it creates a complete song project, not only a raw MIDI file.
- The audio button now renders WAV on demand when no WAV/MP3 file exists yet, then opens the rendered audio file.
- WAV rendering is enabled by default for fresh presets, but can still be disabled in Options.


## v0.4.2 register / render polish

- Added an **Auto octave/range guard** option and **Max melody pitch** control.
- Reduced the default melodic register so leads/counters no longer dominate in a very high, piercing octave.
- Folded runaway melody/counter/arpeggio notes back into a musical range instead of deleting them.
- Softened the built-in WAV renderer waveforms and reduced high-note lead/counter dominance.
- Changed several bright bell/celesta-style preset parts to lower octave/volume defaults.
- GUI presets now default to **randomize on generate** enabled.
- MP3 export is enabled by default in the settings and is skipped gracefully if ffmpeg is not available.
- Removed a duplicate LoFi bass track from the preset definition.


## v0.4.3 ffmpeg compatibility hotfix

- Removed `-hide_banner` from MP3 conversion because some older Windows ffmpeg builds reject that option.
- Captures ffmpeg stdout/stderr so failed MP3 conversion does not spam the installer/launcher console.
- Adds MP3 fallback conversion modes and keeps the WAV when MP3 conversion fails.

### v0.4.8 balancing notes

- Changing a musical preset no longer changes the GUI theme. The visual theme is only changed through the Options tab.
- The Normalize Instrument Loudness option now considers per-track note density and durations in addition to velocity, and also adjusts MIDI CC7 volume.
- The Reduce Rapid Note Bursts option removes overly hectic tonal retriggers while keeping drums and real chord clusters intact. This is especially useful for AlgoMusic-inspired tracker/gate/arpeggio presets.

## v0.4.8 Fine Tune tab

This version adds a dedicated **Fine Tune** tab. It contains a global arpeggio-rate slider and per-track sliders for octave, semitone transpose, cents fine-tune and local arpeggio rate. These values are stored in the project JSON and are applied before MIDI/WAV/MP3 output, so regenerating with the same seed keeps the fine-tune decisions.

The **Smart Fine Tune** button applies a conservative automatic layout: bass stays low, pads move slightly down and get tiny cents offsets, arpeggios are kept less busy, counters are moved out of the lead lane, and drums are left untouched.
