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

from .midi_writer import MidiTrackData, write_midi
from .models import ChordEvent, GeneratorSettings, SectionEvent, SongResult, TrackSettings
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
    "Popcorn-style original pulse": [0, 2, 4, 2, 0, 2, 4, 7, 5, 4, 2, 0, 2, 4, 2, 0],
    "Ode-to-Joy public-domain hint": [2, 2, 3, 4, 4, 3, 2, 1, 0, 0, 1, 2, 2, 1, 1],
    "Fuer-Elise public-domain hint": [4, 3, 4, 3, 4, 1, 3, 2, 0, -2, 0, 1, 2],
    "Canon public-domain hint": [0, 4, 5, 2, 3, 0, 3, 4, 5, 7, 4, 5, 3, 4],
    "Toccata public-domain hint": [0, 7, 5, 3, 2, 0, -2, 0, 2, 3, 5, 7],
    "Original arcade anthem": [0, 0, 4, 7, 4, 2, 0, -1, 0, 2, 4, 2, 0],
}


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


def _swing_offset(step_index: int, step_len: int, swing: int) -> int:
    if swing <= 0:
        return 0
    return int(step_len * (swing / 100.0) * 0.33) if step_index % 2 == 1 else 0


def build_sections(settings: GeneratorSettings) -> List[SectionEvent]:
    count = clamp(settings.section_count, 3, 7)
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
    for _ in range(length - 1):
        if rng.randint(0, 100) < settings.motif_memory and degrees:
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

    # Kicks
    kick_steps = [0, 8] if "four" not in pattern else [0, 4, 8, 12]
    if energy > 55 and "break" not in pattern:
        kick_steps += [6 if rng.random() < 0.45 else 10]
    if "broken" in pattern:
        kick_steps = [0, 3, 8, 11]
    for step in sorted(set(kick_steps)):
        vel = _velocity(rng, 88, settings.humanize_velocity, 12 if step == 0 else 0)
        data.add_note(_human_tick(rng, start + step * sixteenth, settings.humanize_ticks), max(20, sixteenth // 2), 9, DRUM_NOTES["kick"], vel)
        notes += 1

    # Snare / clap on 2 and 4
    for step in [4, 12]:
        snare = DRUM_NOTES["clap"] if "electro" in pattern or energy > 72 else DRUM_NOTES["snare"]
        data.add_note(_human_tick(rng, start + step * sixteenth, settings.humanize_ticks), max(20, sixteenth // 2), 9, snare, _velocity(rng, 82, settings.humanize_velocity, 8))
        notes += 1

    # Hats
    hat_rate = 2 if energy > 58 else 4
    for step in range(0, 16, hat_rate):
        if rng.randint(0, 100) <= track.density:
            hat = DRUM_NOTES["open_hat"] if step % 8 == 6 and rng.random() < 0.35 else DRUM_NOTES["closed_hat"]
            accent = 8 if step % 4 == 0 else -4
            tick = start + step * sixteenth + _swing_offset(step, sixteenth, settings.swing)
            data.add_note(_human_tick(rng, tick, settings.humanize_ticks), max(10, sixteenth // 2), 9, hat, _velocity(rng, 58, settings.humanize_velocity, accent))
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
    steps = [0, 2, 4, 6] if "eighth" in pattern else [0, 4, 8, 12]
    if "sync" in pattern or settings.variation > 55:
        steps = [0, 3, 6, 8, 11, 14]
    if settings.keep_bass_on_roots:
        candidates = [base, base + 12, base + 7]
    else:
        candidates = [base + i for i in [0, 3, 5, 7, 10, 12]]
    notes = 0
    sixteenth = beat // 4
    for i, step in enumerate(steps):
        if rng.randint(0, 100) > track.density + section.energy // 4:
            continue
        pitch = candidates[i % len(candidates)]
        duration = int(sixteenth * (2.8 if len(steps) <= 4 else 1.6))
        tick = start + step * sixteenth + _swing_offset(step, sixteenth, settings.swing)
        data.add_note(_human_tick(rng, tick, settings.humanize_ticks), duration, track.channel, pitch, _velocity(rng, track.volume, settings.humanize_velocity, 12 if step == 0 else 0))
        notes += 1
    return notes


def _add_chord_bar(rng: random.Random, data: MidiTrackData, settings: GeneratorSettings, track: TrackSettings, bar: int, section: SectionEvent, chord_notes: Sequence[int], previous_voicing: Sequence[int] | None) -> Tuple[int, List[int]]:
    bar_len = _bar_ticks(settings)
    start = bar * bar_len
    beat = settings.ticks_per_beat
    voicing = voice_lead([n + track.octave * 12 for n in chord_notes], previous_voicing, low=42 + track.octave * 4, high=78 + track.octave * 4)
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
    voicing = voice_lead([n + 12 + track.octave * 12 for n in chord_notes], previous_voicing, low=50, high=88)
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
    pcs = voice_lead([n + 12 + track.octave * 12 for n in chord_notes], None, low=54, high=90)
    if len(pcs) < 3:
        pcs = list(pcs) + [pcs[0] + 12]
    pattern = (track.pattern or "auto").lower()
    order = list(range(len(pcs)))
    if "down" in pattern:
        order = list(reversed(order))
    elif "updown" in pattern:
        order = list(range(len(pcs))) + list(reversed(range(1, len(pcs) - 1)))
    notes = 0
    steps = 16 if section.energy > 48 or settings.complexity > 55 else 8
    for step in range(steps):
        if rng.randint(0, 100) > track.density + settings.complexity // 5:
            continue
        pitch = pcs[order[step % len(order)]] + (12 if step >= 8 and rng.random() < settings.variation / 140 else 0)
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
    template_name = settings.melody_template or "auto"
    # Known/public-domain inspired motifs are made more recognizable by using the template more directly.
    direct_template = template_name != "auto"
    density = track.density + (18 if "Hook" in section.name else 0) - (20 if section.name == "Intro" else 0)
    step_count = 8 if settings.complexity < 70 else 16
    step_len = bar_len // step_count
    notes = 0
    last_pitch = None
    for step in range(step_count):
        if not direct_template and rng.randint(0, 100) > density:
            continue
        if direct_template and step >= len(motif) and rng.randint(0, 100) > density:
            continue
        degree = motif[(bar * step_count + step) % len(motif)] if motif else rng.randint(0, 7)
        pitch = degree_pitch(degree, key_pc, settings.mode, 5 + track.octave)
        # Pull toward chord tones on strong beats.
        if step % 4 == 0:
            candidates = [n + 12 + track.octave * 12 for n in chord.notes]
            pitch = min(candidates, key=lambda p: abs(pitch - p))
        else:
            pitch = nearest_scale_pitch(pitch, key_pc, settings.mode, 58 + track.octave * 12, 94 + track.octave * 12)
        if last_pitch is not None and abs(pitch - last_pitch) > 12 and rng.randint(0, 100) < settings.motif_memory:
            pitch = pitch - 12 if pitch > last_pitch else pitch + 12
        duration = int(step_len * rng.choice([0.75, 0.9, 1.4 if step_count == 8 else 1.0]))
        tick = start + step * step_len + _swing_offset(step, step_len, settings.swing)
        data.add_note(_human_tick(rng, tick, settings.humanize_ticks), duration, track.channel, pitch, _velocity(rng, track.volume, settings.humanize_velocity, 12 if step % 4 == 0 else 0))
        last_pitch = pitch
        notes += 1
        # Call-and-response echo in upper octave for sparse melody.
        if settings.call_response and step in (2, 6, 10, 14) and rng.randint(0, 100) < settings.variation // 2:
            echo_pitch = nearest_scale_pitch(pitch + rng.choice([-5, 7, 12]), key_pc, settings.mode, 58, 98)
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
    candidates = scale_pitches(key_pc, settings.mode, 55 + track.octave * 12, 86 + track.octave * 12)
    chord_pcs = {n % 12 for n in chord.notes}
    candidates = [p for p in candidates if p % 12 in chord_pcs] or candidates
    notes = 0
    for off in [beat, beat * 3]:
        pitch = rng.choice(candidates)
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
        pitch = (chord.notes[i % len(chord.notes)] + 24 + track.octave * 12)
        tick = start + rng.randint(0, max(0, bar_len - beat))
        data.add_note(_human_tick(rng, tick, settings.humanize_ticks * 2), beat * rng.choice([1, 2, 3]), track.channel, pitch, _velocity(rng, min(track.volume, 70), settings.humanize_velocity, -18))
        notes += 1
    return notes


def _default_title(settings: GeneratorSettings, seed: int) -> str:
    preset = settings.preset_name.replace("PythonSoundHelix", "PSH").replace(" ", "_")
    return f"{preset}_seed{seed}"


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
    if settings.export_json:
        payload = {
            "application": "PythonSoundHelix",
            "version": "0.2.0",
            "license": "GPLv3",
            "title": result.title,
            "seed": result.seed,
            "midi_path": result.midi_path,
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
        f"Generated by PythonSoundHelix 0.2.0 (GPLv3)",
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
