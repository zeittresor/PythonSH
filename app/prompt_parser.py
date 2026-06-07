from __future__ import annotations

import json
import random
import re
import unicodedata
from pathlib import Path
from typing import Dict, Iterable, List, Tuple

STYLE_DATA_PATH = Path(__file__).resolve().parent / "prompt_style_words.json"

try:
    from .style_reference_db import match_prompt_reference, reference_candidates, packaged_reference_count
except Exception:  # keeps parser usable if the optional DB is damaged
    match_prompt_reference = None
    reference_candidates = None
    def packaged_reference_count() -> int:
        return 0

KEY_WORDS = {
    "c#": "C#", "cis": "C#", "des": "C#", "db": "C#", "c sharp": "C#",
    "d#": "D#", "dis": "D#", "ees": "D#", "eb": "D#", "d sharp": "D#",
    "f#": "F#", "fis": "F#", "gb": "F#", "f sharp": "F#",
    "g#": "G#", "gis": "G#", "ab": "G#", "g sharp": "G#",
    "a#": "A#", "ais": "A#", "bb": "A#", "b flat": "A#",
    "c": "C", "d": "D", "e": "E", "f": "F", "g": "G", "a": "A", "b": "B", "h": "B",
}

NEGATION_PATTERNS = {
    "drum": ["no drums", "without drums", "ohne drums", "ohne schlagzeug", "keine drums", "keine schlagzeug", "sans batterie", "без ударных"],
    "bass": ["no bass", "without bass", "ohne bass", "kein bass", "sans basse", "без баса"],
    "pad": ["no pad", "without pad", "ohne pad", "keine pads", "sans pad"],
}

INTENSITY_WORDS = {
    "soft": -15, "gentle": -18, "calm": -20, "ruhig": -20, "sanft": -18, "zart": -20, "chill": -16, "relaxed": -18,
    "hard": 18, "heavy": 20, "hart": 18, "aggressiv": 22, "aggressive": 22, "intense": 18, "epic": 12,
}

SPEED_WORDS = {
    "very slow": -42, "langsam": -30, "slow": -28, "downtempo": -26, "ruhig": -18,
    "medium": 0, "midtempo": 0, "fast": 28, "schnell": 28, "rapid": 34, "speed": 38, "uptempo": 24,
    "sehr schnell": 42, "very fast": 42,
}

MOOD_MINOR = ["minor", "moll", "dark", "dunkel", "düster", "duester", "sad", "traurig", "melancholic", "melancholisch", "mysterious", "mystisch", "occult", "okkult"]
MOOD_MAJOR = ["major", "dur", "happy", "fröhlich", "frohlich", "bright", "hell", "uplifting", "positiv", "positive", "sunny", "sommer", "summer"]
SPARSE_WORDS = ["sparse", "minimal", "wenig", "sparsam", "subtle", "subtil", "luftig", "airy"]
DENSE_WORDS = ["dense", "voll", "viel", "busy", "complex", "komplex", "reich", "rich"]
LONG_WORDS = ["long", "lange", "lang", "extended", "epic", "ausgedehnt"]
SHORT_WORDS = ["short", "kurz", "klein", "sketch", "quick"]

ROLE_WORDS = {
    "piano": {"melody": 0, "chord": 0, "pad": 48, "bass": 32},
    "klavier": {"melody": 0, "chord": 0, "pad": 48, "bass": 32},
    "orchestral": {"melody": 40, "chord": 48, "pad": 48, "bass": 43},
    "orchester": {"melody": 40, "chord": 48, "pad": 48, "bass": 43},
    "guitar": {"melody": 27, "chord": 25, "pad": 27, "bass": 33},
    "gitarre": {"melody": 27, "chord": 25, "pad": 27, "bass": 33},
    "chiptune": {"melody": 80, "chord": 81, "pad": 88, "bass": 38},
    "8bit": {"melody": 80, "chord": 81, "pad": 88, "bass": 38},
    "choir": {"melody": 52, "chord": 52, "pad": 52},
    "chor": {"melody": 52, "chord": 52, "pad": 52},
}

STYLE_FALLBACKS = ["Synthwave", "Dark Ambient", "Acid House", "Drum and Bass", "20s Jazz", "House", "Canon Dream", "Piano", "Ambient"]


REFERENCE_FAMILY_MAP = {
    "bigbeat": "dnb", "breakbeat": "dnb", "rave_techno": "techno", "oldschool_rave": "dnb",
    "cinematic_synth": "ambient", "electronic_synth": "trance", "berlin_school": "ambient",
    "french_house": "house", "disco_electronic": "house", "progressive_house": "house", "ambient_house": "ambient",
    "idm": "techno", "downtempo": "ambient", "psybient": "ambient",
    "metal": "band", "thrash_metal": "band", "heavy_metal": "band", "doom_metal": "band", "industrial_metal": "band",
    "hard_rock": "band", "classic_rock": "band", "prog_rock": "band", "grunge": "band", "post_punk": "band",
    "pop_disco": "house", "dance_pop": "house", "pop_funk": "band", "funk_pop": "band", "soul_funk": "band",
    "reggae": "band", "dub": "band", "folk": "band", "jazz": "piano", "jazz_funk": "band",
    "trip_hop": "hiphop", "west_coast_hiphop": "hiphop", "boom_bap": "hiphop", "future_garage": "house",
    "brostep": "dnb", "uplifting_trance": "trance", "synthpop": "house", "industrial": "techno",
}


def canonical_family(family: str) -> str:
    f = normalize(family).replace(" ", "_")
    return REFERENCE_FAMILY_MAP.get(f, f or "auto")


