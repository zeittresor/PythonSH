# Changelog

## v0.7.8

- Added a packaged local SQLite style reference database with more than 2,000 rows.
- The database contains style aliases from the Synthwave Midi Reimaginer vocabulary plus curated artist/song reference aliases.
- Artist/song references are mapped only to high-level traits: style family, BPM range, mode tendency, drum feel, bass feel and GM instrument colors. Original songs/melodies are not copied.
- Prompt parser now checks the reference database before generic style matching.
- Added prompt metadata fields: prompt_reference_name, prompt_reference_type and prompt_reference_traits.
- Added a Reference DB tab for searching reference matches and adding user references to app_data/user_style_references.jsonl.
- Added docs/style_reference_schema_postgresql.sql for a future PostgreSQL-backed reference service while keeping local SQLite as the zero-install default.

## v0.7.8

- Added a dedicated psytrance/goa branch instead of treating Goa Trance as generic trance.
- Goa/Psy/acid prompts now force a minor, drive-oriented phrase plan, drums+bass first arrangement, rolling psy bass and stronger four-on-the-floor drum programming.
- Acid lead prompts now create a gated 16th-note acid lead in B/Hook sections rather than a generic melody-first line.
- Psytrance track balancing now boosts kick/bass and reduces pads so prompts like "goa trance uplifting acid lead" no longer resolve to melody/pad-forward output.

## v0.7.8

- Converted the Generate workflow to prompt-first: direct generator parameter panels are hidden by default.
- Added `app/prompt_parser.py` and `app/prompt_style_words.json`.
- Prompt parsing supports English/German/French/Russian-ish vocabulary for style, mood, tempo, density, instruments, meter, key/mode hints, no-drums/no-bass and dissonance control.
- Imported 168 style vocabulary profiles from the uploaded Synthwave Midi Reimaginer style preset data for style matching and instrument/BPM hints.
- CLI now accepts `--prompt "..."` and `--language ...`.
- Generation JSON/chord sheet includes prompt and prompt interpretation.

## v0.7.8

- Added varied seed-specific bass rhythm families so bass no longer always uses the same tango-like hit layout.
- Bass pattern can now be sparse roots, root/fifth, walking, broken octave, syncopated, offbeat pulse, pedal, or rarely tango-like, with section-level variation.
- Added style-safe automatic instrument selection per role and seed. Presets can now change instruments from song to song while staying within the chosen style.
- Added `lock instrument` checkbox in the Finetuning tab. Locked instruments are preserved exactly; unlocked instruments may be auto-selected by the composer.
- Extra tracks added from Finetuning are locked by default because adding them is an explicit manual choice.
- JSON export now includes `effective_tracks` and `bass_pattern_family` for debugging generated arrangements.

## v0.7.8

- Fixed arrangement intro selection: the first bars now have one explicit seed-selected lead role, so songs no longer all drift into pad-first intros.
- Opening role can be drum, bass, melody, chord, or pad depending on seed/style.
- Additional user-added melody tracks are now treated as sparse chord-tone counter/harmony lines by default instead of independent lead melodies.
- Final quality pass is stricter for melody/counter lines: prominent melody notes are chord-tonal, quiet passing notes remain scale-safe, and counter melodies use chord tones only.
- Updated docs/version markers.

## v0.7.8

- Presets now act as style hints by default: key, mode, progression and melody template remain Auto unless manually overridden.
- Added seed-specific arrangement entry profiles so songs can start with pad, melody, drums, chords or bass instead of nearly always bass-first.
- Auto progression now creates section-specific phrase plans instead of resolving to one short repeated progression name.
- Intro uses its own ramp phrase and A/Hook sections get small cycle variations to reduce same-loop repetition.
- Role loudness is seed-varied so some tracks can be foreground, subtle, delayed or occasionally absent.
- Purple and other themes now set explicit readable inactive/active tab colors.
- Language selector now updates main tabs, menu items, buttons, checkboxes and key tooltips immediately for English, German, French and Russian.

## v0.7.8

- Fixed generated songs overwriting previous output files. Output filenames now include the seed and auto-increment when needed.
- Randomized generation now ignores the previously generated title so every generation can receive a fresh song name.
- Reworked Tracks into a Finetuning tab with instrument selection, role/function selection, volume slider, fine-tune slider, octave and transpose controls.
- Added extra-track creation in the Finetuning tab.
- Added Options controls for English/German/French/Russian and interface themes.
- Added GM instrument names for user-facing instrument selection.

