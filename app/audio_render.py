# PythonSoundHelix - GPLv3 Python/PyQt6 reimplementation inspired by SoundHelix.
# Original project: https://www.soundhelix.com/
# This file is part of PythonSoundHelix and is released under GPLv3.

from __future__ import annotations

import math
import shutil
import subprocess
import wave
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, Iterable, List, Sequence, Tuple

from .midi_writer import MidiTrackData
from .models import TrackSettings
from .music_theory import clamp


@dataclass
class RenderNote:
    track_index: int
    role: str
    program: int
    channel: int
    pitch: int
    velocity: int
    start_tick: int
    end_tick: int
    pan: int


def _collect_notes(tracks: Sequence[MidiTrackData], settings: Sequence[TrackSettings]) -> List[RenderNote]:
    notes: List[RenderNote] = []
    for idx, data in enumerate(tracks):
        ts = settings[idx] if idx < len(settings) else TrackSettings(name=data.name, role="melody")
        open_notes: Dict[Tuple[int, int], List[Tuple[int, int]]] = {}
        for ev in sorted(data.events, key=lambda e: (e.tick, 0 if e.kind == "note_on" else 1)):
            if ev.kind == "note_on" and ev.b > 0:
                open_notes.setdefault((ev.channel, ev.a), []).append((ev.tick, ev.b))
            elif ev.kind in ("note_off", "note_on"):
                key = (ev.channel, ev.a)
                if open_notes.get(key):
                    start, vel = open_notes[key].pop(0)
                    if ev.tick > start:
                        notes.append(RenderNote(idx, ts.role.lower(), ts.program, ev.channel, ev.a, vel, start, ev.tick, ts.pan))
        # Close hanging notes defensively.
        for (channel, pitch), starts in open_notes.items():
            for start, vel in starts:
                notes.append(RenderNote(idx, ts.role.lower(), ts.program, channel, pitch, vel, start, start + 240, ts.pan))
    return notes


def _waveform(kind: str, t, freq: float):
    import numpy as np
    phase = 2.0 * math.pi * freq * t
    base = np.sin(phase)
    if kind == "square":
        # Soft square: fewer harsh overtones than sign(sin), therefore less chip/beep-like.
        sig = base + 0.28 * np.sin(3 * phase) + 0.12 * np.sin(5 * phase)
        return np.tanh(sig * 1.05)
    if kind == "saw":
        # Band-limited-ish saw made from a few harmonics. This keeps leads bright but not piercing.
        sig = base
        for h in range(2, 7):
            sig += ((-1) ** (h + 1)) * np.sin(h * phase) / h
        return sig / 1.85
    if kind == "triangle":
        sig = base
        sign = -1.0
        for h in (3, 5, 7):
            sig += sign * np.sin(h * phase) / (h * h)
            sign *= -1.0
        return sig * 0.82
    return base


def _program_wave(program: int, role: str) -> str:
    if role == "bass" or 80 <= program <= 87:
        return "square" if role == "bass" else "saw"
    if role in ("pad", "texture") or 88 <= program <= 99:
        return "sine"
    if role in ("arpeggio", "counter") or program in (8, 10, 11, 12, 112):
        return "triangle"
    if 24 <= program <= 31:
        return "saw"
    return "sine"


def _render_drum(note: RenderNote, frames: int, sr: int, rng_seed: int):
    import numpy as np
    t = np.arange(frames, dtype=np.float32) / float(sr)
    # Deterministic pseudo-noise per note, avoiding Python's slow sample loop.
    rng = np.random.default_rng(rng_seed + note.pitch * 131 + note.start_tick)
    if note.pitch in (35, 36):  # kick
        freq = 62.0 * np.exp(-t * 14.0) + 34.0
        sig = np.sin(2 * np.pi * freq * t) * np.exp(-t * 10.0)
    elif note.pitch in (38, 39, 40):  # snare/clap
        noise = rng.uniform(-1.0, 1.0, frames).astype(np.float32)
        tone = np.sin(2 * np.pi * 185.0 * t)
        sig = (noise * 0.75 + tone * 0.25) * np.exp(-t * 18.0)
    elif note.pitch in (42, 44, 46):  # hats
        noise = rng.uniform(-1.0, 1.0, frames).astype(np.float32)
        sig = noise * np.exp(-t * 45.0)
    elif note.pitch in (49, 51, 57):  # cymbal
        noise = rng.uniform(-1.0, 1.0, frames).astype(np.float32)
        sig = noise * np.exp(-t * 5.0)
    else:  # toms
        freq = 90.0 + (note.pitch - 45) * 12.0
        sig = np.sin(2 * np.pi * freq * t) * np.exp(-t * 9.0)
    return sig.astype(np.float32)


