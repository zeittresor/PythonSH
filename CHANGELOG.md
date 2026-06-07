# Changelog

## v0.6.5

- Fixed arrangement intro selection: the first bars now have one explicit seed-selected lead role, so songs no longer all drift into pad-first intros.
- Opening role can be drum, bass, melody, chord, or pad depending on seed/style.
- Additional user-added melody tracks are now treated as sparse chord-tone counter/harmony lines by default instead of independent lead melodies.
- Final quality pass is stricter for melody/counter lines: prominent melody notes are chord-tonal, quiet passing notes remain scale-safe, and counter melodies use chord tones only.
- Updated docs/version markers.

## v0.6.5

- Presets now act as style hints by default: key, mode, progression and melody template remain Auto unless manually overridden.
- Added seed-specific arrangement entry profiles so songs can start with pad, melody, drums, chords or bass instead of nearly always bass-first.
- Auto progression now creates section-specific phrase plans instead of resolving to one short repeated progression name.
- Intro uses its own ramp phrase and A/Hook sections get small cycle variations to reduce same-loop repetition.
- Role loudness is seed-varied so some tracks can be foreground, subtle, delayed or occasionally absent.
- Purple and other themes now set explicit readable inactive/active tab colors.
- Language selector now updates main tabs, menu items, buttons, checkboxes and key tooltips immediately for English, German, French and Russian.

## v0.6.5

- Fixed generated songs overwriting previous output files. Output filenames now include the seed and auto-increment when needed.
- Randomized generation now ignores the previously generated title so every generation can receive a fresh song name.
- Reworked Tracks into a Finetuning tab with instrument selection, role/function selection, volume slider, fine-tune slider, octave and transpose controls.
- Added extra-track creation in the Finetuning tab.
- Added Options controls for English/German/French/Russian and interface themes.
- Added GM instrument names for user-facing instrument selection.

