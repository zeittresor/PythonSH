from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, List, Sequence, Tuple

NOTE_TO_PC = {
    "C": 0, "C#": 1, "DB": 1, "D": 2, "D#": 3, "EB": 3, "E": 4,
    "F": 5, "F#": 6, "GB": 6, "G": 7, "G#": 8, "AB": 8,
    "A": 9, "A#": 10, "BB": 10, "B": 11,
}
PC_TO_NAME_SHARP = ["C", "C#", "D", "D#", "E", "F", "F#", "G", "G#", "A", "A#", "B"]

MAJOR_SCALE = [0, 2, 4, 5, 7, 9, 11]
NAT_MINOR_SCALE = [0, 2, 3, 5, 7, 8, 10]
HARM_MINOR_SCALE = [0, 2, 3, 5, 7, 8, 11]

DRUM_NOTES = {"kick": 36, "snare": 38, "closed_hat": 42, "open_hat": 46, "clap": 39, "ride": 51, "tom": 45}


def clamp(value, low, high):
    return max(low, min(high, value))


def key_pc(key: str) -> int:
    key = (key or "C").strip().upper().replace("♯", "#").replace("♭", "B")
    return NOTE_TO_PC.get(key, 0)


def mode_scale(mode: str) -> List[int]:
    return NAT_MINOR_SCALE if (mode or "major").lower().startswith("min") else MAJOR_SCALE


def scale_pcs(key: str, mode: str, harmonic_minor: bool = False) -> set[int]:
    root = key_pc(key)
    scale = HARM_MINOR_SCALE if harmonic_minor and (mode or "").lower().startswith("min") else mode_scale(mode)
    return {(root + s) % 12 for s in scale}


def note_name(midi_note: int) -> str:
    return f"{PC_TO_NAME_SHARP[midi_note % 12]}{midi_note // 12 - 1}"


def degree_to_pc(root: int, mode: str, degree: int) -> int:
    scale = mode_scale(mode)
    return (root + scale[degree % len(scale)]) % 12


def diatonic_note_in_range(key: str, mode: str, degree: int, low: int, high: int) -> int:
    pc = degree_to_pc(key_pc(key), mode, degree)
    candidates = [p for p in range(low, high + 1) if p % 12 == pc]
    if not candidates:
        return clamp(low, 0, 127)
    mid = (low + high) // 2
    return min(candidates, key=lambda p: abs(p - mid))


def _roman_intervals(mode: str) -> Dict[str, Tuple[int, str]]:
    # return scale degree index and triad quality for functional chords.
    if (mode or "").lower().startswith("min"):
        return {
            "i": (0, "min"), "ii°": (1, "dim"), "bIII": (2, "maj"), "III": (2, "maj"),
            "iv": (3, "min"), "V": (4, "maj"), "v": (4, "min"), "VI": (5, "maj"),
            "VII": (6, "maj"), "bVII": (6, "maj"),
        }
    return {
        "I": (0, "maj"), "ii": (1, "min"), "iii": (2, "min"), "IV": (3, "maj"),
        "V": (4, "maj"), "vi": (5, "min"), "vii°": (6, "dim"),
    }


def chord_from_symbol(symbol: str, key: str, mode: str, octave: int = 4) -> Tuple[int, List[int]]:
    sym = (symbol or "I").strip()
    root_pc = key_pc(key)
    # absolute symbols, e.g. C#m, F#, Bb
    base = sym.replace("♯", "#").replace("♭", "b")
    quality = None
    abs_name = None
    if base[:2].upper() in NOTE_TO_PC:
        abs_name = base[:2].upper()
        suffix = base[2:]
    elif base[:1].upper() in NOTE_TO_PC:
        abs_name = base[:1].upper()
        suffix = base[1:]
    else:
        suffix = ""
    if abs_name:
        root = NOTE_TO_PC[abs_name]
        quality = "min" if suffix.lower().startswith("m") and not suffix.lower().startswith("maj") else "maj"
    else:
        table = _roman_intervals(mode)
        if sym not in table:
            # tolerate upper/lower by mode
            sym2 = sym.lower() if (mode or "").lower().startswith("min") else sym
            sym2 = {"bvi": "VI", "biii": "III", "bvii": "VII"}.get(sym2, sym2)
            if sym2 not in table:
                sym2 = "i" if (mode or "").lower().startswith("min") else "I"
            degree, quality = table[sym2]
        else:
            degree, quality = table[sym]
        scale = HARM_MINOR_SCALE if (mode or "").lower().startswith("min") and sym in ("V", "vii°") else mode_scale(mode)
        root = (root_pc + scale[degree]) % 12
    intervals = {"maj": [0, 4, 7], "min": [0, 3, 7], "dim": [0, 3, 6]}[quality or "maj"]
    base_note = 12 * (octave + 1) + root
    return root, [base_note + i for i in intervals]


def chord_tones_in_range(symbol: str, key: str, mode: str, low: int, high: int) -> List[int]:
    root, chord = chord_from_symbol(symbol, key, mode, 3)
    pcs = {p % 12 for p in chord}
    out = [p for p in range(low, high + 1) if p % 12 in pcs]
    return out or [diatonic_note_in_range(key, mode, 0, low, high)]


def scale_tones_in_range(key: str, mode: str, low: int, high: int, harmonic_minor: bool = False) -> List[int]:
    pcs = scale_pcs(key, mode, harmonic_minor)
    return [p for p in range(low, high + 1) if p % 12 in pcs]


def nearest_allowed_pitch(pitch: int, allowed_pcs: set[int], low: int, high: int) -> int:
    pitch = clamp(pitch, low, high)
    if pitch % 12 in allowed_pcs:
        return pitch
    candidates = [p for p in range(low, high + 1) if p % 12 in allowed_pcs]
    if not candidates:
        return pitch
    return min(candidates, key=lambda p: (abs(p - pitch), p))


def safe_filename(name: str) -> str:
    bad = '<>:"/\\|?*\n\r\t'
    s = ''.join('_' if c in bad else c for c in name).strip().strip('.')
    return s[:120] or "song"


def voice_lead(prev: Sequence[int] | None, chord: Sequence[int], low: int = 48, high: int = 72) -> List[int]:
    pcs = [n % 12 for n in chord]
    voices: List[int] = []
    anchors = prev if prev and len(prev) >= 3 else [low + 4, low + 9, low + 16]
    used = set()
    for i, pc in enumerate(pcs[:3]):
        candidates = [p for p in range(low, high + 1) if p % 12 == pc and p not in used]
        if not candidates:
            candidates = [p for p in range(low, high + 1) if p % 12 == pc]
        target = anchors[min(i, len(anchors) - 1)]
        p = min(candidates, key=lambda x: abs(x - target))
        voices.append(p); used.add(p)
    return sorted(voices)