def _style_from_reference(ref: dict, fallback: dict | None = None) -> dict:
    inst = ref.get("instruments") or {}
    programs = inst.get("programs") if isinstance(inst, dict) else {}
    return {
        "id": ref.get("style_id") or canonical_family(ref.get("style_family", "auto")),
        "name": ref.get("style_name") or ref.get("canonical_name") or ref.get("alias") or "Reference",
        "bpm_min": ref.get("bpm_min") or (fallback or {}).get("bpm_min"),
        "bpm_max": ref.get("bpm_max") or (fallback or {}).get("bpm_max"),
        "drum_feel": ref.get("drum_feel") or canonical_family(ref.get("style_family", "auto")),
        "programs": programs or (fallback or {}).get("programs", {}),
        "swing": (fallback or {}).get("swing", 0),
        "meter": (fallback or {}).get("meter", "4/4"),
        "reference": ref,
    }

STYLE_FAMILY_TERMS = {
    "techno": ["techno", "tekkno", "schranz", "minimal tekkno", "acid techno", "hard techno", "detroit techno", "industrial techno"],
    "house": ["house", "deep house", "tech house", "techhouse", "garage house", "french house", "acid house", "disco house", "vocal house", "afro house", "latin house", "amapiano", "ukg", "uk garage"],
    "psytrance": ["goa", "psy", "psytrance", "psy trance", "psychedelic trance"],
    "trance": ["trance", "uplifting trance", "acid trance", "rave", "big room"],
    "dnb": ["drum and bass", "drum n bass", "dran and bass", "drom and bass", "drum an bass", "drumandbass", "dnb", "d n b", "d&b", "jungle", "jump up", "techstep", "liquid dnb", "breakcore"],
    "hardcore": ["hardcore", "happy hardcore", "gabba", "frenchcore", "hardstyle", "speedcore"],
    "ambient": ["ambient", "dark ambient", "meditation", "drone", "spherical", "calm", "pad"],
    "piano": ["piano", "klavier", "walzer", "waltz", "ragtime"],
    "canon": ["canon", "baroque", "orchestral", "orchester", "church", "gospel", "choral", "choir"],
    "band": ["rock", "metal", "punk", "ska", "reggae", "dub", "rockabilly", "indie"],
    "latin": ["latin", "cumbia", "merengue", "tango", "cha cha", "cha-cha", "salsa"],
    "chiptune": ["8-bit", "8bit", "chiptune", "sid", "sid tune"],
    "hiphop": ["hiphop", "hip hop", "trap", "drill", "gangster rap", "rnb", "rhythm and grime", "grime"],
}

DRUM_HARD_WORDS = ["hard drums", "heavy drums", "hard kick", "starker kick", "harte drums", "harte kick", "druckvolle drums", "pounding drums", "relentless kick", "909", "four on the floor", "club kick"]

FAMILY_DEFAULTS = {
    "techno": {"preset": "Minor House", "mode": "minor", "bpm_min": 124, "bpm_max": 148, "template": "Toccata contour", "complexity": 72, "variation": 56},
    "house": {"preset": "Minor House", "mode": "minor", "bpm_min": 118, "bpm_max": 132, "template": "SoundHelix piano contour", "complexity": 62, "variation": 58},
    "psytrance": {"preset": "Minor House", "mode": "minor", "bpm_min": 140, "bpm_max": 150, "template": "Toccata contour", "complexity": 82, "variation": 72},
    "trance": {"preset": "Minor House", "mode": "minor", "bpm_min": 132, "bpm_max": 146, "template": "Toccata contour", "complexity": 68, "variation": 68},
    "dnb": {"preset": "DNB Coherent", "mode": "minor", "bpm_min": 160, "bpm_max": 176, "template": "Toccata contour", "complexity": 76, "variation": 62},
    "hardcore": {"preset": "DNB Coherent", "mode": "minor", "bpm_min": 160, "bpm_max": 190, "template": "Toccata contour", "complexity": 82, "variation": 54},
    "ambient": {"preset": "Calm Ambient", "mode": "minor", "bpm_min": 64, "bpm_max": 94, "template": "SoundHelix piano contour", "complexity": 38, "variation": 52},
    "piano": {"preset": "Night Piano", "mode": "auto", "bpm_min": 72, "bpm_max": 108, "template": "SoundHelix piano contour", "complexity": 45, "variation": 55},
    "canon": {"preset": "Canon Dream", "mode": "major", "bpm_min": 78, "bpm_max": 112, "template": "Canon contour", "complexity": 46, "variation": 48},
    "band": {"preset": "Structured Pop", "mode": "auto", "bpm_min": 88, "bpm_max": 142, "template": "SoundHelix piano contour", "complexity": 58, "variation": 60},
    "latin": {"preset": "Structured Pop", "mode": "major", "bpm_min": 92, "bpm_max": 138, "template": "SoundHelix piano contour", "complexity": 62, "variation": 70},
    "chiptune": {"preset": "Toccata Drive", "mode": "auto", "bpm_min": 120, "bpm_max": 160, "template": "Toccata contour", "complexity": 75, "variation": 70},
    "hiphop": {"preset": "Structured Pop", "mode": "minor", "bpm_min": 70, "bpm_max": 110, "template": "SoundHelix piano contour", "complexity": 50, "variation": 58},
}

