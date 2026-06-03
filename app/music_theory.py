# PythonSoundHelix - GPLv3 Python/PyQt6 reimplementation inspired by SoundHelix.
# Original source basis: SoundHelix SVN archive soundhelix-code-r896-trunk, version 0.10u.
# Original project: https://www.soundhelix.com/
# This file is part of PythonSoundHelix and is released under GPLv3.

from __future__ import annotations

import math
import re
from typing import List, Sequence, Tuple

NOTE_TO_PC = {
    "C": 0, "C#": 1, "DB": 1, "D": 2, "D#": 3, "EB": 3, "E": 4,
    "F": 5, "F#": 6, "GB": 6, "G": 7, "G#": 8, "AB": 8, "A": 9,
    "A#": 10, "BB": 10, "B": 11, "CB": 11, "E#": 5, "FB": 4, "B#": 0,
}
PC_TO_NOTE = ["C", "C#", "D", "Eb", "E", "F", "F#", "G", "Ab", "A", "Bb", "B"]
MAJOR_SCALE = [0, 2, 4, 5, 7, 9, 11]
MINOR_SCALE = [0, 2, 3, 5, 7, 8, 10]
DORIAN_SCALE = [0, 2, 3, 5, 7, 9, 10]
MIXOLYDIAN_SCALE = [0, 2, 4, 5, 7, 9, 10]
PHRYGIAN_SCALE = [0, 1, 3, 5, 7, 8, 10]
LYDIAN_SCALE = [0, 2, 4, 6, 7, 9, 11]
PENTATONIC_MAJOR = [0, 2, 4, 7, 9]
PENTATONIC_MINOR = [0, 3, 5, 7, 10]
BLUES_MINOR = [0, 3, 5, 6, 7, 10]

ROMAN_DEGREES = {
    "I": 0, "II": 1, "III": 2, "IV": 3, "V": 4, "VI": 5, "VII": 6,
}

GM_PROGRAMS = {
    "Acoustic Grand Piano": 0,
    "Bright Acoustic Piano": 1,
    "Electric Grand Piano": 2,
    "Honky-tonk Piano": 3,
    "Electric Piano 1": 4,
    "Electric Piano 2": 5,
    "Harpsichord": 6,
    "Clavinet": 7,
    "Celesta": 8,
    "Music Box": 10,
    "Vibraphone": 11,
    "Marimba": 12,
    "Drawbar Organ": 16,
    "Reed Organ": 20,
    "Accordion": 21,
    "Acoustic Guitar (nylon)": 24,
    "Acoustic Guitar (steel)": 25,
    "Electric Guitar (jazz)": 26,
    "Electric Guitar (clean)": 27,
    "Electric Guitar (muted)": 28,
    "Overdriven Guitar": 29,
    "Distortion Guitar": 30,
    "Acoustic Bass": 32,
    "Electric Bass (finger)": 33,
    "Electric Bass (pick)": 34,
    "Fretless Bass": 35,
    "Synth Bass 1": 38,
    "Synth Bass 2": 39,
    "Violin": 40,
    "Viola": 41,
    "Cello": 42,
    "String Ensemble 1": 48,
    "String Ensemble 2": 49,
    "SynthStrings 1": 50,
    "Choir Aahs": 52,
    "Voice Oohs": 53,
    "Orchestra Hit": 55,
    "Trumpet": 56,
    "Trombone": 57,
    "French Horn": 60,
    "Brass Section": 61,
    "SynthBrass 1": 62,
    "Soprano Sax": 64,
    "Alto Sax": 65,
    "Tenor Sax": 66,
    "Oboe": 68,
    "Clarinet": 71,
    "Flute": 73,
    "Pan Flute": 75,
    "Lead 1 (square)": 80,
    "Lead 2 (sawtooth)": 81,
    "Lead 3 (calliope)": 82,
    "Lead 8 (bass + lead)": 87,
    "Pad 1 (new age)": 88,
    "Pad 2 (warm)": 89,
    "Pad 3 (polysynth)": 90,
    "Pad 4 (choir)": 91,
    "Pad 7 (halo)": 94,
    "FX 1 (rain)": 96,
    "FX 3 (crystal)": 98,
    "Sitar": 104,
    "Banjo": 105,
    "Kalimba": 108,
    "Tinkle Bell": 112,
    "Reverse Cymbal": 119,
    "Guitar Fret Noise": 120,
    "Breath Noise": 121,
    "Seashore": 122,
}

