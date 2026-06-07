from __future__ import annotations

import json
import re
import sqlite3
import unicodedata
from pathlib import Path
from typing import Dict, List, Optional

ROOT = Path(__file__).resolve().parent.parent
PACKAGED_DB = Path(__file__).resolve().parent / "style_reference.sqlite"
USER_DB_DIR = ROOT / "app_data"
USER_JSONL = USER_DB_DIR / "user_style_references.jsonl"


def normalize(text: str) -> str:
    text = (text or "").lower().replace("ß", "ss").replace("&", " and ")
    text = unicodedata.normalize("NFKD", text)
    text = "".join(c for c in text if not unicodedata.combining(c))
    text = re.sub(r"[^a-z0-9#а-яё]+", " ", text).strip()
    return re.sub(r"\s+", " ", text)


def packaged_reference_count() -> int:
    try:
        with sqlite3.connect(PACKAGED_DB) as conn:
            return int(conn.execute("SELECT COUNT(*) FROM reference_entries").fetchone()[0])
    except Exception:
        return 0


def _row_to_dict(row: sqlite3.Row) -> Dict:
    d = dict(row)
    try:
        d["instruments"] = json.loads(d.get("instruments_json") or "{}")
    except Exception:
        d["instruments"] = {}
    return d


def _score_match(prompt_norm: str, alias_norm: str, confidence: int = 70) -> int:
    if not alias_norm:
        return 0
    if alias_norm == prompt_norm:
        return 250 + confidence
    if re.search(r"(^|\s)" + re.escape(alias_norm) + r"($|\s)", prompt_norm):
        # Multiword specific references should outrank single-word style traits.
        words = max(1, len(alias_norm.split()))
        return 100 + min(80, len(alias_norm)) + words * 15 + confidence // 3
    return 0


def _packaged_candidates(prompt: str, limit: int = 8) -> List[Dict]:
    pnorm = normalize(prompt)
    if not pnorm or not PACKAGED_DB.exists():
        return []
    candidates: List[Dict] = []
    try:
        with sqlite3.connect(PACKAGED_DB) as conn:
            conn.row_factory = sqlite3.Row
            # Scan is acceptable for ~2k rows and avoids fragile FTS dependencies.
            for row in conn.execute("SELECT * FROM reference_entries"):
                d = _row_to_dict(row)
                score = _score_match(pnorm, d.get("normalized_alias", ""), int(d.get("confidence") or 70))
                if score:
                    d["score"] = score
                    candidates.append(d)
    except Exception:
        return []
    candidates.sort(key=lambda x: (int(x.get("score") or 0), len(x.get("normalized_alias") or "")), reverse=True)
    return candidates[:limit]


def _user_candidates(prompt: str, limit: int = 8) -> List[Dict]:
    pnorm = normalize(prompt)
    if not pnorm or not USER_JSONL.exists():
        return []
    out: List[Dict] = []
    try:
        for line in USER_JSONL.read_text(encoding="utf-8").splitlines():
            if not line.strip():
                continue
            d = json.loads(line)
            alias_norm = normalize(d.get("alias") or d.get("canonical_name") or "")
            score = _score_match(pnorm, alias_norm, int(d.get("confidence") or 85)) + 20
            if score:
                d.setdefault("normalized_alias", alias_norm)
                d.setdefault("reference_type", "user")
                d.setdefault("source", "user")
                d["score"] = score
                out.append(d)
    except Exception:
        return []
    out.sort(key=lambda x: (int(x.get("score") or 0), len(x.get("normalized_alias") or "")), reverse=True)
    return out[:limit]


def match_prompt_reference(prompt: str, limit: int = 8) -> Optional[Dict]:
    matches = reference_candidates(prompt, limit=limit)
    return matches[0] if matches else None


def reference_candidates(prompt: str, limit: int = 8) -> List[Dict]:
    matches = _packaged_candidates(prompt, limit=limit * 2) + _user_candidates(prompt, limit=limit * 2)
    matches.sort(key=lambda x: (int(x.get("score") or 0), len(x.get("normalized_alias") or "")), reverse=True)
    return matches[:limit]


def add_user_reference(alias: str, canonical_name: str, style_family: str, traits: str = "", bpm_min: int = 0, bpm_max: int = 0, mode: str = "auto", programs: Optional[Dict] = None) -> Path:
    USER_DB_DIR.mkdir(parents=True, exist_ok=True)
    row = {
        "reference_type": "user",
        "alias": alias.strip(),
        "normalized_alias": normalize(alias),
        "canonical_name": canonical_name.strip() or alias.strip(),
        "style_family": style_family.strip() or "auto",
        "style_id": style_family.strip() or "auto",
        "style_name": canonical_name.strip() or alias.strip(),
        "bpm_min": int(bpm_min or 0) or None,
        "bpm_max": int(bpm_max or 0) or None,
        "mode": mode or "auto",
        "drum_feel": style_family.strip() or "auto",
        "bass_feel": "auto",
        "groove": traits.strip(),
        "instruments": {"programs": programs or {}},
        "intensity": 0,
        "tags": "user_reference;no_cover",
        "traits": traits.strip(),
        "no_copy": 1,
        "confidence": 90,
        "source": "user",
    }
    if not row["alias"]:
        raise ValueError("alias is required")
    with USER_JSONL.open("a", encoding="utf-8") as f:
        f.write(json.dumps(row, ensure_ascii=False) + "\n")
    return USER_JSONL
