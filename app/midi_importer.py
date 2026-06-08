from __future__ import annotations

import json
import math
import struct
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List, Tuple, Optional

from .music_theory import NOTE_TO_PC, PC_TO_NAME_SHARP, MAJOR_SCALE, NAT_MINOR_SCALE, safe_filename

ROOT = Path(__file__).resolve().parent.parent
USER_PRESET_DIR = ROOT / "app_data" / "imported_midi_presets"

@dataclass
class MidiNote:
    channel: int
    pitch: int
    velocity: int
    start: int
    end: int
    program: int = 0


def _read_var(data: bytes, pos: int) -> Tuple[int, int]:
    value = 0
    while True:
        b = data[pos]
        pos += 1
        value = (value << 7) | (b & 0x7F)
        if not (b & 0x80):
            break
    return value, pos


def _major_minor_score(hist: List[int], root: int, scale: List[int]) -> int:
    pcs = {(root + s) % 12 for s in scale}
    score = sum(hist[pc] * (4 if pc == root else 2 if pc in pcs else -3) for pc in range(12))
    return score


def guess_key_mode(notes: List[MidiNote]) -> Tuple[str, str]:
    hist = [0] * 12
    for n in notes:
        dur = max(1, n.end - n.start)
        hist[n.pitch % 12] += dur
    if not any(hist):
        return "C", "major"
    best = None
    for root in range(12):
        for mode, scale in [("major", MAJOR_SCALE), ("minor", NAT_MINOR_SCALE)]:
            score = _major_minor_score(hist, root, scale)
            if best is None or score > best[0]:
                best = (score, root, mode)
    _, root, mode = best
    return PC_TO_NAME_SHARP[root], mode


def parse_midi(path: str | Path) -> Dict:
    data = Path(path).read_bytes()
    pos = 0
    if data[pos:pos+4] != b"MThd":
        raise ValueError("Not a Standard MIDI file")
    hlen = struct.unpack(">I", data[pos+4:pos+8])[0]
    fmt, ntrks, division = struct.unpack(">HHH", data[pos+8:pos+14])
    pos += 8 + hlen
    if division & 0x8000:
        ticks_per_beat = 480
    else:
        ticks_per_beat = max(1, division)
    notes: List[MidiNote] = []
    tempos: List[Tuple[int, int]] = []
    time_sigs: List[Tuple[int, int, int]] = []
    programs_by_channel = {ch: 0 for ch in range(16)}
    for _ in range(ntrks):
        if data[pos:pos+4] != b"MTrk":
            break
        length = struct.unpack(">I", data[pos+4:pos+8])[0]
        chunk = data[pos+8:pos+8+length]
        pos += 8 + length
        tpos = 0
        tick = 0
        running: Optional[int] = None
        active: Dict[Tuple[int, int], List[Tuple[int, int, int]]] = {}
        local_program = {ch: programs_by_channel.get(ch, 0) for ch in range(16)}
        while tpos < len(chunk):
            delta, tpos = _read_var(chunk, tpos)
            tick += delta
            status = chunk[tpos]
            if status & 0x80:
                tpos += 1
                if status < 0xF0:
                    running = status
            else:
                if running is None:
                    break
                status = running
            if status == 0xFF:
                meta = chunk[tpos]; tpos += 1
                size, tpos = _read_var(chunk, tpos)
                payload = chunk[tpos:tpos+size]; tpos += size
                if meta == 0x51 and len(payload) == 3:
                    tempos.append((tick, int.from_bytes(payload, "big")))
                elif meta == 0x58 and len(payload) >= 2:
                    time_sigs.append((tick, payload[0], 2 ** payload[1]))
                elif meta == 0x2F:
                    break
                continue
            if status in (0xF0, 0xF7):
                size, tpos = _read_var(chunk, tpos)
                tpos += size
                continue
            etype = status & 0xF0
            ch = status & 0x0F
            if etype in (0x80, 0x90, 0xA0, 0xB0, 0xE0):
                if tpos + 2 > len(chunk):
                    break
                a, b = chunk[tpos], chunk[tpos+1]; tpos += 2
                if etype == 0x90 and b > 0:
                    active.setdefault((ch, a), []).append((tick, int(b), int(local_program.get(ch, 0))))
                elif etype == 0x80 or (etype == 0x90 and b == 0):
                    stack = active.get((ch, a))
                    if stack:
                        st, vel, prog = stack.pop(0)
                        if tick > st:
                            notes.append(MidiNote(ch, int(a), vel, st, tick, prog))
            elif etype in (0xC0, 0xD0):
                if tpos >= len(chunk):
                    break
                a = chunk[tpos]; tpos += 1
                if etype == 0xC0:
                    local_program[ch] = int(a)
                    programs_by_channel[ch] = int(a)
            else:
                break
        for (ch, pitch), stack in active.items():
            for st, vel, prog in stack:
                if tick > st:
                    notes.append(MidiNote(ch, int(pitch), int(vel), int(st), int(tick), int(prog)))
    tempos.sort()
    time_sigs.sort()
    tempo_us = tempos[0][1] if tempos else 500000
    bpm = int(round(60000000 / max(1, tempo_us)))
    numerator, denominator = (time_sigs[0][1], time_sigs[0][2]) if time_sigs else (4, 4)
    return {"format": fmt, "ticks_per_beat": ticks_per_beat, "bpm": bpm, "time_signature": [numerator, denominator], "notes": notes, "programs_by_channel": programs_by_channel}