DRUM_NOTES = {
    "kick": 36,
    "snare": 38,
    "rim": 37,
    "clap": 39,
    "closed_hat": 42,
    "open_hat": 46,
    "low_tom": 45,
    "mid_tom": 47,
    "high_tom": 50,
    "crash": 49,
    "ride": 51,
}


def clamp(value: int | float, lo: int, hi: int) -> int:
    return max(lo, min(hi, int(round(value))))


def key_to_pc(key: str) -> int:
    return NOTE_TO_PC.get((key or "C").strip().upper(), 0)


def scale_for_mode(mode: str) -> List[int]:
    m = (mode or "major").lower().strip()
    if m in ("minor", "aeolian"):
        return MINOR_SCALE[:]
    if m == "dorian":
        return DORIAN_SCALE[:]
    if m == "mixolydian":
        return MIXOLYDIAN_SCALE[:]
    if m == "phrygian":
        return PHRYGIAN_SCALE[:]
    if m == "lydian":
        return LYDIAN_SCALE[:]
    if m in ("pentatonic major", "major pentatonic"):
        return PENTATONIC_MAJOR[:]
    if m in ("pentatonic minor", "minor pentatonic"):
        return PENTATONIC_MINOR[:]
    if m in ("blues", "minor blues", "blues minor"):
        return BLUES_MINOR[:]
    return MAJOR_SCALE[:]


def midi_note_name(pitch: int) -> str:
    return f"{PC_TO_NOTE[pitch % 12]}{pitch // 12 - 1}"


def parse_progression(text: str) -> List[str]:
    cleaned = (text or "I,V,vi,IV").replace("|", ",").replace(";", ",")
    parts = [p.strip() for p in cleaned.split(",") if p.strip()]
    return parts or ["I", "V", "vi", "IV"]


def parse_progression_units(text: str, default_units: int = 1, max_units_per_token: int = 8) -> List[Tuple[str, int]]:
    """Parse roman or absolute chord progression tokens.

    SoundHelix' Popcorn XML uses a chord pattern such as "Am/10,G/2". We keep
    that expressive input form, but translate durations into bar-like units for
    the Python generator. Plain tokens use default_units.
    """
    units: List[Tuple[str, int]] = []
    for raw in parse_progression(text):
        symbol = raw
        length = default_units
        if "/" in raw:
            symbol, length_text = raw.rsplit("/", 1)
            try:
                # SoundHelix patterns often use tick/sub-beat-ish durations. For a GUI
                # generator, map four duration units roughly to one bar.
                length = max(1, min(max_units_per_token, int(round(float(length_text) / 4.0))))
            except ValueError:
                length = default_units
        symbol = symbol.strip().lstrip("+") or "I"
        units.append((symbol, max(1, length)))
    return units or [("I", 1)]


def _roman_root_degree(symbol: str) -> int:
    s = symbol.strip()
    roman = ""
    for ch in s:
        if ch.upper() in "IVX":
            roman += ch.upper()
        else:
            break
    roman = roman.replace("IIII", "IV")
    return ROMAN_DEGREES.get(roman, 0)


def _looks_like_roman(symbol: str) -> bool:
    s = symbol.strip().lstrip("+")
    return bool(re.match(r"^[ivIV]+", s)) and not re.match(r"^[A-Ga-g]", s)


def _absolute_root(symbol: str) -> Tuple[int | None, str]:
    s = symbol.strip().lstrip("+")
    m = re.match(r"^([A-Ga-g])([#bB]?)(.*)$", s)
    if not m:
        return None, s
    root = (m.group(1).upper() + m.group(2).upper()).strip()
    return NOTE_TO_PC.get(root), m.group(3) or ""


def chord_for_roman(symbol: str, key_pc: int, mode: str) -> Tuple[int, List[int], str]:
    """Return chord root pc, relative triad/seventh pcs, and quality label."""
    sym = symbol.strip() or "I"
    scale = scale_for_mode(mode)
    if len(scale) < 7:
        scale = MAJOR_SCALE if (mode or "major").lower().startswith("major") else MINOR_SCALE
    degree = _roman_root_degree(sym)
    root_pc = (key_pc + scale[degree]) % 12
    lower = sym.lower()
    explicit_dim = "dim" in lower or "°" in lower
    explicit_aug = "aug" in lower or "+" in sym[1:]
    is_minor = sym[:1].islower() or "m" in sym[1:3]
    if explicit_dim:
        intervals = [0, 3, 6]
        quality = "dim"
    elif explicit_aug:
        intervals = [0, 4, 8]
        quality = "aug"
    elif is_minor:
        intervals = [0, 3, 7]
        quality = "m"
    else:
        intervals = [0, 4, 7]
        quality = ""
    if "7" in sym:
        intervals.append(11 if "maj7" in lower else 10)
        quality += "7"
    return root_pc, intervals, quality


