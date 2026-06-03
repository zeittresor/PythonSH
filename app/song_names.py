# PythonSoundHelix - GPLv3 Python/PyQt6 reimplementation inspired by SoundHelix.
# Original source basis: SoundHelix SVN archive soundhelix-code-r896-trunk, version 0.10u.
# Original project: https://www.soundhelix.com/
# This file is part of PythonSoundHelix and is released under GPLv3.

from __future__ import annotations

import random
import re
import xml.etree.ElementTree as ET
from pathlib import Path
from typing import Dict, List

FALLBACK_WORDS: Dict[str, List[str]] = {
    "adjective": ["electric", "curious", "midnight", "neon", "analog", "bouncy", "cosmic", "playful", "crystal", "synthetic", "wandering", "binary"],
    "subject": ["engineer", "dreamer", "pilot", "machine", "magician", "robot", "traveller", "signal"],
    "animal": ["cat", "frog", "hamster", "crocodile", "mouse", "owl", "fox", "whale"],
    "ending": ["from outer space", "after midnight", "on the dancefloor", "under glass", "in the future", "from Berlin", "beyond the stars"],
    "city": ["Berlin", "Hamburg", "London", "Paris", "Sydney"],
}

# Avoid a few old demo words that can look unpleasant in a modern GUI file list.
BLOCKED_WORDS = {
    "suicidal", "on drugs", "on acid", "in my pants", "pistol-whipped", "perverted", "idiot", "stupid",
}


def _resource_xml(base_dir: str | Path | None) -> Path | None:
    candidates: List[Path] = []
    if base_dir:
        base = Path(base_dir)
        candidates.append(base / "resources" / "original_soundhelix_examples" / "Standard-SongNameEngine.xml")
        candidates.append(base / "Standard-SongNameEngine.xml")
    here = Path(__file__).resolve()
    candidates.append(here.parents[1] / "resources" / "original_soundhelix_examples" / "Standard-SongNameEngine.xml")
    for path in candidates:
        if path.exists():
            return path
    return None


def load_wordlists(base_dir: str | Path | None = None) -> Dict[str, List[str]]:
    path = _resource_xml(base_dir)
    if not path:
        return {k: v[:] for k, v in FALLBACK_WORDS.items()}
    try:
        root = ET.fromstring(path.read_text(encoding="utf-8"))
    except Exception:
        return {k: v[:] for k, v in FALLBACK_WORDS.items()}
    words: Dict[str, List[str]] = {}
    for var in root.findall(".//variable"):
        name = var.attrib.get("name", "").strip()
        text = (var.text or "").strip()
        if not name or not text or "${" in text and name not in {"ending", "songName"}:
            # Recursive helper variables are intentionally handled by templates below.
            continue
        parts = [p.strip() for p in text.split(",") if p.strip()]
        parts = [p for p in parts if p.lower() not in BLOCKED_WORDS]
        if parts:
            words[name] = parts
    for key, fallback in FALLBACK_WORDS.items():
        words.setdefault(key, fallback[:])
    return words


def _stable_mix(seed: int, text: str) -> int:
    value = seed & 0x7FFFFFFF
    for ch in text:
        value = ((value * 131) + ord(ch)) & 0x7FFFFFFF
    return value


def _pick(rng: random.Random, words: Dict[str, List[str]], key: str) -> str:
    seq = words.get(key) or FALLBACK_WORDS.get(key) or [key]
    value = rng.choice(seq)
    if "${city}" in value:
        value = value.replace("${city}", _pick(rng, words, "city"))
    return value


def _display(text: str) -> str:
    text = re.sub(r"\s+", " ", text).strip(" ,")
    if not text:
        return "Untitled Algorithm"
    # Keep silly SoundHelix wording, but use readable title case for file names.
    small = {"a", "an", "and", "at", "by", "for", "from", "in", "my", "of", "on", "or", "the", "to", "under", "with", "without"}
    parts = []
    for i, word in enumerate(text.split(" ")):
        low = word.lower()
        if i > 0 and low in small:
            parts.append(low)
        elif word.startswith("("):
            parts.append(word)
        else:
            parts.append(word[:1].upper() + word[1:])
    return " ".join(parts)


def generate_song_name(seed: int, preset_name: str = "", base_dir: str | Path | None = None) -> str:
    """Generate a deterministic SoundHelix-style random song title.

    The original project used a configurable SongNameEngine. This Python version
    loads the bundled GPLv3 Standard-SongNameEngine.xml word lists when available
    and expands a compatible subset with deterministic seeding.
    """
    words = load_wordlists(base_dir)
    rng = random.Random(_stable_mix(seed, preset_name or "PythonSoundHelix"))
    ending = _pick(rng, words, "ending")
    optional = f", {ending}" if rng.random() < 0.62 else ""
    adj1 = _pick(rng, words, "adjective")
    adj2 = _pick(rng, words, "adjective")
    adj3 = _pick(rng, words, "adjective")
    subject = _pick(rng, words, "subject")
    animal = _pick(rng, words, "animal")
    templates = [
        f"{adj1} {subject}'s {adj2} {animal}{optional}",
        f"The {adj1} {subject}{optional}",
        f"The {adj1} {animal}{optional}",
        f"{adj1} and {adj2}",
        f"{adj1} {animal} {ending}",
        f"The {adj1} {adj2} {subject}",
        f"{adj1} {subject} and the {adj3} {animal}",
    ]
    return _display(rng.choice(templates))
