# PythonSoundHelix v0.2.0

PythonSoundHelix is a GPLv3 Python/PyQt6 reimplementation and expansion inspired by the original Java SoundHelix project.

The original SoundHelix project (soundhelix.com) is a Java framework for algorithmic random music composition with XML configuration and MIDI output. This Python version keeps the core ideas—seeded composition, configurable harmony, arrangement engines, sequence-like track roles and MIDI export—but removes the Java runtime dependency and adds a Windows-focused PyQt6 GUI.

## What is included

- PyQt6 Windows GUI, no tkinter.
- Pure-Python Standard MIDI File writer, no Java required.
- Preset system inspired by the original XML examples:
  - Original XML Popcorn Expansion
  - Legacy XML Piano Expansion
  - Legacy XML Guitar Expansion
  - Extended Pop
  - Arcade Byte Bubbles
  - public-domain-inspired motif examples: Ode, Elise, Canon and Toccata.
- Editable track table with roles: drum, bass, chord, arpeggio, melody, pad, counter and texture.
- Seed control and random seed mode.
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

Generated MIDI files are written to `output/`.

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
.venv\Scripts\python.exe PythonSoundHelix.py --nogui --preset "PythonSoundHelix Extended Pop" --random-seed
```

## License

GPLv3. See `COPYING`.

The bundled XML files in `resources/original_soundhelix_examples/` are copied from the supplied SoundHelix source archive and are also treated as GPLv3 reference material.

## Notes about example melodies

The public-domain-inspired examples use short transformed interval contours and generator variation. They are not bundled recordings and are not intended as exact covers. The new `Arcade Byte Bubbles` preset is an original catchy synthetic hook designed to provide the same kind of immediately recognizable, playful generator test that the Popcorn example provides.


## Source (this python port)

github.com/zeittresor/PythonSH
