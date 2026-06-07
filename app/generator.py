from __future__ import annotations

import json
import math
import os
import random
import time
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Dict, List, Sequence, Tuple

from .midi_writer import MidiTrack, write_midi
from .music_theory import (
    DRUM_NOTES, chord_from_symbol, chord_tones_in_range, clamp, key_pc, mode_scale,
    nearest_allowed_pitch, note_name, safe_filename, scale_pcs, scale_tones_in_range, voice_lead,
)

APP_VERSION = "0.6.5"
ENGINE_NAME = "quality-locked auto-arranger v0.6.5"

PRESET_NAMES = [
    "Auto Composer", "Toccata Drive", "Structured Pop", "Night Piano", "Minor House", "Calm Ambient", "DNB Coherent", "Canon Dream", "Elise Inspired"
]
PROGRESSION_NAMES = [
    "Auto mode-safe",
    "Minor classic: i-V-i-iv",
    "Minor lift: i-VII-VI-V",
    "Minor cadence: i-iv-V-i",
    "Major classic: I-V-vi-IV",
    "Major cadence: I-IV-V-I",
    "Major canon: I-V-vi-iii-IV-I-IV-V",
]
MELODY_TEMPLATES = [
    "auto", "SoundHelix piano contour", "Toccata contour", "Elise inspired contour", "Canon contour", "Row Boat contour"
]


@dataclass
class TrackSettings:
    name: str
    role: str
    enabled: bool = True
    channel: int = 0
    program: int = 0
    volume: int = 80
    pan: int = 64
    octave: int = 0
    transpose: int = 0
    fine_tune_cents: int = 0


@dataclass
class GeneratorSettings:
    preset_name: str = "Auto Composer"
    title: str = ""
    seed: int = 1192594075
    randomize_seed: bool = True
    bpm: int = 142
    bars: int = 96
    beats_per_bar: int = 4
    ticks_per_beat: int = 480
    key: str = "Auto"
    mode: str = "auto"
    progression: str = "Auto mode-safe"
    custom_progression: str = ""
    harmonic_rhythm: int = 1
    section_count: int = 5
    melody_template: str = "auto"
    melody_coverage: int = 50
    complexity: int = 78
    variation: int = 72
    seed_variation_strength: int = 70
    swing: int = 2
    motif_memory: int = 70
    accent_strength: int = 52
    humanize_ticks: int = 4
    humanize_velocity: int = 6
    lfo_expression: bool = True
    call_response: bool = True
    keep_bass_on_roots: bool = True
    add_markers: bool = True
    export_json: bool = True
    export_chord_sheet: bool = True
    use_rating_memory: bool = True
    allow_dissonance: bool = False
    tracks: List[TrackSettings] = field(default_factory=lambda: [
        TrackSettings("Tight Drums", "drum", True, 9, 0, 70, 64, 0),
        TrackSettings("Tonal Bass", "bass", True, 1, 38, 72, 48, -1),
        TrackSettings("Lead Melody", "melody", True, 2, 0, 72, 64, 0),
        TrackSettings("Chord Pulse", "chord", True, 3, 4, 62, 36, 0),
        TrackSettings("Soft Pad", "pad", True, 4, 89, 46, 82, 0),
    ])

    def to_dict(self):
        d = asdict(self)
        return d

    @classmethod
    def from_dict(cls, data: dict):
        fields = {k for k in cls.__dataclass_fields__}
        kwargs = {k: v for k, v in data.items() if k in fields and k != "tracks"}
        tracks = data.get("tracks") or []
        if tracks:
            allowed = set(TrackSettings.__dataclass_fields__.keys())
            kwargs["tracks"] = [TrackSettings(**{k: v for k, v in t.items() if k in allowed}) for t in tracks]
        else:
            kwargs["tracks"] = cls().tracks
        return cls(**kwargs)


@dataclass
class Section:
    name: str
    start_bar: int
    bars: int
    energy: int
    phrase: str


@dataclass
class Chord:
    bar: int
    tick: int
    symbol: str
    root: int
    notes: List[int]
    section: str


@dataclass
class SongResult:
    title: str
    seed: int
    midi_path: str
    json_path: str
    chord_sheet_path: str
    note_count: int
    render_log: str = ""


TITLE_A = ["Contemporary", "Crystalline", "Coherent", "Midnight", "Electric", "Circular", "Motorized", "Structured", "Silver", "Careful"]
TITLE_B = ["Drive", "Machine", "Pulse", "Garden", "Signal", "Orbit", "Window", "Engine", "Arc", "Motion"]


def output_stem_for(title: str, seed: int) -> str:
    base = safe_filename(title).strip("._- ") or "PythonSoundHelix_Song"
    return f"{base}_seed{int(seed)}"


def unique_output_paths(output_dir: Path, title: str, seed: int):
    stem = output_stem_for(title, seed)
    idx = 1
    while True:
        suffix = "" if idx == 1 else f"_{idx:02d}"
        midi = output_dir / f"{stem}{suffix}.mid"
        js = output_dir / f"{stem}{suffix}.json"
        chords = output_dir / f"{stem}{suffix}_chords.txt"
        if not midi.exists() and not js.exists() and not chords.exists():
            return stem + suffix, midi, js, chords
        idx += 1


def generate_title(seed: int, preset: str = "") -> str:
    preset_hash = sum(ord(c) for c in (preset or ""))
    r = random.Random(seed ^ 0xA1171E ^ (preset_hash << 7))
    return f"{r.choice(TITLE_A)} and {r.choice(TITLE_B)}"




def _style_hint(settings: GeneratorSettings) -> str:
    name = (settings.preset_name or "Auto Composer").lower()
    if name == "auto composer":
        r = random.Random(settings.seed ^ 0xA07C0DE)
        return r.choice(["piano", "toccata", "pop", "house", "dnb", "ambient", "canon", "elise"])
    if "dnb" in name or "drum" in name:
        return "dnb"
    if "house" in name:
        return "house"
    if "ambient" in name or "calm" in name:
        return "ambient"
    if "piano" in name:
        return "piano"
    if "canon" in name:
        return "canon"
    if "elise" in name:
        return "elise"
    if "toccata" in name or "drive" in name:
        return "toccata"
    return "pop"


