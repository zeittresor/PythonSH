# Changelog

## v0.4.3

- Added auto octave/range guard and max melody pitch option.
- Lowered default lead/counter/arpeggio register to avoid overly high, piepsig output.
- Softened the internal WAV synth waveforms and reduced high-note dominance.
- Randomize-on-generate is now the default for GUI presets.
- MP3 export defaults on in settings and skips gracefully when ffmpeg is missing.
- Updated generated JSON/chord-sheet version strings to 0.4.3.
- Cleaned up bright bell/celesta preset octaves and removed duplicate LoFi bass track.


## v0.4.1

- Renamed the main GUI action from "Generate MIDI" to "Generate Song" / "Song generieren".
- Fixed the WAV/MP3 playback workflow: when a song exists but no audio file was rendered yet, the button now renders WAV on demand and then opens it.
- Added a dedicated background audio-render worker so the GUI does not block during on-demand rendering.
- Enabled WAV rendering by default for fresh presets while keeping it optional in the Options tab.

## v0.4.0

- Added SoundHelix-style random song-title generation when the title field is blank.
- Added optional per-instrument loudness normalization with target velocity and strength controls.
- Added optional WAV rendering via a built-in lightweight synth.
- Added optional MP3 export through ffmpeg when available.
- Added per-track instrument dropdowns using General MIDI names.
- Added Options tab with theme selection: Dark, Light, Hell, Matrix, Ocean and Avatar.
- Added English/German GUI language switching and tooltips for important controls.
- Added more genre presets: Synthwave, House, Drum and Bass, Ambient, Matrix/Cyber, Funk, LoFi and Orchestral.
- Added CLI flags: `--normalize`, `--render-wav`, `--render-mp3`.
- Updated package version to 0.4.0.

## v0.2.0

- Initial PyQt6 GPLv3 PythonSoundHelix version.
- Added MIDI export, presets, XML inspector, history/rating memory, JSON project/result export and chord sheets.