def chord_for_symbol(symbol: str, key_pc: int, mode: str) -> Tuple[int, List[int], str]:
    sym = (symbol or "I").strip().lstrip("+")
    if _looks_like_roman(sym):
        return chord_for_roman(sym, key_pc, mode)
    root_pc, rest = _absolute_root(sym)
    if root_pc is None:
        return chord_for_roman(sym, key_pc, mode)
    lower = rest.lower()
    if "dim" in lower or "°" in lower:
        intervals = [0, 3, 6]
        quality = "dim"
    elif "aug" in lower or "+" in rest:
        intervals = [0, 4, 8]
        quality = "aug"
    elif lower.startswith("m") and not lower.startswith("maj"):
        intervals = [0, 3, 7]
        quality = "m"
    else:
        intervals = [0, 4, 7]
        quality = ""
    if "7" in lower:
        intervals.append(11 if "maj7" in lower else 10)
        quality += "7"
    return root_pc, intervals, quality


def chord_symbol_name(symbol: str, key_pc: int, mode: str) -> str:
    root, _, quality = chord_for_symbol(symbol, key_pc, mode)
    return f"{PC_TO_NOTE[root]}{quality} ({symbol})"


def notes_for_chord(symbol: str, key_pc: int, mode: str, octave: int = 4) -> List[int]:
    root, intervals, _ = chord_for_symbol(symbol, key_pc, mode)
    base = 12 * (octave + 1) + root
    return [base + i for i in intervals]


def voice_lead(chord_notes: Sequence[int], previous: Sequence[int] | None, low: int = 48, high: int = 76) -> List[int]:
    """Pick inversions with small movement, similar in spirit to SoundHelix' minimizeChordDistance."""
    candidates: List[List[int]] = []
    pcs = [n % 12 for n in chord_notes]
    for octave in range(1, 7):
        base = [12 * (octave + 1) + pc for pc in pcs]
        for inv in range(len(base)):
            inv_notes = base[inv:] + [n + 12 for n in base[:inv]]
            if min(inv_notes) >= low and max(inv_notes) <= high:
                candidates.append(sorted(inv_notes))
    if not candidates:
        return sorted([clamp(n, low, high) for n in chord_notes])
    if not previous:
        middle = (low + high) / 2
        return min(candidates, key=lambda c: abs(sum(c) / len(c) - middle))
    return min(candidates, key=lambda c: sum(abs(c[i % len(c)] - previous[i % len(previous)]) for i in range(max(len(c), len(previous)))))


def scale_pitches(key_pc: int, mode: str, low: int, high: int) -> List[int]:
    scale = scale_for_mode(mode)
    notes = []
    for p in range(low, high + 1):
        if (p - key_pc) % 12 in scale:
            notes.append(p)
    return notes


def nearest_scale_pitch(target: int, key_pc: int, mode: str, low: int, high: int) -> int:
    candidates = scale_pitches(key_pc, mode, low, high)
    return min(candidates, key=lambda p: (abs(p - target), p)) if candidates else clamp(target, low, high)


def degree_pitch(degree: int, key_pc: int, mode: str, octave: int = 5) -> int:
    scale = scale_for_mode(mode)
    if not scale:
        return 60
    d = int(degree)
    octave_shift, idx = divmod(d, len(scale))
    return 12 * (octave + 1 + octave_shift) + key_pc + scale[idx]


def euclidean_rhythm(pulses: int, steps: int) -> List[int]:
    """Bjorklund-like pulse distribution; good for SoundHelix-style generated patterns."""
    pulses = clamp(pulses, 0, steps)
    if steps <= 0:
        return []
    if pulses == 0:
        return [0] * steps
    if pulses == steps:
        return [1] * steps
    pattern = []
    for i in range(steps):
        pattern.append(1 if math.floor((i + 1) * pulses / steps) != math.floor(i * pulses / steps) else 0)
    return pattern


def safe_filename(name: str) -> str:
    keep = []
    for ch in name:
        if ch.isalnum() or ch in " ._-":
            keep.append(ch)
        else:
            keep.append("_")
    result = "".join(keep).strip().strip(".")
    return result or "PythonSoundHelix_Song"