def _auto_phrase_plan(settings: GeneratorSettings) -> Dict[str, List[str]]:
    r = random.Random(settings.seed ^ 0xA640)
    style = _style_hint(settings)
    minor = settings.mode == "minor"
    minor_plans = [
        {"A":["i","VI","iv","V","i","VII","VI","V"], "B":["VI","III","VII","iv","VI","III","iv","V"], "HOOK":["i","VII","VI","V","i","iv","V","i"], "OUT":["VI","iv","V","i"]},
        {"A":["i","VII","VI","VII","iv","i","V","i"], "B":["III","VII","i","VI","iv","i","V","V"], "HOOK":["i","VI","III","VII","iv","i","V","i"], "OUT":["iv","V","i","i"]},
        {"A":["i","iv","VII","III","VI","iv","V","i"], "B":["VI","III","iv","V","i","VII","VI","V"], "HOOK":["i","V","VI","III","iv","i","V","i"], "OUT":["VI","V","i","i"]},
    ]
    major_plans = [
        {"A":["I","V","vi","IV","I","IV","V","I"], "B":["ii","V","iii","vi","IV","I","V","V"], "HOOK":["IV","V","iii","vi","IV","V","I","I"], "OUT":["IV","V","I","I"]},
        {"A":["I","vi","IV","V","ii","V","I","I"], "B":["vi","iii","IV","I","ii","V","I","V"], "HOOK":["I","V","vi","IV","IV","V","I","I"], "OUT":["IV","V","I","I"]},
        {"A":["I","IV","V","I","vi","ii","V","I"], "B":["iii","vi","ii","V","IV","I","V","V"], "HOOK":["I","V","vi","IV","ii","V","I","I"], "OUT":["IV","V","I","I"]},
    ]
    if style in ("dnb", "house", "toccata"):
        base = r.choice(minor_plans if minor else major_plans)
    elif style in ("ambient", "elise"):
        base = r.choice(minor_plans if minor else major_plans)
    else:
        base = r.choice(major_plans if not minor else minor_plans)
    # rotate A/B lightly per seed so the same preset does not always begin with the same harmonic face.
    out = {k:list(v) for k,v in base.items()}
    if r.random() < 0.55:
        rot = r.randrange(1, 4)
        out["A"] = out["A"][rot:] + out["A"][:rot]
    # Intro is a deliberate seed-specific ramp, not just the first A loop.
    out["INTRO"] = [out["A"][0], out["A"][0], out["A"][1], out["A"][2], out["A"][3]]
    return out


def arrangement_profile(settings: GeneratorSettings) -> Dict[str, object]:
    r = random.Random(settings.seed ^ 0xE17A ^ (sum(ord(c) for c in settings.preset_name or "") << 3))
    style_hint = _style_hint(settings)
    roles = ["drum", "bass", "melody", "chord", "pad"]
    # v0.6.5: choose one explicit lead role for the opening.  Earlier versions often
    # allowed pad+chord support to sneak in at bar 0, which made many songs feel as if
    # they always started with a pad.  Now only the lead role owns the first bars.
    if style_hint in ("ambient", "piano", "canon", "elise"):
        lead_pool = ["melody", "chord", "pad", "bass"]
    elif style_hint in ("dnb", "house", "toccata"):
        lead_pool = ["drum", "bass", "melody", "chord", "pad"]
    else:
        lead_pool = roles
    lead_role = lead_pool[r.randrange(len(lead_pool))]
    if r.random() < 0.18:
        lead_role = r.choice(roles)
    style = f"{lead_role}s_first" if lead_role == "drum" else f"{lead_role}_first"
    secondary = [x for x in roles if x != lead_role]
    r.shuffle(secondary)
    entry = {lead_role: 0}
    # Let the opening breathe: each next role enters a little later, but not always
    # in the same order. This is the procedural "mal so, mal so" part.
    for i, role in enumerate(secondary):
        entry[role] = [2, 4, 8, 12][i]
    intro_solo_bars = r.choice([2, 3, 4, 5])
    mult = {"drum":1.0, "bass":1.0, "melody":1.0, "chord":0.88, "pad":0.78}
    focus = r.choice(roles)
    for role in list(mult):
        if role == focus:
            mult[role] *= r.choice([1.05, 1.12, 1.18])
        elif role == lead_role:
            mult[role] *= r.choice([0.96, 1.02, 1.08])
        else:
            mult[role] *= r.choice([0.62, 0.74, 0.86, 0.94])
    return {"style": style, "lead_role": lead_role, "intro_solo_bars": intro_solo_bars, "entry": entry, "mult": mult, "focus": focus}


