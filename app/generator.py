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

APP_VERSION = "0.7.8"
ENGINE_NAME = "prompt-first semantic relation arranger v0.7.8"

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
    lock_instrument: bool = False


@dataclass
class GeneratorSettings:
    preset_name: str = "Auto Composer"
    title: str = ""
    prompt: str = ""
    prompt_language: str = "English"
    prompt_interpretation: str = ""
    prompt_style_id: str = ""
    prompt_style_name: str = ""
    prompt_style_family: str = ""
    prompt_style_blend: List[str] = field(default_factory=list)
    prompt_relation_profile: str = ""
    prompt_semantic_tags: List[str] = field(default_factory=list)
    prompt_style_confidence: int = 0
    prompt_drum_feel: str = ""
    prompt_intensity: int = 0
    prompt_hard_drums: bool = False
    prompt_reference_name: str = ""
    prompt_reference_type: str = ""
    prompt_reference_traits: str = ""
    prompt_mode: bool = True
    direct_style_hint: str = "Auto / random style"
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
    """Return the composition family, not just the UI preset.

    v0.7.8: Prompt style has priority.  In v0.7.0 a prompt such as
    "techno misc with hard drums" was parsed as Techno, but the generator
    still behaved like the generic Minor House preset and could even pick a
    pad-first arrangement.  This function makes style recognition drive the
    actual engine.
    """
    family = (getattr(settings, "prompt_style_family", "") or "").lower().strip()
    sid = (getattr(settings, "prompt_style_id", "") or "").lower().strip()
    name = ((getattr(settings, "prompt_style_name", "") or "") + " " + (settings.preset_name or "Auto Composer")).lower()
    if family:
        return family
    if any(t in sid or t in name for t in ["schranz", "hard_techno", "acid_techno", "minimal_tekkno", "techno", "tekkno"]):
        return "techno"
    if any(t in sid or t in name for t in ["house", "garage", "ukg", "amapiano"]):
        return "house"
    if any(t in sid or t in name for t in ["goa", "psytrance", "psy_trance", "psy trance", "psy"]):
        return "psytrance"
    if any(t in sid or t in name for t in ["trance", "acid_trance", "uplifting_trance", "rave"]):
        return "trance"
    if any(t in sid or t in name for t in ["dnb", "drum_and_bass", "jungle", "breakcore", "techstep"]):
        return "dnb"
    if any(t in sid or t in name for t in ["gabba", "hardcore", "frenchcore", "hardstyle"]):
        return "hardcore"
    if any(t in sid or t in name for t in ["ambient", "drone", "meditation", "pad"]):
        return "ambient"
    if any(t in sid or t in name for t in ["piano", "klavier", "waltz", "walzer"]):
        return "piano"
    if any(t in sid or t in name for t in ["canon", "baroque", "orchestra", "orchestral", "choral", "church", "gospel"]):
        return "canon"
    if "elise" in sid or "elise" in name:
        return "elise"
    if any(t in sid or t in name for t in ["rock", "metal", "punk", "ska", "reggae", "dub"]):
        return "band"
    if "toccata" in name or "drive" in name:
        return "toccata"
    if (settings.preset_name or "").lower() == "auto composer":
        r = random.Random(settings.seed ^ 0xA07C0DE)
        return r.choice(["piano", "toccata", "pop", "house", "dnb", "ambient", "canon", "elise", "techno"])
    return "pop"


def _prompt_tokens(settings: GeneratorSettings) -> str:
    return ((getattr(settings, "prompt", "") or "") + " " + (getattr(settings, "prompt_style_id", "") or "") + " " + (getattr(settings, "prompt_style_name", "") or "") + " " + (getattr(settings, "prompt_reference_name", "") or "")).lower().replace("_", " ").replace("-", " ")


def _style_blend(settings: GeneratorSettings) -> List[str]:
    explicit = getattr(settings, "prompt_style_blend", None)
    if isinstance(explicit, (list, tuple)) and explicit:
        out: List[str] = []
        for item in explicit:
            item = str(item).lower().replace("_", " ").replace("-", " ").strip()
            if item and item not in out:
                out.append(item)
        return out
    text = _prompt_tokens(settings)
    found: List[str] = []
    if "goa" in text:
        found.append("goa")
    if any(x in text for x in ["psytrance", "psy trance", "psychedelic trance", "psy"]):
        found.append("psytrance")
    if "techno" in text or "tekkno" in text:
        found.append("techno")
    if "grunge" in text or "nirvana" in text:
        found.append("grunge")
    if "acid" in text:
        found.append("acid")
    if any(x in text for x in ["dnb", "drum and bass", "drum n bass", "dran and bass", "jungle", "techstep", "liquid"]):
        found.append("dnb")
    if "trance" in text and "psytrance" not in found and "goa" not in found:
        found.append("trance")
    if "hard" in text or "fat" in text or "fett" in text or "heavy" in text:
        found.append("hard")
    out: List[str] = []
    for item in found:
        if item not in out:
            out.append(item)
    return out


def _relation_profile(settings: GeneratorSettings) -> str:
    return (getattr(settings, "prompt_relation_profile", "") or "").lower().strip()

def _has_semantic(settings: GeneratorSettings, tag: str) -> bool:
    tags = getattr(settings, "prompt_semantic_tags", []) or []
    return str(tag).lower() in {str(t).lower() for t in tags}


