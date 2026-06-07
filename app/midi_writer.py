from __future__ import annotations

from dataclasses import dataclass, field
from typing import List, Tuple


def _varlen(value: int) -> bytes:
    value = max(0, int(value))
    buffer = value & 0x7F
    out = []
    while True:
        value >>= 7
        if value:
            buffer <<= 8
            buffer |= ((value & 0x7F) | 0x80)
        else:
            break
    while True:
        out.append(buffer & 0xFF)
        if buffer & 0x80:
            buffer >>= 8
        else:
            break
    return bytes(out)


@dataclass
class MidiEvent:
    tick: int
    order: int
    data: bytes


@dataclass
class MidiTrack:
    name: str
    events: List[MidiEvent] = field(default_factory=list)
    _order: int = 0

    def add(self, tick: int, data: bytes):
        self.events.append(MidiEvent(max(0, int(tick)), self._order, data)); self._order += 1

    def program(self, tick: int, channel: int, program: int):
        self.add(tick, bytes([0xC0 | (channel & 0x0F), program & 0x7F]))

    def cc(self, tick: int, channel: int, controller: int, value: int):
        self.add(tick, bytes([0xB0 | (channel & 0x0F), controller & 0x7F, value & 0x7F]))

    def note(self, tick: int, duration: int, channel: int, pitch: int, velocity: int):
        tick = max(0, int(tick)); duration = max(1, int(duration))
        pitch = max(0, min(127, int(pitch))); velocity = max(1, min(127, int(velocity)))
        self.add(tick, bytes([0x90 | (channel & 0x0F), pitch, velocity]))
        self.add(tick + duration, bytes([0x80 | (channel & 0x0F), pitch, 0]))


def _meta_text(kind: int, text: str) -> bytes:
    payload = text.encode('utf-8', errors='replace')
    return bytes([0xFF, kind]) + _varlen(len(payload)) + payload


def _tempo_meta(bpm: int) -> bytes:
    us = int(round(60_000_000 / max(1, bpm)))
    return bytes([0xFF, 0x51, 0x03, (us >> 16) & 0xFF, (us >> 8) & 0xFF, us & 0xFF])


def _timesig_meta(beats_per_bar: int) -> bytes:
    import math
    den_power = 2
    return bytes([0xFF, 0x58, 0x04, beats_per_bar & 0xFF, den_power, 24, 8])


def _track_chunk(events: List[MidiEvent]) -> bytes:
    events = sorted(events, key=lambda e: (e.tick, e.order))
    data = bytearray()
    last = 0
    for e in events:
        data += _varlen(e.tick - last)
        data += e.data
        last = e.tick
    data += b'\x00\xFF\x2F\x00'
    return b'MTrk' + len(data).to_bytes(4, 'big') + bytes(data)


def write_midi(path: str, tracks: List[MidiTrack], ticks_per_beat: int, bpm: int, beats_per_bar: int, title: str, markers: List[Tuple[int, str]] | None = None):
    meta_events = [
        MidiEvent(0, 0, _meta_text(0x03, title)),
        MidiEvent(0, 1, _tempo_meta(bpm)),
        MidiEvent(0, 2, _timesig_meta(beats_per_bar)),
    ]
    for i, (tick, label) in enumerate(markers or []):
        meta_events.append(MidiEvent(tick, 10 + i, _meta_text(0x06, label)))
    chunks = [_track_chunk(meta_events)]
    for tr in tracks:
        evs = [MidiEvent(0, -1, _meta_text(0x03, tr.name))] + tr.events
        chunks.append(_track_chunk(evs))
    header = b'MThd' + (6).to_bytes(4, 'big') + (1).to_bytes(2, 'big') + len(chunks).to_bytes(2, 'big') + int(ticks_per_beat).to_bytes(2, 'big')
    with open(path, 'wb') as f:
        f.write(header + b''.join(chunks))