SEMANTIC_TAG_TERMS = {
    "dark": ["dark", "dunkel", "duester", "düster", "noir", "sombre", "темн", "darkness"],
    "melodic": ["melodic", "melodisch", "melodique", "мелод"],
    "hard": ["hard", "hart", "heavy", "fett", "fat", "brutal", "aggressive", "aggressiv", "druckvoll"],
    "uplifting": ["uplifting", "euphoric", "euphorisch", "erhebend", "bright", "hell"],
    "acid": ["acid", "acid lead", "303", "tb303", "tb-303"],
    "deep": ["deep", "tief", "sub", "subbass", "sub bass", "reese"],
    "liquid": ["liquid", "smooth", "weich", "atmospheric dnb", "atmospheric drum and bass"],
    "neuro": ["neuro", "neurofunk", "techstep", "darkstep", "reese", "mechanical"],
    "breakbeat": ["breakbeat", "breaks", "amen", "jungle"],
    "no_drums": ["no drums", "ohne drums", "ohne schlagzeug", "sans batterie", "без ударных"],
    "no_bass": ["no bass", "ohne bass", "sans basse", "без баса"],
    "piano": ["piano", "klavier", "grand piano"],
    "orchestral": ["orchestral", "orchester", "orchestra", "symphonic", "sinfonisch"],
    "guitar": ["guitar", "gitarre", "riff"],
    "grunge": ["grunge", "nirvana", "loud quiet", "loud/quiet", "distortion guitar", "alt rock", "alternative rock"],
    "dub": ["dub", "echo", "delay", "reggae dub"],
    "chiptune": ["chiptune", "8bit", "8-bit", "sid", "arcade"],
}

RELATION_RULES = [
    {"id": "dark_melodic_dnb", "family": "dnb", "require_any": ["dnb"], "require_all": ["dark", "melodic"], "bpm": (166, 174), "mode": "minor", "preset": "DNB Coherent", "template": "SoundHelix piano contour", "drum_feel": "dnb_break", "hard_drums": True, "intensity": 20, "vol": {"drum": 94, "bass": 92, "melody": 62, "chord": 46, "pad": 26}, "program": {"drum": 0, "bass": 39, "melody": 81, "chord": 88, "pad": 90}},
    {"id": "liquid_dnb", "family": "dnb", "require_any": ["dnb"], "require_all": ["liquid"], "bpm": (168, 174), "mode": "minor", "preset": "DNB Coherent", "template": "SoundHelix piano contour", "drum_feel": "liquid_break", "hard_drums": False, "intensity": 10, "vol": {"drum": 82, "bass": 84, "melody": 66, "chord": 48, "pad": 42}, "program": {"drum": 0, "bass": 38, "melody": 80, "chord": 88, "pad": 89}},
    {"id": "techstep_dnb", "family": "dnb", "require_any": ["dnb"], "require_all": ["neuro"], "bpm": (170, 176), "mode": "minor", "preset": "DNB Coherent", "template": "Toccata contour", "drum_feel": "techstep_break", "hard_drums": True, "intensity": 26, "vol": {"drum": 98, "bass": 96, "melody": 50, "chord": 38, "pad": 14}, "program": {"drum": 0, "bass": 87, "melody": 81, "chord": 87, "pad": 90}},
    {"id": "goa_techno_psy", "family": "psytrance", "require_any": ["psytrance", "goa"], "require_all": ["techno"], "bpm": (144, 150), "mode": "minor", "preset": "Minor House", "template": "Toccata contour", "drum_feel": "psytrance", "hard_drums": True, "intensity": 28, "vol": {"drum": 112, "bass": 108, "melody": 64, "chord": 52, "pad": 10}, "program": {"drum": 0, "bass": 38, "melody": 81, "chord": 87, "pad": 90}},
    {"id": "acid_techno", "family": "techno", "require_any": ["techno"], "require_all": ["acid"], "bpm": (130, 145), "mode": "minor", "preset": "Minor House", "template": "Toccata contour", "drum_feel": "acid_techno", "hard_drums": True, "intensity": 24, "vol": {"drum": 96, "bass": 92, "melody": 58, "chord": 68, "pad": 12}, "program": {"drum": 0, "bass": 38, "melody": 81, "chord": 87, "pad": 90}},
    {"id": "techno_grunge", "family": "techno", "require_any": ["techno"], "require_all": ["grunge"], "bpm": (126, 138), "mode": "minor", "preset": "Minor House", "template": "Toccata contour", "drum_feel": "techno_rock", "hard_drums": True, "intensity": 18, "vol": {"drum": 94, "bass": 84, "melody": 62, "chord": 76, "pad": 10}, "program": {"drum": 0, "bass": 38, "melody": 30, "chord": 29, "pad": 50}},
    {"id": "dark_ambient_drone", "family": "ambient", "require_any": ["ambient"], "require_all": ["dark"], "bpm": (58, 82), "mode": "minor", "preset": "Calm Ambient", "template": "SoundHelix piano contour", "drum_feel": "none", "hard_drums": False, "intensity": -16, "vol": {"drum": 0, "bass": 44, "melody": 46, "chord": 40, "pad": 72}, "program": {"bass": 32, "melody": 88, "chord": 89, "pad": 91}, "disable": ["drum"]},
    {"id": "reggae_dub", "family": "band", "require_any": ["band"], "require_all": ["dub"], "bpm": (70, 92), "mode": "minor", "preset": "Structured Pop", "template": "SoundHelix piano contour", "drum_feel": "dub", "hard_drums": False, "intensity": 4, "vol": {"drum": 70, "bass": 86, "melody": 54, "chord": 62, "pad": 48}, "program": {"drum": 0, "bass": 34, "melody": 26, "chord": 27, "pad": 89}},
    {"id": "symphonic_metal", "family": "band", "require_any": ["band"], "require_all": ["orchestral"], "bpm": (110, 156), "mode": "minor", "preset": "Structured Pop", "template": "Toccata contour", "drum_feel": "rock", "hard_drums": True, "intensity": 26, "vol": {"drum": 92, "bass": 84, "melody": 66, "chord": 80, "pad": 58}, "program": {"drum": 0, "bass": 34, "melody": 30, "chord": 29, "pad": 48}},
    {"id": "chiptune_arcade", "family": "chiptune", "require_any": ["chiptune"], "require_all": [], "bpm": (130, 168), "mode": "auto", "preset": "Toccata Drive", "template": "Toccata contour", "drum_feel": "chip", "hard_drums": False, "intensity": 12, "vol": {"drum": 68, "bass": 78, "melody": 78, "chord": 66, "pad": 38}, "program": {"drum": 0, "bass": 38, "melody": 80, "chord": 81, "pad": 88}},
]