def _psy_techno_combo(settings: GeneratorSettings) -> bool:
    blend = set(_style_blend(settings))
    return "psytrance" in blend and ("techno" in blend or "acid" in blend or "goa" in _prompt_tokens(settings))

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
    if style == "psytrance":
        base = r.choice([
            {"A":["i","VII","VI","VII","i","VII","VI","V"], "B":["iv","i","VI","VII","iv","i","V","V"], "HOOK":["i","i","VII","VI","i","i","iv","VII"], "OUT":["VI","VII","i","i"]},
            {"A":["i","i","VII","VI","iv","i","VII","i"], "B":["VI","VII","i","iv","VI","VII","V","V"], "HOOK":["i","VII","i","VI","i","VII","iv","V"], "OUT":["iv","V","i","i"]},
        ])
    elif style in ("dnb", "house", "toccata", "trance"):
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
    r = random.Random(settings.seed ^ 0xE17A ^ (sum(ord(c) for c in ((getattr(settings, "prompt_style_id", "") or settings.preset_name or ""))) << 3))
    style_hint = _style_hint(settings)
    roles = ["drum", "bass", "melody", "chord", "pad"]
    hard_drums = bool(getattr(settings, "prompt_hard_drums", False))
    intensity = int(getattr(settings, "prompt_intensity", 0) or 0)

    if style_hint == "psytrance":
        lead_pool = ["drum", "drum", "bass", "drum"] if _psy_techno_combo(settings) else ["drum", "bass", "drum", "bass"]
    elif style_hint in ("techno", "hardcore"):
        lead_pool = ["drum", "drum", "drum", "bass", "chord"] if hard_drums or intensity > 10 else ["drum", "drum", "bass", "chord", "melody"]
    elif style_hint == "dnb":
        lead_pool = ["drum", "drum", "bass"]
    elif style_hint in ("house", "trance", "toccata"):
        lead_pool = ["drum", "bass", "melody", "chord"]
    elif style_hint in ("ambient", "piano", "canon", "elise"):
        lead_pool = ["melody", "chord", "pad", "bass"]
    else:
        lead_pool = roles

    lead_role = lead_pool[r.randrange(len(lead_pool))]
    if hard_drums and style_hint in ("techno", "hardcore", "house", "dnb", "psytrance"):
        lead_role = "drum"
    style = ("goa_techno_psy_drive" if _psy_techno_combo(settings) else "psytrance_drive") if style_hint == "psytrance" else (f"{lead_role}s_first" if lead_role == "drum" else f"{lead_role}_first")

    if style_hint == "dnb":
        prof_name = _relation_profile(settings)
        if prof_name in ("dark_melodic_dnb", "liquid_dnb"):
            entry = {"drum": 0, "bass": 0, "chord": 8, "melody": 8, "pad": 16}
        else:
            entry = {"drum": 0, "bass": 0, "chord": 8, "melody": 12, "pad": 24}
        secondary = []
        if prof_name:
            style = prof_name + "_drive"
        else:
            style = "dark_melodic_dnb_drive" if "dark" in _prompt_tokens(settings) or "melodic" in _prompt_tokens(settings) else "dnb_breakbeat_drive"
        lead_role = "drum"
    elif style_hint == "psytrance":
        entry = {"drum": 0, "bass": 0, "chord": 12 if _psy_techno_combo(settings) else 8, "melody": 12 if _psy_techno_combo(settings) else 8, "pad": 48 if _psy_techno_combo(settings) else 24}
        secondary = []
    elif style_hint == "techno":
        if _relation_profile(settings) == "techno_grunge" or "grunge" in _style_blend(settings):
            entry = {"drum": 0, "bass": 1, "chord": 2, "melody": 8, "pad": 48}
            style = "techno_grunge_drive"
        else:
            entry = {"drum": 0, "bass": 2, "chord": 4, "melody": 8, "pad": 16}
        secondary = []
    elif style_hint == "hardcore":
        entry = {"drum": 0, "bass": 1, "chord": 4, "melody": 8, "pad": 20}
        secondary = []
    else:
        secondary = [x for x in roles if x != lead_role]
        r.shuffle(secondary)
        entry = {lead_role: 0}
        for i, role in enumerate(secondary):
            entry[role] = [2, 4, 8, 12][i]

    intro_solo_bars = 1 if style_hint in ("psytrance", "techno", "hardcore") else r.choice([2, 3, 4, 5])
    mult = {"drum": 1.0, "bass": 1.0, "melody": 1.0, "chord": 0.88, "pad": 0.78}
    if style_hint == "dnb":
        if _relation_profile(settings) in ("dark_melodic_dnb", "liquid_dnb"):
            mult.update({"drum": 1.42, "bass": 1.30, "melody": 0.70, "chord": 0.44, "pad": 0.30})
        else:
            mult.update({"drum": 1.46, "bass": 1.32, "melody": 0.48, "chord": 0.48, "pad": 0.18})
        focus = "drum+bass"
    elif style_hint == "psytrance":
        if _psy_techno_combo(settings):
            mult.update({"drum": 1.72, "bass": 1.66, "melody": 0.58, "chord": 0.38, "pad": 0.04})
            focus = "drum+bass"
        else:
            mult.update({"drum": 1.34, "bass": 1.42, "melody": 0.78, "chord": 0.54, "pad": 0.18})
            focus = "bass"
    elif style_hint == "techno":
        if _relation_profile(settings) == "techno_grunge" or "grunge" in _style_blend(settings):
            mult.update({"drum": 1.34, "bass": 1.18, "melody": 0.72, "chord": 1.12, "pad": 0.08})
            focus = "drum+riff"
        else:
            mult.update({"drum": 1.28 if hard_drums else 1.15, "bass": 1.10, "melody": 0.54, "chord": 0.88, "pad": 0.32})
            focus = "drum" if hard_drums else r.choice(["drum", "bass", "chord"])
    elif style_hint == "hardcore":
        mult.update({"drum": 1.36, "bass": 1.18, "melody": 0.45, "chord": 0.82, "pad": 0.18})
        focus = "drum"
    elif style_hint == "dnb":
        mult.update({"drum": 1.22, "bass": 1.15, "melody": 0.62, "chord": 0.72, "pad": 0.38})
        focus = r.choice(["drum", "bass"])
    else:
        focus = r.choice(roles)
        for role in list(mult):
            if role == focus:
                mult[role] *= r.choice([1.05, 1.12, 1.18])
            elif role == lead_role:
                mult[role] *= r.choice([0.96, 1.02, 1.08])
            else:
                mult[role] *= r.choice([0.62, 0.74, 0.86, 0.94])
    return {"style": style, "lead_role": lead_role, "intro_solo_bars": intro_solo_bars, "entry": entry, "mult": mult, "focus": focus, "style_family": style_hint}

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
    style_family = str(prof.get("style_family", _style_hint(settings)))
    if style_family == "dnb":
        if role in ("drum", "bass"):
            return True
        if role == "pad":
            return sec.name in ("B", "Hook") and rel % 8 in (0, 1)
        if role == "chord":
            return sec.name in ("A", "B", "Hook") and rel % 4 in (0, 2)
        if role == "melody":
            return sec.name in ("B", "Hook") and rel % 8 in (0, 1, 4, 5)
    if style_family == "psytrance":
        if role in ("drum", "bass"):
            return True
        if role == "pad":
            return sec.name in ("B", "Hook") and rel % 8 in (0, 1, 2)
        if role == "chord":
            return sec.name in ("B", "Hook") and rel % 4 in (0, 2)
        if role == "melody":
            return sec.name in ("B", "Hook") and rel % 4 in (0, 1, 2)
    if style_family in ("techno", "hardcore"):
        if role == "pad" and sec.name not in ("B", "Hook"):
            return False
        if role == "pad" and rel % 4 not in (0, 1):
            return False
        if role == "melody" and sec.name == "Intro":
            return False
        if role == "melody" and sec.name not in ("B", "Hook") and rel % 8 not in (0, 4):
            return False
        if role == "chord" and rel % 2 == 1:
            return False
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
        if style == "psytrance":
            settings.mode = "minor"
        elif style == "dnb":
            settings.mode = "minor"
        elif style in ("house", "techno", "trance", "hardcore", "toccata", "ambient", "elise"):
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
        elif style in ("psytrance", "techno", "hardcore"):
            pool = ["Toccata contour", "Toccata contour", "SoundHelix piano contour"]
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
    # v0.7.0: preset = style hint, not fixed harmony. Core musical choices stay auto by default.
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



