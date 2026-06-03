# PythonSoundHelix v0.4.3

PythonSoundHelix is a GPLv3 Python/PyQt6 reimplementation and expansion inspired by the original Java SoundHelix project.

The original SoundHelix project is a Java framework for algorithmic random music composition with XML configuration and MIDI output. This Python version keeps the core ideas—seeded composition, configurable harmony, arrangement engines, sequence-like track roles, random song names and MIDI export—but removes the Java runtime dependency and adds a Windows-focused PyQt6 GUI.

<img width="1361" height="979" alt="grafik" src="https://github.com/user-attachments/assets/965a3d40-a6c0-46cc-9848-5f6151acb25b" />

Example Output #1 :

https://github.com/user-attachments/assets/4525d977-92a7-4a5b-a0a2-e133c2a394b3

Example Output #2 :

https://github.com/user-attachments/assets/4c86acb8-f6a9-42a3-abdf-fc95119c9bf0

## What is included

- PyQt6 Windows GUI, no tkinter.
- Pure-Python Standard MIDI File writer, no Java required.
- SoundHelix-style deterministic random song titles when the song-title field is left blank.
- Preset system inspired by the original XML examples:
  - Original XML Popcorn Expansion
  - Legacy XML Piano Expansion
  - Legacy XML Guitar Expansion
  - Extended Pop
  - Arcade Byte Bubbles
  - public-domain-inspired motif examples: Ode, Elise, Canon and Toccata
  - new genre/style presets: Synthwave, House, Drum and Bass, Ambient, Matrix/Cyber, Funk, LoFi and Orchestral.
- Editable track table with roles: drum, bass, chord, arpeggio, melody, pad, counter and texture.
- Per-track instrument dropdowns using General MIDI program names.
- Optional per-instrument loudness normalization. It moves normal notes toward a similar average level while preserving strong accents, fills and highlighted song moments.
- Auto octave/range guard for melody, counter, arpeggio and texture voices, reducing overly high/piercing generated lines while preserving the musical motif.
- Optional WAV rendering through a built-in lightweight synth. No SoundFont is required.
- Optional MP3 rendering when `ffmpeg` is installed and available in `PATH`; MP3 rendering is enabled by default and gracefully skipped when ffmpeg is missing.
- Options tab with theme switching: Dark, Light, Hell, Matrix, Ocean and Avatar.
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


## v0.4.1 hotfix

- The main generation button is now labeled **Generate Song** because it creates a complete song project, not only a raw MIDI file.
- The audio button now renders WAV on demand when no WAV/MP3 file exists yet, then opens the rendered audio file.
- WAV rendering is enabled by default for fresh presets, but can still be disabled in Options.


## v0.4.3 register / render polish

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