def normalize(text: str) -> str:
    text = (text or "").lower().replace("ß", "ss")
    text = text.replace("♯", "#").replace("♭", "b")
    text = unicodedata.normalize("NFKD", text)
    text = "".join(c for c in text if not unicodedata.combining(c))
    return text


def canonicalize_prompt_text(text: str) -> tuple[str, list[str]]:
    """Return a typo-tolerant prompt used for matching, plus correction notes.

    v0.7.8: The parser must treat common style typos as intent, not as random
    tokens that accidentally match unrelated references.  Example: "dark melodic
    dran and bass" is overwhelmingly likely to mean "dark melodic drum and
    bass", not Aggrotech.
    """
    original = text or ""
    n = normalize(original)
    notes: list[str] = []
    replacements = [
        (r"\bdran\s*(?:and|n|&)\s*bass\b", "drum and bass", "dran and bass→drum and bass"),
        (r"\bdrom\s*(?:and|n|&)\s*bass\b", "drum and bass", "drom and bass→drum and bass"),
        (r"\bdrum\s+an\s+bass\b", "drum and bass", "drum an bass→drum and bass"),
        (r"\bdrumandbass\b", "drum and bass", "drumandbass→drum and bass"),
        (r"\bd\s*[&+/]\s*b\b", "dnb", "d/b→dnb"),
        (r"\bd\s*n\s*b\b", "dnb", "d n b→dnb"),
        (r"\bjungel\b", "jungle", "jungel→jungle"),
        (r"\bdrum\s*bass\b", "drum and bass", "drum bass→drum and bass"),
        (r"\bdrums\s*(?:and|n|&)\s*bass\b", "drum and bass", "drums and bass→drum and bass"),
        (r"\bdrum\s*['’]?n\s*bass\b", "drum and bass", "drum'n'bass→drum and bass"),
        (r"\btehcno\b", "techno", "tehcno→techno"),
        (r"\btecno\b", "techno", "tecno→techno"),
        (r"\btechnoo\b", "techno", "technoo→techno"),
        (r"\bpsychtrance\b", "psytrance", "psychtrance→psytrance"),
        (r"\bpsitrance\b", "psytrance", "psitrance→psytrance"),
        (r"\bpsy\s*transe\b", "psytrance", "psy transe→psytrance"),
        (r"\bgoar\b", "goa", "goar→goa"),
        (r"\bsynth\s*wave\b", "synthwave", "synth wave→synthwave"),
        (r"\bdark\s*step\b", "techstep", "dark step→techstep"),
    ]
    for pattern, repl, note in replacements:
        new_n = re.sub(pattern, repl, n)
        if new_n != n:
            notes.append(note)
            n = new_n
    return n, notes


def explicit_family_from_prompt(prompt: str) -> str | None:
    n, _ = canonicalize_prompt_text(prompt)
    if phrase_in(n, ["drum and bass", "drum n bass", "dnb", "liquid dnb", "liquid drum and bass", "techstep", "jungle", "jump up"]):
        return "dnb"
    if phrase_in(n, ["goa", "psytrance", "psy trance", "psychedelic trance"]):
        return "psytrance"
    if phrase_in(n, ["techno", "tekkno", "schranz", "acid techno", "hard techno"]):
        return "techno"
    if phrase_in(n, ["house", "deep house", "tech house", "techhouse", "acid house", "french house"]):
        return "house"
    if phrase_in(n, ["trance", "uplifting trance", "acid trance"]):
        return "trance"
    if phrase_in(n, ["ambient", "drone", "dark ambient"]):
        return "ambient"
    if phrase_in(n, ["metal", "heavy metal", "thrash metal", "symphonic metal", "rock", "punk", "ska", "reggae", "dub", "grunge"]):
        return "band"
    if phrase_in(n, ["chiptune", "8bit", "8-bit", "sid tune", "arcade"]):
        return "chiptune"
    if phrase_in(n, ["hiphop", "hip hop", "trap", "drill", "grime", "rnb"]):
        return "hiphop"
    if phrase_in(n, ["latin", "cumbia", "merengue", "tango", "salsa"]):
        return "latin"
    return None


def words(text: str) -> List[str]:
    return re.findall(r"[a-zа-яё0-9#]+", normalize(text), flags=re.IGNORECASE)


def phrase_in(text: str, phrases: Iterable[str]) -> bool:
    n = normalize(text)
    return any(normalize(p) in n for p in phrases)


def style_family_for(style: dict | None, prompt: str = "") -> str:
    sid = normalize((style or {}).get("id") or "")
    name = normalize((style or {}).get("name") or "")
    hay = f"{sid} {name} {normalize(prompt)}"
    for family, terms in STYLE_FAMILY_TERMS.items():
        if any(normalize(t).replace("-", " ") in hay.replace("_", " ").replace("-", " ") for t in terms):
            return family
    return "pop"