ROLE_PROGRAM_POOLS = {
    "piano": {
        "bass": [32, 33, 34], "melody": [0, 1, 4, 5, 6], "chord": [0, 1, 4], "pad": [48, 49, 88, 89], "counter": [4, 5, 6],
    },
    "toccata": {
        "bass": [32, 38, 39], "melody": [16, 17, 18, 80, 81], "chord": [16, 18, 19, 48], "pad": [48, 51, 89, 91], "counter": [19, 80, 81],
    },
    "house": {
        "bass": [38, 39, 81, 87], "melody": [80, 81, 82, 88, 89], "chord": [4, 5, 88, 90], "pad": [88, 89, 90, 91, 95], "counter": [81, 82, 89],
    },
    "techno": {
        "bass": [38, 39, 87, 88], "melody": [81, 82, 87, 100], "chord": [81, 87, 88, 100], "pad": [89, 90, 91], "counter": [81, 82, 87],
    },
    "trance": {
        "bass": [38, 39, 81, 87], "melody": [81, 82, 88, 89], "chord": [81, 88, 89, 90], "pad": [89, 90, 91, 92], "counter": [81, 82, 88],
    },
    "psytrance": {
        "bass": [38, 39], "melody": [81, 82, 87, 88], "chord": [81, 87, 88], "pad": [89, 90, 91], "counter": [81, 82, 87],
    },
    "hardcore": {
        "bass": [38, 39, 87], "melody": [81, 82, 87], "chord": [87, 100, 81], "pad": [90, 91], "counter": [81, 87],
    },
    "dnb": {
        "bass": [38, 39, 81, 87], "melody": [80, 81, 82, 86], "chord": [4, 5, 88, 90], "pad": [89, 90, 91, 95], "counter": [80, 81, 82],
    },
    "ambient": {
        "bass": [32, 33, 38], "melody": [0, 4, 5, 73, 80, 88], "chord": [48, 49, 88, 89], "pad": [88, 89, 90, 91, 92, 95], "counter": [73, 88, 89],
    },
    "canon": {
        "bass": [32, 42, 43], "melody": [40, 41, 56, 73, 0], "chord": [48, 49, 50], "pad": [48, 49, 52, 89], "counter": [40, 41, 73],
    },
    "elise": {
        "bass": [0, 32, 42], "melody": [0, 4, 5, 6], "chord": [0, 48, 49], "pad": [48, 49, 89], "counter": [4, 5, 6],
    },
    "pop": {
        "bass": [32, 33, 34, 38], "melody": [0, 4, 5, 80, 81], "chord": [0, 4, 24, 27, 88], "pad": [48, 49, 88, 89, 90], "counter": [4, 5, 80],
    },
}


