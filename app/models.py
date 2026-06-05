# PythonSoundHelix - GPLv3 Python/PyQt6 reimplementation inspired by SoundHelix.
# Original source basis: SoundHelix SVN archive soundhelix-code-r896-trunk, version 0.10u.
# Original project: https://www.soundhelix.com/
# This file is part of PythonSoundHelix and is released under GPLv3.

from __future__ import annotations

from dataclasses import dataclass, asdict, field
from typing import Any, Dict, List


@dataclass
class TrackSettings:
    """GUI/editable track configuration.

    Roles are intentionally close to SoundHelix' sequence-engine ideas, but kept
    Pythonic and extensible: drum, bass, chord, arpeggio, melody, pad, counter,
    texture. A track can be disabled in the GUI without removing it from the
    project JSON.
    """

    name: str
    role: str
    enabled: bool = True
    channel: int = 0
    program: int = 0
    volume: int = 96
    pan: int = 64
    octave: int = 0
    transpose: int = 0
    fine_tune_cents: int = 0
    arp_rate: int = 100
    density: int = 70
    complexity: int = 55
    activity: int = 80
    pattern: str = "auto"
    accent: int = 50
    mute_in_intro: bool = False
    fill_every: int = 8

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

    @staticmethod
    def from_dict(data: Dict[str, Any]) -> "TrackSettings":
        defaults = TrackSettings(name="Track", role="melody").to_dict()
        merged = {**defaults, **(data or {})}
        return TrackSettings(**merged)


@dataclass
class GeneratorSettings:
    preset_name: str = "PythonSoundHelix Extended Pop"
    seed: int = 123456789
    randomize_seed: bool = True
    title: str = ""
    bpm: int = 118
    bars: int = 96
    beats_per_bar: int = 4
    ticks_per_beat: int = 480
    key: str = "C"
    mode: str = "major"
    progression: str = "I,V,vi,IV"
    custom_progression: str = ""
    harmonic_rhythm: int = 1
    section_count: int = 5
    swing: int = 8
    humanize_ticks: int = 8
    humanize_velocity: int = 8
    complexity: int = 55
    variation: int = 45
    motif_memory: int = 70
    accent_strength: int = 52
    seed_variation_strength: int = 70
    lfo_expression: bool = True
    call_response: bool = True
    keep_bass_on_roots: bool = True
    add_markers: bool = True
    export_json: bool = True
    export_chord_sheet: bool = True
    use_rating_memory: bool = True
    normalize_velocity: bool = False
    normalize_target: int = 88
    normalize_strength: int = 72
    global_arpeggio_rate: int = 100
    rhythmic_smoothing: bool = True
    smoothing_strength: int = 55
    auto_range_guard: bool = True
    max_melody_pitch: int = 79
    render_wav: bool = True
    render_mp3: bool = True
    audio_sample_rate: int = 44100
    ui_theme: str = "Dark"
    language: str = "en"
    melody_template: str = "auto"
    groove_template: str = "auto"
    description: str = ""
    tracks: List[TrackSettings] = field(default_factory=list)

    def effective_progression(self) -> str:
        return (self.custom_progression or self.progression or "I,V,vi,IV").strip()

    def to_dict(self) -> Dict[str, Any]:
        data = asdict(self)
        data["tracks"] = [t.to_dict() for t in self.tracks]
        return data

    @staticmethod
    def from_dict(data: Dict[str, Any]) -> "GeneratorSettings":
        base = GeneratorSettings()
        merged = {**base.to_dict(), **(data or {})}
        merged["tracks"] = [TrackSettings.from_dict(t) for t in merged.get("tracks", [])]
        return GeneratorSettings(**merged)


@dataclass
class MidiEvent:
    tick: int
    kind: str
    channel: int = 0
    a: int = 0
    b: int = 0
    text: str = ""


@dataclass
class MidiNote:
    track: str
    channel: int
    pitch: int
    start: int
    duration: int
    velocity: int


@dataclass
class ChordEvent:
    bar: int
    tick: int
    symbol: str
    root: int
    notes: List[int]
    section: str


@dataclass
class SectionEvent:
    name: str
    start_bar: int
    bars: int
    energy: int


@dataclass
class SongResult:
    title: str
    seed: int
    midi_path: str
    json_path: str
    chord_sheet_path: str
    sections: List[SectionEvent]
    chords: List[ChordEvent]
    note_count: int
    settings: GeneratorSettings
    wav_path: str = ""
    mp3_path: str = ""
    render_log: str = ""

    def summary(self) -> str:
        section_text = ", ".join(f"{s.name}:{s.bars}" for s in self.sections)
        audio = []
        if self.wav_path:
            audio.append("WAV")
        if self.mp3_path:
            audio.append("MP3")
        audio_text = f" | audio={'+'.join(audio)}" if audio else ""
        return f"{self.title} | seed={self.seed} | notes={self.note_count} | sections={section_text}{audio_text}"
