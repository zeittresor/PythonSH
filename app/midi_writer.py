# PythonSoundHelix - GPLv3 Python/PyQt6 reimplementation inspired by SoundHelix.
# Original source basis: SoundHelix SVN archive soundhelix-code-r896-trunk, version 0.10u.
# Original project: https://www.soundhelix.com/
# This file is part of PythonSoundHelix and is released under GPLv3.

from __future__ import annotations

from dataclasses import dataclass, field
from typing import List, Tuple

from .models import MidiEvent
from .music_theory import clamp


@dataclass
class MidiTrackData:
    name: str
    events: List[MidiEvent] = field(default_factory=list)

    def add_note(self, start: int, duration: int, channel: int, pitch: int, velocity: int) -> None:
        start = max(0, int(start))
        duration = max(1, int(duration))
        self.events.append(MidiEvent(tick=start, kind="note_on", channel=channel, a=clamp(pitch, 0, 127), b=clamp(velocity, 1, 127)))
        self.events.append(MidiEvent(tick=start + duration, kind="note_off", channel=channel, a=clamp(pitch, 0, 127), b=0))

    def add_program(self, tick: int, channel: int, program: int) -> None:
        if channel == 9:
            return
        self.events.append(MidiEvent(tick=max(0, int(tick)), kind="program", channel=channel, a=clamp(program, 0, 127)))

    def add_cc(self, tick: int, channel: int, controller: int, value: int) -> None:
        self.events.append(MidiEvent(tick=max(0, int(tick)), kind="cc", channel=channel, a=clamp(controller, 0, 127), b=clamp(value, 0, 127)))

    def add_pitch_bend(self, tick: int, channel: int, value: int) -> None:
        # value is 14-bit centered at 8192.
        value = clamp(value, 0, 16383)
        self.events.append(MidiEvent(tick=max(0, int(tick)), kind="pitch_bend", channel=channel, a=value & 0x7F, b=(value >> 7) & 0x7F))

    def add_marker(self, tick: int, text: str) -> None:
        self.events.append(MidiEvent(tick=max(0, int(tick)), kind="marker", text=str(text)))

    def add_track_name(self) -> None:
        self.events.append(MidiEvent(tick=0, kind="track_name", text=self.name))


def _var_len(value: int) -> bytes:
    value = max(0, int(value))
    buffer = value & 0x7F
    out = []
    while value >> 7:
        value >>= 7
        buffer <<= 8
        buffer |= ((value & 0x7F) | 0x80)
    while True:
        out.append(buffer & 0xFF)
        if buffer & 0x80:
            buffer >>= 8
        else:
            break
    return bytes(out)


def _meta_event(meta_type: int, payload: bytes) -> bytes:
    return bytes([0xFF, meta_type]) + _var_len(len(payload)) + payload


def _encode_text(text: str) -> bytes:
    return text.encode("utf-8", errors="replace")


def _event_priority(event: MidiEvent) -> int:
    order = {
        "track_name": 0,
        "program": 1,
        "cc": 2,
        "pitch_bend": 3,
        "marker": 4,
        "note_off": 5,
        "note_on": 6,
    }
    return order.get(event.kind, 99)


def _encode_event(event: MidiEvent) -> bytes:
    ch = clamp(event.channel, 0, 15)
    if event.kind == "note_on":
        return bytes([0x90 | ch, clamp(event.a, 0, 127), clamp(event.b, 0, 127)])
    if event.kind == "note_off":
        return bytes([0x80 | ch, clamp(event.a, 0, 127), clamp(event.b, 0, 127)])
    if event.kind == "program":
        return bytes([0xC0 | ch, clamp(event.a, 0, 127)])
    if event.kind == "cc":
        return bytes([0xB0 | ch, clamp(event.a, 0, 127), clamp(event.b, 0, 127)])
    if event.kind == "pitch_bend":
        return bytes([0xE0 | ch, clamp(event.a, 0, 127), clamp(event.b, 0, 127)])
    if event.kind == "marker":
        return _meta_event(0x06, _encode_text(event.text))
    if event.kind == "track_name":
        return _meta_event(0x03, _encode_text(event.text))
    return b""


def _track_chunk(events: List[MidiEvent]) -> bytes:
    events = sorted(events, key=lambda e: (max(0, e.tick), _event_priority(e), e.channel, e.a, e.b))
    data = bytearray()
    last_tick = 0
    for event in events:
        tick = max(0, int(event.tick))
        data.extend(_var_len(tick - last_tick))
        encoded = _encode_event(event)
        data.extend(encoded)
        last_tick = tick
    data.extend(_var_len(0))
    data.extend(_meta_event(0x2F, b""))
    return b"MTrk" + len(data).to_bytes(4, "big") + bytes(data)


def write_midi(path: str, tracks: List[MidiTrackData], ticks_per_beat: int, bpm: int, beats_per_bar: int, title: str, markers: List[Tuple[int, str]] | None = None) -> None:
    """Write a Standard MIDI File type 1 using only the Python stdlib."""
    markers = markers or []
    header = b"MThd" + (6).to_bytes(4, "big") + (1).to_bytes(2, "big") + (len(tracks) + 1).to_bytes(2, "big") + int(ticks_per_beat).to_bytes(2, "big")

    meta = bytearray()
    meta.extend(_var_len(0))
    meta.extend(_meta_event(0x03, _encode_text(title or "PythonSoundHelix")))
    meta.extend(_var_len(0))
    micros_per_quarter = int(60_000_000 / max(1, bpm))
    meta.extend(_meta_event(0x51, micros_per_quarter.to_bytes(3, "big")))
    meta.extend(_var_len(0))
    denominator_power = 2  # 4/4 denominator
    meta.extend(_meta_event(0x58, bytes([clamp(beats_per_bar, 1, 16), denominator_power, 24, 8])))
    last = 0
    for tick, text in sorted(markers, key=lambda x: x[0]):
        tick = max(0, int(tick))
        meta.extend(_var_len(tick - last))
        meta.extend(_meta_event(0x06, _encode_text(text)))
        last = tick
    meta.extend(_var_len(0))
    meta.extend(_meta_event(0x2F, b""))
    meta_chunk = b"MTrk" + len(meta).to_bytes(4, "big") + bytes(meta)

    chunks = [meta_chunk]
    for track in tracks:
        track.add_track_name()
        chunks.append(_track_chunk(track.events))

    with open(path, "wb") as f:
        f.write(header)
        for chunk in chunks:
            f.write(chunk)