def auto_program_for(settings: GeneratorSettings, track: TrackSettings, track_index: int) -> int:
    """Choose a style-compatible GM program unless the user locked the instrument.

    This keeps generated songs from always using the same instrument set while still
    letting Finetuning override the engine with the new lock checkbox.
    """
    if getattr(track, "lock_instrument", False) or (track.role or "").lower() == "drum":
        return int(track.program)
    style = _style_hint(settings)
    pools = ROLE_PROGRAM_POOLS.get(style, ROLE_PROGRAM_POOLS["pop"])
    role = (track.role or "melody").lower()
    pool = pools.get(role) or pools.get("counter") or [int(track.program)]
    salt = sum(ord(c) for c in f"{track.name}:{role}:{track_index}:{settings.preset_name}")
    r = random.Random(settings.seed ^ 0x1A57A11 ^ salt)
    return int(pool[r.randrange(len(pool))])


def effective_track_for_generation(settings: GeneratorSettings, track: TrackSettings, track_index: int, forced_role: str | None = None) -> TrackSettings:
    role = forced_role or track.role
    profile = _relation_profile(settings)
    # Relation profiles already picked role-compatible programs in the prompt parser.
    # Keep those choices unless the profile intentionally falls back to the generic
    # style pools. This prevents "symphonic metal" or "liquid DnB" from being
    # overwritten by the broad family defaults.
    relation_program_locked = bool(profile)
    program = int(track.program) if relation_program_locked else auto_program_for(settings, track, track_index)
    volume = track.volume
    if not getattr(track, "lock_instrument", False):
        if _style_hint(settings) == "dnb":
            if profile == "liquid_dnb":
                if role == "drum": volume = max(volume, 84); program = 0
                elif role == "bass": volume = max(volume, 86); program = program if relation_program_locked else 38
                elif role == "melody": volume = min(max(volume, 58), 68)
                elif role == "chord": volume = min(max(volume, 42), 54)
                elif role == "pad": volume = min(max(volume, 34), 48)
            elif profile == "dark_melodic_dnb":
                if role == "drum": volume = max(volume, 96); program = 0
                elif role == "bass": volume = max(volume, 92); program = program if relation_program_locked else 39
                elif role == "melody": volume = min(max(volume, 58), 64)
                elif role == "chord": volume = min(max(volume, 40), 50)
                elif role == "pad": volume = min(max(volume, 24), 32)
            elif profile in ("techstep_dnb", "neurofunk_dnb"):
                if role == "drum": volume = max(volume, 100); program = 0
                elif role == "bass": volume = max(volume, 98); program = 87
                elif role == "melody": volume = min(max(volume, 46), 54)
                elif role == "chord": volume = min(max(volume, 34), 44)
                elif role == "pad": volume = min(volume, 14)
            else:
                if role == "drum": volume = max(volume, 96); program = 0
                elif role == "bass": volume = max(volume, 92); program = 38 + ((settings.seed >> 2) & 1)
                elif role == "melody": volume = min(max(volume, 48), 58); program = 80 + ((settings.seed >> 4) & 3)
                elif role == "chord": volume = min(max(volume, 40), 52); program = 88
                elif role == "pad": volume = min(volume, 20); program = 89 + ((settings.seed >> 6) & 1)
        elif _style_hint(settings) == "psytrance":
            if _psy_techno_combo(settings):
                if role == "drum": volume = max(volume, 112); program = 0
                elif role == "bass": volume = max(volume, 108); program = 38 + ((settings.seed >> 3) & 1)
                elif role == "melody": volume = min(max(volume, 58), 66); program = 81 + ((settings.seed >> 5) & 1)
                elif role == "chord": volume = min(max(volume, 46), 56); program = 87
                elif role == "pad": volume = min(volume, 10); program = 90
            else:
                if role == "drum": volume = max(volume, 86)
                elif role == "bass": volume = max(volume, 88); program = 38 + ((settings.seed >> 2) & 1)
                elif role == "melody": volume = min(max(volume, 64), 74)
                elif role == "chord": volume = min(max(volume, 58), 68)
                elif role == "pad": volume = min(volume, 24)
        elif profile == "dark_ambient_drone":
            if role == "bass": volume = min(max(volume, 38), 48)
            elif role == "melody": volume = min(max(volume, 40), 54)
            elif role == "chord": volume = min(max(volume, 34), 46)
            elif role == "pad": volume = max(volume, 68)
        elif profile == "symphonic_metal":
            if role == "drum": volume = max(volume, 92); program = 0
            elif role == "bass": volume = max(volume, 82)
            elif role == "melody": volume = min(max(volume, 62), 72)
            elif role == "chord": volume = max(volume, 76)
            elif role == "pad": volume = max(volume, 56)
        elif profile == "reggae_dub":
            if role == "drum": volume = min(max(volume, 62), 76)
            elif role == "bass": volume = max(volume, 86)
            elif role == "pad": volume = max(volume, 48)
        elif role == "melody":
            volume = min(volume, 70)
        elif role in ("counter", "harmony"):
            volume = min(volume, 52)
        elif role == "pad":
            volume = min(volume, 46)
    return TrackSettings(track.name, role, track.enabled, track.channel, int(program), int(volume), track.pan, track.octave, track.transpose, track.fine_tune_cents, getattr(track, "lock_instrument", False))


def bass_pattern_family(settings: GeneratorSettings) -> str:
    style = _style_hint(settings)
    r = random.Random(settings.seed ^ 0xBA55CAFE ^ (sum(ord(c) for c in settings.preset_name or "") << 1))
    if style == "psytrance":
        return "psy_rolling"
    elif style == "dnb":
        prof = _relation_profile(settings)
        if prof == "liquid_dnb":
            return "dnb_sub"
        if prof in ("dark_melodic_dnb", "techstep_dnb", "neurofunk_dnb"):
            return "dnb_reese"
        return "dnb_sub" if (settings.seed & 1) else "dnb_reese"
    elif style in ("techno", "hardcore"):
        pool = ["offbeat_pulse", "pedal", "syncopated", "root_fifth", "broken_octave"]
    elif style in ("house", "dnb", "trance", "toccata"):
        pool = ["offbeat_pulse", "syncopated", "broken_octave", "walking", "root_fifth", "sparse_roots"]
    elif style in ("piano", "canon", "elise"):
        pool = ["sparse_roots", "broken_octave", "walking", "root_fifth"]
    elif style == "ambient":
        pool = ["sparse_roots", "pedal", "root_fifth", "walking"]
    else:
        pool = ["root_fifth", "walking", "broken_octave", "syncopated", "sparse_roots"]
    # Tango-like rhythm exists, but it is deliberately rare.
    if r.random() < 0.07:
        pool.append("tango_like")
    return pool[r.randrange(len(pool))]


