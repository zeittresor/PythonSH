# PythonSoundHelix - GPLv3 Python/PyQt6 reimplementation inspired by SoundHelix.
# This file is part of PythonSoundHelix and is released under GPLv3.

from __future__ import annotations

import re
from pathlib import Path
from typing import Dict, List


def summarize_xml(path: str | Path) -> Dict[str, object]:
    path = Path(path)
    text = path.read_text(encoding="utf-8", errors="replace")
    def one(tag: str, default: str = "") -> str:
        m = re.search(rf"<{tag}>(.*?)</{tag}>", text, re.S | re.I)
        return re.sub(r"\s+", " ", m.group(1)).strip() if m else default
    classes = sorted(set(re.findall(r'class="([^"]+)"', text)))
    instruments = re.findall(r"<instrument>(.*?)</instrument>", text, re.S | re.I)
    instruments = [re.sub(r"\s+", " ", x).strip() for x in instruments]
    activity_vectors = re.findall(r'<activityVector\s+name="([^"]+)"', text)
    tracks = len(re.findall(r"<track>", text))
    return {
        "file": path.name,
        "bars": one("bars", "random/implicit"),
        "beats_per_bar": one("beatsPerBar", "4"),
        "ticks_per_beat": one("ticksPerBeat", ""),
        "bpm": one("bpm", "random/implicit"),
        "tracks": tracks,
        "classes": classes,
        "instruments": instruments,
        "activity_vectors": activity_vectors,
        "preview": text[:2500],
    }


def format_summary(summary: Dict[str, object]) -> str:
    lines: List[str] = []
    lines.append(f"File: {summary.get('file')}")
    lines.append(f"Structure: bars={summary.get('bars')} | beats/bar={summary.get('beats_per_bar')} | ticks/beat={summary.get('ticks_per_beat')} | bpm={summary.get('bpm')}")
    lines.append(f"Tracks: {summary.get('tracks')}")
    instruments = summary.get("instruments") or []
    if instruments:
        lines.append("Instruments: " + ", ".join(str(x) for x in instruments[:18]))
    vectors = summary.get("activity_vectors") or []
    if vectors:
        lines.append("Activity vectors: " + ", ".join(str(x) for x in vectors[:24]))
    classes = summary.get("classes") or []
    if classes:
        lines.append("Component classes: " + ", ".join(str(x) for x in classes[:32]))
    lines.append("\nXML preview:\n" + str(summary.get("preview", "")))
    return "\n".join(lines)
