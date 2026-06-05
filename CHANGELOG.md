# Changelog

## v0.4.9

- Added Generate-tab **Seed variation** control.
- Added CLI option `--seed-variation`.
- Made template melodies seed-sensitive without destroying their contour.
- Improved Popcorn-inspired contour hook behavior and reduced chord-tone flattening.
- Made arpeggio row order and phrase density react more clearly to seed changes.


## v0.4.8

- Renamed **AlgoMusic MUI Ambient House** to **AlgoMusic Ambient House** because MUI belongs to the Amiga GUI/theme context, not to the music style.
- Added **AlgoMusic Techno Pattern Rows**, a new screenshot-informed preset that recombines digit/dash melody rows and symbol-based drum rows into full songs.
- Added pattern-bank helpers for AlgoMusic-style digit rows (`1`, `2`, `3`, `4`, `-`) and drum rows (`+`, `^`, `*`, `.`, `:`, `X`).
- Added new pattern options: `algomusic drums` and `digit progression`.
- Added the new melody template `AlgoMusic digit progression`.
- Cleaned up AlgoMusic track/descriptions that incorrectly used MUI as a musical term.
- Regenerated bundled preset JSON files.

## v0.4.4

- Reworked the Original XML Popcorn Expansion preset toward the original Java SoundHelix-Popcorn XML/log behavior.
- Added 36-section legacy activity-matrix support for the Popcorn compatibility preset.
- Added full-length XML-style Popcorn defaults: 137 BPM, 288 bars and 12 ticks per beat.
- Scaled the original duration-bearing Am/G/F/C/Em/D chord pattern across the full song.
- Added a separate PythonSoundHelix Popcorn Expansion preset for the shorter enhanced variant.
- Increased GUI section-count range to 64 and lowered ticks-per-beat minimum to 12.
- Updated generated JSON/chord-sheet version strings to 0.4.4.

## v0.4.3

- Removed `-hide_banner` from MP3 conversion because some older Windows ffmpeg builds reject that option.
- Captures ffmpeg stdout/stderr so failed MP3 conversion does not spam the installer/launcher console.
- Adds MP3 fallback conversion modes and keeps the WAV when MP3 conversion fails.

## v0.4.2

- Added auto octave/range guard and max melody pitch option.
- Lowered default lead/counter/arpeggio register to avoid overly high, piepsig output.
- Softened the internal WAV synth waveforms and reduced high-note dominance.
- Randomize-on-generate is now the default for GUI presets.
- MP3 export defaults on in settings and skips gracefully when ffmpeg is missing.
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

## v0.4.8 Fine Tune / arpeggio control pass

- Added a dedicated Fine Tune tab.
- Added a global arpeggio-rate slider, persisted in project JSON as `global_arpeggio_rate`.
- Added per-track octave, semitone transpose, cents fine-tune and arpeggio-rate sliders.
- Added `Smart Fine Tune`, which spreads bass/chords/pads/melodies/arpeggios into saner pitch lanes and calms arpeggio rates.
- Added per-track `transpose`, `fine_tune_cents` and `arp_rate` fields.
- MIDI output now writes pitch-bend events for cents fine-tuning on non-drum tracks.
- The built-in WAV renderer now also applies cents fine-tuning, so exported WAV/MP3 matches the fine-tune settings.
- Added CLI option `--arpeggio-rate` for quick no-GUI testing.