def section_bass_pattern(settings: GeneratorSettings, sec: Section, bar: int) -> str:
    family = bass_pattern_family(settings)
    r = random.Random(settings.seed + sec.start_bar * 193 + sum(ord(c) for c in sec.name) * 17)
    if _style_hint(settings) == "psytrance":
        return "psy_rolling"
    if _style_hint(settings) == "dnb":
        if sec.name in ("B", "Hook"):
            return "dnb_reese" if ((bar - sec.start_bar) // 4) % 2 else "dnb_sub"
        return "dnb_sub"
    if sec.name == "Intro" and r.random() < 0.55:
        return "sparse_roots"
    if sec.name in ("B", "Hook") and r.random() < 0.45:
        variants = ["walking", "syncopated", "broken_octave", "offbeat_pulse"]
        return variants[r.randrange(len(variants))]
    if sec.name == "Outro" and r.random() < 0.55:
        return "sparse_roots"
    # Tiny bar-block variation avoids one mechanical bass groove across the whole song.
    if (bar - sec.start_bar) // 4 % 3 == 2 and family not in ("pedal", "sparse_roots"):
        return "root_fifth"
    return family

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
    if _style_hint(settings) == "psytrance":
        return compose_psytrance_acid_lead(tr, ts, settings, sections, chords, rng)
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


def compose_psytrance_acid_lead(tr: MidiTrack, ts: TrackSettings, settings: GeneratorSettings, sections: Sequence[Section], chords: Sequence[Chord], rng: random.Random) -> int:
    count = 0
    bar_ticks = settings.ticks_per_beat * settings.beats_per_bar
    acid_steps = [0, 7, 12, 7, 3, 7, 10, 7, 0, 7, 12, 15, 14, 12, 10, 7]
    for chord in chords:
        sec = section_for_bar(sections, chord.bar)
        rel = chord.bar - sec.start_bar
        if sec.name == "Intro" or sec.energy < 60:
            continue
        if sec.name == "A" and rel % 8 not in (4, 5, 6, 7):
            continue
        if sec.name == "Outro":
            continue
        base = chord_tones_in_range(chord.symbol, settings.key, settings.mode, 60, 72)[0]
        for step in range(16):
            # Acid lead is present but not constant: gaps create gate movement.
            if sec.name == "B" and step % 4 == 3:
                continue
            if sec.name == "Hook" and step in (7, 15):
                continue
            pitch = nearest_allowed_pitch(base + acid_steps[(step + rel + (settings.seed % 5)) % len(acid_steps)], scale_pcs(settings.key, settings.mode, chord.symbol == "V" and settings.mode == "minor") | {n % 12 for n in chord.notes}, 58, 82)
            tick = chord.bar * bar_ticks + int(step * settings.ticks_per_beat / 4)
            dur = int(settings.ticks_per_beat * (0.18 if step % 2 else 0.24))
            vel = role_velocity(settings, "melody", clamp(ts.volume * 0.52 + sec.energy * 0.08 + (8 if step % 4 == 0 else 0), 38, 72))
            count += add_note(tr, tick, dur, ts.channel, pitch + ts.octave * 12 + ts.transpose, vel, settings, chord, 58, 82)
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
    count = 0
    bar_ticks = settings.ticks_per_beat * settings.beats_per_bar
    for idx, chord in enumerate(chords):
        if not role_active(settings, sections, chord.bar, "bass"):
            continue
        sec = section_for_bar(sections, chord.bar)
        root = 12 * 3 + chord.root + ts.octave * 12 + ts.transpose
        root = nearest_allowed_pitch(root, {chord.root}, 28, 52)
        chord_pcs = {n % 12 for n in chord.notes}
        third_candidates = chord_tones_in_range(chord.symbol, settings.key, settings.mode, 30, 58)
        third = min(third_candidates, key=lambda p: abs(p - (root + 3))) if third_candidates else root + 3
        fifth = nearest_allowed_pitch(root + 7, scale_pcs(settings.key, settings.mode, chord.symbol == "V" and settings.mode == "minor") | chord_pcs, 31, 56)
        octave = nearest_allowed_pitch(root + 12, {chord.root}, 36, 60)
        next_root = root
        if idx + 1 < len(chords):
            next_chord = chords[idx + 1]
            next_root = nearest_allowed_pitch(12 * 3 + next_chord.root + ts.octave * 12 + ts.transpose, {next_chord.root}, 28, 52)
        approach = nearest_allowed_pitch(next_root - 1 if next_root >= root else next_root + 1, scale_pcs(settings.key, settings.mode, chord.symbol == "V" and settings.mode == "minor") | chord_pcs, 28, 58)
        pattern = section_bass_pattern(settings, sec, chord.bar)
        if settings.beats_per_bar == 3:
            pattern_map = {
                "sparse_roots": [(0.0, root, 0.82), (2.0, fifth, 0.48)],
                "root_fifth": [(0.0, root, 0.60), (1.0, fifth, 0.42), (2.0, octave, 0.42)],
                "walking": [(0.0, root, 0.45), (1.0, third, 0.38), (2.0, approach, 0.40)],
                "broken_octave": [(0.0, root, 0.45), (1.5, octave, 0.45), (2.25, fifth, 0.35)],
                "syncopated": [(0.0, root, 0.42), (1.25, fifth, 0.35), (2.15, octave, 0.32)],
                "offbeat_pulse": [(0.5, root, 0.35), (1.5, fifth, 0.35), (2.5, root, 0.30)],
                "pedal": [(0.0, root, 1.25)],
                "tango_like": [(0.0, root, 0.65), (1.5, fifth, 0.38), (2.25, octave, 0.32)],
                "psy_rolling": [(0.25, root, 0.18), (0.5, root, 0.18), (0.75, octave, 0.16), (1.25, root, 0.18), (1.5, root, 0.18), (1.75, fifth, 0.16), (2.25, root, 0.18), (2.5, root, 0.18), (2.75, octave, 0.16)],
                "dnb_sub": [(0.0, root, 0.35), (1.5, root, 0.28), (2.0, fifth, 0.30)],
                "dnb_reese": [(0.0, root, 0.60), (1.5, fifth, 0.28), (2.5, root, 0.34)],
            }
        else:
            pattern_map = {
                "sparse_roots": [(0.0, root, 0.85), (2.0, fifth, 0.55)],
                "root_fifth": [(0.0, root, 0.58), (1.0, fifth, 0.36), (2.0, root, 0.46), (3.0, octave, 0.34)],
                "walking": [(0.0, root, 0.40), (1.0, third, 0.34), (2.0, fifth, 0.36), (3.0, approach, 0.34)],
                "broken_octave": [(0.0, root, 0.42), (0.75, octave, 0.32), (2.0, fifth, 0.42), (3.0, octave, 0.30)],
                "syncopated": [(0.0, root, 0.38), (1.25, fifth, 0.34), (2.5, octave, 0.32), (3.25, fifth, 0.28)],
                "offbeat_pulse": [(0.5, root, 0.32), (1.5, root, 0.32), (2.5, fifth, 0.32), (3.5, root, 0.28)],
                "pedal": [(0.0, root, 1.4), (2.0, root, 1.1)],
                "tango_like": [(0.0, root, 0.58), (1.5, fifth, 0.42), (2.0, root, 0.48), (3.0, octave, 0.38)],
                "psy_rolling": [(0.25, root, 0.18), (0.5, root, 0.18), (0.75, octave, 0.16), (1.25, root, 0.18), (1.5, root, 0.18), (1.75, fifth, 0.16), (2.25, root, 0.18), (2.5, root, 0.18), (2.75, octave, 0.16), (3.25, root, 0.18), (3.5, root, 0.18), (3.75, fifth, 0.16)],
                "dnb_sub": [(0.0, root, 0.35), (0.75, root, 0.22), (1.5, fifth, 0.28), (2.0, root, 0.30), (2.75, approach, 0.20), (3.5, root, 0.24)],
                "dnb_reese": [(0.0, root, 0.55), (1.25, fifth, 0.28), (1.75, octave, 0.22), (2.5, root, 0.35), (3.25, approach, 0.22)],
            }
        pat = pattern_map.get(pattern, pattern_map["root_fifth"])
        if _style_hint(settings) == "psytrance":
            vel = role_velocity(settings, "bass", clamp(ts.volume * 0.72 + sec.energy * 0.15, 52, 94))
        else:
            vel = role_velocity(settings, "bass", clamp(ts.volume * 0.56 + sec.energy * 0.11, 34, 76))
        for off, pitch, dur in pat:
            if off < settings.beats_per_bar:
                count += add_note(tr, chord.bar * bar_ticks + int(off * settings.ticks_per_beat), int(dur * settings.ticks_per_beat), ts.channel, pitch, vel, settings, chord, 28, 58)
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
        style_family = _style_hint(settings)
        if style_family in ("techno", "hardcore") and not pad:
            hits = [0, 2] if sec.name in ("B", "Hook") else [0]
        elif style_family in ("techno", "hardcore") and pad:
            hits = [0] if sec.name in ("B", "Hook") else []
        else:
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
        style_family = _style_hint(settings)
        hard = bool(getattr(settings, "prompt_hard_drums", False))
        if style_family == "psytrance":
            if _psy_techno_combo(settings):
                hits=[
                  (0,"kick",base+34),(0,"tom",base+12),(1,"kick",base+30),(1,"tom",base+8),(2,"kick",base+32),(2,"tom",base+10),(3,"kick",base+30),(3,"tom",base+8),
                  (0.25,"closed_hat",base-14),(0.5,"open_hat",base+2),(0.75,"closed_hat",base-18),
                  (1.25,"closed_hat",base-14),(1.5,"open_hat",base+1),(1.75,"closed_hat",base-18),
                  (2.0,"clap",base+10),(2.0,"snare",base+6),(2.25,"closed_hat",base-14),(2.5,"open_hat",base+3),(2.75,"closed_hat",base-18),
                  (3.25,"closed_hat",base-14),(3.5,"open_hat",base+1),(3.75,"closed_hat",base-18)]
                if sec.name in ("A", "B", "Hook"):
                    hits += [(0,"ride",base-18),(1,"ride",base-20),(2,"ride",base-18),(3,"ride",base-20)]
                if sec.name in ("B", "Hook"):
                    hits += [(0.5,"clap",base-10),(1.5,"clap",base-10),(3.5,"ride",base-8)]
            else:
                hits=[(0,"kick",base+22),(1,"kick",base+18),(2,"kick",base+20),(3,"kick",base+18),
                      (0.5,"closed_hat",base-6),(0.75,"closed_hat",base-16),(1.5,"closed_hat",base-5),(1.75,"closed_hat",base-16),
                      (2.5,"closed_hat",base-5),(2.75,"closed_hat",base-16),(3.5,"closed_hat",base-4),(3.75,"closed_hat",base-16),
                      (2,"clap",base+4)]
                if sec.name in ("B", "Hook"):
                    hits += [(1,"open_hat",base-5),(3,"open_hat",base-5),(3.5,"ride",base-14)]
        elif style_family in ("techno", "hardcore"):
            hits=[(0,"kick",base+16),(1,"kick",base+10),(2,"kick",base+14),(3,"kick",base+10),
                  (0.5,"closed_hat",base-10),(1.5,"closed_hat",base-8),(2.5,"closed_hat",base-10),(3.5,"closed_hat",base-8),
                  (2,"clap",base+2)]
            if sec.name in ("B", "Hook"):
                hits += [(1,"open_hat",base-8),(3,"open_hat",base-8),(3.5,"ride",base-18)]
            if hard:
                hits += [(0.75,"closed_hat",base-16),(1.75,"closed_hat",base-16),(2.75,"closed_hat",base-16),(3.75,"closed_hat",base-16)]
        elif style_family == "dnb":
            hits=[(0.0,"kick",base+18),(0.75,"kick",base-4),(1.5,"snare",base+22),(2.0,"kick",base+4),(2.75,"kick",base-6),(3.0,"snare",base+16),
                  (0.25,"closed_hat",base-18),(0.5,"closed_hat",base-14),(1.0,"closed_hat",base-20),(1.25,"closed_hat",base-18),
                  (1.75,"closed_hat",base-16),(2.25,"closed_hat",base-18),(2.5,"open_hat",base-10),(3.25,"closed_hat",base-18),(3.5,"closed_hat",base-16)]
            if sec.name in ("B", "Hook"):
                hits += [(0.5,"snare",base-10),(2.5,"snare",base-12),(3.5,"ride",base-16)]
        else:
            hits=[(0,"kick",base+8),(2,"snare",base),(1,"closed_hat",base-24),(3,"closed_hat",base-24)]
            if _style_hint(settings) in ("house", "trance") or "house" in settings.preset_name.lower() or "drive" in settings.preset_name.lower():
                hits += [(1,"kick",base-6),(3,"kick",base-6)]
        if bar == sec.start_bar+sec.bars-1:
            hits += [(3.5,"snare",base+6)]
        for off,name,vel in hits:
            if off < settings.beats_per_bar:
                tr.note(bar*bar_ticks+int(off*settings.ticks_per_beat), max(1,settings.ticks_per_beat//12), 9, DRUM_NOTES[name], int(clamp(vel,24,124 if _psy_techno_combo(settings) else 104))); count+=1
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
                    # v0.7.0 default is conservative: melody notes are chord-tonal on
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
                    vel = clamp(e.data[2] - density_penalty, 28, 92 if _style_hint(settings) == "psytrance" else 76)
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
    parse_prompt = bool(getattr(settings, "prompt_mode", True))
    direct_style_hint = str(getattr(settings, "direct_style_hint", "") or "").strip()
    use_direct_style_hint = (not parse_prompt) and direct_style_hint and not direct_style_hint.lower().startswith("auto")
    if parse_prompt or use_direct_style_hint:
        try:
            from .prompt_parser import apply_prompt_to_settings
            manual_before_prompt = settings.to_dict()
            parser_text = getattr(settings, "prompt", "") if parse_prompt else direct_style_hint
            apply_prompt_to_settings(settings, parser_text, getattr(settings, "prompt_language", "English"))
            if use_direct_style_hint:
                # In direct-parameter view, the style pulldown is a style/drum/instrument hint.
                # It may choose family, drums, instruments and tempo, but explicit manual fields
                # such as key/mode/progression/template/custom progression remain authoritative.
                settings.prompt_mode = False
                settings.direct_style_hint = direct_style_hint
                settings.prompt = manual_before_prompt.get("prompt", "")
                for always in ["title", "seed", "randomize_seed", "bars", "ticks_per_beat", "section_count",
                               "melody_coverage", "export_json", "export_chord_sheet", "use_rating_memory",
                               "allow_dissonance", "lfo_expression", "add_markers"]:
                    if always in manual_before_prompt:
                        setattr(settings, always, manual_before_prompt[always])
                # Preserve explicit overrides, but let Auto fields stay style-aware.
                if str(manual_before_prompt.get("key", "Auto")).lower() != "auto":
                    settings.key = manual_before_prompt["key"]
                if str(manual_before_prompt.get("mode", "auto")).lower() != "auto":
                    settings.mode = manual_before_prompt["mode"]
                if not str(manual_before_prompt.get("progression", "Auto")).lower().startswith("auto"):
                    settings.progression = manual_before_prompt["progression"]
                if str(manual_before_prompt.get("custom_progression", "")).strip():
                    settings.custom_progression = manual_before_prompt["custom_progression"]
                if str(manual_before_prompt.get("melody_template", "auto")).lower() != "auto":
                    settings.melody_template = manual_before_prompt["melody_template"]
                interp = getattr(settings, "prompt_interpretation", "") or "style hint"
                settings.prompt_interpretation = f"direct_style_hint={direct_style_hint}; " + interp
            rng=random.Random(settings.seed)
        except Exception as exc:
            settings.prompt_interpretation = f"Prompt/style parser warning: {type(exc).__name__}: {exc}"
    resolve_auto_settings(settings, rng)
    sanitize_mode_progression(settings)
    settings.bpm = clamp(settings.bpm, 48, 220); settings.bars=clamp(settings.bars, 16, 256); settings.beats_per_bar=clamp(settings.beats_per_bar,3,4)
    title = generate_title(settings.seed, settings.preset_name) if settings.randomize_seed or not settings.title.strip() else settings.title.strip()
    settings.title = title
    out=Path(output_dir); out.mkdir(parents=True, exist_ok=True)
    sections=build_sections(settings); chords=build_chords(settings, sections)
    tracks=[]; active_tracks=[]; note_count=0
    melody_seen = 0
    for track_index, t in enumerate(settings.tracks):
        if not t.enabled: continue
        role = (t.role or "").lower()
        forced_role = None
        if role == "melody" and melody_seen > 0:
            forced_role = "counter"
        effective = effective_track_for_generation(settings, t, track_index, forced_role)
        tr = setup_track(effective)
        if effective.role == "drum": note_count += compose_drums(tr,effective,settings,sections)
        elif effective.role == "bass": note_count += compose_bass(tr,effective,settings,sections,chords)
        elif effective.role == "melody":
            note_count += compose_melody(tr,effective,settings,sections,chords,rng)
            melody_seen += 1
        elif effective.role == "counter":
            note_count += compose_counter_melody(tr,effective,settings,sections,chords,max(1, melody_seen))
            melody_seen += 1
        elif effective.role == "chord": note_count += compose_chords(tr,effective,settings,sections,chords,False)
        elif effective.role == "pad": note_count += compose_chords(tr,effective,settings,sections,chords,True)
        tracks.append(tr); active_tracks.append(effective)
    quality_pass(tracks, active_tracks, settings, chords)
    note_count=sum(1 for tr in tracks for e in tr.events if len(e.data)>=3 and (e.data[0]&0xF0)==0x90 and e.data[2]>0)
    output_stem, midi, js, chord_path = unique_output_paths(out, title, settings.seed)
    markers=[(s.start_bar*settings.beats_per_bar*settings.ticks_per_beat,s.name) for s in sections] if settings.add_markers else []
    write_midi(str(midi), tracks, settings.ticks_per_beat, settings.bpm, settings.beats_per_bar, title, markers)
    sheet=make_chord_sheet(title, settings, sections, chords, note_count)
    if settings.export_chord_sheet: chord_path.write_text(sheet,encoding='utf-8')
    if settings.export_json:
        payload={"application":"PythonSoundHelix","version":APP_VERSION,"engine":ENGINE_NAME,"title":title,"seed":settings.seed,"output_stem":output_stem,"midi_path":str(midi),"note_count":note_count,"arrangement_profile":arrangement_profile(settings),"bass_pattern_family":bass_pattern_family(settings),"prompt":getattr(settings,"prompt", ""),"prompt_interpretation":getattr(settings,"prompt_interpretation", ""),"direct_style_hint":getattr(settings,"direct_style_hint", ""),"prompt_style_id":getattr(settings,"prompt_style_id", ""),"prompt_style_name":getattr(settings,"prompt_style_name", ""),"prompt_style_family":_style_hint(settings),"prompt_style_blend":_style_blend(settings),"prompt_relation_profile":getattr(settings,"prompt_relation_profile", ""),"prompt_semantic_tags":getattr(settings,"prompt_semantic_tags", []),"prompt_style_confidence":getattr(settings,"prompt_style_confidence", 0),"prompt_hard_drums":getattr(settings,"prompt_hard_drums", False),"prompt_reference_name":getattr(settings,"prompt_reference_name", ""),"prompt_reference_type":getattr(settings,"prompt_reference_type", ""),"prompt_reference_traits":getattr(settings,"prompt_reference_traits", ""),"effective_tracks":[asdict(t) for t in active_tracks],"settings":settings.to_dict(),"sections":[asdict(s) for s in sections],"chords":[asdict(c) for c in chords]}
        js.write_text(json.dumps(payload,indent=2,ensure_ascii=False),encoding='utf-8')
    return SongResult(title,settings.seed,str(midi),str(js) if settings.export_json else "",str(chord_path) if settings.export_chord_sheet else "",note_count, f"{ENGINE_NAME}: auto phrase plans, seed-specific arrangement entry profile, varied bass pattern family={bass_pattern_family(settings)}, auto-instruments unless locked, reference-aware prompt mapping, strict tonal correction; prompt_interpretation=" + getattr(settings, "prompt_interpretation", "auto") + ".")


def make_chord_sheet(title: str, settings: GeneratorSettings, sections: Sequence[Section], chords: Sequence[Chord], note_count: int) -> str:
    lines=[title,"="*len(title),"",f"Generated by PythonSoundHelix {APP_VERSION} (GPLv3)",f"Engine: {ENGINE_NAME}",f"Preset: {settings.preset_name}",f"Seed: {settings.seed}",f"Prompt: {getattr(settings, 'prompt', '') or 'auto'}",f"Interpretation: {getattr(settings, 'prompt_interpretation', '') or 'auto'}",f"Tempo: {settings.bpm} BPM | Key: {settings.key} {settings.mode} | Bars: {settings.bars}",f"Progression: {settings.progression}",f"Arrangement profile: {arrangement_profile(settings)['style']} | style_family={_style_hint(settings)} | blend={'+'.join(_style_blend(settings)) or 'auto'} | relation={getattr(settings, 'prompt_relation_profile', '') or 'auto'} | focus={arrangement_profile(settings)['focus']} | bass={bass_pattern_family(settings)}",f"Melody coverage: {settings.melody_coverage}% distributed across the whole phrase, not prefix-only",f"Notes: {note_count}","","Sections:"]
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
