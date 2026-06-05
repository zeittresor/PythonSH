# PythonSoundHelix - GPLv3 Python/PyQt6 reimplementation inspired by SoundHelix.
# Original source basis: SoundHelix SVN archive soundhelix-code-r896-trunk, version 0.10u.
# Original project: https://www.soundhelix.com/
# This file is part of PythonSoundHelix and is released under GPLv3.

from __future__ import annotations

import json
import math
import os
import random
import time
from dataclasses import asdict
from pathlib import Path
from typing import Dict, Iterable, List, Optional, Sequence, Tuple

from .audio_render import convert_wav_to_mp3, ffmpeg_available, render_tracks_to_wav
from .midi_writer import MidiTrackData, write_midi
from .models import ChordEvent, GeneratorSettings, SectionEvent, SongResult, TrackSettings
from .song_names import generate_song_name
from .music_theory import (
    DRUM_NOTES,
    clamp,
    degree_pitch,
    key_to_pc,
    midi_note_name,
    nearest_scale_pitch,
    notes_for_chord,
    parse_progression_units,
    safe_filename,
    scale_pitches,
    voice_lead,
)

SECTION_NAMES = ["Intro", "A", "Rise", "Hook", "Break", "Hook 2", "Outro"]
MELODY_TEMPLATES: Dict[str, List[int]] = {
    "auto": [],
    "Popcorn-style original pulse": [0, 0, -2, 0, 3, 0, -2, 0, 0, 0, -2, 0, 5, 3, 0, -2],
    "Popcorn-style recognizable contour": [0, 0, -2, 0, 3, 0, -2, 0, 0, 0, -2, 0, 5, 3, 0, -2],
    "Ode-to-Joy public-domain hint": [2, 2, 3, 4, 4, 3, 2, 1, 0, 0, 1, 2, 2, 1, 1],
    "Fuer-Elise public-domain hint": [4, 3, 4, 3, 4, 1, 3, 2, 0, -2, 0, 1, 2],
    "Canon public-domain hint": [0, 4, 5, 2, 3, 0, 3, 4, 5, 7, 4, 5, 3, 4],
    "Toccata public-domain hint": [0, 7, 5, 3, 2, 0, -2, 0, 2, 3, 5, 7],
    "Original arcade anthem": [0, 0, 4, 7, 4, 2, 0, -1, 0, 2, 4, 2, 0],
    "AlgoMusic tracker pulse": [0, 0, 7, 0, 3, 5, 0, -2, 0, 7, 5, 3, 2, 0, -2, 0],
    "AlgoMusic house chord riff": [0, 2, 3, 2, 0, -2, 0, 2, 5, 3, 2, 0, -2, -4, -2, 0],
    "AlgoMusic random walk": [0, 3, 2, 5, 3, 7, 5, 3, 0, -2, 0, 2, -1, 2, 4, 2],
}

# v0.4.9: contour-based Popcorn-inspired phrase bank. These are deliberately
# not a note-for-note copy of any copyrighted composition; they preserve the
# synthetic pulse, repeated-note contour and minor-key call/answer feel so the
# preset is more recognizable while remaining a newly generated derivative.
POPCORN_CONTOUR_BANK = [
    [0, 0, -2, 0, 3, 0, -2, 0, 0, 0, -2, 0, 5, 3, 0, -2],
    [0, 0, -2, 0, 3, 0, -2, 0, 2, 2, 0, 2, 5, 3, 2, 0],
    [0, 3, 0, -2, 0, 3, 0, -2, 5, 3, 0, -2, 0, -2, -4, -2],
    [0, 0, -2, 0, 3, 0, -2, 0, -2, -2, -4, -2, 0, -2, -4, -5],
]

LEGACY_POPCORN_HARMONY = "+Am/10,G/2,F/2,Am/12,G/2,F/2,Am/2,+C/8,Em/2,D/2,C/12,Em/2,D/2,C/4"


# Screenshot-informed AlgoMusic pattern rows.
# The user supplied screenshots of AlgoMusic's Techno preset showing long rows
# of compact digit/dash melody cells and symbol-based drum cells. The rows below
# are newly written approximations of that structure: digits select chord/scale
# tones, '-' means rest/hold, and drum symbols map to tracker-like percussion.
ALGOMUSIC_DIGIT_PATTERN_BANK = [
    "1---1---1---1---",
    "1-1---1---1-1---",
    "1---2---1---2---",
    "1--2--1--2--112-",
    "1-1---2-1---1---",
    "1---2--1---12-1-",
    "1--2--121--2-12-",
    "1---1---2-11-11-",
    "1---3---1---3---",
    "1-3---1---3-1---",
    "1---3-4-3-2-1---",
    "1---1---4---1---",
    "1-2-3---3-2-1---",
    "1---31--3-1---1-",
    "1-3-1-3-1-3-1-3-",
    "1-2-3-4-1-2-3-4-",
]

ALGOMUSIC_DRUM_SYMBOL_BANK = [
    "----+-----+-----",
    ".---:---.---:---",
    "--^---^---^---^-",
    "*--*--*--*****--",
    "*--*--*--*--***-",
    "---^--+---^--+--",
    "----+-----++-+--",
    ".---:---.--+:-+-",
    "---^--+---^--+X-",
    ".---.---.---.---",
    "---^--+---^--+--",
    "----+-----+++--+",
]

# Activity matrix copied from the original SoundHelix-Popcorn console trace.
# Each character represents one of 36 structural sections; the classic preset
# uses 288 bars, therefore one activity section spans 8 bars.
LEGACY_POPCORN_ACTIVITY = {
    "accomp": "*****-------------*****-------***---",
    "arpeggio": "----------**---**---------******----",
    "base_snare": "--****---****---***-********-******-",
    "bass": "------********---------***----------",
    "chords": "***********-----------------********",
    "clap": "--------**---********-**---*********",
    "hihat": "-----------***********--*******-----",
    "melody": "-**-***----------***-----*****--**--",
    "pad": "-------*********---**********-------",
    "string": "-----**********----------------***--",
}

def _is_legacy_popcorn(settings: GeneratorSettings) -> bool:
    return "popcorn" in (settings.preset_name or "").lower() and "original xml" in (settings.preset_name or "").lower()


def _is_algomusic(settings: GeneratorSettings) -> bool:
    return "algomusic" in (settings.preset_name or "").lower() or "algomusic" in (settings.groove_template or "").lower()


def _seed_variation(settings: GeneratorSettings) -> float:
    return clamp(getattr(settings, "seed_variation_strength", 70), 0, 100) / 100.0


def _track_seed(track: TrackSettings) -> int:
    return sum((idx + 1) * ord(ch) for idx, ch in enumerate((track.name or "") + "|" + (track.pattern or "")))


def _is_popcorn_template(settings: GeneratorSettings) -> bool:
    text = f"{settings.preset_name} {settings.melody_template}".lower()
    return "popcorn" in text


