# PythonSoundHelix - GPLv3 Python/PyQt6 reimplementation inspired by SoundHelix.
# This file is part of PythonSoundHelix and is released under GPLv3.

from __future__ import annotations

import json
import time
from pathlib import Path
from typing import Any, Dict, List


class HistoryStore:
    def __init__(self, path: str | Path):
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.records: List[Dict[str, Any]] = []
        self.load()

    def load(self) -> None:
        if not self.path.exists():
            self.records = []
            return
        try:
            data = json.loads(self.path.read_text(encoding="utf-8"))
            self.records = data if isinstance(data, list) else data.get("records", [])
        except Exception:
            self.records = []

    def save(self) -> None:
        self.path.write_text(json.dumps(self.records[-500:], indent=2, ensure_ascii=False), encoding="utf-8")

    def add_result(self, title: str, midi_path: str, settings: Dict[str, Any], note_count: int, seed: int) -> Dict[str, Any]:
        record = {
            "id": f"{int(time.time() * 1000)}_{seed}",
            "created_at": time.strftime("%Y-%m-%d %H:%M:%S"),
            "title": title,
            "midi_path": midi_path,
            "seed": seed,
            "note_count": note_count,
            "rating": 0,
            "settings": settings,
        }
        self.records.append(record)
        self.save()
        return record

    def rate(self, record_id: str, rating: int) -> None:
        for record in self.records:
            if record.get("id") == record_id:
                record["rating"] = 1 if rating > 0 else -1 if rating < 0 else 0
                record["rated_at"] = time.strftime("%Y-%m-%d %H:%M:%S")
                break
        self.save()

    def reset_ratings(self) -> None:
        for record in self.records:
            record["rating"] = 0
            record.pop("rated_at", None)
        self.save()

    def taste_profile(self) -> Dict[str, Any]:
        positives = [r for r in self.records if r.get("rating") == 1]
        if not positives:
            return {"positive_count": 0}
        def avg(field: str, default: float) -> float:
            vals = []
            for r in positives:
                try:
                    vals.append(float(r.get("settings", {}).get(field, default)))
                except Exception:
                    pass
            return sum(vals) / len(vals) if vals else default
        progressions: Dict[str, int] = {}
        modes: Dict[str, int] = {}
        for r in positives:
            s = r.get("settings", {})
            prog = s.get("custom_progression") or s.get("progression")
            if prog:
                progressions[prog] = progressions.get(prog, 0) + 1
            mode = s.get("mode")
            if mode:
                modes[mode] = modes.get(mode, 0) + 1
        favorite_progression = max(progressions, key=progressions.get) if progressions else ""
        favorite_mode = max(modes, key=modes.get) if modes else ""
        return {
            "positive_count": len(positives),
            "avg_bpm": avg("bpm", 120),
            "avg_complexity": avg("complexity", 55),
            "avg_variation": avg("variation", 50),
            "favorite_progression": favorite_progression,
            "favorite_mode": favorite_mode,
        }

    def rows(self) -> List[Dict[str, Any]]:
        return list(reversed(self.records[-200:]))
