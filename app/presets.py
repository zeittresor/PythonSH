# PythonSoundHelix - GPLv3 Python/PyQt6 reimplementation inspired by SoundHelix.
# Original source basis: SoundHelix SVN archive soundhelix-code-r896-trunk, version 0.10u.
# Original project: https://www.soundhelix.com/
# This file is part of PythonSoundHelix and is released under GPLv3.

from __future__ import annotations

from copy import deepcopy
from pathlib import Path
from typing import Dict, List

from .models import GeneratorSettings, TrackSettings
from .music_theory import GM_PROGRAMS


def _t(name: str, role: str, channel: int, program_name: str | int, volume: int, pan: int, density: int, complexity: int, activity: int, pattern: str = "auto", octave: int = 0, mute_intro: bool = False, fill_every: int = 8) -> TrackSettings:
    program = program_name if isinstance(program_name, int) else GM_PROGRAMS.get(program_name, 0)
    return TrackSettings(name=name, role=role, channel=channel, program=program, volume=volume, pan=pan, density=density, complexity=complexity, activity=activity, pattern=pattern, octave=octave, mute_in_intro=mute_intro, fill_every=fill_every)


def _base(name: str) -> GeneratorSettings:
    return GeneratorSettings(preset_name=name, tracks=[])


def make_presets() -> Dict[str, GeneratorSettings]:
    presets: Dict[str, GeneratorSettings] = {}

    p = _base("PythonSoundHelix Extended Pop")
    p.description = "Modern pop/electro generator with full band arrangement, motif memory and rating-aware randomization."
    p.bpm = 118; p.bars = 96; p.key = "C"; p.mode = "major"; p.progression = "I,V,vi,IV"; p.complexity = 58; p.variation = 52; p.swing = 7
    p.tracks = [
        _t("Drum Matrix", "drum", 9, 0, 100, 64, 82, 70, 92, "electro four", fill_every=8),
        _t("Round Bass", "bass", 1, "Synth Bass 1", 92, 50, 78, 55, 88, "sync eighth", octave=-1, mute_intro=True),
        _t("Pulse Chords", "chord", 2, "Electric Piano 2", 82, 38, 70, 55, 82, "stab"),
        _t("Warm Pad", "pad", 3, "Pad 2 (warm)", 70, 74, 55, 35, 95, "long"),
        _t("Lead Motif", "melody", 4, "Lead 2 (sawtooth)", 96, 64, 68, 70, 78, "auto", mute_intro=True),
        _t("Answer Bell", "counter", 5, "Vibraphone", 54, 86, 42, 45, 48, "answer", octave=0, mute_intro=True),
    ]
    presets[p.preset_name] = p

    p = _base("Original XML Popcorn Expansion")
    p.description = "Closer compatibility preset for the original SoundHelix-Popcorn XML/log: 137 BPM, 288 bars, 12 TPB, 36 activity sections and the original Am/G/F/C/Em/D chord pattern. Still Python-native and editable in the GUI."
    p.bpm = 137; p.bars = 288; p.beats_per_bar = 4; p.ticks_per_beat = 12; p.key = "A"; p.mode = "minor"
    p.progression = "Am/10,G/2,F/2,Am/12,G/2,F/2,Am/2,+C/8,Em/2,D/2,C/12,Em/2,D/2,C/4"
    p.harmonic_rhythm = 1; p.section_count = 36
    p.complexity = 62; p.variation = 42; p.swing = 0; p.humanize_ticks = 0; p.humanize_velocity = 6; p.motif_memory = 78; p.accent_strength = 30
    p.melody_template = "Popcorn-style original pulse"; p.auto_range_guard = True; p.max_melody_pitch = 84
    p.use_rating_memory = False
    # Long classic preset: avoid unexpectedly rendering an eight-minute WAV/MP3 on every generation.
    # The Render/Play button can still render audio explicitly.
    p.render_wav = False; p.render_mp3 = False
    p.tracks = [
        _t("base_snare", "drum", 9, 0, 100, 64, 72, 68, 100, "base_snare", fill_every=0),
        _t("clap", "drum", 9, 0, 88, 64, 56, 50, 100, "clap", fill_every=0),
        _t("hihat", "drum", 9, 0, 70, 64, 64, 52, 100, "hihat", fill_every=0),
        _t("bass", "bass", 1, "Synth Bass 2", 92, 48, 70, 48, 100, "eighth", octave=-1),
        _t("chords", "chord", 2, "Drawbar Organ", 76, 38, 52, 44, 100, "stab"),
        _t("accomp", "chord", 3, "Electric Piano 2", 70, 42, 50, 38, 100, "stab"),
        _t("arpeggio", "arpeggio", 4, "Celesta", 56, 82, 70, 60, 100, "updown", octave=0),
        _t("melody", "melody", 5, "Lead 1 (square)", 96, 62, 86, 78, 100, "template", octave=0),
        _t("pad", "pad", 6, "Pad 7 (halo)", 58, 88, 38, 30, 100, "long"),
        _t("string", "pad", 7, "String Ensemble 1", 60, 76, 34, 28, 100, "long"),
    ]
    presets[p.preset_name] = p

    p = _base("PythonSoundHelix Popcorn Expansion")
    p.description = "Shorter, more modern Python expansion of the Popcorn idea with extra tracks and GUI-friendly audio rendering."
    p.bpm = 136; p.bars = 128; p.key = "A"; p.mode = "minor"; p.progression = "Am/10,G/2,F/2,Am/12,G/2,F/2,Am/2,+C/8,Em/2,D/2,C/12,Em/2,D/2,C/4"; p.harmonic_rhythm = 1
    p.complexity = 72; p.variation = 66; p.swing = 4; p.melody_template = "Popcorn-style original pulse"
    p.tracks = [
        _t("Popcorn Drums Plus", "drum", 9, 0, 104, 64, 88, 82, 95, "electro four", fill_every=4),
        _t("Pop Bass", "bass", 1, "Synth Bass 2", 96, 48, 84, 60, 92, "sync eighth", octave=-1),
        _t("Pluck Hook", "melody", 2, "Lead 1 (square)", 105, 62, 96, 86, 100, "template"),
        _t("Glass Arp", "arpeggio", 3, "Celesta", 74, 80, 90, 72, 88, "updown", octave=0),
        _t("Offbeat Organ", "chord", 4, "Drawbar Organ", 72, 36, 68, 50, 76, "stab"),
        _t("Space Pad", "pad", 5, "Pad 7 (halo)", 62, 94, 45, 38, 88, "long"),
        _t("Noise Spark", "texture", 6, "FX 3 (crystal)", 42, 72, 38, 70, 46, "spark", octave=0),
    ]
    presets[p.preset_name] = p

    p = _base("Public Domain Ode Electro")
    p.description = "Electro arrangement with a short public-domain Ode-to-Joy-style motif transformed by the generator."
    p.bpm = 124; p.bars = 96; p.key = "D"; p.mode = "major"; p.progression = "I,V,vi,IV,ii,V,I,I"; p.complexity = 62; p.variation = 58; p.swing = 5; p.melody_template = "Ode-to-Joy public-domain hint"
    p.tracks = [
        _t("Ceremony Drums", "drum", 9, 0, 96, 64, 76, 68, 88, "four"),
        _t("Choir Pad", "pad", 1, "Choir Aahs", 76, 62, 52, 36, 94, "long"),
        _t("Classic Lead", "melody", 2, "Lead 3 (calliope)", 96, 72, 86, 65, 92, "template"),
        _t("Piano Chords", "chord", 3, "Bright Acoustic Piano", 82, 44, 68, 50, 84, "block"),
        _t("Cello Bass", "bass", 4, "Cello", 84, 54, 62, 48, 80, "eighth", octave=-1),
        _t("Bell Answer", "counter", 5, "Vibraphone", 52, 92, 34, 44, 45, "answer", octave=0),
    ]
    presets[p.preset_name] = p

    p = _base("Public Domain Elise Synth")
    p.description = "Minor-key synth piece using a short public-domain Für-Elise-style interval contour as a seed, not a fixed cover."
    p.bpm = 132; p.bars = 112; p.key = "A"; p.mode = "minor"; p.progression = "i,VII,VI,V,i,iv,V,i"; p.complexity = 68; p.variation = 62; p.swing = 3; p.melody_template = "Fuer-Elise public-domain hint"
    p.tracks = [
        _t("Broken Beat", "drum", 9, 0, 92, 64, 74, 78, 86, "broken electro", fill_every=8),
        _t("Left Hand Bass", "bass", 1, "Synth Bass 1", 90, 42, 72, 58, 88, "sync eighth", octave=-1),
        _t("Elise Pluck", "melody", 2, "Clavinet", 94, 68, 86, 78, 92, "template"),
        _t("Dark Arp", "arpeggio", 3, "Harpsichord", 76, 82, 88, 72, 84, "down", octave=0),
        _t("Minor Pad", "pad", 4, "Pad 3 (polysynth)", 66, 78, 48, 36, 90, "long"),
    ]
    presets[p.preset_name] = p

    p = _base("Public Domain Canon Dream")
    p.description = "Pachelbel-Canon-inspired public-domain chord movement with modern arps and pads."
    p.bpm = 110; p.bars = 128; p.key = "D"; p.mode = "major"; p.progression = "I,V,vi,iii,IV,I,IV,V"; p.complexity = 55; p.variation = 48; p.swing = 6; p.melody_template = "Canon public-domain hint"
    p.tracks = [
        _t("Soft Drum", "drum", 9, 0, 78, 64, 54, 42, 70, "soft four", fill_every=16),
        _t("Canon Bass", "bass", 1, "Fretless Bass", 84, 50, 66, 48, 82, "eighth", octave=-1),
        _t("Glass Canon", "arpeggio", 2, "Vibraphone", 68, 86, 84, 64, 86, "updown", octave=0),
        _t("String Pad", "pad", 3, "String Ensemble 1", 72, 42, 58, 40, 96, "long"),
        _t("Quiet Lead", "melody", 4, "Flute", 76, 70, 52, 48, 54, "template"),
    ]
    presets[p.preset_name] = p

    p = _base("Public Domain Toccata Drive")
    p.description = "Dark organ/electro drive with a short public-domain toccata-like contour and heavier drums."
    p.bpm = 142; p.bars = 96; p.key = "D"; p.mode = "minor"; p.progression = "i,VII,VI,V,iv,i,V,i"; p.complexity = 78; p.variation = 72; p.swing = 2; p.melody_template = "Toccata public-domain hint"
    p.tracks = [
        _t("Heavy Machine", "drum", 9, 0, 108, 64, 90, 86, 96, "electro four", fill_every=4),
        _t("Pedal Bass", "bass", 1, "Synth Bass 2", 100, 45, 92, 72, 94, "sync eighth", octave=-1),
        _t("Organ Hook", "melody", 2, "Drawbar Organ", 102, 65, 86, 82, 94, "template"),
        _t("Church Stabs", "chord", 3, "Reed Organ", 82, 38, 74, 68, 86, "stab"),
        _t("Dark Halo", "pad", 4, "Pad 7 (halo)", 60, 92, 38, 45, 78, "long"),
    ]
    presets[p.preset_name] = p

    p = _base("Legacy XML Piano Expansion")
    p.description = "Python expansion inspired by the original SoundHelix-Piano XML: piano, arpeggio, melody and bass with richer controls."
    p.bpm = 96; p.bars = 112; p.key = "C"; p.mode = "major"; p.progression = "I,vi,IV,V"; p.complexity = 48; p.variation = 44; p.swing = 10
    p.tracks = [
        _t("Piano Accomp", "chord", 0, "Acoustic Grand Piano", 90, 48, 66, 44, 86, "block"),
        _t("Piano Arpeggio", "arpeggio", 1, "Bright Acoustic Piano", 78, 82, 76, 54, 76, "updown"),
        _t("Piano Melody", "melody", 2, "Electric Grand Piano", 78, 64, 55, 48, 64, "auto", octave=0, mute_intro=True),
        _t("Upright Bass", "bass", 3, "Acoustic Bass", 74, 52, 55, 38, 70, "eighth", octave=-1),
        _t("Room Pad", "pad", 4, "String Ensemble 2", 52, 75, 28, 24, 60, "long"),
    ]
    presets[p.preset_name] = p

    p = _base("Legacy XML Guitar Expansion")
    p.description = "Python expansion inspired by the original SoundHelix-Guitar XML: strummed guitar, bass and melody."
    p.bpm = 104; p.bars = 96; p.key = "G"; p.mode = "major"; p.progression = "I,V,vi,IV"; p.complexity = 50; p.variation = 45; p.swing = 12
    p.tracks = [
        _t("Steel Guitar", "chord", 0, "Acoustic Guitar (steel)", 90, 42, 78, 45, 90, "guitar"),
        _t("Clean Lead", "melody", 1, "Electric Guitar (clean)", 78, 68, 45, 48, 56, "auto", mute_intro=True),
        _t("Picked Bass", "bass", 2, "Electric Bass (finger)", 82, 52, 62, 40, 82, "eighth", octave=-1),
        _t("Light Percussion", "drum", 9, 0, 80, 64, 48, 38, 56, "soft four", fill_every=16),
    ]
    presets[p.preset_name] = p

    p = _base("New Arcade Byte Bubbles")
    p.description = "New catchy arcade/electro example with an original hook in the spirit of memorable synthetic novelty melodies."
    p.bpm = 150; p.bars = 96; p.key = "F"; p.mode = "mixolydian"; p.progression = "I,VII,IV,I"; p.complexity = 74; p.variation = 74; p.swing = 4; p.melody_template = "Original arcade anthem"
    p.tracks = [
        _t("Arcade Drums", "drum", 9, 0, 104, 64, 86, 82, 94, "electro four", fill_every=4),
        _t("Bubble Bass", "bass", 1, "Synth Bass 1", 98, 42, 88, 70, 92, "sync eighth", octave=-1),
        _t("Byte Hook", "melody", 2, "Lead 1 (square)", 104, 66, 94, 86, 100, "template"),
        _t("Coin Arp", "arpeggio", 3, "Tinkle Bell", 66, 84, 84, 76, 82, "updown", octave=0),
        _t("Chip Chords", "chord", 4, "Lead 8 (bass + lead)", 72, 34, 70, 55, 74, "stab"),
        _t("Pixel Dust", "texture", 5, "FX 3 (crystal)", 40, 90, 36, 65, 42, "spark", octave=0),
    ]
    presets[p.preset_name] = p


    p = _base("Synthwave Night Drive")
    p.description = "Wide synthwave preset with sidechain-like pulse chords, steady electronic drums and a neon lead contour."
    p.bpm = 112; p.bars = 128; p.key = "C"; p.mode = "minor"; p.progression = "i,VI,III,VII"; p.complexity = 62; p.variation = 60; p.swing = 3
    p.tracks = [
        _t("Retro Drums", "drum", 9, 0, 98, 64, 78, 70, 90, "electro four", fill_every=8),
        _t("Sub Drive", "bass", 1, "Synth Bass 1", 96, 48, 82, 64, 92, "sync eighth", octave=-1),
        _t("Sidechain Chords", "chord", 2, "Pad 3 (polysynth)", 78, 38, 72, 55, 86, "stab"),
        _t("Night Pad", "pad", 3, "Pad 2 (warm)", 66, 78, 46, 35, 98, "long"),
        _t("Chrome Lead", "melody", 4, "Lead 2 (sawtooth)", 94, 64, 64, 68, 76, "auto", mute_intro=True),
        _t("Glass Echo", "counter", 5, "Celesta", 50, 90, 38, 45, 45, "answer", octave=0),
    ]
    presets[p.preset_name] = p

    p = _base("House Floor Builder")
    p.description = "Four-on-the-floor dance preset with repeating bass, offbeat harmonic stabs and gradual hook energy."
    p.bpm = 126; p.bars = 128; p.key = "F"; p.mode = "minor"; p.progression = "i,VI,III,VII"; p.complexity = 60; p.variation = 52; p.swing = 2
    p.tracks = [
        _t("Club Drums", "drum", 9, 0, 108, 64, 92, 78, 98, "electro four", fill_every=4),
        _t("Rubber Bass", "bass", 1, "Synth Bass 2", 98, 50, 88, 66, 96, "sync eighth", octave=-1),
        _t("Piano Stab", "chord", 2, "Electric Piano 2", 86, 40, 78, 58, 90, "stab"),
        _t("Air Pad", "pad", 3, "Pad 1 (new age)", 54, 82, 35, 30, 86, "long"),
        _t("Hook Lead", "melody", 4, "Lead 1 (square)", 84, 64, 58, 62, 62, "auto", mute_intro=True),
    ]
    presets[p.preset_name] = p

    p = _base("Drum and Bass Neon")
    p.description = "Fast broken-beat preset with busy bass movement, glass arps and high-energy fills."
    p.bpm = 172; p.bars = 96; p.key = "E"; p.mode = "minor"; p.progression = "i,VII,VI,V"; p.complexity = 82; p.variation = 78; p.swing = 4
    p.tracks = [
        _t("Break Drums", "drum", 9, 0, 110, 64, 94, 90, 100, "broken electro", fill_every=4),
        _t("Reese-ish Bass", "bass", 1, "Synth Bass 2", 104, 48, 92, 84, 96, "sync eighth", octave=-1),
        _t("Neon Arp", "arpeggio", 2, "Lead 8 (bass + lead)", 76, 82, 92, 80, 86, "updown", octave=0),
        _t("Dark Pad", "pad", 3, "Pad 7 (halo)", 56, 76, 40, 40, 76, "long"),
        _t("Needle Lead", "melody", 4, "Lead 2 (sawtooth)", 86, 62, 62, 70, 62, "auto", mute_intro=True),
    ]
    presets[p.preset_name] = p

    p = _base("Ambient Ocean Pad")
    p.description = "Slow, spacious ambient preset with long pads, light textures and sparse melodic fragments."
    p.bpm = 78; p.bars = 96; p.key = "Bb"; p.mode = "lydian"; p.progression = "I,V,ii,IV"; p.complexity = 34; p.variation = 46; p.swing = 10
    p.tracks = [
        _t("Soft Tide", "pad", 0, "Pad 1 (new age)", 76, 42, 36, 25, 100, "long"),
        _t("Deep Current", "bass", 1, "Fretless Bass", 58, 52, 35, 25, 50, "eighth", octave=-1),
        _t("Pearl Arp", "arpeggio", 2, "Vibraphone", 44, 88, 40, 45, 42, "updown", octave=0),
        _t("Ocean Spark", "texture", 3, "FX 1 (rain)", 38, 90, 38, 55, 48, "spark", octave=0),
        _t("Lonely Flute", "melody", 4, "Flute", 62, 60, 28, 35, 34, "auto", mute_intro=True),
    ]
    presets[p.preset_name] = p

    p = _base("Matrix Terminal Pulse")
    p.description = "Minimal cyber sequence preset with ticking percussion, repeating bass and crystalline counters."
    p.bpm = 132; p.bars = 96; p.key = "G"; p.mode = "phrygian"; p.progression = "i,II,i,VII"; p.complexity = 68; p.variation = 70; p.swing = 1
    p.tracks = [
        _t("Terminal Ticks", "drum", 9, 0, 92, 64, 72, 78, 88, "broken electro", fill_every=8),
        _t("Code Bass", "bass", 1, "Synth Bass 1", 94, 50, 82, 68, 90, "sync eighth", octave=-1),
        _t("Green Arp", "arpeggio", 2, "Kalimba", 70, 84, 86, 72, 86, "updown", octave=0),
        _t("CRT Pad", "pad", 3, "Pad 4 (choir)", 54, 72, 34, 36, 78, "long"),
        _t("Debug Lead", "counter", 4, "Lead 1 (square)", 64, 62, 38, 50, 52, "answer"),
    ]
    presets[p.preset_name] = p

    p = _base("Funky Brass Shuffle")
    p.description = "Upbeat funky preset with swung drums, bass movement, brass stabs and short call/response phrases."
    p.bpm = 108; p.bars = 96; p.key = "Eb"; p.mode = "mixolydian"; p.progression = "I,IV,I,V"; p.complexity = 64; p.variation = 68; p.swing = 28
    p.tracks = [
        _t("Shuffle Kit", "drum", 9, 0, 96, 64, 72, 72, 92, "four", fill_every=8),
        _t("Finger Bass", "bass", 1, "Electric Bass (finger)", 94, 46, 82, 62, 90, "eighth", octave=-1),
        _t("Brass Hits", "chord", 2, "Brass Section", 86, 34, 72, 60, 82, "stab"),
        _t("Clav Groove", "arpeggio", 3, "Clavinet", 76, 74, 78, 66, 86, "updown"),
        _t("Sax Reply", "counter", 4, "Alto Sax", 70, 86, 45, 56, 58, "answer"),
    ]
    presets[p.preset_name] = p

    p = _base("LoFi Piano Rain")
    p.description = "Soft lo-fi/chill preset with gentle piano, rounded bass, rain texture and relaxed swing."
    p.bpm = 86; p.bars = 96; p.key = "A"; p.mode = "minor"; p.progression = "i,VI,iv,V"; p.complexity = 42; p.variation = 45; p.swing = 18
    p.tracks = [
        _t("Dusty Beat", "drum", 9, 0, 70, 64, 48, 44, 70, "soft four", fill_every=16),
        _t("Soft Bass", "bass", 1, "Fretless Bass", 68, 48, 46, 34, 72, "eighth", octave=-1),
        _t("Rain Piano", "chord", 2, "Electric Piano 1", 80, 42, 64, 40, 86, "block"),
        _t("Cassette Pad", "pad", 3, "Pad 2 (warm)", 46, 76, 34, 28, 80, "long"),
        _t("Window Melody", "melody", 4, "Vibraphone", 56, 66, 35, 40, 40, "auto", octave=0, mute_intro=True),
        _t("Rain Noise", "texture", 5, "FX 1 (rain)", 34, 92, 28, 50, 44, "spark", octave=0),
    ]
    presets[p.preset_name] = p

    p = _base("Orchestral Trailer Sketch")
    p.description = "Cinematic sketch preset with strings, brass, low bass and heavy-but-simple percussion."
    p.bpm = 92; p.bars = 80; p.key = "D"; p.mode = "minor"; p.progression = "i,VI,III,VII"; p.complexity = 58; p.variation = 50; p.swing = 0
    p.tracks = [
        _t("War Drums", "drum", 9, 0, 100, 64, 66, 58, 88, "four", fill_every=8),
        _t("Low Strings", "bass", 1, "Cello", 92, 46, 58, 46, 86, "eighth", octave=-1),
        _t("String Ostinato", "arpeggio", 2, "String Ensemble 1", 82, 72, 78, 64, 82, "updown"),
        _t("Brass Chords", "chord", 3, "Brass Section", 88, 40, 56, 50, 74, "stab"),
        _t("Choir Pad", "pad", 4, "Choir Aahs", 62, 82, 35, 28, 86, "long"),
    ]
    presets[p.preset_name] = p


    # AlgoMusic legacy-inspired presets. The Aminet listing describes AlgoMusic 2.4
    # as Thomas Schürger's Amiga/m68k program that creates random songs through a
    # series of algorithms in a Techno/House manner. These presets are new Python
    # implementations of that historical idea, not copied Amiga code.
    p = _base("AlgoMusic Legacy Techno House")
    p.description = "Amiga/AlgoMusic-inspired Techno-House generator: tracker-like pulse, tracker-style algorithmic activity, gated stabs and simple deterministic randomness. Newly written Python logic; no Amiga binary/code is bundled."
    p.bpm = 132; p.bars = 144; p.key = "A"; p.mode = "minor"; p.progression = "i,VII,VI,VII,i,iv,V,i"; p.harmonic_rhythm = 1; p.section_count = 12
    p.complexity = 72; p.variation = 78; p.swing = 2; p.humanize_ticks = 2; p.humanize_velocity = 10; p.motif_memory = 46; p.accent_strength = 62
    p.melody_template = "AlgoMusic tracker pulse"; p.groove_template = "algomusic legacy"; p.ui_theme = "Amiga MUI"; p.normalize_velocity = True; p.normalize_target = 84; p.render_wav = True; p.render_mp3 = True
    p.tracks = [
        _t("Classic Kick Snare", "drum", 9, 0, 104, 64, 86, 78, 98, "amiga four", fill_every=8),
        _t("Tracker Hats", "drum", 9, 0, 76, 64, 88, 64, 92, "tracker hats", fill_every=0),
        _t("Algorithmic Bass", "bass", 1, "Synth Bass 1", 98, 46, 88, 76, 92, "acid pulse", octave=-1),
        _t("Legacy Gate Chords", "chord", 2, "Electric Piano 2", 82, 34, 74, 66, 82, "random gate"),
        _t("Tracker Arp", "arpeggio", 3, "Lead 8 (bass + lead)", 74, 82, 92, 74, 78, "tracker arp", octave=0),
        _t("Algo Hook", "melody", 4, "Lead 1 (square)", 88, 62, 68, 76, 70, "template", mute_intro=True),
        _t("Amiga Pad", "pad", 5, "Pad 3 (polysynth)", 58, 88, 40, 34, 74, "long"),
    ]
    presets[p.preset_name] = p

    p = _base("AlgoMusic 040 Acid Jam")
    p.description = "Faster 68040-era acid/techno sketch inspired by AlgoMusic's random Techno/House premise: short gated bass cells, bright tracker arp and sparse robotic counters."
    p.bpm = 148; p.bars = 128; p.key = "C"; p.mode = "phrygian"; p.progression = "i,II,VII,i,VI,VII,i,V"; p.harmonic_rhythm = 1; p.section_count = 16
    p.complexity = 82; p.variation = 86; p.swing = 1; p.humanize_ticks = 1; p.humanize_velocity = 8; p.motif_memory = 38; p.accent_strength = 70
    p.melody_template = "AlgoMusic random walk"; p.groove_template = "algomusic acid"; p.ui_theme = "MagicWB"; p.normalize_velocity = True; p.normalize_target = 86; p.render_wav = True; p.render_mp3 = True
    p.tracks = [
        _t("040 Machine Kit", "drum", 9, 0, 110, 64, 94, 88, 100, "amiga four", fill_every=4),
        _t("Acid Cell Bass", "bass", 1, "Synth Bass 2", 106, 44, 95, 90, 98, "acid pulse", octave=-1),
        _t("Random Gate Organ", "chord", 2, "Drawbar Organ", 78, 36, 70, 74, 76, "random gate"),
        _t("040 Tracker Arp", "arpeggio", 3, "Clavinet", 82, 84, 96, 88, 88, "tracker arp", octave=0),
        _t("Robot Answer", "counter", 4, "Lead 2 (sawtooth)", 66, 74, 50, 64, 54, "answer"),
        _t("Low CPU Pad", "pad", 5, "Pad 2 (warm)", 48, 92, 30, 30, 62, "long"),
    ]
    presets[p.preset_name] = p

    p = _base("AlgoMusic Ambient House")
    p.description = "Softer Amiga/AlgoMusic-flavored ambient-house preset: random-gated e-piano, low tracker bass, sparse melody and wider pads."
    p.bpm = 116; p.bars = 128; p.key = "D"; p.mode = "dorian"; p.progression = "i,IV,VII,III,i,VI,IV,V"; p.harmonic_rhythm = 2; p.section_count = 10
    p.complexity = 50; p.variation = 68; p.swing = 8; p.humanize_ticks = 5; p.humanize_velocity = 12; p.motif_memory = 58; p.accent_strength = 42
    p.melody_template = "AlgoMusic house chord riff"; p.groove_template = "algomusic mellow"; p.ui_theme = "Amiga MUI"; p.normalize_velocity = True; p.normalize_target = 78; p.render_wav = True; p.render_mp3 = True
    p.tracks = [
        _t("Mellow 4/4 Kit", "drum", 9, 0, 84, 64, 70, 58, 78, "soft four", fill_every=16),
        _t("Warm Tracker Bass", "bass", 1, "Fretless Bass", 76, 46, 62, 48, 76, "acid pulse", octave=-1),
        _t("Ambient Electric Gate", "chord", 2, "Electric Piano 1", 78, 38, 62, 52, 82, "random gate"),
        _t("Soft Tracker Arp", "arpeggio", 3, "Vibraphone", 56, 84, 54, 46, 52, "tracker arp", octave=0),
        _t("Guide Melody", "melody", 4, "Flute", 66, 64, 40, 44, 44, "template", mute_intro=True),
        _t("Ambient Pad Layer", "pad", 5, "Pad 1 (new age)", 62, 88, 38, 28, 92, "long"),
    ]
    presets[p.preset_name] = p


    p = _base("AlgoMusic Techno Pattern Rows")
    p.description = "Screenshot-informed AlgoMusic-style Techno preset: separate digit/dash melody rows and symbol-based drum rows are selected per bar and recombined into a full song. Newly written Python logic based on the visual pattern concept, not copied Amiga code."
    p.bpm = 138; p.bars = 160; p.key = "A"; p.mode = "minor"; p.progression = "i,VII,VI,VII,i,VII,iv,V"; p.harmonic_rhythm = 1; p.section_count = 16
    p.complexity = 76; p.variation = 82; p.swing = 1; p.humanize_ticks = 1; p.humanize_velocity = 8; p.motif_memory = 52; p.accent_strength = 66
    p.melody_template = "AlgoMusic digit progression"; p.groove_template = "algomusic techno rows"; p.ui_theme = "MagicWB"; p.normalize_velocity = True; p.normalize_target = 85; p.render_wav = True; p.render_mp3 = True
    p.tracks = [
        _t("Symbol Row Drums", "drum", 9, 0, 108, 64, 96, 88, 100, "algomusic drums", fill_every=4),
        _t("Tracker Row Hats", "drum", 9, 0, 72, 64, 92, 70, 96, "tracker hats", fill_every=0),
        _t("Row Bass", "bass", 1, "Synth Bass 2", 102, 46, 90, 84, 96, "acid pulse", octave=-1),
        _t("Digit Gate Chords", "chord", 2, "Electric Piano 2", 78, 34, 78, 72, 88, "random gate"),
        _t("Digit Row Lead", "melody", 3, "Lead 1 (square)", 92, 62, 88, 82, 90, "digit progression", mute_intro=True),
        _t("Row Tracker Arp", "arpeggio", 4, "Clavinet", 78, 82, 94, 82, 86, "tracker arp", octave=0),
        _t("Machine Pad", "pad", 5, "Pad 3 (polysynth)", 52, 88, 35, 30, 70, "long"),
    ]
    presets[p.preset_name] = p

    return presets


PRESETS = make_presets()


def get_preset(name: str) -> GeneratorSettings:
    settings = PRESETS.get(name) or next(iter(PRESETS.values()))
    return GeneratorSettings.from_dict(deepcopy(settings.to_dict()))


def preset_names() -> List[str]:
    return list(PRESETS.keys())


def xml_reference_files(base_dir: str | Path) -> List[Path]:
    root = Path(base_dir) / "resources" / "original_soundhelix_examples"
    return sorted(root.glob("*.xml"))