def _seeded_popcorn_phrase(settings: GeneratorSettings, track: TrackSettings, bar: int) -> List[int]:
    # Keep the main phrase anchored every few bars, but let the seed select
    # alternate contour rows so two randomized generations do not collapse into
    # the same melody order.
    depth = _seed_variation(settings)
    phrase_idx = ((settings.seed // 97) + (bar // 2) + _track_seed(track)) % len(POPCORN_CONTOUR_BANK)
    if bar % 8 in (0, 1) and depth < 0.90:
        phrase_idx = 0
    phrase = POPCORN_CONTOUR_BANK[phrase_idx][:]
    if depth > 0.05:
        rng = random.Random(settings.seed + _track_seed(track) * 131 + bar * 8191)
        # Rotate only at phrase boundaries, never per note, to keep a hook-like
        # identity while still changing the generated song for each seed.
        if rng.random() < 0.35 * depth and bar % 4 not in (0, 1):
            rot = rng.choice([0, 0, 2, 4, 8])
            phrase = phrase[rot:] + phrase[:rot]
        for i in range(len(phrase)):
            # Strong beats and the first cell remain stable; weak cells may get
            # a tiny diatonic nudge. This is what makes seed changes audible.
            if i % 4 and rng.random() < 0.16 * depth * (settings.variation / 100.0):
                phrase[i] += rng.choice([-1, 0, 1])
    return phrase


def _seeded_template_degree(settings: GeneratorSettings, track: TrackSettings, bar: int, step: int, motif: Sequence[int]) -> int:
    if not motif:
        return 0
    depth = _seed_variation(settings)
    if _is_popcorn_template(settings):
        phrase = _seeded_popcorn_phrase(settings, track, bar)
        return phrase[step % len(phrase)]
    rng = random.Random(settings.seed + _track_seed(track) * 181 + bar * 4099 + step * 67)
    phase = 0
    if depth > 0.05:
        phase = (settings.seed + _track_seed(track) + (bar // 4) * 3) % max(1, len(motif))
        if rng.random() > depth:
            phase = 0
    degree = motif[(bar * len(motif) + step + phase) % len(motif)]
    if depth > 0.05 and step % 4 and rng.random() < 0.18 * depth * (settings.variation / 100.0):
        degree += rng.choice([-2, -1, 1, 2])
    return degree


def _legacy_activity_key(track: TrackSettings) -> str:
    name = (track.name or "").lower().strip().replace(" ", "_")
    pat = (track.pattern or "").lower().strip().replace(" ", "_")
    role = (track.role or "").lower().strip()
    for key in LEGACY_POPCORN_ACTIVITY:
        if key in name or key in pat:
            return key
    if role == "drum":
        return "base_snare"
    if role == "counter":
        return "accomp"
    return role if role in LEGACY_POPCORN_ACTIVITY else name




def _stable_track_index(settings: GeneratorSettings, track: TrackSettings, bar: int, salt: int = 0) -> int:
    return abs(settings.seed * 131 + bar * 977 + salt * 37 + sum(ord(ch) for ch in (track.name + track.pattern)))


def _algomusic_digit_row(settings: GeneratorSettings, track: TrackSettings, bar: int) -> str:
    return ALGOMUSIC_DIGIT_PATTERN_BANK[_stable_track_index(settings, track, bar, 17) % len(ALGOMUSIC_DIGIT_PATTERN_BANK)]


def _algomusic_drum_row(settings: GeneratorSettings, track: TrackSettings, bar: int) -> str:
    return ALGOMUSIC_DRUM_SYMBOL_BANK[_stable_track_index(settings, track, bar, 29) % len(ALGOMUSIC_DRUM_SYMBOL_BANK)]


def _is_algomusic_digit_pattern(settings: GeneratorSettings, track: TrackSettings) -> bool:
    text = f"{settings.melody_template} {track.pattern} {settings.groove_template}".lower()
    return "digit" in text or "pattern bank" in text or "techno rows" in text


def _is_algomusic_drum_pattern(settings: GeneratorSettings, track: TrackSettings) -> bool:
    text = f"{track.pattern} {settings.groove_template}".lower()
    return "symbol" in text or "techno rows" in text or "algomusic drums" in text

def _bar_ticks(settings: GeneratorSettings) -> int:
    return settings.ticks_per_beat * settings.beats_per_bar


def _step_ticks(settings: GeneratorSettings, division: int = 4) -> int:
    return max(1, settings.ticks_per_beat // max(1, division // 4 if division > 4 else 1))


def _human_tick(rng: random.Random, base_tick: int, amount: int) -> int:
    if amount <= 0:
        return base_tick
    return max(0, base_tick + rng.randint(-amount, amount))


def _velocity(rng: random.Random, base: int, human: int, accent: int = 0) -> int:
    return clamp(base + accent + rng.randint(-human, human), 1, 127)


BASE_ROLE_RANGES: Dict[str, Tuple[int, int]] = {
    # Tuned to avoid the first v0.4.1 test problem: nice motifs, but too many
    # dominant notes in the glassy upper register. The user can still override
    # per-track octave; the guard just folds runaway notes back into a musical lane.
    "bass": (31, 52),
    "chord": (45, 72),
    "pad": (43, 72),
    "arpeggio": (50, 81),
    "melody": (52, 79),
    "counter": (50, 76),
    "texture": (48, 78),
}


def _role_range(settings: GeneratorSettings, track: TrackSettings) -> Tuple[int, int]:
    role = (track.role or "melody").lower().strip()
    low, high = BASE_ROLE_RANGES.get(role, (48, 80))
    if not getattr(settings, "auto_range_guard", True):
        return low + track.octave * 12, high + track.octave * 12
    # Respect the user's octave nudge, but cap melodic/counter voices so the
    # built-in synth and common GM sounds don't become piercing.
    low += track.octave * 7
    high += track.octave * 7
    melodic_cap = clamp(getattr(settings, "max_melody_pitch", 79), 60, 96)
    if role in ("melody", "counter", "arpeggio", "texture"):
        high = min(high, melodic_cap + (2 if role == "arpeggio" else 0))
    if role in ("pad", "chord"):
        high = min(high, melodic_cap - 2)
    if high <= low + 7:
        high = low + 12
    return int(low), int(high)




def _track_transpose(track: TrackSettings) -> int:
    return clamp(getattr(track, "transpose", 0), -24, 24)


def _track_arp_rate(settings: GeneratorSettings, track: TrackSettings) -> float:
    global_rate = clamp(getattr(settings, "global_arpeggio_rate", 100), 25, 240) / 100.0
    local_rate = clamp(getattr(track, "arp_rate", 100), 25, 240) / 100.0
    return max(0.20, min(3.00, global_rate * local_rate))


def _apply_track_pitch(pitch: int, settings: GeneratorSettings, track: TrackSettings, low: int | None = None, high: int | None = None) -> int:
    if (track.role or "").lower().strip() == "drum":
        return clamp(pitch, 0, 127)
    if low is None or high is None:
        low, high = _role_range(settings, track)
    return _fold_pitch(int(pitch) + _track_transpose(track), low, high)


def _fine_tune_pitch_bend_value(track: TrackSettings) -> int:
    # General MIDI devices commonly default to +/-2 semitones pitch-bend range.
    # Therefore 200 cents maps to a full 14-bit bend span from center to edge.
    cents = clamp(getattr(track, "fine_tune_cents", 0), -100, 100)
    return clamp(8192 + round((cents / 200.0) * 8192), 0, 16383)

def _fold_pitch(pitch: int, low: int, high: int) -> int:
    while pitch > high:
        pitch -= 12
    while pitch < low:
        pitch += 12
    return clamp(pitch, max(0, low), min(127, high))


def _fold_notes(notes: Sequence[int], low: int, high: int) -> List[int]:
    return [_fold_pitch(int(n), low, high) for n in notes]


def _swing_offset(step_index: int, step_len: int, swing: int) -> int:
    if swing <= 0:
        return 0
    return int(step_len * (swing / 100.0) * 0.33) if step_index % 2 == 1 else 0


def build_sections(settings: GeneratorSettings) -> List[SectionEvent]:
    count = clamp(settings.section_count, 3, 64)
    bars = max(8, settings.bars)
    base = bars // count
    remainder = bars % count
    sections: List[SectionEvent] = []
    start = 0
    for i in range(count):
        length = base + (1 if i < remainder else 0)
        # Snap to even bars where possible, while preserving total in the last section.
        if i < count - 1 and length > 5 and length % 2:
            length += 1
        if i == count - 1:
            length = bars - start
        name = SECTION_NAMES[i] if i < len(SECTION_NAMES) else f"Section {i + 1}"
        pos = i / max(1, count - 1)
        energy = clamp(28 + 65 * math.sin(pos * math.pi) + (18 if "Hook" in name else 0) - (12 if name == "Break" else 0), 10, 100)
        sections.append(SectionEvent(name=name, start_bar=start, bars=length, energy=energy))
        start += length
        if start >= bars:
            break
    return sections


def section_for_bar(sections: Sequence[SectionEvent], bar: int) -> SectionEvent:
    for section in sections:
        if section.start_bar <= bar < section.start_bar + section.bars:
            return section
    return sections[-1]


def build_chords(settings: GeneratorSettings, sections: Sequence[SectionEvent]) -> List[ChordEvent]:
    key_pc = key_to_pc(settings.key)
    bar_len = _bar_ticks(settings)
    if _is_legacy_popcorn(settings):
        # The Java Popcorn XML uses duration-bearing absolute chords. The Python
        # engine is bar-based, so scale the XML pattern over the full song instead
        # of reducing it to the generic pop I/V/vi/IV-style loop.
        units = parse_progression_units(settings.effective_progression(), 1, max_units_per_token=32, divide_duration_by_four=False)
        total_units = sum(length for _, length in units) or 1
        expanded = []
        used = 0
        for idx, (sym, length) in enumerate(units):
            if idx == len(units) - 1:
                bars_for = max(1, settings.bars - used)
            else:
                bars_for = max(1, round(settings.bars * length / total_units))
                used += bars_for
            expanded.extend([sym] * bars_for)
        expanded = expanded[:settings.bars] or ["Am"]
    else:
        units = parse_progression_units(settings.effective_progression(), max(1, settings.harmonic_rhythm))
        expanded: List[str] = []
        for sym, length in units:
            expanded.extend([sym] * max(1, length * max(1, settings.harmonic_rhythm)))
        if not expanded:
            expanded = ["I"]
    chords: List[ChordEvent] = []
    for bar in range(settings.bars):
        symbol = expanded[bar % len(expanded)]
        section = section_for_bar(sections, bar)
        chord_notes = notes_for_chord(symbol, key_pc, settings.mode, octave=4)
        chords.append(ChordEvent(bar=bar, tick=bar * bar_len, symbol=symbol, root=chord_notes[0] % 12, notes=chord_notes, section=section.name))
    return chords


def _is_active(rng: random.Random, settings: GeneratorSettings, track: TrackSettings, section: SectionEvent, bar: int) -> bool:
    if not track.enabled:
        return False
    if track.mute_in_intro and section.name == "Intro":
        return False
    if _is_legacy_popcorn(settings):
        key = _legacy_activity_key(track)
        matrix = LEGACY_POPCORN_ACTIVITY.get(key)
        if matrix:
            section_idx = min(len(matrix) - 1, max(0, int(bar * len(matrix) / max(1, settings.bars))))
            return matrix[section_idx] == "*"
    probability = (track.activity * 0.55 + section.energy * 0.35 + settings.complexity * 0.10)
    if section.name == "Break" and track.role in ("drum", "bass"):
        probability -= 20
    if "Hook" in section.name and track.role in ("melody", "arpeggio", "chord"):
        probability += 12
    if track.role == "pad":
        probability += 10
    # Stable pseudo-random activity per track/bar, SoundHelix-style but GUI friendly.
    return rng.randint(0, 100) < clamp(probability, 0, 100)


def _setup_track(track: TrackSettings) -> MidiTrackData:
    data = MidiTrackData(track.name)
    data.add_program(0, track.channel, track.program)
    data.add_cc(0, track.channel, 7, track.volume)
    data.add_cc(0, track.channel, 10, track.pan)
    data.add_cc(0, track.channel, 91, 18 if track.role in ("pad", "texture") else 8)
    data.add_cc(0, track.channel, 93, 10 if track.role in ("melody", "arpeggio", "texture") else 2)
    if track.channel != 9 and getattr(track, "fine_tune_cents", 0):
        data.add_pitch_bend(0, track.channel, _fine_tune_pitch_bend_value(track))
    return data


def _add_lfo(track_data: MidiTrackData, settings: GeneratorSettings, track: TrackSettings, end_tick: int) -> None:
    if not settings.lfo_expression or track.channel == 9:
        return
    period = _bar_ticks(settings) * 8
    step = max(settings.ticks_per_beat, period // 16)
    for tick in range(0, end_tick, step):
        value = 74 + int(18 * math.sin((tick / max(1, period)) * math.tau + track.channel))
        track_data.add_cc(tick, track.channel, 11, clamp(value, 25, 127))


def _motif(settings: GeneratorSettings, rng: random.Random) -> List[int]:
    template = MELODY_TEMPLATES.get(settings.melody_template or "auto", [])
    if template:
        return template[:]
    length = 8 + (settings.complexity // 20) * 2
    degrees = [0]
    algomusic = _is_algomusic(settings)
    for _ in range(length - 1):
        if algomusic and rng.randint(0, 100) < settings.variation:
            # AlgoMusic-inspired behavior: a tracker-like seeded random walk that
            # occasionally snaps back to the home degree instead of freely wandering.
            move = rng.choice([-3, -2, -1, 0, 1, 2, 3, 5])
            degrees.append(0 if rng.random() < 0.18 else degrees[-1] + move)
        elif rng.randint(0, 100) < settings.motif_memory and degrees:
            move = rng.choice([-2, -1, 0, 1, 2, 3])
            degrees.append(degrees[-1] + move)
        else:
            degrees.append(rng.randint(-2, 7))
    return degrees


def _add_drum_bar(rng: random.Random, data: MidiTrackData, settings: GeneratorSettings, track: TrackSettings, bar: int, section: SectionEvent, total_bars: int) -> int:
    bar_len = _bar_ticks(settings)
    start = bar * bar_len
    beat = settings.ticks_per_beat
    sixteenth = beat // 4
    notes = 0
    energy = (section.energy + track.density + settings.complexity) / 3
    pattern = (track.pattern or "auto").lower()

    only_clap = "clap" in pattern and "base" not in pattern
    only_hihat = "hihat" in pattern or "hat" in pattern
    only_base_snare = "base_snare" in pattern or "base snare" in pattern
    is_amiga = "amiga" in pattern or "tracker" in pattern

    if _is_algomusic_drum_pattern(settings, track):
        row = _algomusic_drum_row(settings, track, bar)
        cell_len = max(1, bar_len // max(1, len(row)))
        for idx, symbol in enumerate(row):
            tick = start + idx * cell_len + _swing_offset(idx, cell_len, settings.swing)
            dur = max(1, int(cell_len * 0.55))
            sym = symbol.lower()
            if sym == "+":
                data.add_note(_human_tick(rng, tick, settings.humanize_ticks), dur, 9, DRUM_NOTES["kick"], _velocity(rng, 88, settings.humanize_velocity, 10 if idx % 4 == 0 else 0)); notes += 1
            elif sym == "^":
                data.add_note(_human_tick(rng, tick, settings.humanize_ticks), dur, 9, DRUM_NOTES["snare"], _velocity(rng, 82, settings.humanize_velocity, 6)); notes += 1
            elif sym == "*":
                data.add_note(_human_tick(rng, tick, settings.humanize_ticks), dur, 9, DRUM_NOTES["closed_hat"], _velocity(rng, 62, settings.humanize_velocity, 5 if idx % 4 == 0 else -5)); notes += 1
            elif sym == ".":
                data.add_note(_human_tick(rng, tick, settings.humanize_ticks), dur, 9, DRUM_NOTES["closed_hat"], _velocity(rng, 44, settings.humanize_velocity, -10)); notes += 1
            elif sym == ":":
                data.add_note(_human_tick(rng, tick, settings.humanize_ticks), dur, 9, DRUM_NOTES["rim"], _velocity(rng, 54, settings.humanize_velocity, -4)); notes += 1
            elif sym == "x":
                for drum, base_vel in (("kick", 92), ("snare", 88), ("crash", 82)):
                    data.add_note(_human_tick(rng, tick, settings.humanize_ticks), dur, 9, DRUM_NOTES[drum], _velocity(rng, base_vel, settings.humanize_velocity, 8)); notes += 1
        return notes

    # Kicks
    if not only_clap and not only_hihat:
        kick_steps = [0, 8] if "four" not in pattern else [0, 4, 8, 12]
        if is_amiga and "four" in pattern:
            kick_steps = [0, 4, 8, 12, 14 if rng.random() < 0.35 else 10]
        if energy > 55 and "break" not in pattern:
            kick_steps += [6 if rng.random() < 0.45 else 10]
        if "broken" in pattern:
            kick_steps = [0, 3, 8, 11]
        for step in sorted(set(kick_steps)):
            vel = _velocity(rng, 88, settings.humanize_velocity, 12 if step == 0 else 0)
            data.add_note(_human_tick(rng, start + step * sixteenth, settings.humanize_ticks), max(1, sixteenth // 2), 9, DRUM_NOTES["kick"], vel)
            notes += 1

    # Snare / clap on 2 and 4
    if not only_hihat:
        for step in [4, 12]:
            snare = DRUM_NOTES["clap"] if only_clap or "electro" in pattern or energy > 72 else DRUM_NOTES["snare"]
            data.add_note(_human_tick(rng, start + step * sixteenth, settings.humanize_ticks), max(1, sixteenth // 2), 9, snare, _velocity(rng, 82, settings.humanize_velocity, 8))
            notes += 1

    # Hats
    if not only_clap and not only_base_snare:
        hat_rate = 1 if "tracker hats" in pattern else (2 if energy > 58 else 4)
        for step in range(0, 16, hat_rate):
            if rng.randint(0, 100) <= track.density:
                hat = DRUM_NOTES["open_hat"] if step % 8 == 6 and rng.random() < (0.45 if is_amiga else 0.35) else DRUM_NOTES["closed_hat"]
                accent = 10 if step % 4 == 0 else (-7 if is_amiga and step % 2 else -4)
                tick = start + step * sixteenth + _swing_offset(step, sixteenth, settings.swing)
                data.add_note(_human_tick(rng, tick, settings.humanize_ticks), max(1, sixteenth // 2), 9, hat, _velocity(rng, 58, settings.humanize_velocity, accent))
                notes += 1

    # Fills near section boundaries.
    boundary = (bar + 1 == section.start_bar + section.bars) or (track.fill_every and (bar + 1) % track.fill_every == 0)
    if boundary and section.name != "Intro" and rng.randint(0, 100) < track.complexity:
        fill_notes = [DRUM_NOTES["low_tom"], DRUM_NOTES["mid_tom"], DRUM_NOTES["high_tom"], DRUM_NOTES["snare"]]
        for i, note in enumerate(fill_notes):
            tick = start + bar_len - beat + i * (beat // 4)
            data.add_note(_human_tick(rng, tick, settings.humanize_ticks), max(10, beat // 5), 9, note, _velocity(rng, 78, settings.humanize_velocity, i * 4))
            notes += 1
        if bar + 1 < total_bars:
            data.add_note(start + bar_len - beat // 8, beat // 4, 9, DRUM_NOTES["crash"], _velocity(rng, 92, settings.humanize_velocity, 10))
            notes += 1
    return notes


def _chord_notes_for_bar(chords: Sequence[ChordEvent], bar: int) -> List[int]:
    return chords[min(bar, len(chords) - 1)].notes


def _add_bass_bar(rng: random.Random, data: MidiTrackData, settings: GeneratorSettings, track: TrackSettings, bar: int, section: SectionEvent, chord: ChordEvent) -> int:
    bar_len = _bar_ticks(settings)
    start = bar * bar_len
    beat = settings.ticks_per_beat
    root = chord.notes[0] % 12
    base = 36 + root + 12 * track.octave
    if base < 30:
        base += 12
    if base > 55:
        base -= 12
    pattern = (track.pattern or "auto").lower()
    sixteenth = max(1, beat // 4)
    steps = [0, 2, 4, 6] if "eighth" in pattern else [0, 4, 8, 12]
    if "sync" in pattern or settings.variation > 55:
        steps = [0, 3, 6, 8, 11, 14]
    if "acid" in pattern or "tracker" in pattern:
        steps = [0, 3, 4, 7, 8, 10, 12, 15]
        if settings.variation > 75:
            steps += [rng.choice([1, 5, 13])]
    if settings.keep_bass_on_roots:
        candidates = [base, base + 12, base + 7]
    else:
        candidates = [base + i for i in [0, 3, 5, 7, 10, 12]]
    if "acid" in pattern or "tracker" in pattern:
        candidates = [base, base + 7, base + 12, base + 10, base + 3, base + 5]
    notes = 0
    for i, step in enumerate(steps):
        if rng.randint(0, 100) > track.density + section.energy // 4:
            continue
        low, high = _role_range(settings, track)
        pitch = _apply_track_pitch(candidates[i % len(candidates)], settings, track, low, high)
        duration = int(sixteenth * (0.95 if ("acid" in pattern or "tracker" in pattern) else (2.8 if len(steps) <= 4 else 1.6)))
        tick = start + step * sixteenth + _swing_offset(step, sixteenth, settings.swing)
        data.add_note(_human_tick(rng, tick, settings.humanize_ticks), duration, track.channel, pitch, _velocity(rng, track.volume, settings.humanize_velocity, 12 if step == 0 else 0))
        notes += 1
    return notes


def _add_chord_bar(rng: random.Random, data: MidiTrackData, settings: GeneratorSettings, track: TrackSettings, bar: int, section: SectionEvent, chord_notes: Sequence[int], previous_voicing: Sequence[int] | None) -> Tuple[int, List[int]]:
    bar_len = _bar_ticks(settings)
    start = bar * bar_len
    beat = settings.ticks_per_beat
    low, high = _role_range(settings, track)
    voicing = voice_lead([n + track.octave * 12 + _track_transpose(track) for n in chord_notes], previous_voicing, low=low, high=high)
    voicing = _fold_notes(voicing, low, high)
    pattern = (track.pattern or "auto").lower()
    notes = 0
    if "guitar" in pattern:
        offsets = [0, beat // 3, beat * 2 // 3, beat, beat + beat // 2, beat * 2 + beat // 3]
        for i, off in enumerate(offsets):
            if rng.randint(0, 100) > track.density:
                continue
            pitch = voicing[i % len(voicing)]
            data.add_note(_human_tick(rng, start + off, settings.humanize_ticks), beat // 2, track.channel, pitch, _velocity(rng, track.volume - 8, settings.humanize_velocity, 8 if i == 0 else 0))
            notes += 1
    elif "gate" in pattern:
        gate_steps = 8 if settings.complexity < 72 else 16
        gate_len = max(1, bar_len // gate_steps)
        for step in range(gate_steps):
            # Pseudo-random gate cells, stable per seed/bar but still algorithmic.
            if rng.randint(0, 100) > track.density + (12 if step % 4 == 0 else -8):
                continue
            for pitch in voicing:
                data.add_note(_human_tick(rng, start + step * gate_len, settings.humanize_ticks), max(1, int(gate_len * 0.58)), track.channel, pitch, _velocity(rng, track.volume - 8, settings.humanize_velocity, 8 if step % 4 == 0 else -6))
                notes += 1
    elif "stab" in pattern:
        for off in [0, beat * 2, beat * 3 + beat // 2]:
            for pitch in voicing:
                data.add_note(_human_tick(rng, start + off, settings.humanize_ticks), beat // 2, track.channel, pitch, _velocity(rng, track.volume - 4, settings.humanize_velocity, 10 if off == 0 else 0))
                notes += 1
    else:
        reps = 2 if section.energy < 55 else 4
        for rep in range(reps):
            off = rep * (bar_len // reps)
            if rng.randint(0, 100) > track.density + 10:
                continue
            for pitch in voicing:
                data.add_note(_human_tick(rng, start + off, settings.humanize_ticks), int(bar_len / reps * 0.80), track.channel, pitch, _velocity(rng, track.volume - 10, settings.humanize_velocity, 8 if rep == 0 else 0))
                notes += 1
    return notes, voicing


def _add_pad_bar(rng: random.Random, data: MidiTrackData, settings: GeneratorSettings, track: TrackSettings, bar: int, section: SectionEvent, chord_notes: Sequence[int], previous_voicing: Sequence[int] | None) -> Tuple[int, List[int]]:
    if bar % max(1, settings.harmonic_rhythm) != 0 and previous_voicing:
        return 0, list(previous_voicing)
    bar_len = _bar_ticks(settings)
    start = bar * bar_len
    low, high = _role_range(settings, track)
    voicing = voice_lead([n + 12 + track.octave * 12 + _track_transpose(track) for n in chord_notes], previous_voicing, low=low, high=high)
    voicing = _fold_notes(voicing, low, high)
    length = bar_len * max(1, settings.harmonic_rhythm) - settings.ticks_per_beat // 8
    notes = 0
    for pitch in voicing:
        data.add_note(_human_tick(rng, start, settings.humanize_ticks // 2), length, track.channel, pitch, _velocity(rng, min(track.volume, 82), settings.humanize_velocity, -12))
        notes += 1
    return notes, voicing


def _add_arpeggio_bar(rng: random.Random, data: MidiTrackData, settings: GeneratorSettings, track: TrackSettings, bar: int, section: SectionEvent, chord_notes: Sequence[int]) -> int:
    bar_len = _bar_ticks(settings)
    start = bar * bar_len
    beat = settings.ticks_per_beat
    sixteenth = beat // 4
    low, high = _role_range(settings, track)
    pcs = voice_lead([n + 12 + track.octave * 12 + _track_transpose(track) for n in chord_notes], None, low=low, high=high)
    pcs = _fold_notes(pcs, low, high)
    if len(pcs) < 3:
        pcs = list(pcs) + [pcs[0] + 12]
    pattern = (track.pattern or "auto").lower()
    order = list(range(len(pcs)))
    if "tracker" in pattern:
        rotate = bar % max(1, len(pcs))
        order = order[rotate:] + order[:rotate]
        if bar % 2:
            order = list(reversed(order))
    elif "down" in pattern:
        order = list(reversed(order))
    elif "updown" in pattern:
        order = list(range(len(pcs))) + list(reversed(range(1, len(pcs) - 1)))
    # v0.4.9: seed must influence not only title/humanization but also row order.
    # Keep it phrase-level so arps remain musical instead of random noise.
    depth = _seed_variation(settings)
    if order and depth > 0.05:
        vrng = random.Random(settings.seed + _track_seed(track) * 251 + bar * 613)
        if vrng.random() < 0.55 * depth:
            rot = vrng.randrange(len(order))
            order = order[rot:] + order[:rot]
        if vrng.random() < 0.25 * depth and "updown" not in pattern:
            order = list(reversed(order))
    notes = 0
    base_steps = 16 if ("tracker" in pattern or section.energy > 48 or settings.complexity > 55) else 8
    rate = _track_arp_rate(settings, track)
    if depth > 0.05 and settings.variation > 25:
        vrng = random.Random(settings.seed + _track_seed(track) * 263 + bar * 719)
        rate *= vrng.choice([0.75, 0.875, 1.0, 1.0, 1.125, 1.25])
    steps = clamp(round(base_steps * rate), 2, 64)
    for step in range(int(steps)):
        if rng.randint(0, 100) > track.density + settings.complexity // 5:
            continue
        pitch = pcs[order[step % len(order)]] + (12 if step >= 8 and rng.random() < (settings.variation / (120 if "tracker" in pattern else 180)) else 0)
        pitch = _fold_pitch(pitch, low, high)
        dur = int((bar_len / steps) * 0.78)
        tick = start + int(step * bar_len / steps) + _swing_offset(step, sixteenth, settings.swing)
        data.add_note(_human_tick(rng, tick, settings.humanize_ticks), dur, track.channel, pitch, _velocity(rng, track.volume - 6, settings.humanize_velocity, 8 if step % 4 == 0 else 0))
        notes += 1
    return notes


def _add_melody_bar(rng: random.Random, data: MidiTrackData, settings: GeneratorSettings, track: TrackSettings, bar: int, section: SectionEvent, chord: ChordEvent, motif: Sequence[int]) -> int:
    bar_len = _bar_ticks(settings)
    start = bar * bar_len
    beat = settings.ticks_per_beat
    key_pc = key_to_pc(settings.key)
    low, high = _role_range(settings, track)
    template_name = settings.melody_template or "auto"
    # Known/public-domain inspired motifs are made more recognizable by using the template more directly.
    # AlgoMusic-inspired templates keep the recognizable seed but add more stochastic gates.
    direct_template = template_name != "auto"
    algomusic_template = "algomusic" in template_name.lower()
    density = track.density + (18 if "Hook" in section.name else 0) - (20 if section.name == "Intro" else 0)
    step_count = 8 if settings.complexity < 70 else 16
    step_len = bar_len // step_count
    notes = 0
    last_pitch = None
    if _is_algomusic_digit_pattern(settings, track):
        row = _algomusic_digit_row(settings, track, bar)
        step_count = max(8, min(32, len(row)))
        step_len = max(1, bar_len // step_count)
        tone_bank = voice_lead([n + track.octave * 12 + _track_transpose(track) for n in chord.notes] + [chord.notes[0] + 12 + track.octave * 12 + _track_transpose(track)], None, low=low, high=high)
        tone_bank = _fold_notes(tone_bank, low, high)
        for step in range(step_count):
            symbol = row[step % len(row)]
            if symbol not in "1234":
                continue
            if rng.randint(0, 100) > density + (10 if step % 4 == 0 else 0):
                continue
            pitch = tone_bank[(int(symbol) - 1) % len(tone_bank)]
            if last_pitch is not None and abs(pitch - last_pitch) > 12 and rng.randint(0, 100) < settings.motif_memory:
                pitch = pitch - 12 if pitch > last_pitch else pitch + 12
            pitch = _fold_pitch(pitch, low, high)
            tick = start + step * step_len + _swing_offset(step, step_len, settings.swing)
            duration = max(1, int(step_len * rng.choice([0.55, 0.75, 0.95])))
            data.add_note(_human_tick(rng, tick, settings.humanize_ticks), duration, track.channel, pitch, _velocity(rng, track.volume, settings.humanize_velocity, 10 if step % 4 == 0 else -2))
            last_pitch = pitch
            notes += 1
        return notes

    for step in range(step_count):
        if not direct_template and rng.randint(0, 100) > density:
            continue
        if direct_template and step >= len(motif) and rng.randint(0, 100) > density:
            continue
        if algomusic_template and step % 4 not in (0, 2) and rng.randint(0, 100) > density + settings.variation // 3:
            continue
        if direct_template:
            degree = _seeded_template_degree(settings, track, bar, step, motif)
        else:
            degree = motif[(bar * step_count + step) % len(motif)] if motif else rng.randint(0, 7)
        pitch = degree_pitch(degree, key_pc, settings.mode, 4 + track.octave)
        # Auto-melodies benefit from chord snapping. Template hooks should keep
        # their contour; otherwise recognizable presets become generic chord
        # tones and different seeds sound almost identical.
        if not direct_template and step % 4 == 0:
            candidates = _fold_notes([n + track.octave * 12 for n in chord.notes], low, high)
            pitch = min(candidates, key=lambda p: abs(pitch - p))
        else:
            pitch = nearest_scale_pitch(pitch, key_pc, settings.mode, low, high)
            pitch = _fold_pitch(pitch, low, high)
        if last_pitch is not None and abs(pitch - last_pitch) > 12 and rng.randint(0, 100) < settings.motif_memory:
            pitch = pitch - 12 if pitch > last_pitch else pitch + 12
        pitch = _apply_track_pitch(pitch, settings, track, low, high)
        duration = int(step_len * (rng.choice([0.45, 0.62, 0.82]) if algomusic_template else rng.choice([0.75, 0.9, 1.4 if step_count == 8 else 1.0])))
        tick = start + step * step_len + _swing_offset(step, step_len, settings.swing)
        data.add_note(_human_tick(rng, tick, settings.humanize_ticks), duration, track.channel, pitch, _velocity(rng, track.volume, settings.humanize_velocity, 12 if step % 4 == 0 else 0))
        last_pitch = pitch
        notes += 1
        # Call-and-response echo in upper octave for sparse melody.
        if settings.call_response and step in (2, 6, 10, 14) and rng.randint(0, 100) < settings.variation // 2:
            echo_pitch = nearest_scale_pitch(pitch + rng.choice([-7, -5, 4, 7]), key_pc, settings.mode, low, high)
            echo_pitch = _fold_pitch(echo_pitch, low, high)
            data.add_note(_human_tick(rng, tick + step_len // 2, settings.humanize_ticks), max(1, duration // 2), track.channel, echo_pitch, _velocity(rng, track.volume - 18, settings.humanize_velocity, -4))
            notes += 1
    return notes


def _add_counter_bar(rng: random.Random, data: MidiTrackData, settings: GeneratorSettings, track: TrackSettings, bar: int, section: SectionEvent, chord: ChordEvent) -> int:
    if rng.randint(0, 100) > track.density + settings.variation // 3:
        return 0
    bar_len = _bar_ticks(settings)
    start = bar * bar_len
    beat = settings.ticks_per_beat
    key_pc = key_to_pc(settings.key)
    low, high = _role_range(settings, track)
    candidates = scale_pitches(key_pc, settings.mode, low, high)
    chord_pcs = {n % 12 for n in chord.notes}
    candidates = [p for p in candidates if p % 12 in chord_pcs] or candidates
    notes = 0
    for off in [beat, beat * 3]:
        pitch = rng.choice(candidates)
        pitch = _apply_track_pitch(pitch, settings, track, low, high)
        data.add_note(_human_tick(rng, start + off, settings.humanize_ticks), beat, track.channel, pitch, _velocity(rng, track.volume - 12, settings.humanize_velocity, 0))
        notes += 1
    return notes


def _add_texture_bar(rng: random.Random, data: MidiTrackData, settings: GeneratorSettings, track: TrackSettings, bar: int, section: SectionEvent, chord: ChordEvent) -> int:
    if rng.randint(0, 100) > track.density:
        return 0
    bar_len = _bar_ticks(settings)
    start = bar * bar_len
    beat = settings.ticks_per_beat
    notes = 0
    for i in range(1 + settings.variation // 35):
        low, high = _role_range(settings, track)
        pitch = _apply_track_pitch((chord.notes[i % len(chord.notes)] + 12 + track.octave * 12), settings, track, low, high)
        tick = start + rng.randint(0, max(0, bar_len - beat))
        data.add_note(_human_tick(rng, tick, settings.humanize_ticks * 2), beat * rng.choice([1, 2, 3]), track.channel, pitch, _velocity(rng, min(track.volume, 70), settings.humanize_velocity, -18))
        notes += 1
    return notes




def _count_note_ons(tracks: Sequence[MidiTrackData]) -> int:
    return sum(1 for data in tracks for ev in data.events if ev.kind == "note_on" and ev.b > 0)


def _paired_note_events(data: MidiTrackData):
    """Return paired (note_on, note_off, duration) objects for post-processing."""
    open_notes: Dict[Tuple[int, int], List] = {}
    pairs = []
    for ev in sorted(data.events, key=lambda e: (e.tick, 0 if e.kind == "note_on" and e.b > 0 else 1)):
        if ev.kind == "note_on" and ev.b > 0:
            open_notes.setdefault((ev.channel, ev.a), []).append(ev)
        elif ev.kind in ("note_off", "note_on"):
            key = (ev.channel, ev.a)
            if open_notes.get(key):
                on_ev = open_notes[key].pop(0)
                if ev.tick > on_ev.tick:
                    pairs.append((on_ev, ev, ev.tick - on_ev.tick))
    return pairs


def _smooth_note_bursts(tracks: Sequence[MidiTrackData], settings: GeneratorSettings, track_settings: Sequence[TrackSettings]) -> None:
    """Reduce harsh machine-gun note bursts on tonal tracks.

    This is a post-generation musical hygiene pass. It does not quantize the song;
    it only removes very dense repeated triggers where one instrumental line fires
    too many separate notes in a short time window. Chord clusters that start at
    essentially the same tick are preserved.
    """
    if not getattr(settings, "rhythmic_smoothing", True):
        return
    strength = clamp(getattr(settings, "smoothing_strength", 55), 0, 100) / 100.0
    if strength <= 0:
        return
    beat = max(1, settings.ticks_per_beat)
    role_factor = {
        "bass": 0.28,
        "melody": 0.38,
        "counter": 0.42,
        "arpeggio": 0.30,
        "chord": 0.55,
        "pad": 0.80,
        "texture": 0.45,
    }
    for idx, data in enumerate(tracks):
        track = track_settings[idx] if idx < len(track_settings) else TrackSettings(name=data.name, role="melody")
        role = (track.role or "melody").lower().strip()
        if role == "drum":
            continue
        pairs = _paired_note_events(data)
        if not pairs:
            continue
        # AlgoMusic and high-density tracks get a slightly stronger burst guard.
        density_boost = max(0.0, (track.density - 70) / 100.0)
        algo_boost = 0.12 if (_is_algomusic(settings) or "tracker" in (track.pattern or "").lower() or "acid" in (track.pattern or "").lower()) else 0.0
        min_gap = int(beat * role_factor.get(role, 0.38) * (0.45 + strength * 0.95 + density_boost + algo_boost))
        min_gap = max(1, min_gap)
        same_cluster = max(2, int(beat * 0.025))
        drop_ids = set()
        last_cluster_tick = -10**12
        for on_ev, off_ev, duration in sorted(pairs, key=lambda p: (p[0].tick, -p[0].b, p[0].a)):
            # Keep true simultaneous chord notes together.
            if abs(on_ev.tick - last_cluster_tick) <= same_cluster:
                continue
            if on_ev.tick - last_cluster_tick < min_gap:
                drop_ids.add(id(on_ev)); drop_ids.add(id(off_ev))
            else:
                last_cluster_tick = on_ev.tick
        if drop_ids:
            data.events = [ev for ev in data.events if id(ev) not in drop_ids]


def _track_energy(data: MidiTrackData, total_ticks: int) -> float:
    pairs = _paired_note_events(data)
    if not pairs:
        return 0.0
    total_ticks = max(1, int(total_ticks))
    acc = 0.0
    for on_ev, _off_ev, duration in pairs:
        v = max(1, min(127, on_ev.b)) / 127.0
        acc += (v * v) * max(1, duration)
    return math.sqrt(acc / total_ticks)


def _cc7_volume(data: MidiTrackData, fallback: int) -> int:
    for ev in data.events:
        if ev.kind == "cc" and ev.a == 7:
            return clamp(ev.b, 0, 127)
    return clamp(fallback, 0, 127)

def _normalize_track_velocities(tracks: Sequence[MidiTrackData], settings: GeneratorSettings, track_settings: Sequence[TrackSettings] | None = None, total_ticks: int | None = None) -> None:
    """Equalize perceived loudness per track while preserving musical accents.

    v0.4.7 improves the earlier velocity-only pass. It now considers note density
    and note duration, so a very busy arpeggio/gate line is not left much louder
    than a sparser melody merely because its average velocity is similar.
    """
    if not settings.normalize_velocity:
        return
    target = clamp(settings.normalize_target, 35, 120)
    strength = clamp(settings.normalize_strength, 0, 100) / 100.0
    if strength <= 0:
        return
    track_settings = list(track_settings or [])
    total_ticks = int(total_ticks or max((ev.tick for data in tracks for ev in data.events), default=1))
    stats = []
    for idx, data in enumerate(tracks):
        note_ons = [ev for ev in data.events if ev.kind == "note_on" and ev.b > 0]
        if not note_ons:
            continue
        ts = track_settings[idx] if idx < len(track_settings) else TrackSettings(name=data.name, role="melody")
        role = (ts.role or "melody").lower().strip()
        avg = sum(ev.b for ev in note_ons) / max(1, len(note_ons))
        energy = _track_energy(data, total_ticks)
        # Drums should remain present but not dominate; hats/arps/gates are dense and need more compensation.
        role_weight = {
            "drum": 0.92,
            "bass": 0.96,
            "chord": 0.92,
            "pad": 0.86,
            "arpeggio": 1.10,
            "melody": 1.00,
            "counter": 1.06,
            "texture": 1.12,
        }.get(role, 1.0)
        stats.append({"data": data, "track": ts, "note_ons": note_ons, "avg": avg, "energy": max(energy * role_weight, 0.0001), "role": role})
    if not stats:
        return
    energies = sorted(x["energy"] for x in stats if x["energy"] > 0)
    median_energy = energies[len(energies) // 2] if energies else 0.01
    for st in stats:
        data = st["data"]; ts = st["track"]; note_ons = st["note_ons"]; avg = st["avg"]; role = st["role"]
        local_target = target
        if role == "drum":
            local_target = min(118, target + 1)
        elif role in ("arpeggio", "counter", "texture"):
            local_target = max(35, target - 5)
        elif role == "pad":
            local_target = max(35, target - 8)
        velocity_factor = max(0.50, min(1.60, local_target / max(1.0, avg)))
        energy_factor = max(0.42, min(1.70, median_energy / st["energy"]))
        # Energy factor is the important part for perceived balance; velocity target keeps user intent.
        factor = (energy_factor * 0.72 + velocity_factor * 0.28)
        for ev in note_ons:
            desired = ev.b * factor
            local_strength = strength
            # Preserve special events: strong accents and fills keep more of their original contrast.
            if ev.b >= avg + 18:
                local_strength *= 0.35
            elif ev.b <= avg - 20:
                local_strength = min(1.0, local_strength * 1.15)
            ev.b = clamp(ev.b + (desired - ev.b) * local_strength, 1, 127)
        # Also rebalance MIDI channel volume CC7, because many GM synths weigh CC7
        # more heavily than note velocity. Keep this gentler than note velocity.
        current_vol = _cc7_volume(data, getattr(ts, "volume", 96))
        desired_vol = current_vol * (1.0 + (factor - 1.0) * 0.55)
        new_vol = clamp(current_vol + (desired_vol - current_vol) * strength, 20, 127)
        for ev in data.events:
            if ev.kind == "cc" and ev.a == 7:
                ev.b = new_vol

def _default_title(settings: GeneratorSettings, seed: int) -> str:
    # SoundHelix-style random title: deterministic for the seed, human-readable for the GUI/files.
    return generate_song_name(seed, settings.preset_name)


def generate_song(settings: GeneratorSettings, output_dir: str | os.PathLike[str], taste_profile: Optional[dict] = None, progress_callback=None) -> SongResult:
    """Generate an extended SoundHelix-inspired MIDI composition."""
    settings = GeneratorSettings.from_dict(settings.to_dict())
    if settings.randomize_seed:
        settings.seed = int(time.time_ns() % 2_147_483_647)
    rng = random.Random(settings.seed)

    # Optional lightweight learning: positive ratings nudge random generations toward preferred traits.
    if taste_profile and settings.use_rating_memory and settings.randomize_seed:
        if taste_profile.get("positive_count", 0) >= 2:
            settings.bpm = clamp(round((settings.bpm + taste_profile.get("avg_bpm", settings.bpm)) / 2), 40, 240)
            settings.complexity = clamp(round((settings.complexity + taste_profile.get("avg_complexity", settings.complexity)) / 2), 1, 100)
            settings.variation = clamp(round((settings.variation + taste_profile.get("avg_variation", settings.variation)) / 2), 1, 100)
            if rng.random() < 0.35 and taste_profile.get("favorite_progression"):
                settings.custom_progression = taste_profile["favorite_progression"]
            if rng.random() < 0.25 and taste_profile.get("favorite_mode"):
                settings.mode = taste_profile["favorite_mode"]

    output = Path(output_dir)
    output.mkdir(parents=True, exist_ok=True)
    title = settings.title.strip() or _default_title(settings, settings.seed)
    settings.title = title
    safe = safe_filename(title)
    midi_path = output / f"{safe}.mid"
    json_path = output / f"{safe}.json"
    chord_sheet_path = output / f"{safe}_chords.txt"

    sections = build_sections(settings)
    chords = build_chords(settings, sections)
    bar_len = _bar_ticks(settings)
    end_tick = settings.bars * bar_len
    markers = [(section.start_bar * bar_len, section.name) for section in sections] if settings.add_markers else []

    tracks: List[MidiTrackData] = []
    note_count = 0
    motif = _motif(settings, rng)
    previous_voicings: Dict[str, List[int]] = {}

    for idx, track in enumerate(settings.tracks):
        if progress_callback:
            progress_callback(int(5 + 80 * idx / max(1, len(settings.tracks))), f"Generating {track.name}...")
        if not track.enabled:
            continue
        data = _setup_track(track)
        _add_lfo(data, settings, track, end_tick)
        for bar in range(settings.bars):
            section = section_for_bar(sections, bar)
            active_rng = random.Random(settings.seed + sum(ord(ch) for ch in track.name) * 31 + bar * 97)
            if not _is_active(active_rng, settings, track, section, bar):
                continue
            chord = chords[bar]
            role = track.role.lower().strip()
            if role == "drum":
                note_count += _add_drum_bar(rng, data, settings, track, bar, section, settings.bars)
            elif role == "bass":
                note_count += _add_bass_bar(rng, data, settings, track, bar, section, chord)
            elif role == "chord":
                count, voicing = _add_chord_bar(rng, data, settings, track, bar, section, chord.notes, previous_voicings.get(track.name))
                previous_voicings[track.name] = voicing
                note_count += count
            elif role == "pad":
                count, voicing = _add_pad_bar(rng, data, settings, track, bar, section, chord.notes, previous_voicings.get(track.name))
                previous_voicings[track.name] = voicing
                note_count += count
            elif role == "arpeggio":
                note_count += _add_arpeggio_bar(rng, data, settings, track, bar, section, chord.notes)
            elif role == "counter":
                note_count += _add_counter_bar(rng, data, settings, track, bar, section, chord)
            elif role == "texture":
                note_count += _add_texture_bar(rng, data, settings, track, bar, section, chord)
            else:
                note_count += _add_melody_bar(rng, data, settings, track, bar, section, chord, motif)
        tracks.append(data)

    if getattr(settings, "rhythmic_smoothing", True):
        if progress_callback:
            progress_callback(86, "Smoothing rapid note bursts...")
        _smooth_note_bursts(tracks, settings, settings.tracks)
        note_count = _count_note_ons(tracks)

    if settings.normalize_velocity:
        if progress_callback:
            progress_callback(88, "Normalizing instrument loudness...")
        _normalize_track_velocities(tracks, settings, settings.tracks, end_tick)

    note_count = _count_note_ons(tracks)

    if progress_callback:
        progress_callback(90, "Writing MIDI...")
    write_midi(str(midi_path), tracks, settings.ticks_per_beat, settings.bpm, settings.beats_per_bar, title, markers)

    chord_sheet_text = make_chord_sheet(title, settings, sections, chords, note_count)
    if settings.export_chord_sheet:
        chord_sheet_path.write_text(chord_sheet_text, encoding="utf-8")
    else:
        chord_sheet_path = Path("")

    result = SongResult(
        title=title,
        seed=settings.seed,
        midi_path=str(midi_path),
        json_path=str(json_path) if settings.export_json else "",
        chord_sheet_path=str(chord_sheet_path) if settings.export_chord_sheet else "",
        sections=sections,
        chords=chords,
        note_count=note_count,
        settings=settings,
    )

    if settings.render_wav or settings.render_mp3:
        wav_path = output / f"{safe}.wav"
        mp3_path = output / f"{safe}.mp3"
        try:
            if progress_callback:
                progress_callback(92, "Rendering WAV with internal synth...")
            result.wav_path = render_tracks_to_wav(
                wav_path, tracks, settings.tracks, settings.bpm, settings.ticks_per_beat, end_tick, settings.audio_sample_rate, progress_callback, settings.normalize_velocity
            )
            result.render_log += "WAV rendered with the built-in lightweight synth. "
            if settings.render_mp3:
                if ffmpeg_available():
                    if progress_callback:
                        progress_callback(99, "Converting WAV to MP3 with ffmpeg...")
                    try:
                        result.mp3_path = convert_wav_to_mp3(result.wav_path, mp3_path)
                        result.render_log += "MP3 rendered via ffmpeg/libmp3lame. "
                    except Exception as mp3_exc:
                        result.mp3_path = ""
                        result.render_log += f"MP3 skipped: {mp3_exc} "
                else:
                    result.render_log += "MP3 skipped: ffmpeg was not found in PATH. "
        except Exception as exc:
            result.render_log += f"Audio render warning: {type(exc).__name__}: {exc}"

    if settings.export_json:
        payload = {
            "application": "PythonSoundHelix",
            "version": "0.4.9",
            "license": "GPLv3",
            "title": result.title,
            "seed": result.seed,
            "midi_path": result.midi_path,
            "wav_path": result.wav_path,
            "mp3_path": result.mp3_path,
            "render_log": result.render_log,
            "note_count": result.note_count,
            "settings": settings.to_dict(),
            "sections": [asdict(s) for s in sections],
            "chords": [asdict(c) for c in chords],
        }
        json_path.write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")
    if progress_callback:
        progress_callback(100, "Done")
    return result


def make_chord_sheet(title: str, settings: GeneratorSettings, sections: Sequence[SectionEvent], chords: Sequence[ChordEvent], note_count: int) -> str:
    lines = [
        title,
        "=" * len(title),
        "",
        f"Generated by PythonSoundHelix 0.4.9 (GPLv3)",
        f"Preset: {settings.preset_name}",
        f"Seed: {settings.seed}",
        f"Tempo: {settings.bpm} BPM | Key: {settings.key} {settings.mode} | Bars: {settings.bars}",
        f"Progression: {settings.effective_progression()}",
        f"Notes: {note_count}",
        "",
        "Sections:",
    ]
    for s in sections:
        lines.append(f"  - {s.name}: bars {s.start_bar + 1}-{s.start_bar + s.bars}, energy {s.energy}%")
    lines += ["", "Chord map:"]
    current = None
    buffer: List[str] = []
    for chord in chords:
        if chord.section != current:
            if buffer:
                lines.append("    " + " | ".join(buffer))
                buffer.clear()
            current = chord.section
            lines.append(f"  [{current}]")
        root_name = midi_note_name(chord.notes[0])[:-1]
        buffer.append(f"{chord.bar + 1}:{chord.symbol}({root_name})")
        if len(buffer) >= 8:
            lines.append("    " + " | ".join(buffer))
            buffer.clear()
    if buffer:
        lines.append("    " + " | ".join(buffer))
    lines += [
        "",
        "Note: Additional melody templates named after public-domain works are only short, transformed hints, not exact bundled recordings.",
    ]
    return "\n".join(lines) + "\n"