def prompt_intensity(prompt: str) -> int:
    score = 0
    norm = normalize(prompt)
    for term, value in INTENSITY_WORDS.items():
        if normalize(term) in norm:
            score += int(value)
    if phrase_in(prompt, DRUM_HARD_WORDS):
        score += 18
    return int(max(-40, min(45, score)))


def hard_drums_requested(prompt: str) -> bool:
    return phrase_in(prompt, DRUM_HARD_WORDS)


def _load_styles() -> List[dict]:
    try:
        data = json.loads(STYLE_DATA_PATH.read_text(encoding="utf-8"))
        return list(data.get("styles", []))
    except Exception:
        return []


def match_style(prompt: str, seed: int) -> Tuple[dict | None, List[Tuple[str, int]]]:
    styles = _load_styles()
    if not styles:
        return None, []
    norm = normalize(prompt)
    w = set(words(prompt))
    scores: List[Tuple[int, dict]] = []
    for st in styles:
        name = normalize(st.get("name") or "")
        toks = set(st.get("tokens") or [])
        score = 0
        if name and name in norm:
            score += 80 + len(name)
        for part in name.split():
            if len(part) > 2 and part in w:
                score += 18
        score += len(w & toks) * 4
        # Strong common shorthand boosts.
        aliases = {
            "drum_and_bass": ["drum and bass", "drum n bass", "dnb"],
            "liquid_dnb": ["liquid drum and bass", "liquid dnb"],
            "dnb": ["drum and bass", "drum n bass", "dnb"],
            "ukg": ["ukg", "uk garage"],
            "8_bit_sound": ["8 bit", "8-bit", "chiptune"],
            "synthwave": ["synthwave", "retrowave"],
            "dark_ambient": ["dark ambient", "dunkler ambient"],
        }
        for sid, phrases in aliases.items():
            if st.get("id") == sid and phrase_in(prompt, phrases):
                score += 90
        fam = style_family_for(st, prompt)
        if hard_drums_requested(prompt) and fam in ("techno", "hardcore", "dnb"):
            score += 18
        if "hard" in w and any(t in name for t in ["schranz", "hard", "gabba", "hardcore"]):
            score += 22
        if score:
            scores.append((score, st))
    scores.sort(key=lambda x: (x[0], x[1].get("name", "")), reverse=True)
    if scores and scores[0][0] >= 12:
        return scores[0][1], [(s.get("name", ""), sc) for sc, s in scores[:5]]
    # Empty / vague prompt: choose a style deterministically from the imported list.
    r = random.Random(seed ^ 0x707070)
    preferred = [s for s in styles if s.get("name") in STYLE_FALLBACKS]
    return r.choice(preferred or styles), []


def _program_from_style(style: dict, role: str) -> int | None:
    programs = style.get("programs") or {}
    if role == "bass":
        return programs.get("bass")
    if role == "melody":
        return programs.get("lead", programs.get("hook", programs.get("pluck")))
    if role == "chord":
        return programs.get("pluck", programs.get("vibe", programs.get("hook")))
    if role == "pad":
        return programs.get("pad", programs.get("echo"))
    return None


def _contains_any(prompt: str, terms: Iterable[str]) -> bool:
    norm = normalize(prompt)
    return any(normalize(t) in norm for t in terms)


def _parse_key(prompt: str) -> str | None:
    norm = normalize(prompt)
    # Match explicit forms first: "in c#", "key c#", "tonart fis".
    m = re.search(r"(?:key|tonart|in|en)\s+([a-g](?:#|b)?|cis|dis|fis|gis|ais|des|es|ees|as|bes|h)\b", norm)
    if m:
        return KEY_WORDS.get(m.group(1), None)
    return None


def _parse_bpm(prompt: str) -> int | None:
    m = re.search(r"\b(?:bpm|tempo)\s*[:=]?\s*(\d{2,3})\b", normalize(prompt))
    if not m:
        m = re.search(r"\b(\d{2,3})\s*bpm\b", normalize(prompt))
    if m:
        return max(48, min(220, int(m.group(1))))
    return None


def _style_to_generic_preset(style: dict | None, prompt: str, seed: int) -> str:
    family = style_family_for(style, prompt)
    if family == "dnb" or family == "hardcore":
        return "DNB Coherent"
    if family in ("techno", "house", "trance", "psytrance"):
        return "Minor House"
    if family == "ambient":
        return "Calm Ambient"
    if family == "piano":
        return "Night Piano"
    if family == "canon":
        return "Canon Dream"
    if family in ("chiptune",):
        return "Toccata Drive"
    if family in ("band", "latin", "hiphop"):
        return "Structured Pop"
    return "Auto Composer"


def style_blend_for_prompt(prompt: str) -> list[str]:
    n = normalize(prompt).replace("_", " ").replace("-", " ")
    out: list[str] = []
    checks = [
        ("goa", ["goa"]),
        ("psytrance", ["psytrance", "psy trance", "psychedelic trance", "psy"]),
        ("techno", ["techno", "tekkno", "acid techno", "hard techno"]),
        ("acid", ["acid", "acid lead", "303"]),
        ("trance", ["trance"]),
        ("hard", ["hard", "fat", "fett", "heavy", "druckvoll"]),
    ]
    for name, terms in checks:
        if name == "trance" and ("goa" in out or "psytrance" in out):
            continue
        if any(t in n for t in terms) and name not in out:
            out.append(name)
    return out


