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
        _t("Answer Bell", "counter", 5, "Music Box", 64, 86, 42, 45, 48, "answer", octave=1, mute_intro=True),
    ]
    presets[p.preset_name] = p

    p = _base("Original XML Popcorn Expansion")
    p.description = "Uses the bundled SoundHelix-Popcorn XML chord idea as a springboard, then expands it with extra Python tracks and GUI controls."
    p.bpm = 136; p.bars = 128; p.key = "A"; p.mode = "minor"; p.progression = "Am/10,G/2,F/2,Am/12,G/2,F/2,Am/2,+C/8,Em/2,D/2,C/12,Em/2,D/2,C/4"; p.harmonic_rhythm = 1
    p.complexity = 72; p.variation = 66; p.swing = 4; p.melody_template = "Popcorn-style original pulse"
    p.tracks = [
        _t("Popcorn Drums Plus", "drum", 9, 0, 104, 64, 88, 82, 95, "electro four", fill_every=4),
        _t("Pop Bass", "bass", 1, "Synth Bass 2", 96, 48, 84, 60, 92, "sync eighth", octave=-1),
        _t("Pluck Hook", "melody", 2, "Lead 1 (square)", 105, 62, 96, 86, 100, "template"),
        _t("Glass Arp", "arpeggio", 3, "Celesta", 82, 80, 90, 72, 88, "updown", octave=1),
        _t("Offbeat Organ", "chord", 4, "Drawbar Organ", 72, 36, 68, 50, 76, "stab"),
        _t("Space Pad", "pad", 5, "Pad 7 (halo)", 62, 94, 45, 38, 88, "long"),
        _t("Noise Spark", "texture", 6, "FX 3 (crystal)", 54, 72, 38, 70, 46, "spark", octave=1),
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
        _t("Bell Answer", "counter", 5, "Vibraphone", 58, 92, 34, 44, 45, "answer", octave=1),
    ]
    presets[p.preset_name] = p

    p = _base("Public Domain Elise Synth")
    p.description = "Minor-key synth piece using a short public-domain Für-Elise-style interval contour as a seed, not a fixed cover."
    p.bpm = 132; p.bars = 112; p.key = "A"; p.mode = "minor"; p.progression = "i,VII,VI,V,i,iv,V,i"; p.complexity = 68; p.variation = 62; p.swing = 3; p.melody_template = "Fuer-Elise public-domain hint"
    p.tracks = [
        _t("Broken Beat", "drum", 9, 0, 92, 64, 74, 78, 86, "broken electro", fill_every=8),
        _t("Left Hand Bass", "bass", 1, "Synth Bass 1", 90, 42, 72, 58, 88, "sync eighth", octave=-1),
        _t("Elise Pluck", "melody", 2, "Clavinet", 94, 68, 86, 78, 92, "template"),
        _t("Dark Arp", "arpeggio", 3, "Harpsichord", 82, 82, 88, 72, 84, "down", octave=1),
        _t("Minor Pad", "pad", 4, "Pad 3 (polysynth)", 66, 78, 48, 36, 90, "long"),
    ]
    presets[p.preset_name] = p

    p = _base("Public Domain Canon Dream")
    p.description = "Pachelbel-Canon-inspired public-domain chord movement with modern arps and pads."
    p.bpm = 110; p.bars = 128; p.key = "D"; p.mode = "major"; p.progression = "I,V,vi,iii,IV,I,IV,V"; p.complexity = 55; p.variation = 48; p.swing = 6; p.melody_template = "Canon public-domain hint"
    p.tracks = [
        _t("Soft Drum", "drum", 9, 0, 78, 64, 54, 42, 70, "soft four", fill_every=16),
        _t("Canon Bass", "bass", 1, "Fretless Bass", 84, 50, 66, 48, 82, "eighth", octave=-1),
        _t("Glass Canon", "arpeggio", 2, "Music Box", 78, 86, 84, 64, 86, "updown", octave=1),
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
        _t("Piano Melody", "melody", 2, "Electric Grand Piano", 82, 64, 55, 48, 64, "auto", octave=1, mute_intro=True),
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
        _t("Coin Arp", "arpeggio", 3, "Tinkle Bell", 78, 84, 84, 76, 82, "updown", octave=1),
        _t("Chip Chords", "chord", 4, "Lead 8 (bass + lead)", 72, 34, 70, 55, 74, "stab"),
        _t("Pixel Dust", "texture", 5, "FX 3 (crystal)", 50, 90, 36, 65, 42, "spark", octave=1),
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