def role_active(settings: GeneratorSettings, sections: Sequence[Section], bar: int, role: str) -> bool:
    prof = arrangement_profile(settings)
    role = (role or "").lower()
    entry = int(prof["entry"].get(role, 0))
    if bar < entry:
        return False
    sec = section_for_bar(sections, bar)
    r = random.Random(settings.seed + bar * 97 + sum(ord(c) for c in role) * 31)
    rel = bar - sec.start_bar
    lead = str(prof.get("lead_role", "pad"))
    # In the first bars only the chosen lead role should be audible.  This prevents
    # the old behavior where pad/chord layers made every intro feel like a pad intro.
    if sec.name == "Intro" and rel < int(prof.get("intro_solo_bars", 3)):
        return role == lead
    if role == "drum" and sec.name == "Intro" and role != lead and r.random() < 0.42:
        return False
    if role == "drum" and sec.name == "Outro" and r.random() < 0.38:
        return False
    if role == "bass" and sec.name == "Intro" and role != lead and rel < max(2, sec.bars // 3):
        return False
    if role == "melody" and sec.name == "Intro" and role != lead and rel < sec.bars // 2:
        return False
    if role == "chord" and sec.name == "B" and r.random() < 0.18:
        return False
    if role == "pad" and sec.name == "Hook" and prof["focus"] in ("drum", "bass") and r.random() < 0.25:
        return False
    return True


def role_velocity(settings: GeneratorSettings, role: str, value: float) -> int:
    prof = arrangement_profile(settings)
    return int(clamp(value * float(prof["mult"].get(role, 1.0)), 1, 127))

def sanitize_mode_progression(settings: GeneratorSettings) -> None:
    p = (settings.progression or "").lower()
    c = (settings.custom_progression or "").strip()
    if c:
        tokens = c.replace(',', ' ').replace(';', ' ').split()
        has_minor = any(tok.lower() in ["i", "iv", "v", "vi", "vii", "am", "em", "bm", "c#m", "f#m", "g#m", "d#m"] for tok in tokens)
        has_major_roman = any(tok in ["I", "IV", "V"] for tok in tokens)
        if has_minor and not has_major_roman:
            settings.mode = "minor"
        elif has_major_roman and not has_minor:
            settings.mode = "major"
        return
    if p.startswith("minor"):
        settings.mode = "minor"
    elif p.startswith("major"):
        settings.mode = "major"




def resolve_auto_settings(settings: GeneratorSettings, rng: random.Random) -> None:
    keys = ["C", "D", "E", "F", "G", "A", "B", "C#", "F#", "G#"]
    style = _style_hint(settings)
    if not settings.key or settings.key.lower() == "auto":
        settings.key = rng.choice(keys)
    if not settings.mode or settings.mode.lower() == "auto":
        if style in ("dnb", "house", "toccata", "ambient", "elise"):
            settings.mode = rng.choice(["minor", "minor", "major"])
        else:
            settings.mode = rng.choice(["major", "minor", "major"])
    if not settings.progression or settings.progression.lower().startswith("auto"):
        settings.progression = "Auto resolved phrase plan"
    if not settings.melody_template or settings.melody_template.lower() == "auto":
        if style == "toccata":
            pool = ["Toccata contour", "SoundHelix piano contour", "Canon contour"]
        elif style == "piano":
            pool = ["SoundHelix piano contour", "Canon contour", "Elise inspired contour"]
        elif style == "canon":
            pool = ["Canon contour", "SoundHelix piano contour"]
        elif style == "elise":
            pool = ["Elise inspired contour", "SoundHelix piano contour"]
        elif style == "dnb":
            pool = ["Toccata contour", "SoundHelix piano contour", "Canon contour"]
        else:
            pool = ["SoundHelix piano contour", "Toccata contour", "Canon contour", "Row Boat contour"]
        settings.melody_template = rng.choice(pool)

def preset_defaults(name: str) -> GeneratorSettings:
    s = GeneratorSettings(preset_name=name)
    if name == "Auto Composer":
        return s
    if name == "Toccata Drive":
        s.bpm=142; s.bars=96; s.beats_per_bar=4; s.ticks_per_beat=480; s.complexity=78; s.variation=72; s.seed_variation_strength=70; s.swing=2; s.motif_memory=70; s.accent_strength=52; s.humanize_ticks=4; s.humanize_velocity=6; s.melody_coverage=65
    elif name == "Structured Pop":
        s.bpm=118; s.complexity=58; s.variation=52
    elif name == "Night Piano":
        s.bpm=92; s.bars=80; s.tracks[0].enabled=False
    elif name == "Minor House":
        s.bpm=126
    elif name == "Calm Ambient":
        s.bpm=82; s.bars=80; s.tracks[0].enabled=False; s.tracks[2].volume=62; s.tracks[4].volume=62
    elif name == "DNB Coherent":
        s.bpm=168; s.complexity=72
    elif name == "Canon Dream":
        s.bpm=94; s.tracks[0].enabled=False
    elif name == "Elise Inspired":
        s.bpm=96; s.beats_per_bar=3; s.bars=72; s.tracks[0].enabled=False
    # v0.6.5: preset = style hint, not fixed harmony. Core musical choices stay auto by default.
    s.key="Auto"; s.mode="auto"; s.progression="Auto mode-safe"; s.melody_template="auto"
    return s


def build_sections(settings: GeneratorSettings) -> List[Section]:
    bars = max(32, settings.bars)
    ratios = [("Intro", .16, 28, "INTRO"), ("A", .22, 62, "A"), ("B", .22, 74, "B"), ("Hook", .26, 92, "HOOK"), ("Outro", .14, 32, "OUT")]
    counts = []
    used = 0
    for i, (_, r, _, _) in enumerate(ratios):
        n = bars - used if i == len(ratios)-1 else max(4, int(round(bars*r)))
        used += n if i < len(ratios)-1 else 0
        counts.append(n)
    while sum(counts) > bars:
        counts[max(range(len(counts)), key=lambda i: counts[i])] -= 1
    while sum(counts) < bars:
        counts[-2] += 1
    out=[]; start=0
    for (name, _, energy, phrase), n in zip(ratios, counts):
        out.append(Section(name, start, n, energy, phrase)); start += n
    return out


def _base_progression(settings: GeneratorSettings) -> Dict[str, List[str]]:
    p = settings.progression
    if p.lower().startswith("auto"):
        return _auto_phrase_plan(settings)
    if settings.custom_progression.strip():
        base = [x.strip() for x in settings.custom_progression.replace(';', ',').split(',') if x.strip()]
        return {"A": base, "B": base[1:]+base[:1], "HOOK": base[2:]+base[:2], "OUT": base[-2:]+base[:1]}
    if p.startswith("Minor classic"):
        return {"A": ["i", "V", "i", "iv", "VI", "VII", "V", "i"], "B": ["VI", "VII", "i", "V", "iv", "i", "VI", "V"], "HOOK": ["i", "iv", "V", "i", "VI", "VII", "V", "i"], "OUT": ["iv", "V", "i", "i"]}
    if p.startswith("Minor lift"):
        return {"A": ["i", "VII", "VI", "V", "iv", "i", "V", "i"], "B": ["iv", "i", "VI", "V", "III", "VII", "VI", "V"], "HOOK": ["VI", "VII", "i", "V", "i", "iv", "V", "i"], "OUT": ["iv", "V", "i", "i"]}
    if p.startswith("Minor cadence"):
        return {"A": ["i", "iv", "V", "i", "VI", "iv", "V", "i"], "B": ["VI", "III", "iv", "V", "i", "VII", "VI", "V"], "HOOK": ["i", "VI", "iv", "V", "i", "iv", "V", "i"], "OUT": ["iv", "V", "i", "i"]}
    if p.startswith("Major canon"):
        return {"A": ["I", "V", "vi", "iii", "IV", "I", "IV", "V"], "B": ["vi", "iii", "IV", "I", "ii", "V", "I", "V"], "HOOK": ["I", "V", "vi", "iii", "IV", "I", "IV", "V"], "OUT": ["IV", "V", "I", "I"]}
    if p.startswith("Major cadence"):
        return {"A": ["I", "IV", "V", "I"], "B": ["ii", "V", "iii", "vi"], "HOOK": ["IV", "I", "V", "vi", "IV", "V", "I", "I"], "OUT": ["IV", "V", "I", "I"]}
    if p.startswith("Major classic"):
        return {"A": ["I", "V", "vi", "IV"], "B": ["ii", "V", "I", "vi"], "HOOK": ["IV", "V", "iii", "vi", "IV", "V", "I", "I"], "OUT": ["IV", "V", "I", "I"]}
    return _base_progression(GeneratorSettings(mode=settings.mode, progression=("Minor classic: i-V-i-iv" if settings.mode == "minor" else "Major classic: I-V-vi-IV")))


def build_chords(settings: GeneratorSettings, sections: Sequence[Section]) -> List[Chord]:
    phrases = _base_progression(settings)
    bar_ticks = settings.ticks_per_beat * settings.beats_per_bar
    chords: List[Chord] = []
    for sec in sections:
        phrase = phrases.get(sec.phrase) or phrases.get("A") or ["i" if settings.mode == "minor" else "I"]
        alt = phrases.get("B") or phrase
        for i in range(sec.bars):
            bar = sec.start_bar + i
            cycle = i // max(1, len(phrase))
            local_phrase = phrase
            if sec.phrase == "A" and cycle % 2 == 1 and len(alt) >= 4:
                local_phrase = phrase[:max(1, len(phrase)//2)] + alt[max(0, len(alt)//2):]
            elif sec.phrase == "HOOK" and cycle % 2 == 1 and len(phrase) > 4:
                local_phrase = phrase[2:] + phrase[:2]
            sym = local_phrase[i % len(local_phrase)]
            if sec.name == "Outro" and i >= sec.bars - 2:
                sym = "i" if settings.mode == "minor" else "I"
            root, notes = chord_from_symbol(sym, settings.key, settings.mode, 4)
            chords.append(Chord(bar, bar * bar_ticks, sym, root, notes, sec.name))
    return chords


def section_for_bar(sections: Sequence[Section], bar: int) -> Section:
    for s in sections:
        if s.start_bar <= bar < s.start_bar + s.bars:
            return s
    return sections[-1]


# Abstract contour cells: (beat offset, length in beats, scale degree, accent). These are not recordings.
PIANO_CONTOUR = [
    (0.0,.5,0,1),(0.5,.5,2,0),(1.0,.5,4,0),(1.5,.5,7,1),(2.0,.5,6,0),(2.5,.5,4,0),(3.0,1.0,2,1),
    (0.0,.5,1,0),(0.5,.5,3,0),(1.0,1.0,5,1),(2.0,.5,4,0),(2.5,.5,2,0),(3.0,1.0,0,1),
    (0.0,.5,4,1),(0.5,.5,5,0),(1.0,.5,7,0),(1.5,.5,8,1),(2.0,.5,7,0),(2.5,.5,5,0),(3.0,1.0,4,1),
    (0.0,.5,2,0),(0.5,.5,4,0),(1.0,1.0,3,1),(2.0,.5,2,0),(2.5,.5,1,0),(3.0,1.0,0,1),
]
TOCCATA_CONTOUR = [
    (0.0,.25,0,1),(0.25,.25,4,0),(0.5,.25,7,0),(0.75,.25,4,0),(1.0,.25,0,1),(1.25,.25,4,0),(1.5,.25,7,0),(1.75,.25,4,0),
    (2.0,.25,1,1),(2.25,.25,5,0),(2.5,.25,8,0),(2.75,.25,5,0),(3.0,.5,7,1),(3.5,.5,4,0),
]
ELISE_CONTOUR = [(0,.5,7,1),(.5,.5,6,0),(1,.5,7,1),(1.5,.5,6,0),(2,.5,7,1),(2.5,.5,2,0),(3,.5,5,0),(3.5,.5,3,0),(4,1,0,1),(5,.5,-3,0),(5.5,.5,0,0),(6,.5,2,0),(6.5,1,3,1)]
CANON_CONTOUR = [(0,.5,4,1),(.5,.5,3,0),(1,.5,2,0),(1.5,.5,1,0),(2,.5,0,1),(2.5,.5,-1,0),(3,.5,0,0),(3.5,.5,1,0)]
ROW_CONTOUR = [(0,.75,0,1),(.75,.75,0,0),(1.5,.5,0,0),(2,.5,1,0),(2.5,.75,2,1),(3.25,.5,2,0),(3.75,.5,1,0),(4.25,.5,2,0),(4.75,.5,3,0),(5.25,1.5,4,1)]


def contour_for(settings: GeneratorSettings):
    name = settings.melody_template.lower()
    if "toccata" in name or "toccata" in settings.preset_name.lower(): return TOCCATA_CONTOUR
    if "elise" in name: return ELISE_CONTOUR
    if "canon" in name: return CANON_CONTOUR
    if "row" in name: return ROW_CONTOUR
    return PIANO_CONTOUR


def normalized_contour_for(settings: GeneratorSettings):
    # Older contour definitions used repeated 0..bar offsets to describe multiple bars.
    # v0.6.1 expands those resets into absolute phrase beats so the melody does not
    # fire a whole phrase in one bar and then wait silently for the next pattern.
    raw = contour_for(settings)
    out = []
    bar_offset = 0.0
    last_off = -1.0
    for off, dur, deg, acc in raw:
        if off < last_off - 0.001:
            bar_offset += settings.beats_per_bar
        out.append((off + bar_offset, dur, deg, acc))
        last_off = off
    return out




def section_contour(settings: GeneratorSettings, section_index: int, section_name: str, rng: random.Random):
    base = normalized_contour_for(settings)
    if not base:
        return base
    # Preserve the rhythmic identity but alter the melodic arc per section. This gives a
    # red thread without restarting the same phrase endlessly.
    name = (section_name or "").lower()
    shift_by_section = {"intro": 0, "a": 0, "b": 3, "hook": 5, "outro": -2}
    shift = shift_by_section.get(name, (section_index * 2) % 7)
    if settings.variation > 60:
        shift += ((settings.seed >> (section_index % 12)) & 3) - 1
    # rotate degrees, not timing, so the phrase keeps musical pacing while changing contour.
    degs = [d for _, _, d, _ in base]
    rot = 0 if section_index in (0, 1) else (settings.seed + section_index * 5) % len(degs)
    out = []
    for i, (off, dur, deg, acc) in enumerate(base):
        src = degs[(i + rot) % len(degs)]
        if name == "b" and i % 4 == 1:
            src = -src // 2
        if name == "hook" and acc:
            src += 1
        # Intro/outro are less busy; hook gets slightly clearer accents.
        ndur = dur
        if name == "intro" and dur < 0.75:
            ndur = max(dur, 0.5)
        out.append((off, ndur, src + shift, acc or (name == "hook" and i % 7 == 0)))
    return out

def coverage_indices(n: int, coverage: int, seed: int, section_index: int) -> set[int]:
    # Coverage is distributed through the full phrase, never a prefix. At 50% it takes every other phrase cell with rotation.
    coverage = clamp(int(coverage), 5, 100)
    take = max(1, min(n, round(n * coverage / 100)))
    if take >= n:
        return set(range(n))
    rot = (seed + section_index * 7) % n
    idx = set()
    for i in range(take):
        idx.add((rot + int(round((i + 0.5) * n / take))) % n)
    return idx


def degree_pitch(settings: GeneratorSettings, degree: int, chord: Chord, strong: bool, low: int, high: int) -> int:
    if strong:
        tones = chord_tones_in_range(chord.symbol, settings.key, settings.mode, low, high)
        return tones[degree % len(tones)]
    tones = scale_tones_in_range(settings.key, settings.mode, low, high, harmonic_minor=(chord.symbol == "V" and settings.mode == "minor"))
    return tones[degree % len(tones)]


def add_note(track: MidiTrack, tick: int, dur: int, ch: int, pitch: int, vel: int, settings: GeneratorSettings, chord: Chord | None = None, low: int = 0, high: int = 127) -> int:
    if ch != 9:
        allowed = scale_pcs(settings.key, settings.mode, harmonic_minor=(chord is not None and chord.symbol == "V" and settings.mode == "minor"))
        if chord is not None and (tick // settings.ticks_per_beat) % settings.beats_per_bar in (0, 2):
            allowed |= {p % 12 for p in chord.notes}
        pitch = nearest_allowed_pitch(pitch, allowed, max(0, low), min(127, high))
    track.note(tick, dur, ch, pitch, vel)
    return 1


def setup_track(t: TrackSettings) -> MidiTrack:
    tr = MidiTrack(t.name)
    ch = 9 if t.role == "drum" else t.channel
    tr.program(0, ch, t.program)
    tr.cc(0, ch, 7, clamp(t.volume, 0, 127)); tr.cc(0, ch, 10, clamp(t.pan, 0, 127)); tr.cc(0, ch, 91, 14)
    cents = int(getattr(t, "fine_tune_cents", 0) or 0)
    if ch != 9 and cents:
        # Approximate fine tune via MIDI pitch bend. Assumes default +/-2 semitone bend range.
        bend = int(round(8192 + clamp(cents, -100, 100) * 8192 / 200))
        bend = clamp(bend, 0, 16383)
        tr.add(0, bytes([0xE0 | (ch & 0x0F), bend & 0x7F, (bend >> 7) & 0x7F]))
    return tr


def compose_melody(tr: MidiTrack, ts: TrackSettings, settings: GeneratorSettings, sections: Sequence[Section], chords: Sequence[Chord], rng: random.Random) -> int:
    count = 0
    bar_ticks = settings.ticks_per_beat * settings.beats_per_bar
    section_transforms = [0, 2, 4, 7, 0]
    template_name = (settings.melody_template or "").lower()
    preset_name = (settings.preset_name or "").lower()
    for si, sec in enumerate(sections):
        contour = section_contour(settings, si, sec.name, rng)
        phrase_beats = max(settings.beats_per_bar, max((off + dur for off, dur, _, _ in contour), default=settings.beats_per_bar))
        phrase_bars = max(1, int(math.ceil(phrase_beats / settings.beats_per_bar)))
        entry = int(arrangement_profile(settings)["entry"].get("melody", 0))
        if sec.name == "Intro":
            if entry == 0:
                sec_start = sec.start_bar
            else:
                sec_start = max(sec.start_bar + entry, sec.start_bar + max(0, sec.bars // 2 - min(2, phrase_bars)))
            max_bars = sec.start_bar + sec.bars - sec_start
        else:
            sec_start = max(sec.start_bar, entry)
            max_bars = sec.start_bar + sec.bars - sec_start
        if max_bars <= 0:
            continue
        selected = coverage_indices(len(contour), settings.melody_coverage, settings.seed, si)
        repeat_count = max(1, math.ceil(max_bars / phrase_bars))
        # Use an occasional larger phrase block to avoid obvious same-pattern restarts.
        if repeat_count > 2 and settings.variation > 55 and sec.name in ("B", "Hook"):
            phrase_bars = min(max_bars, phrase_bars + 1)
            repeat_count = max(1, math.ceil(max_bars / phrase_bars))
        for rep in range(repeat_count):
            start_bar = sec_start + rep * phrase_bars
            if start_bar >= sec.start_bar + sec.bars:
                break
            trans = section_transforms[si % len(section_transforms)] + (rep % 2 if settings.variation > 60 else 0)
            last_added_abs_beat = -99.0
            for ci, (abs_off, dur, deg, acc) in enumerate(contour):
                local_bar = int(abs_off // settings.beats_per_bar)
                beat = abs_off - local_bar * settings.beats_per_bar
                target_bar = start_bar + local_bar
                if target_bar >= sec.start_bar + sec.bars or not role_active(settings, sections, target_bar, "melody"):
                    continue
                chord = chords[min(target_bar, len(chords)-1)]
                is_source_cell = ci in selected
                is_transition_cell = (target_bar == sec.start_bar or target_bar >= sec.start_bar + sec.bars - 1)
                # Coverage no longer means "delete the tail of the melody". Non-selected cells
                # become sparse harmonic filler on structurally useful positions so low coverage
                # still sounds composed rather than empty.
                if not is_source_cell:
                    if not (acc or abs(beat - round(beat)) < 0.01 or (settings.melody_coverage < 55 and (ci + rep + si) % 5 == 0)):
                        continue
                # Keep rapid note clusters subtle. Dense 16th/32nd-like melody bursts are allowed
                # mostly as small transition figures, not as the default melody texture.
                min_gap = 0.75 if sec.name not in ("B", "Hook") else 0.50
                if "toccata" in template_name or "toccata" in preset_name:
                    min_gap = 0.50 if not (sec.name in ("B", "Hook") and is_transition_cell) else 0.25
                if abs_off - last_added_abs_beat < min_gap and not (acc and is_transition_cell):
                    continue
                strong = (abs(beat - round(beat)) < 0.01 and int(round(beat)) in (0, 2)) or acc == 1 or dur >= 0.75
                if is_source_cell:
                    pitch = degree_pitch(settings, deg + trans, chord, strong, 58, 79)
                else:
                    # Filler is deliberately chord-tonal and quieter; it connects phrases without
                    # sounding like another unrelated melody generator.
                    tones = chord_tones_in_range(chord.symbol, settings.key, settings.mode, 58, 77)
                    pitch = tones[(ci + rep + si) % len(tones)]
                if is_source_cell and not strong:
                    # Passing notes may be scalar, but keep them close to the active chord to avoid
                    # the "schräg gegen die Begleitung" effect.
                    chord_tones = chord_tones_in_range(chord.symbol, settings.key, settings.mode, 56, 80)
                    nearest_chord = min(chord_tones, key=lambda p: abs(p - pitch))
                    if abs(nearest_chord - pitch) > 3:
                        pitch = nearest_chord
                tick = target_bar * bar_ticks + int(round(beat * settings.ticks_per_beat))
                vel = ts.volume * .56 + sec.energy * .075 + (5 if acc else 0)
                if not is_source_cell:
                    vel -= 10
                vel = role_velocity(settings, "melody", clamp(vel, 34, 78))
                note_len = max(int(dur * settings.ticks_per_beat * .92), settings.ticks_per_beat // 3)
                count += add_note(tr, tick, note_len, ts.channel, pitch + ts.octave*12 + ts.transpose, vel, settings, chord, 52, 82)
                last_added_abs_beat = abs_off
    return count


def compose_counter_melody(tr: MidiTrack, ts: TrackSettings, settings: GeneratorSettings, sections: Sequence[Section], chords: Sequence[Chord], melody_index: int = 1) -> int:
    # Extra melody tracks are not allowed to become independent lead melodies by default.
    # They become sparse chord-tone answers in a separate register, so several user-added
    # melody instruments do not fight each other harmonically.
    count = 0
    bar_ticks = settings.ticks_per_beat * settings.beats_per_bar
    for chord in chords:
        sec = section_for_bar(sections, chord.bar)
        if sec.name in ("Intro", "Outro") and chord.bar - sec.start_bar < max(2, sec.bars // 2):
            continue
        if sec.energy < 58 or (chord.bar + melody_index) % 4 not in (1, 3):
            continue
        tones = chord_tones_in_range(chord.symbol, settings.key, settings.mode, 55, 74)
        pitch = tones[(chord.bar + melody_index * 2) % len(tones)]
        # Keep counter lines away from the lead register unless user explicitly transposes.
        if melody_index % 2 == 1:
            pitch = nearest_allowed_pitch(pitch - 12, {n % 12 for n in chord.notes}, 48, 67)
        off = 1.0 if settings.beats_per_bar >= 4 else 1.0
        if sec.name in ("Hook", "B") and (chord.bar + melody_index) % 8 == 3:
            off = max(0.0, settings.beats_per_bar - 1.0)
        vel = role_velocity(settings, "melody", clamp(ts.volume * 0.42 + sec.energy * 0.045, 24, 52))
        count += add_note(tr, chord.bar * bar_ticks + int(off * settings.ticks_per_beat), int(settings.ticks_per_beat * 0.65), ts.channel, pitch + ts.octave*12 + ts.transpose, vel, settings, chord, 45, 74)
    return count


def compose_bass(tr: MidiTrack, ts: TrackSettings, settings: GeneratorSettings, sections: Sequence[Section], chords: Sequence[Chord]) -> int:
    count=0; bar_ticks=settings.ticks_per_beat*settings.beats_per_bar
    for chord in chords:
        if not role_active(settings, sections, chord.bar, "bass"):
            continue
        sec = section_for_bar(sections, chord.bar)
        root = 12*3 + chord.root + ts.octave*12 + ts.transpose
        root = nearest_allowed_pitch(root, {chord.root}, 28, 52)
        fifth = nearest_allowed_pitch(root + 7, scale_pcs(settings.key, settings.mode, chord.symbol=="V" and settings.mode=="minor"), 31, 56)
        pat = [(0, root, .58), (1.5, fifth, .42), (2.0, root, .48), (3.0, root+12, .38)] if settings.beats_per_bar == 4 else [(0, root, .7), (1, fifth, .55), (2, root+12, .55)]
        vel = role_velocity(settings, "bass", clamp(ts.volume*.58 + sec.energy*.12, 38, 78))
        for off, p, dur in pat:
            if off < settings.beats_per_bar:
                count += add_note(tr, chord.bar*bar_ticks+int(off*settings.ticks_per_beat), int(dur*settings.ticks_per_beat), ts.channel, p, vel, settings, chord, 28, 58)
    return count


def compose_chords(tr: MidiTrack, ts: TrackSettings, settings: GeneratorSettings, sections: Sequence[Section], chords: Sequence[Chord], pad=False) -> int:
    count=0; prev=None; bar_ticks=settings.ticks_per_beat*settings.beats_per_bar
    role_name = "pad" if pad else "chord"
    for chord in chords:
        if not role_active(settings, sections, chord.bar, role_name):
            continue
        sec = section_for_bar(sections, chord.bar)
        if pad and (chord.bar - sec.start_bar) % 2: continue
        if sec.name == "Intro" and not pad and chord.bar < sec.start_bar + sec.bars//2: continue
        voicing = voice_lead(prev, chord.notes, 48 if not pad else 43, 72 if not pad else 64); prev=voicing
        hits = [0] if pad or settings.beats_per_bar == 3 else [0, 2]
        vel = role_velocity(settings, role_name, clamp(ts.volume * (.42 if pad else .50) + sec.energy * (.04 if pad else .07), 24, 68))
        dur = int((bar_ticks * (1.9 if pad else .62/settings.beats_per_bar))) if pad else int(.58*settings.ticks_per_beat)
        for off in hits:
            for p in voicing:
                count += add_note(tr, chord.bar*bar_ticks+off*settings.ticks_per_beat, dur, ts.channel, p+ts.octave*12+ts.transpose, vel, settings, chord, 40, 76)
    return count


def compose_drums(tr: MidiTrack, ts: TrackSettings, settings: GeneratorSettings, sections: Sequence[Section]) -> int:
    count=0; bar_ticks=settings.ticks_per_beat*settings.beats_per_bar
    for bar in range(settings.bars):
        if not role_active(settings, sections, bar, "drum"):
            continue
        sec=section_for_bar(sections, bar)
        if sec.energy < 30: continue
        base=role_velocity(settings, "drum", clamp(ts.volume*.55+sec.energy*.14, 40, 82))
        hits=[(0,"kick",base+8),(2,"snare",base),(1,"closed_hat",base-24),(3,"closed_hat",base-24)]
        if "house" in settings.preset_name.lower() or "drive" in settings.preset_name.lower():
            hits += [(1,"kick",base-6),(3,"kick",base-6)]
        if bar == sec.start_bar+sec.bars-1:
            hits += [(3.5,"snare",base+6)]
        for off,name,vel in hits:
            if off < settings.beats_per_bar:
                tr.note(bar*bar_ticks+int(off*settings.ticks_per_beat), max(1,settings.ticks_per_beat//12), 9, DRUM_NOTES[name], int(clamp(vel,20,100))); count+=1
    return count


def quality_pass(tracks: Sequence[MidiTrack], active_settings: Sequence[TrackSettings], settings: GeneratorSettings, chords: Sequence[Chord]) -> None:
    # hard timing grid + final tonal correction for every non-drum note-on.
    # v0.6.1 also rewrites matching note-off pitches when a note-on pitch is corrected.
    bar_ticks = settings.ticks_per_beat * settings.beats_per_bar
    for tr, ts in zip(tracks, active_settings):
        role = (ts.role or "").lower()
        note_count = sum(1 for e in tr.events if len(e.data) >= 3 and (e.data[0] & 0xF0) == 0x90 and e.data[2] > 0)
        density_penalty = max(0, note_count - (180 if role == "melody" else 260)) * (0.030 if role == "melody" else 0.018)
        active_pitch_map: Dict[Tuple[int, int], List[int]] = {}
        for e in sorted(tr.events, key=lambda ev: (ev.tick, ev.order)):
            if len(e.data) < 3:
                continue
            status = e.data[0] & 0xF0
            ch = e.data[0] & 0x0F
            if status == 0x90 and e.data[2] > 0:
                if ch == 9:
                    continue
                bar = clamp(e.tick // bar_ticks, 0, len(chords)-1)
                chord = chords[bar]
                beat_pos = (e.tick - bar * bar_ticks) / max(1, settings.ticks_per_beat)
                chord_pcs = {n % 12 for n in chord.notes}
                scale_allowed = scale_pcs(settings.key, settings.mode, chord.symbol == "V" and settings.mode == "minor")
                if role == "melody":
                    # v0.6.5 default is conservative: melody notes are chord-tonal on
                    # strong/visible positions and only very quiet passing notes may use
                    # wider scale tones. This avoids lead/counter melody clashes.
                    strong = abs(beat_pos - round(beat_pos)) < 0.03 and int(round(beat_pos)) in (0, 2, settings.beats_per_bar - 1)
                    allowed = (scale_allowed | chord_pcs) if settings.allow_dissonance else (chord_pcs if strong or e.data[2] >= 56 else (scale_allowed | chord_pcs))
                    low, high = 52, 82
                    vel = clamp(e.data[2] - density_penalty - 6, 20, 74)
                elif role in ("counter", "harmony"):
                    allowed = (scale_allowed | chord_pcs) if settings.allow_dissonance else chord_pcs
                    low, high = 45, 74
                    vel = clamp(e.data[2] - density_penalty - 8, 16, 58)
                elif role in ("chord", "pad"):
                    allowed = chord_pcs
                    low, high = 40, 76
                    vel = clamp(e.data[2] - density_penalty, 16, 70)
                elif role == "bass":
                    allowed = {chord.root, (chord.root + 7) % 12} | chord_pcs
                    low, high = 24, 58
                    vel = clamp(e.data[2] - density_penalty, 24, 76)
                else:
                    allowed = scale_allowed | chord_pcs
                    low, high = 24, 96
                    vel = clamp(e.data[2] - density_penalty, 18, 84)
                old_pitch = e.data[1]
                new_pitch = nearest_allowed_pitch(old_pitch, allowed, low, high)
                e.data = bytes([e.data[0], int(new_pitch), int(vel)])
                active_pitch_map.setdefault((ch, old_pitch), []).append(int(new_pitch))
            elif status == 0x80 or (status == 0x90 and e.data[2] == 0):
                if ch == 9:
                    continue
                old_pitch = e.data[1]
                queue = active_pitch_map.get((ch, old_pitch))
                if queue:
                    new_pitch = queue.pop(0)
                    e.data = bytes([e.data[0], int(new_pitch), e.data[2]])


def generate_song(settings: GeneratorSettings, output_dir: str | os.PathLike, progress=None) -> SongResult:
    settings = GeneratorSettings.from_dict(settings.to_dict())
    if settings.randomize_seed:
        settings.seed = int(time.time_ns() % 2_147_483_647)
    rng=random.Random(settings.seed)
    resolve_auto_settings(settings, rng)
    sanitize_mode_progression(settings)
    settings.bpm = clamp(settings.bpm, 48, 220); settings.bars=clamp(settings.bars, 16, 256); settings.beats_per_bar=clamp(settings.beats_per_bar,3,4)
    title = generate_title(settings.seed, settings.preset_name) if settings.randomize_seed or not settings.title.strip() else settings.title.strip()
    settings.title = title
    out=Path(output_dir); out.mkdir(parents=True, exist_ok=True)
    sections=build_sections(settings); chords=build_chords(settings, sections)
    tracks=[]; active_tracks=[]; note_count=0
    melody_seen = 0
    for t in settings.tracks:
        if not t.enabled: continue
        effective = t
        tr=setup_track(t)
        role = (t.role or "").lower()
        if role=="drum": note_count += compose_drums(tr,t,settings,sections)
        elif role=="bass": note_count += compose_bass(tr,t,settings,sections,chords)
        elif role=="melody":
            if melody_seen == 0:
                note_count += compose_melody(tr,t,settings,sections,chords,rng)
            else:
                effective = TrackSettings(t.name, "counter", t.enabled, t.channel, t.program, min(t.volume, 54), t.pan, t.octave, t.transpose, t.fine_tune_cents)
                note_count += compose_counter_melody(tr,effective,settings,sections,chords,melody_seen)
            melody_seen += 1
        elif role=="chord": note_count += compose_chords(tr,t,settings,sections,chords,False)
        elif role=="pad": note_count += compose_chords(tr,t,settings,sections,chords,True)
        tracks.append(tr); active_tracks.append(effective)
    quality_pass(tracks, active_tracks, settings, chords)
    note_count=sum(1 for tr in tracks for e in tr.events if len(e.data)>=3 and (e.data[0]&0xF0)==0x90 and e.data[2]>0)
    output_stem, midi, js, chord_path = unique_output_paths(out, title, settings.seed)
    markers=[(s.start_bar*settings.beats_per_bar*settings.ticks_per_beat,s.name) for s in sections] if settings.add_markers else []
    write_midi(str(midi), tracks, settings.ticks_per_beat, settings.bpm, settings.beats_per_bar, title, markers)
    sheet=make_chord_sheet(title, settings, sections, chords, note_count)
    if settings.export_chord_sheet: chord_path.write_text(sheet,encoding='utf-8')
    if settings.export_json:
        payload={"application":"PythonSoundHelix","version":APP_VERSION,"engine":ENGINE_NAME,"title":title,"seed":settings.seed,"output_stem":output_stem,"midi_path":str(midi),"note_count":note_count,"arrangement_profile":arrangement_profile(settings),"settings":settings.to_dict(),"sections":[asdict(s) for s in sections],"chords":[asdict(c) for c in chords]}
        js.write_text(json.dumps(payload,indent=2,ensure_ascii=False),encoding='utf-8')
    return SongResult(title,settings.seed,str(midi),str(js) if settings.export_json else "",str(chord_path) if settings.export_chord_sheet else "",note_count, f"{ENGINE_NAME}: auto phrase plans, seed-specific arrangement entry profile, strict tonal correction, role loudness variation.")


def make_chord_sheet(title: str, settings: GeneratorSettings, sections: Sequence[Section], chords: Sequence[Chord], note_count: int) -> str:
    lines=[title,"="*len(title),"",f"Generated by PythonSoundHelix {APP_VERSION} (GPLv3)",f"Engine: {ENGINE_NAME}",f"Preset: {settings.preset_name}",f"Seed: {settings.seed}",f"Tempo: {settings.bpm} BPM | Key: {settings.key} {settings.mode} | Bars: {settings.bars}",f"Progression: {settings.progression}",f"Arrangement profile: {arrangement_profile(settings)['style']} | focus={arrangement_profile(settings)['focus']}",f"Melody coverage: {settings.melody_coverage}% distributed across the whole phrase, not prefix-only",f"Notes: {note_count}","","Sections:"]
    for s in sections: lines.append(f"  - {s.name}: bars {s.start_bar+1}-{s.start_bar+s.bars}, energy {s.energy}%")
    lines += ["", "Chord map:"]
    current=None; buf=[]
    for c in chords:
        if c.section != current:
            if buf: lines.append("    "+" | ".join(buf)); buf=[]
            current=c.section; lines.append(f"  [{current}]")
        buf.append(f"{c.bar+1}:{c.symbol}({note_name(12*4+c.root)[:-1]})")
        if len(buf)>=8: lines.append("    "+" | ".join(buf)); buf=[]
    if buf: lines.append("    "+" | ".join(buf))
    lines.append("\nRule: the generator locks mode/progression compatibility, snaps non-drum notes to the active scale/chord map, and uses a seed-specific single-lead intro profile so songs can start with drums, pad, bass, chords, or melody without every intro becoming pad-first.")
    return "\n".join(lines)+"\n"