def semantic_tags_for_prompt(prompt: str, family: str | None = None, blend: list[str] | None = None) -> list[str]:
    n = normalize(prompt).replace("_", " ").replace("-", " ")
    tags: list[str] = []
    for fam in (blend or []):
        fam = str(fam).lower().strip()
        if fam and fam not in tags:
            tags.append(fam)
    if family and family not in tags and family != "auto":
        tags.append(family)
    for fam, terms in STYLE_FAMILY_TERMS.items():
        if any(normalize(term).replace("_", " ").replace("-", " ") in n for term in terms):
            if fam not in tags:
                tags.append(fam)
    for tag, terms in SEMANTIC_TAG_TERMS.items():
        if any(normalize(term).replace("_", " ").replace("-", " ") in n for term in terms):
            if tag not in tags:
                tags.append(tag)
    # Cross-style inferences. These are intentionally explicit: users often mix
    # references such as "dark melodic drum and bass" or "goa techno psytrance".
    if "dnb" in tags and "melodic" in tags and "dark" in tags and "dark_melodic" not in tags:
        tags.append("dark_melodic")
    if "psytrance" in tags and "goa" in tags and "goa_psy" not in tags:
        tags.append("goa_psy")
    if "techno" in tags and "hard" in tags and "hard_techno" not in tags:
        tags.append("hard_techno")
    return tags


def relation_profile_for_prompt(prompt: str, family: str, blend: list[str], style: dict | None) -> dict:
    tags = semantic_tags_for_prompt(prompt, family, blend)
    tagset = set(tags)
    # Strongest relation wins. Exact style terms are already in tags/blend.
    for rule in RELATION_RULES:
        any_ok = not rule.get("require_any") or bool(tagset & set(rule.get("require_any", [])))
        all_ok = all(req in tagset for req in rule.get("require_all", []))
        if any_ok and all_ok:
            result = dict(rule)
            result["tags"] = tags
            result["confidence"] = 96 if rule.get("require_all") else 82
            return result
    result = {"id": family or "auto", "family": family or "auto", "tags": tags, "confidence": 65 if family and family != "auto" else 30}
    return result


def apply_relation_profile(settings, relation: dict, notes: list[str]) -> None:
    if not relation:
        return
    profile = str(relation.get("id") or "")
    settings.prompt_relation_profile = profile
    settings.prompt_semantic_tags = list(relation.get("tags") or [])
    settings.prompt_style_confidence = int(relation.get("confidence") or 0)
    if profile:
        notes.append(f"profile={profile}")
    if relation.get("family"):
        settings.prompt_style_family = str(relation["family"])
    if relation.get("preset"):
        settings.preset_name = str(relation["preset"])
    if relation.get("mode"):
        settings.mode = str(relation["mode"])
    if relation.get("template"):
        settings.melody_template = str(relation["template"])
    if relation.get("drum_feel"):
        settings.prompt_drum_feel = str(relation["drum_feel"])
    if relation.get("hard_drums"):
        settings.prompt_hard_drums = True
    if relation.get("intensity") is not None:
        settings.prompt_intensity = max(int(getattr(settings, "prompt_intensity", 0) or 0), int(relation.get("intensity") or 0))
    if relation.get("bpm") and not _parse_bpm(getattr(settings, "prompt", "")):
        lo, hi = relation["bpm"]
        settings.bpm = int(round((int(lo) + int(hi)) / 2))
    for t in getattr(settings, "tracks", []):
        role = getattr(t, "role", "")
        if role in relation.get("disable", []):
            t.enabled = False
        if getattr(t, "lock_instrument", False):
            continue
        if role in relation.get("program", {}):
            t.program = int(max(0, min(127, relation["program"][role])))
        if role in relation.get("vol", {}):
            t.volume = int(max(0, min(127, relation["vol"][role])))