def _melody_channel(notes: List[MidiNote]) -> int:
    groups: Dict[int, List[MidiNote]] = {}
    for n in notes:
        if n.channel == 9:
            continue
        groups.setdefault(n.channel, []).append(n)
    if not groups:
        return 0
    def score(item):
        ch, ns = item
        avg = sum(n.pitch for n in ns) / max(1, len(ns))
        count = len(ns)
        dur_avg = sum(n.end - n.start for n in ns) / max(1, len(ns))
        return avg + min(count, 200) * 0.06 - dur_avg * 0.0008
    return max(groups.items(), key=score)[0]


def _degree_for_pitch(pitch: int, root_pc: int, mode: str) -> int:
    scale = NAT_MINOR_SCALE if mode == "minor" else MAJOR_SCALE
    candidates = []
    for octv in range(-4, 8):
        for i, pc_off in enumerate(scale):
            pc = (root_pc + pc_off) % 12
            # target near original octave but degree encodes diatonic offset
            base = pc + 12 * octv
            # pitch may be 60+, compare pitch class first and rough degree register
            for add in range(0, 128, 12):
                p = pc + add
                candidates.append((abs(p - pitch), i + 7 * ((p - 60) // 12), p))
    candidates.sort(key=lambda x: (x[0], abs(x[2] - pitch)))
    return int(candidates[0][1])


def analyze_midi_to_preset(path: str | Path, preset_name: str | None = None, max_notes: int = 768) -> Dict:
    path = Path(path)
    parsed = parse_midi(path)
    notes: List[MidiNote] = parsed["notes"]
    non_drum = [n for n in notes if n.channel != 9]
    key, mode = guess_key_mode(non_drum)
    root = NOTE_TO_PC.get(key.upper(), 0)
    mel_ch = _melody_channel(notes)
    melody = [n for n in notes if n.channel == mel_ch]
    if not melody:
        melody = non_drum[:]
    melody.sort(key=lambda n: (n.start, -n.pitch, -n.velocity))
    # Make a monophonic contour by keeping the most prominent note per small grid slot.
    tpb = max(1, int(parsed["ticks_per_beat"]))
    grid = max(1, tpb // 8)
    slots: Dict[int, MidiNote] = {}
    for n in melody:
        slot = int(round(n.start / grid))
        prev = slots.get(slot)
        if prev is None or (n.velocity, n.pitch, n.end - n.start) > (prev.velocity, prev.pitch, prev.end - prev.start):
            slots[slot] = n
    selected = sorted(slots.values(), key=lambda n: (n.start, n.pitch))
    if len(selected) > max_notes:
        step = len(selected) / max_notes
        selected = [selected[int(i * step)] for i in range(max_notes)]
    start_tick = min((n.start for n in selected), default=0)
    phrase = []
    for n in selected:
        off = max(0.0, (n.start - start_tick) / tpb)
        dur = max(0.125, min(4.0, (n.end - n.start) / tpb))
        degree = _degree_for_pitch(n.pitch, root, mode)
        accent = 1 if (abs(off - round(off)) < 0.02 or n.velocity >= 88) else 0
        phrase.append([round(off, 4), round(dur, 4), int(degree), int(accent)])
    total_ticks = max((n.end for n in notes), default=tpb * 16)
    beats_per_bar = 3 if parsed["time_signature"][0] == 3 else 4
    bars = max(16, min(256, int(math.ceil(total_ticks / (tpb * beats_per_bar)))))
    programs = parsed.get("programs_by_channel", {})
    def common_program(role: str) -> int:
        chans: List[int]
        if role == "bass":
            candidates = [n for n in non_drum if n.pitch < 55]
        elif role == "melody":
            candidates = melody
        else:
            candidates = non_drum
        if not candidates:
            return {"bass": 38, "melody": 0, "chord": 4, "pad": 89}.get(role, 0)
        ch_counts: Dict[int, int] = {}
        for n in candidates:
            ch_counts[n.channel] = ch_counts.get(n.channel, 0) + 1
        ch = max(ch_counts, key=ch_counts.get)
        return int(programs.get(ch, 0))
    name = preset_name or f"MIDI: {path.stem}"
    return {
        "name": name,
        "source_filename": path.name,
        "source_path_hint": str(path),
        "bpm": parsed["bpm"],
        "bars": bars,
        "beats_per_bar": beats_per_bar,
        "ticks_per_beat": tpb,
        "key": key,
        "mode": mode,
        "melody_template": "Imported MIDI full contour",
        "melody_coverage": 50,
        "imported_midi_phrase": phrase,
        "imported_midi_info": {
            "source_filename": path.name,
            "note_count_total": len(notes),
            "note_count_imported_melody": len(phrase),
            "melody_channel": mel_ch,
            "estimated_key": key,
            "estimated_mode": mode,
            "import_policy": "Transformed contour only; do not copy original songs/melodies 1:1 unless the user has rights and deliberately permits it.",
        },
        "programs": {
            "bass": common_program("bass"),
            "melody": common_program("melody"),
            "chord": common_program("chord"),
            "pad": common_program("pad"),
        },
    }


def save_imported_midi_preset(path: str | Path, preset_name: str | None = None) -> Path:
    USER_PRESET_DIR.mkdir(parents=True, exist_ok=True)
    preset = analyze_midi_to_preset(path, preset_name)
    out = USER_PRESET_DIR / f"{safe_filename(preset['name'])}.json"
    idx = 2
    while out.exists():
        out = USER_PRESET_DIR / f"{safe_filename(preset['name'])}_{idx:02d}.json"
        idx += 1
    out.write_text(json.dumps(preset, indent=2, ensure_ascii=False), encoding="utf-8")
    return out


def list_imported_midi_presets() -> List[str]:
    if not USER_PRESET_DIR.exists():
        return []
    names = []
    for p in sorted(USER_PRESET_DIR.glob("*.json")):
        try:
            data = json.loads(p.read_text(encoding="utf-8"))
            name = str(data.get("name") or p.stem).strip()
            if name:
                names.append(name)
        except Exception:
            continue
    return names


def load_imported_midi_preset(name: str) -> Dict | None:
    if not USER_PRESET_DIR.exists():
        return None
    for p in sorted(USER_PRESET_DIR.glob("*.json")):
        try:
            data = json.loads(p.read_text(encoding="utf-8"))
            if str(data.get("name") or p.stem) == name:
                return data
        except Exception:
            continue
    return None
