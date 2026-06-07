# infos_for_llms.md

v0.6.5 is a quality-first reset. Do not reintroduce independently random per-track composition. The generator must keep one shared song plan: sections, mode, progression, chord map, phrase contour and rhythm grid. Tracks are projections of that plan.

The user specifically complained that melody coverage previously clipped only the beginning. Coverage must be distributed across the whole phrase and must not output an exact copied original phrase. Treat templates as abstract contours only.

Mode/progression compatibility is mandatory. Minor progressions force minor mode; major progressions force major mode. No mixed major/minor track families inside one generated song.


v0.6.5: Melody must not dump a whole phrase in the first bar and then pause until the next pattern. Normalize contour offsets into real multi-bar phrases when contour offsets reset to 0. Apply a melody governor: minimum spacing around half a beat by default, lower melody velocity/CC volume, and strict chord-tone snapping on structurally strong beats. When tonal quality correction changes a note-on pitch, the matching note-off pitch must be changed too.


## v0.6.5
User requested AlgoMusic/SoundHelix-like Auto defaults: do not make all songs start from the same explicit settings. Auto Composer should resolve key/mode/progression/melody-template per seed while maintaining harmonic safety. UI tabs must use always-on vertical scrollbars so Tracks/Options controls are never clipped. Melody coverage must remain distributed over a transformed full phrase and not reintroduce prefix-only behavior.

## v0.6.5 notes

Generated output must never overwrite earlier songs. Filenames include `_seed<seed>` and auto-increment suffixes when needed. If the GUI randomize checkbox is enabled, the previous generated title in the title field must not lock future generations to the same output stem.

Finetuning is the user-facing place for track/instrument adjustments. It includes instrument, role/function, volume, fine-tune cents, octave and transpose. Additional tracks can be added there. Keep defaults conservative because extra independent tracks can damage musical coherence.

## v0.6.5 design note

User feedback on `Circular and Orbit_seed203205412` showed a DNB song still using a fixed minor cadence over long sections and sounding bass-led / insufficiently procedurally arranged. Future changes must keep presets as style hints rather than fixed harmony templates. Use Auto key/mode/progression/template by default, and choose a seed-specific arrangement entry profile (`pad_first`, `melody_first`, `drums_first`, `chords_first`, `bass_first`, `staggered`) so the first audible role varies like SoundHelix/AlgoMusic-style procedural structure.

## v0.6.5 intro and multi-melody rule

Never let pad/chord support automatically share bar 0 with every arrangement profile. The intro should have a single seed-selected lead role for the first few bars: drum, bass, melody, chord, or pad. Extra melody tracks added by the user must not become independent lead generators by default; treat them as counter/harmony lines using chord tones only unless an explicit future "allow dissonance/free counterpoint" option is enabled.