def apply_prompt_to_settings(settings, prompt: str, language: str = "English") -> dict:
    raw_prompt = prompt or ""
    prompt, correction_notes = canonicalize_prompt_text(raw_prompt)
    seed = int(getattr(settings, "seed", 0) or 0)
    explicit_family = explicit_family_from_prompt(prompt)
    style, candidates = match_style(prompt, seed)
    ref = match_prompt_reference(prompt) if match_prompt_reference else None
    ref_candidates = reference_candidates(prompt, limit=5) if reference_candidates else []
    notes: List[str] = []
    notes.extend([f"corrected={n}" for n in correction_notes])
    initial_blend = style_blend_for_prompt(prompt)
    if initial_blend:
        notes.append("blend=" + "+".join(initial_blend))
    ref_family_for_blend = ""
    if ref and explicit_family:
        ref_family = canonical_family(ref.get("style_family") or "")
        ref_type = str(ref.get("reference_type") or "")
        # Explicit style phrases beat vague trait hits. Artist/song refs are kept
        # as trait-blend references, e.g. "techno nirvana" means techno + grunge
        # character, not a cover and not plain Techno.
        if ref_family and ref_family != explicit_family and ref_type == "trait":
            ref = None
            ref_candidates = []
        elif ref_family and ref_family != explicit_family and ref_type in ("artist", "song"):
            raw_ref_family = normalize(ref.get("style_family") or "").replace(" ", "_")
            ref_family_for_blend = raw_ref_family or ref_family
    if ref:
        style = _style_from_reference(ref, style)
        candidates = [(r.get("canonical_name") or r.get("alias") or "reference", int(r.get("score") or 0)) for r in ref_candidates] or candidates
        settings.prompt_reference_name = str(ref.get("canonical_name") or ref.get("alias") or "")
        settings.prompt_reference_type = str(ref.get("reference_type") or "")
        settings.prompt_reference_traits = str(ref.get("traits") or ref.get("groove") or "")
        notes.append(f"reference={settings.prompt_reference_name}")
        notes.append("no_cover=true")
    else:
        settings.prompt_reference_name = ""
        settings.prompt_reference_type = ""
        settings.prompt_reference_traits = ""
    if style:
        family = explicit_family or (canonical_family(ref.get("style_family")) if ref else style_family_for(style, prompt))
        hard_drums = hard_drums_requested(prompt)
        intensity = prompt_intensity(prompt)
        blend = style_blend_for_prompt(prompt)
        if ref_family_for_blend and ref_family_for_blend not in blend:
            blend.append(ref_family_for_blend)
        if explicit_family == "dnb" and "dnb" not in blend:
            blend.append("dnb")
        relation = relation_profile_for_prompt(prompt, family, blend, style)
        if relation.get("family") and relation.get("family") != "auto":
            family = str(relation.get("family"))
        if relation.get("hard_drums"):
            hard_drums = True
        if relation.get("intensity") is not None:
            intensity = max(intensity, int(relation.get("intensity") or 0))
        if family == "dnb":
            hard_drums = True
            intensity = max(intensity, 18 if phrase_in(prompt, ["dark", "hard", "heavy"]) else 10)
        if family == "psytrance" or any(x in normalize(prompt) for x in ["goa", "psytrance", "psy trance", "acid lead", "acid"]):
            hard_drums = True
        if "goa" in blend and "techno" in blend and ("psytrance" in blend or "psy" in normalize(prompt)):
            family = "psytrance"
            hard_drums = True
            intensity = max(intensity, 24)
        notes.append(f"style={style.get('name')}")
        notes.append(f"family={family}")
        settings.prompt_style_id = str(style.get("id") or "")
        settings.prompt_style_name = str(style.get("name") or "")
        settings.prompt_style_family = family
        settings.prompt_style_blend = blend
        settings.prompt_drum_feel = str(style.get("drum_feel") or family)
        settings.prompt_intensity = intensity
        settings.prompt_hard_drums = hard_drums
        settings.preset_name = _style_to_generic_preset(style, prompt, seed)
        settings.key = "Auto"
        defaults = FAMILY_DEFAULTS.get(family, FAMILY_DEFAULTS.get(canonical_family(family), {}))
        settings.mode = str((ref or {}).get("mode") or defaults.get("mode") or "auto")
        apply_relation_profile(settings, relation, notes)
        family = getattr(settings, "prompt_style_family", family) or family
        defaults = FAMILY_DEFAULTS.get(family, FAMILY_DEFAULTS.get(canonical_family(family), defaults))
        if family == "psytrance" or any(x in normalize(prompt) for x in ["goa", "psytrance", "psy trance", "acid"]):
            settings.mode = "minor"
        settings.progression = "Auto mode-safe"
        settings.melody_template = str(defaults.get("template") or "auto")
        lo = int(style.get("bpm_min") or defaults.get("bpm_min") or settings.bpm)
        hi = int(style.get("bpm_max") or defaults.get("bpm_max") or settings.bpm)
        if relation.get("bpm") and not _parse_bpm(prompt):
            lo_rel, hi_rel = relation["bpm"]
            settings.bpm = int((int(lo_rel) + int(hi_rel)) / 2)
        else:
            settings.bpm = int((lo + hi) / 2)
        notes.append(f"bpm≈{settings.bpm}")
        if family in ("techno", "psytrance") and hard_drums:
            settings.bpm = max(settings.bpm, min(150, settings.bpm + 4))
            notes.append("hard_drums=true")
        if (style.get("meter") or "4/4").startswith("3"):
            settings.beats_per_bar = 3
        else:
            settings.beats_per_bar = 4
        if style.get("swing") is not None:
            settings.swing = int(max(0, min(40, float(style.get("swing") or 0) * 100)))
        settings.complexity = int(defaults.get("complexity", settings.complexity))
        settings.variation = int(defaults.get("variation", settings.variation))
        if intensity > 8:
            settings.complexity = min(94, settings.complexity + intensity // 3)
            settings.accent_strength = min(92, getattr(settings, "accent_strength", 52) + intensity // 2)
        if family in ("techno", "hardcore", "psytrance"):
            settings.melody_coverage = min(getattr(settings, "melody_coverage", 50), 38 if family == "psytrance" else 45)
            settings.call_response = False
        for t in getattr(settings, "tracks", []):
            role = getattr(t, "role", "")
            if getattr(t, "lock_instrument", False):
                continue
            prog = _program_from_style(style, role)
            if prog is not None:
                t.program = int(max(0, min(127, prog)))
            if family == "dnb":
                if role == "drum":
                    t.volume = 88
                    t.program = 0
                elif role == "bass":
                    t.volume = 86
                    t.program = 38
                elif role == "melody":
                    t.volume = 58
                elif role == "chord":
                    t.volume = 50
                elif role == "pad":
                    t.volume = 24
            elif family == "psytrance":
                if role == "drum":
                    t.volume = 90
                elif role == "bass":
                    t.volume = 90
                elif role == "melody":
                    t.volume = 68
                elif role == "chord":
                    t.volume = 62
                elif role == "pad":
                    t.volume = 20
            elif family == "techno":
                if role == "drum":
                    t.volume = 86 if hard_drums else 78
                elif role == "bass":
                    t.volume = 78
                elif role == "melody":
                    t.volume = 52
                elif role == "chord":
                    t.volume = 64
                elif role == "pad":
                    t.volume = 24
            elif family == "hardcore":
                if role == "drum": t.volume = 92
                elif role == "bass": t.volume = 82
                elif role == "pad": t.volume = 18
                elif role == "melody": t.volume = 48
            else:
                arp = float(style.get("arp_density") or 0.4)
                pad = float(style.get("pad_density") or 0.4)
                bright = float(style.get("brightness") or 0.5)
                if role == "pad":
                    t.volume = int(max(28, min(70, 34 + pad * 30)))
                if role == "melody":
                    t.volume = int(max(50, min(78, 62 + bright * 16)))
        apply_relation_profile(settings, relation, notes)
    else:
        settings.preset_name = "Auto Composer"
        settings.prompt_style_family = "auto"
        relation = relation_profile_for_prompt(prompt, "auto", style_blend_for_prompt(prompt), None)
        apply_relation_profile(settings, relation, notes)

    bpm = _parse_bpm(prompt)
    if bpm:
        settings.bpm = bpm
        notes.append(f"explicit_bpm={bpm}")
    key = _parse_key(prompt)
    if key:
        settings.key = key
        notes.append(f"key={key}")
    if _contains_any(prompt, MOOD_MINOR):
        settings.mode = "minor"
        notes.append("mode=minor")
    elif _contains_any(prompt, MOOD_MAJOR) and not (getattr(settings, "prompt_style_family", "") == "psytrance" or any(x in normalize(prompt) for x in ["goa", "psytrance", "psy trance", "acid"])):
        settings.mode = "major"
        notes.append("mode=major")

    # Speed words adjust only if no explicit BPM was present.
    if not bpm:
        delta = 0
        norm = normalize(prompt)
        for phrase, value in SPEED_WORDS.items():
            if normalize(phrase) in norm:
                delta += value
        if delta:
            if style and style.get("bpm_min") and style.get("bpm_max"):
                lo, hi = int(style["bpm_min"]), int(style["bpm_max"])
                if delta > 0:
                    settings.bpm = int(max(lo, min(hi, settings.bpm + delta * 0.35)))
                else:
                    settings.bpm = int(max(lo, min(hi, settings.bpm + delta * 0.50)))
            else:
                settings.bpm = int(max(48, min(220, settings.bpm + delta)))
            notes.append(f"speed_delta={delta}")

    if _contains_any(prompt, ["3/4", "waltz", "walzer", "valse"]):
        settings.beats_per_bar = 3
        notes.append("meter=3/4")
    elif _contains_any(prompt, ["4/4", "four on the floor", "club", "dancefloor"]):
        settings.beats_per_bar = 4

    if _contains_any(prompt, LONG_WORDS):
        settings.bars = max(settings.bars, 128)
    if _contains_any(prompt, SHORT_WORDS):
        settings.bars = min(settings.bars, 64)

    if _contains_any(prompt, SPARSE_WORDS):
        settings.complexity = max(25, settings.complexity - 20)
        settings.variation = max(30, settings.variation - 10)
        for t in getattr(settings, "tracks", []):
            if getattr(t, "role", "") in ("chord", "pad", "melody"):
                t.volume = max(28, int(t.volume * 0.86))
        notes.append("density=sparse")
    if _contains_any(prompt, DENSE_WORDS):
        settings.complexity = min(92, settings.complexity + 12)
        settings.variation = min(92, settings.variation + 10)
        notes.append("density=rich")

    # Direct instrument-color words override unlocked tracks.
    norm = normalize(prompt).replace("-", "")
    for term, role_programs in ROLE_WORDS.items():
        if normalize(term).replace("-", "") in norm:
            for t in getattr(settings, "tracks", []):
                prog = role_programs.get(getattr(t, "role", ""))
                if prog is not None and not getattr(t, "lock_instrument", False):
                    t.program = prog
            notes.append(f"instrument_color={term}")

    for role, patterns in NEGATION_PATTERNS.items():
        if phrase_in(prompt, patterns):
            for t in getattr(settings, "tracks", []):
                if getattr(t, "role", "") == role:
                    t.enabled = False
            notes.append(f"disable_{role}=true")

    if phrase_in(prompt, ["only piano", "piano solo", "nur klavier", "solo piano", "nur piano"]):
        for t in getattr(settings, "tracks", []):
            if getattr(t, "role", "") == "drum":
                t.enabled = False
            if getattr(t, "role", "") in ("melody", "chord") and not getattr(t, "lock_instrument", False):
                t.program = 0
            if getattr(t, "role", "") == "pad":
                t.enabled = False
        settings.preset_name = "Night Piano"
        notes.append("arrangement=piano_solo")

    if _contains_any(prompt, ["experimental", "dissonant", "atonal", "schrag", "schräg", "free counterpoint", "frei"]):
        settings.allow_dissonance = True
        notes.append("allow_dissonance=true")
    else:
        settings.allow_dissonance = False

    # Prompt mode should never reuse stale typed titles unless the prompt explicitly asks for a title.
    if not re.search(r"(?:title|titel|named|name it)\s*[:=]", normalize(prompt)):
        settings.title = ""

    if not getattr(settings, "prompt_semantic_tags", None):
        settings.prompt_semantic_tags = semantic_tags_for_prompt(prompt, getattr(settings, "prompt_style_family", "auto"), getattr(settings, "prompt_style_blend", []))
    if not getattr(settings, "prompt_style_confidence", 0):
        settings.prompt_style_confidence = 55 if getattr(settings, "prompt_style_family", "auto") != "auto" else 25
    settings.prompt = prompt
    settings.prompt_language = language
    settings.prompt_interpretation = "; ".join(dict.fromkeys(notes)) if notes else "auto interpretation"
    return {"notes": notes, "style": style, "candidates": candidates}
