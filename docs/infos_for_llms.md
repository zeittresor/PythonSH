# infos_for_llms.md

v0.7.9 is a quality-first reset. Do not reintroduce independently random per-track composition. The generator must keep one shared song plan: sections, mode, progression, chord map, phrase contour and rhythm grid. Tracks are projections of that plan.

The user specifically complained that melody coverage previously clipped only the beginning. Coverage must be distributed across the whole phrase and must not output an exact copied original phrase. Treat templates as abstract contours only.

Mode/progression compatibility is mandatory. Minor progressions force minor mode; major progressions force major mode. No mixed major/minor track families inside one generated song.


v0.7.9: Melody must not dump a whole phrase in the first bar and then pause until the next pattern. Normalize contour offsets into real multi-bar phrases when contour offsets reset to 0. Apply a melody governor: minimum spacing around half a beat by default, lower melody velocity/CC volume, and strict chord-tone snapping on structurally strong beats. When tonal quality correction changes a note-on pitch, the matching note-off pitch must be changed too.


## v0.7.9
User requested AlgoMusic/SoundHelix-like Auto defaults: do not make all songs start from the same explicit settings. Auto Composer should resolve key/mode/progression/melody-template per seed while maintaining harmonic safety. UI tabs must use always-on vertical scrollbars so Tracks/Options controls are never clipped. Melody coverage must remain distributed over a transformed full phrase and not reintroduce prefix-only behavior.

## v0.7.9 notes

Generated output must never overwrite earlier songs. Filenames include `_seed<seed>` and auto-increment suffixes when needed. If the GUI randomize checkbox is enabled, the previous generated title in the title field must not lock future generations to the same output stem.

Finetuning is the user-facing place for track/instrument adjustments. It includes instrument, role/function, volume, fine-tune cents, octave and transpose. Additional tracks can be added there. Keep defaults conservative because extra independent tracks can damage musical coherence.

## v0.7.9 design note

User feedback on `Circular and Orbit_seed203205412` showed a DNB song still using a fixed minor cadence over long sections and sounding bass-led / insufficiently procedurally arranged. Future changes must keep presets as style hints rather than fixed harmony templates. Use Auto key/mode/progression/template by default, and choose a seed-specific arrangement entry profile (`pad_first`, `melody_first`, `drums_first`, `chords_first`, `bass_first`, `staggered`) so the first audible role varies like SoundHelix/AlgoMusic-style procedural structure.

## v0.7.9 intro and multi-melody rule

Never let pad/chord support automatically share bar 0 with every arrangement profile. The intro should have a single seed-selected lead role for the first few bars: drum, bass, melody, chord, or pad. Extra melody tracks added by the user must not become independent lead generators by default; treat them as counter/harmony lines using chord tones only unless an explicit future "allow dissonance/free counterpoint" option is enabled.


## v0.7.9 bass/instrument variation rule

Do not make the bass role use one fixed rhythmic pattern across all generated songs. Bass must use seed/style/section-dependent rhythm families, with tango-like rhythm rare rather than default. Instruments are also part of the procedural arrangement: if a track is not locked in Finetuning, the engine may select a style-safe GM program for that role. If `lock_instrument` is true, never override the user-selected program.


## v0.7.9 prompt-first architecture

The user requested that direct generator parameters no longer be the primary interaction model. The Generate tab should be prompt-first. Keep advanced technical widgets hidden or secondary. Prompt parsing is intentionally local/offline: no LLM/API dependency. `prompt_parser.py` maps multilingual words and imported Synthwave Midi Reimaginer style vocabulary to safe GeneratorSettings. Manual Finetuning remains available as an optional override, especially for locked instruments, but normal users should be able to type a request such as "dark melodic drum and bass with airy pads, no dissonance" and generate a complete song.

## v0.7.9 Prompt style enforcement

Prompt parser output must drive generator behavior, not merely annotate it. Keep `prompt_style_family` as the highest-priority style source inside `generator._style_hint()`. A prompt like "techno misc with hard drums" must lead to a techno family arrangement: four-on-the-floor kick, hard drums if requested, bass/stab emphasis, reduced pads, sparse lead melody. This rule applies to all style families, not just techno.

## v0.7.9 reference DB rule

Artist/song references are allowed only as high-level style interpretation hints. Never generate a cover, melody clone, lyric paraphrase, or recognizably copied arrangement. The local database maps references to abstract traits such as family, tempo range, mode tendency, drum feel, bass feel, intensity, and GM program colors. If expanding the database, prefer many small alias rows with clear `no_copy=1` semantics and confidence values. User additions live in `app_data/user_style_references.jsonl`.


## v0.7.9 multi-style prompt blend rule

Prompts that name multiple related styles separated by punctuation, e.g. `goa / techno / psytrance`, must not be collapsed to only one reference match. The generator should preserve the blend and make audible arrangement decisions from it. For goa+techno+psytrance, use a drum+bass-forward psy/techno drive: layered kick/tom, 4-on-the-floor, open hats, closed hats, clap/snare, rides in active sections, rolling off-beat psy bass from bar 1, reduced pads, and acid/lead parts later in the arrangement.

## v0.7.9 prompt-style priority rule

Prompt parser must correct common style typos before reference matching.  Explicit style phrases beat weak reference hits.  Example: `dark melodic dran and bass` must be normalized to `dark melodic drum and bass` and resolved as DnB, not Aggrotech.  DnB requires a dedicated drum+bass arrangement profile with breakbeat-style drums and sub/reese bass from bar 1.

## v0.7.9 semantic relation rule

Prompt understanding must not be only single best style match. Combine explicit style phrases, typo corrections, reference DB hits, moods and instrument words into relation profiles. Explicit style phrases such as drum and bass / dnb, goa / psytrance / techno, metal, dub, chiptune must override vague trait hits. Keep relation profile data in JSON so bad generations can be diagnosed from prompt_relation_profile, prompt_semantic_tags and prompt_style_confidence.

## v0.7.9 UI/Prompt notes

Generate tab has two modes. Prompt-first is default. Options contains a switch that reveals the original direct parameter controls and disables prompt interpretation by setting `settings.prompt_mode=False`. Do not remove this fallback view. Artist/song references such as Nirvana should be kept as no-copy style-trait blends when combined with explicit styles such as techno.

## v0.7.9 MIDI preset import rule

Imported MIDI files are not copied 1:1. The importer extracts a transformed full-song contour from the most likely melody channel, estimates key/mode/BPM/bars, and stores JSON metadata in app_data/imported_midi_presets. The generator uses that full contour across the generated song and snaps notes to the active generated chord/scale map. This lets users create derivative/inspired presets from MIDI sources while preserving the no-copy policy unless the user has rights and deliberately designs otherwise.