def _render_tonal(note: RenderNote, frames: int, sr: int):
    import numpy as np
    duration = max(1, frames) / float(sr)
    t = np.arange(frames, dtype=np.float32) / float(sr)
    freq = 440.0 * (2.0 ** ((note.pitch - 69) / 12.0))
    kind = _program_wave(note.program, note.role)
    sig = _waveform(kind, t, freq).astype(np.float32)
    if note.role in ("pad", "texture"):
        sig += 0.35 * _waveform("sine", t, freq * 0.5).astype(np.float32)
        sig += 0.18 * _waveform("sine", t, freq * 1.005).astype(np.float32)
        attack = min(frames // 3, int(0.30 * sr))
        release = min(frames // 3, int(0.55 * sr))
    elif note.role in ("bass",):
        sig += 0.22 * _waveform("sine", t, freq * 0.5).astype(np.float32)
        attack = min(frames // 8, int(0.018 * sr))
        release = min(frames // 4, int(0.11 * sr))
    else:
        # Slight body component and slower envelope for leads/counters; this reduces the
        # bare test-oscillator impression of the lightweight renderer.
        if note.role in ("melody", "counter", "arpeggio"):
            sig = sig * 0.84 + 0.10 * _waveform("sine", t, freq * 0.5).astype(np.float32) + 0.06 * _waveform("sine", t, freq * 2.0).astype(np.float32)
        attack = min(frames // 5, int((0.040 if note.role in ("melody", "counter") else 0.025) * sr))
        release = min(frames // 3, int((0.22 if note.role in ("melody", "counter") else 0.16) * sr))
    env = np.ones(frames, dtype=np.float32)
    if attack > 1:
        env[:attack] = np.linspace(0.0, 1.0, attack, dtype=np.float32)
    if release > 1:
        env[-release:] *= np.linspace(1.0, 0.0, release, dtype=np.float32)
    return (sig * env).astype(np.float32)


def render_tracks_to_wav(
    wav_path: str | Path,
    tracks: Sequence[MidiTrackData],
    track_settings: Sequence[TrackSettings],
    bpm: int,
    ticks_per_beat: int,
    total_ticks: int,
    sample_rate: int = 44100,
    progress_callback=None,
) -> str:
    """Render MIDI track data to a simple internal-synth stereo WAV.

    This is intentionally dependency-light and does not need a SoundFont. It is
    not meant to replace a DAW or FluidSynth, but it gives immediate WAV export
    from the generated song on a fresh Windows install. MP3 export is handled
    separately through ffmpeg when available.
    """
    try:
        import numpy as np
    except Exception as exc:  # pragma: no cover
        raise RuntimeError("WAV rendering requires numpy. Run install_windows.bat again.") from exc

    sample_rate = clamp(sample_rate, 8000, 192000)
    sec_per_tick = 60.0 / max(1, bpm) / max(1, ticks_per_beat)
    total_seconds = max(1.0, total_ticks * sec_per_tick + 2.0)
    total_frames = int(total_seconds * sample_rate)
    mix = np.zeros((total_frames, 2), dtype=np.float32)
    notes = _collect_notes(tracks, track_settings)
    if not notes:
        raise RuntimeError("No notes to render.")

    for i, note in enumerate(notes):
        if progress_callback and i % 64 == 0:
            progress_callback(int(92 + 6 * i / max(1, len(notes))), f"Rendering audio {i + 1}/{len(notes)}...")
        start = int(note.start_tick * sec_per_tick * sample_rate)
        end = int(note.end_tick * sec_per_tick * sample_rate)
        if end <= start:
            end = start + max(32, sample_rate // 20)
        end = min(end, total_frames)
        frames = end - start
        if frames <= 0:
            continue
        if note.channel == 9 or note.role == "drum":
            sig = _render_drum(note, frames, sample_rate, rng_seed=1729)
            gain = (note.velocity / 127.0) * 0.72
        else:
            sig = _render_tonal(note, frames, sample_rate)
            role_gain = {
                "bass": 0.48,
                "chord": 0.32,
                "arpeggio": 0.27,
                "melody": 0.32,
                "counter": 0.20,
                "pad": 0.22,
                "texture": 0.18,
            }.get(note.role, 0.34)
            gain = (note.velocity / 127.0) * role_gain
            if note.pitch >= 76 and note.role in ("melody", "counter", "arpeggio", "texture"):
                gain *= 0.74
        pan = max(0.0, min(1.0, note.pan / 127.0))
        left = math.cos(pan * math.pi / 2.0)
        right = math.sin(pan * math.pi / 2.0)
        mix[start:end, 0] += sig * gain * left
        mix[start:end, 1] += sig * gain * right

    peak = float(np.max(np.abs(mix))) if mix.size else 0.0
    if peak > 0:
        mix *= min(0.94 / peak, 1.0)
    pcm = (np.clip(mix, -1.0, 1.0) * 32767.0).astype('<i2')
    wav_path = Path(wav_path)
    wav_path.parent.mkdir(parents=True, exist_ok=True)
    with wave.open(str(wav_path), 'wb') as wf:
        wf.setnchannels(2)
        wf.setsampwidth(2)
        wf.setframerate(sample_rate)
        wf.writeframes(pcm.tobytes())
    return str(wav_path)


def _ffmpeg_run(cmd: List[str]) -> subprocess.CompletedProcess[str]:
    """Run ffmpeg silently so old/broken ffmpeg builds do not spam the GUI console."""
    kwargs = {"stdout": subprocess.PIPE, "stderr": subprocess.PIPE, "text": True}
    if hasattr(subprocess, "CREATE_NO_WINDOW"):
        kwargs["creationflags"] = subprocess.CREATE_NO_WINDOW  # type: ignore[attr-defined]
    return subprocess.run(cmd, **kwargs)


def ffmpeg_available() -> bool:
    ffmpeg = shutil.which("ffmpeg")
    if not ffmpeg:
        return False
    try:
        return _ffmpeg_run([ffmpeg, "-version"]).returncode == 0
    except Exception:
        return False


def convert_wav_to_mp3(wav_path: str | Path, mp3_path: str | Path) -> str:
    ffmpeg = shutil.which("ffmpeg")
    if not ffmpeg:
        raise RuntimeError("ffmpeg was not found in PATH; MP3 export skipped. WAV rendering still works.")

    wav_path = Path(wav_path)
    mp3_path = Path(mp3_path)
    mp3_path.parent.mkdir(parents=True, exist_ok=True)

    # Do not use -hide_banner here. Some older Windows ffmpeg builds reject it and print
    # "Unrecognized option 'hide_banner'" although the WAV render itself succeeded.
    attempts = [
        [ffmpeg, "-y", "-loglevel", "error", "-i", str(wav_path), "-vn", "-codec:a", "libmp3lame", "-q:a", "2", str(mp3_path)],
        [ffmpeg, "-y", "-loglevel", "error", "-i", str(wav_path), "-vn", "-b:a", "192k", str(mp3_path)],
        [ffmpeg, "-y", "-i", str(wav_path), str(mp3_path)],
    ]

    last_error = ""
    for cmd in attempts:
        completed = _ffmpeg_run(cmd)
        if completed.returncode == 0 and mp3_path.exists() and mp3_path.stat().st_size > 0:
            return str(mp3_path)
        last_error = (completed.stderr or completed.stdout or "ffmpeg returned a non-zero exit code").strip()

    if len(last_error) > 400:
        last_error = last_error[:397] + "..."
    raise RuntimeError(f"ffmpeg MP3 conversion failed; WAV was kept. Details: {last_error}")
