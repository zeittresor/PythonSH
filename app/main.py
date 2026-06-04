# PythonSoundHelix - GPLv3 Python/PyQt6 reimplementation inspired by SoundHelix.
# Original source basis: SoundHelix SVN archive soundhelix-code-r896-trunk, version 0.10u.
# Original project: https://www.soundhelix.com/
# This file is part of PythonSoundHelix and is released under GPLv3.

from __future__ import annotations

import argparse
import json
import os
import platform
import subprocess
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional

from . import __version__
from .audio_render import ffmpeg_available
from .generator import generate_song
from .history import HistoryStore
from .models import GeneratorSettings, TrackSettings
from .music_theory import GM_PROGRAMS, clamp
from .presets import get_preset, preset_names, xml_reference_files
from .xml_tools import format_summary, summarize_xml

ROOT = Path(__file__).resolve().parents[1]
OUTPUT_DIR = ROOT / "output"
APP_DATA = ROOT / "app_data"
HISTORY_PATH = APP_DATA / "generation_history.json"

ROLE_OPTIONS = ["drum", "bass", "chord", "arpeggio", "melody", "pad", "counter", "texture"]
PATTERN_OPTIONS = [
    "auto", "template", "electro four", "four", "soft four", "broken electro", "sync eighth", "eighth",
    "stab", "block", "long", "updown", "up", "down", "answer", "spark", "guitar",
    "amiga four", "tracker hats", "acid pulse", "random gate", "tracker arp",
    "algomusic drums", "digit progression",
]


def _theme(bg: str, fg: str, panel: str, input_bg: str, accent: str, accent2: str, border: str) -> str:
    return f"""
QMainWindow, QWidget {{ background: {bg}; color: {fg}; font-size: 10pt; }}
QGroupBox {{ background: {panel}; border: 1px solid {border}; border-radius: 9px; margin-top: 12px; padding: 10px; font-weight: bold; }}
QGroupBox::title {{ subcontrol-origin: margin; left: 12px; padding: 0 6px; color: {fg}; }}
QPushButton {{ background: {accent}; color: white; border: 0; border-radius: 7px; padding: 8px 12px; }}
QPushButton:hover {{ background: {accent2}; }}
QPushButton:disabled {{ background: {border}; color: #9499a5; }}
QLineEdit, QTextEdit, QComboBox, QSpinBox, QTableWidget {{ background: {input_bg}; color: {fg}; border: 1px solid {border}; border-radius: 6px; padding: 4px; selection-background-color: {accent}; }}
QHeaderView::section {{ background: {panel}; color: {fg}; padding: 5px; border: 0; }}
QTabWidget::pane {{ border: 1px solid {border}; }}
QTabBar::tab {{ background: {panel}; color: {fg}; padding: 9px 14px; border-top-left-radius: 7px; border-top-right-radius: 7px; }}
QTabBar::tab:selected {{ background: {accent}; color: white; }}
QProgressBar {{ border: 1px solid {border}; border-radius: 6px; text-align: center; background: {input_bg}; }}
QProgressBar::chunk {{ background: {accent}; border-radius: 5px; }}
QToolTip {{ background: {input_bg}; color: {fg}; border: 1px solid {accent}; padding: 5px; }}
"""

THEMES = {
    "Dark": _theme("#17191f", "#e7eaf0", "#1f2330", "#222631", "#2f6fed", "#3d7cff", "#3b4050"),
    "Light": _theme("#f3f5f8", "#17202a", "#ffffff", "#ffffff", "#2866d8", "#497fe5", "#c8ced8"),
    "Hell": _theme("#1c0808", "#ffe8d8", "#2b0b0b", "#370f0f", "#c73518", "#f05a28", "#73251a"),
    "Matrix": _theme("#020805", "#b8ffd2", "#06150c", "#071c10", "#00994f", "#00c96a", "#0b5d35"),
    "Ocean": _theme("#071924", "#e1f7ff", "#0b2838", "#10364a", "#1586b8", "#1ba6df", "#21566f"),
    "Avatar": _theme("#070d18", "#e7f6ff", "#0b1c30", "#102b45", "#1f8cd6", "#4eb7ff", "#28587a"),
    "Amiga MUI": _theme("#8a8a8a", "#050505", "#b8b8b8", "#d8d8d8", "#315f9e", "#4a79bd", "#555555"),
    "MagicWB": _theme("#6f7895", "#080a10", "#9da6c0", "#c2c8d8", "#314a84", "#5a6fa8", "#3a4258"),
}

TRANSLATIONS: Dict[str, Dict[str, str]] = {
    "en": {
        "tab_generate": "Generate", "tab_tracks": "Tracks", "tab_options": "Options", "tab_history": "History / Ratings", "tab_xml": "Original XML Inspector", "tab_log": "Log",
        "menu_file": "File", "menu_help": "Help", "save_project_menu": "Save project JSON...", "load_project_menu": "Load project JSON...", "open_output_menu": "Open output folder", "about_menu": "About / License",
        "group_generator": "Generator", "group_harmony": "Harmony / structure", "group_perf": "Performance / advanced", "group_audio": "Audio / loudness", "group_ui": "Interface", "group_presets": "Preset notes",
        "preset": "Preset", "song_title": "Song title", "seed": "Seed", "bpm": "BPM", "bars": "Bars", "beats": "Beats per bar", "tpb": "Ticks per beat",
        "key": "Key", "mode": "Mode", "progression": "Progression", "custom_progression": "Custom progression", "harmonic": "Harmonic rhythm", "sections": "Sections", "melody_template": "Melody template",
        "complexity": "Complexity", "variation": "Variation", "swing": "Swing", "motif": "Motif memory", "accent": "Accent", "human_ticks": "Humanize ticks", "human_vel": "Humanize velocity",
        "lfo": "LFO expression CC", "call_response": "call/response melody", "bass_roots": "bass favors chord roots", "markers": "section markers", "export_json": "export JSON result", "export_chords": "export chord sheet", "rating_memory": "use thumbs-up rating memory",
        "generate": "Generate Song", "play_midi": "Play MIDI", "play_audio": "Render/Play WAV/MP3", "open_output": "Open output folder", "save_project": "Save project", "load_project": "Load project", "rate_good": "👍 Rate good", "rate_bad": "👎 Rate bad",
        "normalize_loudness": "Normalize instrument loudness", "normalize_target": "Target velocity", "normalize_strength": "Normalize strength", "range_guard": "Auto octave/range guard", "max_melody_pitch": "Max melody pitch", "render_wav": "Render WAV", "render_mp3": "Render MP3", "sample_rate": "Sample rate", "ffmpeg_status": "MP3 encoder", "theme": "Theme", "language": "Language",
        "tracks_info": "Tracks are editable. Use the instrument dropdown per row to choose GM instruments. Channel 10 is MIDI drum channel; internally it is shown as 9 because MIDI channels are 0-based.",
        "add_track": "Add melody track", "remove_track": "Remove selected", "normalize_channels": "Normalize channels", "history_play": "Play selected", "history_load": "Load selected settings", "reset_ratings": "Reset all ratings",
        "xml_note": "These XML files are bundled as GPLv3 reference/preset material. The Python generator does not require Java.", "xml_label": "Bundled original SoundHelix XML references",
        "random_seed": "randomize on generate", "history_up": "👍 selected", "history_down": "👎 selected", "ready": "Ready.", "generating": "Generating...", "rendering_audio": "No audio file exists yet; rendering WAV now...", "already_rendering": "Audio rendering is already running.", "no_tracks": "No tracks configured.", "already_running": "Generation is already running.", "generate_first": "Generate a song first.",
        "tooltip_title": "Leave this blank to create a deterministic SoundHelix-style random title during generation.",
        "tooltip_normalize": "Moves normal notes of each instrument toward a similar average level, while preserving strong accents/fills.",
        "tooltip_range_guard": "Keeps melody, counter and arpeggio voices in a less piercing register by folding runaway notes down an octave instead of deleting them.",
        "tooltip_max_melody_pitch": "Upper pitch limit for melodic voices when the range guard is enabled. 79 is G5; higher values sound brighter.",
        "tooltip_render_wav": "Renders the MIDI through a lightweight built-in synth to a WAV file. No SoundFont is required.",
        "tooltip_render_mp3": "Creates an MP3 from the rendered WAV when ffmpeg is installed and available in PATH.",
        "tooltip_theme": "Switches the GUI color theme immediately.", "tooltip_language": "Switches visible GUI labels and button text between English and German.",
    },
    "de": {
        "tab_generate": "Generieren", "tab_tracks": "Spuren", "tab_options": "Optionen", "tab_history": "Historie / Bewertungen", "tab_xml": "Original-XML-Inspector", "tab_log": "Log",
        "menu_file": "Datei", "menu_help": "Hilfe", "save_project_menu": "Projekt-JSON speichern...", "load_project_menu": "Projekt-JSON laden...", "open_output_menu": "Ausgabeordner öffnen", "about_menu": "Über / Lizenz",
        "group_generator": "Generator", "group_harmony": "Harmonie / Struktur", "group_perf": "Performance / Erweitert", "group_audio": "Audio / Lautstärke", "group_ui": "Oberfläche", "group_presets": "Preset-Hinweise",
        "preset": "Preset", "song_title": "Songtitel", "seed": "Seed", "bpm": "BPM", "bars": "Takte", "beats": "Schläge pro Takt", "tpb": "Ticks pro Schlag",
        "key": "Tonart", "mode": "Modus", "progression": "Akkordfolge", "custom_progression": "Eigene Akkordfolge", "harmonic": "Harmoniewechsel", "sections": "Songteile", "melody_template": "Melodievorlage",
        "complexity": "Komplexität", "variation": "Variation", "swing": "Swing", "motif": "Motivgedächtnis", "accent": "Akzent", "human_ticks": "Timing-Humanize", "human_vel": "Velocity-Humanize",
        "lfo": "LFO Expression CC", "call_response": "Call/Response-Melodie", "bass_roots": "Bass bevorzugt Grundtöne", "markers": "Songteil-Marker", "export_json": "JSON-Ergebnis exportieren", "export_chords": "Akkordblatt exportieren", "rating_memory": "Daumen-hoch-Lerndaten nutzen",
        "generate": "Song generieren", "play_midi": "MIDI abspielen", "play_audio": "WAV/MP3 rendern/abspielen", "open_output": "Ausgabeordner öffnen", "save_project": "Projekt speichern", "load_project": "Projekt laden", "rate_good": "👍 Gut bewerten", "rate_bad": "👎 Schlecht bewerten",
        "normalize_loudness": "Instrument-Lautstärke normalisieren", "normalize_target": "Ziel-Velocity", "normalize_strength": "Normalisierungsstärke", "range_guard": "Auto-Oktav-/Tonlagen-Schutz", "max_melody_pitch": "Max. Melodietonhöhe", "render_wav": "WAV rendern", "render_mp3": "MP3 rendern", "sample_rate": "Samplerate", "ffmpeg_status": "MP3-Encoder", "theme": "Theme", "language": "Sprache",
        "tracks_info": "Spuren sind editierbar. Über das Instrument-Dropdown pro Zeile kannst du GM-Instrumente wählen. MIDI-Kanal 10 ist der Drum-Kanal; intern wird er als 9 angezeigt, weil MIDI-Kanäle 0-basiert sind.",
        "add_track": "Melodiespur hinzufügen", "remove_track": "Auswahl entfernen", "normalize_channels": "Kanäle normalisieren", "history_play": "Auswahl abspielen", "history_load": "Auswahl laden", "reset_ratings": "Bewertungen zurücksetzen",
        "xml_note": "Diese XML-Dateien sind als GPLv3-Referenz-/Presetmaterial enthalten. Der Python-Generator benötigt kein Java.", "xml_label": "Mitgelieferte originale SoundHelix-XML-Referenzen",
        "random_seed": "beim Generieren randomisieren", "history_up": "👍 Auswahl", "history_down": "👎 Auswahl", "ready": "Bereit.", "generating": "Generiere...", "rendering_audio": "Es existiert noch keine Audiodatei; WAV wird jetzt gerendert...", "already_rendering": "Audio-Rendering läuft bereits.", "no_tracks": "Keine Spuren konfiguriert.", "already_running": "Die Generierung läuft bereits.", "generate_first": "Bitte zuerst einen Song generieren.",
        "tooltip_title": "Leer lassen, damit beim Generieren automatisch ein SoundHelix-artiger Zufallstitel entsteht.",
        "tooltip_normalize": "Bringt normale Noten aller Instrumente näher auf eine Durchschnittslautstärke, lässt starke Akzente/Fills aber weitgehend stehen.",
        "tooltip_range_guard": "Hält Melodie-, Antwort- und Arpeggio-Stimmen in einer weniger spitzen Tonlage, indem Ausreißer eine Oktave heruntergefaltet werden.",
        "tooltip_max_melody_pitch": "Obergrenze für melodische Stimmen, wenn der Tonlagen-Schutz aktiv ist. 79 entspricht G5; höhere Werte klingen heller.",
        "tooltip_render_wav": "Rendert das MIDI über einen einfachen eingebauten Synth als WAV. Kein SoundFont nötig.",
        "tooltip_render_mp3": "Erzeugt aus der WAV-Datei eine MP3, wenn ffmpeg installiert und im PATH verfügbar ist.",
        "tooltip_theme": "Schaltet das Farbschema der GUI sofort um.", "tooltip_language": "Schaltet sichtbare GUI-Texte zwischen Deutsch und Englisch um.",
    },
}


def tr(lang: str, key: str) -> str:
    return TRANSLATIONS.get(lang, TRANSLATIONS["en"]).get(key, TRANSLATIONS["en"].get(key, key))


def open_path(path: str | Path) -> None:
    path = str(path)
    if not path:
        return
    if platform.system() == "Windows":
        os.startfile(path)  # type: ignore[attr-defined]
    elif platform.system() == "Darwin":
        subprocess.Popen(["open", path])
    else:
        subprocess.Popen(["xdg-open", path])


try:
    from PyQt6.QtCore import Qt, QThread, pyqtSignal
    from PyQt6.QtGui import QAction
    from PyQt6.QtWidgets import (
        QApplication, QAbstractItemView, QCheckBox, QComboBox, QFileDialog, QFormLayout,
        QGridLayout, QGroupBox, QHBoxLayout, QHeaderView, QLabel, QLineEdit, QMainWindow,
        QMessageBox, QProgressBar, QPushButton, QScrollArea, QSpinBox, QTabWidget,
        QTableWidget, QTableWidgetItem, QTextEdit, QVBoxLayout, QWidget,
    )
except Exception:  # pragma: no cover - allows --nogui diagnostics without PyQt6 installed.
    QApplication = None  # type: ignore

    class _DummySignal:
        def connect(self, *args, **kwargs): pass
        def emit(self, *args, **kwargs): pass

    def pyqtSignal(*args, **kwargs):  # type: ignore
        return _DummySignal()

    class _DummyThread:
        def __init__(self, *args, **kwargs): pass
        def start(self): pass
        def isRunning(self): return False

    class _DummyWidget:
        def __init__(self, *args, **kwargs): pass
        def __getattr__(self, name):
            def _method(*args, **kwargs): return None
            return _method

    QThread = _DummyThread  # type: ignore
    QMainWindow = _DummyWidget  # type: ignore
    QTableWidgetItem = _DummyWidget  # type: ignore
    class _DummyQt:
        class ItemFlag:
            ItemIsEditable = 1
        class CheckState:
            Checked = 2
            Unchecked = 0
        class ItemDataRole:
            UserRole = 32
    Qt = _DummyQt()  # type: ignore


class GenerateWorker(QThread):
    progress = pyqtSignal(int, str)
    done = pyqtSignal(object)
    failed = pyqtSignal(str)

    def __init__(self, settings: GeneratorSettings, output_dir: Path, taste_profile: dict):
        super().__init__()
        self.settings = settings
        self.output_dir = output_dir
        self.taste_profile = taste_profile

    def run(self) -> None:
        try:
            result = generate_song(self.settings, self.output_dir, self.taste_profile, self.progress.emit)
            self.done.emit(result)
        except Exception as exc:
            self.failed.emit(f"{type(exc).__name__}: {exc}")


class RenderAudioWorker(QThread):
    progress = pyqtSignal(int, str)
    done = pyqtSignal(object)
    failed = pyqtSignal(str)

    def __init__(self, settings: GeneratorSettings, output_dir: Path, taste_profile: dict):
        super().__init__()
        self.settings = settings
        self.output_dir = output_dir
        self.taste_profile = taste_profile

    def run(self) -> None:
        try:
            # Re-run the deterministic generator with the same title/seed and only add audio files.
            # This keeps the button useful even when WAV/MP3 export was not enabled during generation.
            result = generate_song(self.settings, self.output_dir, self.taste_profile, self.progress.emit)
            self.done.emit(result)
        except Exception as exc:
            self.failed.emit(f"{type(exc).__name__}: {exc}")


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.lang = "en"
        self.theme = "Dark"
        self.labels: Dict[str, QLabel] = {}
        self.group_titles: List[tuple[QGroupBox, str]] = []
        self.tab_keys: List[str] = []
        self.tooltip_widgets: List[tuple[QWidget, str]] = []
        self.history = HistoryStore(HISTORY_PATH)
        self.current_settings = get_preset(preset_names()[0])
        self.current_result = None
        self.current_record_id = ""
        self.worker: Optional[GenerateWorker] = None
        self.audio_worker: Optional[RenderAudioWorker] = None
        self.setWindowTitle(f"PythonSoundHelix v{__version__} - PyQt6 GPLv3")
        self.resize(1360, 880)
        self._build_ui()
        self.apply_settings_to_ui(self.current_settings)
        self.refresh_history_table()
        self.refresh_xml_list()
        self.apply_theme("Dark")
        self.apply_language("en")

    def _label(self, key: str) -> QLabel:
        lbl = QLabel(key)
        self.labels[key] = lbl
        return lbl

    def _row(self, form: QFormLayout, key: str, widget: QWidget) -> None:
        form.addRow(self._label(key), widget)

    def _group(self, key: str) -> QGroupBox:
        box = QGroupBox(key)
        self.group_titles.append((box, key))
        return box

    def _tip(self, widget: QWidget, key: str) -> None:
        self.tooltip_widgets.append((widget, key))

    def _scroll_tab(self, content: QWidget) -> QScrollArea:
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setWidget(content)
        return scroll

    def _add_tab(self, widget: QWidget, key: str) -> None:
        self.tabs.addTab(widget, key)
        self.tab_keys.append(key)

    def _build_ui(self) -> None:
        central = QWidget()
        root = QVBoxLayout(central)
        self.tabs = QTabWidget()
        root.addWidget(self.tabs)
        self.setCentralWidget(central)
        self._build_generate_tab()
        self._build_tracks_tab()
        self._build_options_tab()
        self._build_history_tab()
        self._build_xml_tab()
        self._build_log_tab()
        self._build_menu()

    def _build_menu(self) -> None:
        self.file_menu = self.menuBar().addMenu("File")
        self.save_project_action = QAction("Save project JSON...", self)
        self.save_project_action.triggered.connect(self.save_project)
        self.load_project_action = QAction("Load project JSON...", self)
        self.load_project_action.triggered.connect(self.load_project)
        self.open_output_action = QAction("Open output folder", self)
        self.open_output_action.triggered.connect(lambda: open_path(OUTPUT_DIR))
        self.file_menu.addAction(self.save_project_action)
        self.file_menu.addAction(self.load_project_action)
        self.file_menu.addSeparator()
        self.file_menu.addAction(self.open_output_action)
        self.help_menu = self.menuBar().addMenu("Help")
        self.about_action = QAction("About / License", self)
        self.about_action.triggered.connect(self.show_about)
        self.help_menu.addAction(self.about_action)

    def _build_generate_tab(self) -> None:
        tab = QWidget(); outer = QVBoxLayout(tab)
        top = QHBoxLayout(); outer.addLayout(top)

        general = self._group("group_generator"); form = QFormLayout(general)
        self.preset_combo = QComboBox(); self.preset_combo.addItems(preset_names()); self.preset_combo.currentTextChanged.connect(self.load_preset_by_name)
        self.title_edit = QLineEdit(); self.title_edit.setPlaceholderText("auto title when blank")
        self._tip(self.title_edit, "tooltip_title")
        self.seed_spin = QSpinBox(); self.seed_spin.setRange(0, 2_147_483_647)
        self.random_seed_check = QCheckBox("randomize on generate")
        seed_row = QHBoxLayout(); seed_row.addWidget(self.seed_spin); seed_row.addWidget(self.random_seed_check)
        seed_widget = QWidget(); seed_widget.setLayout(seed_row)
        self.bpm_spin = QSpinBox(); self.bpm_spin.setRange(40, 240)
        self.bars_spin = QSpinBox(); self.bars_spin.setRange(8, 512); self.bars_spin.setSingleStep(8)
        self.beats_spin = QSpinBox(); self.beats_spin.setRange(2, 12)
        self.tpb_spin = QSpinBox(); self.tpb_spin.setRange(12, 1920); self.tpb_spin.setSingleStep(12)
        for key, widget in [("preset", self.preset_combo), ("song_title", self.title_edit), ("seed", seed_widget), ("bpm", self.bpm_spin), ("bars", self.bars_spin), ("beats", self.beats_spin), ("tpb", self.tpb_spin)]:
            self._row(form, key, widget)
        top.addWidget(general, 1)

        harmony = self._group("group_harmony"); hform = QFormLayout(harmony)
        self.key_combo = QComboBox(); self.key_combo.addItems(["C", "C#", "D", "Eb", "E", "F", "F#", "G", "Ab", "A", "Bb", "B"])
        self.mode_combo = QComboBox(); self.mode_combo.addItems(["major", "minor", "dorian", "mixolydian", "phrygian", "lydian", "pentatonic major", "pentatonic minor", "blues"])
        self.progression_combo = QComboBox(); self.progression_combo.setEditable(True)
        self.progression_combo.addItems(["I,V,vi,IV", "I,vi,IV,V", "i,VII,VI,V", "I,V,vi,iii,IV,I,IV,V", "I,bVII,IV,I", "i,VI,III,VII", "Am/10,G/2,F/2,Am/12,G/2,F/2,Am/2,+C/8,Em/2,D/2,C/12,Em/2,D/2,C/4"])
        self.custom_progression = QLineEdit(); self.custom_progression.setPlaceholderText("Optional override, e.g. I,V,vi,IV or Am,G,F,Em")
        self.harmonic_spin = QSpinBox(); self.harmonic_spin.setRange(1, 8)
        self.section_spin = QSpinBox(); self.section_spin.setRange(3, 64)
        self.melody_template_combo = QComboBox(); self.melody_template_combo.addItems(["auto", "Popcorn-style original pulse", "Ode-to-Joy public-domain hint", "Fuer-Elise public-domain hint", "Canon public-domain hint", "Toccata public-domain hint", "Original arcade anthem", "AlgoMusic tracker pulse", "AlgoMusic house chord riff", "AlgoMusic random walk", "AlgoMusic digit progression"])
        for key, widget in [("key", self.key_combo), ("mode", self.mode_combo), ("progression", self.progression_combo), ("custom_progression", self.custom_progression), ("harmonic", self.harmonic_spin), ("sections", self.section_spin), ("melody_template", self.melody_template_combo)]:
            self._row(hform, key, widget)
        top.addWidget(harmony, 1)

        performance = self._group("group_perf"); grid = QGridLayout(performance)
        self.complexity_spin = QSpinBox(); self.complexity_spin.setRange(1, 100)
        self.variation_spin = QSpinBox(); self.variation_spin.setRange(1, 100)
        self.swing_spin = QSpinBox(); self.swing_spin.setRange(0, 60)
        self.motif_spin = QSpinBox(); self.motif_spin.setRange(0, 100)
        self.accent_spin = QSpinBox(); self.accent_spin.setRange(0, 100)
        self.human_ticks_spin = QSpinBox(); self.human_ticks_spin.setRange(0, 80)
        self.human_vel_spin = QSpinBox(); self.human_vel_spin.setRange(0, 40)
        self.lfo_check = QCheckBox(); self.call_response_check = QCheckBox(); self.bass_roots_check = QCheckBox(); self.markers_check = QCheckBox(); self.export_json_check = QCheckBox(); self.export_chords_check = QCheckBox(); self.rating_memory_check = QCheckBox()
        for i, (key, widget) in enumerate([("complexity", self.complexity_spin), ("variation", self.variation_spin), ("swing", self.swing_spin), ("motif", self.motif_spin), ("accent", self.accent_spin), ("human_ticks", self.human_ticks_spin), ("human_vel", self.human_vel_spin)]):
            lbl = self._label(key); grid.addWidget(lbl, i, 0); grid.addWidget(widget, i, 1)
        for i, (key, check) in enumerate([("lfo", self.lfo_check), ("call_response", self.call_response_check), ("bass_roots", self.bass_roots_check), ("markers", self.markers_check), ("export_json", self.export_json_check), ("export_chords", self.export_chords_check), ("rating_memory", self.rating_memory_check)]):
            check.setText(key); grid.addWidget(check, i, 2)
        outer.addWidget(performance)

        buttons = QHBoxLayout()
        self.generate_btn = QPushButton(); self.generate_btn.clicked.connect(self.generate_clicked)
        self.play_btn = QPushButton(); self.play_btn.clicked.connect(self.play_last_midi)
        self.play_audio_btn = QPushButton(); self.play_audio_btn.clicked.connect(self.play_last_audio)
        self.open_output_btn = QPushButton(); self.open_output_btn.clicked.connect(lambda: open_path(OUTPUT_DIR))
        self.save_project_btn = QPushButton(); self.save_project_btn.clicked.connect(self.save_project)
        self.load_project_btn = QPushButton(); self.load_project_btn.clicked.connect(self.load_project)
        self.thumb_up_btn = QPushButton(); self.thumb_up_btn.clicked.connect(lambda: self.rate_current(1))
        self.thumb_down_btn = QPushButton(); self.thumb_down_btn.clicked.connect(lambda: self.rate_current(-1))
        for b in [self.generate_btn, self.play_btn, self.play_audio_btn, self.open_output_btn, self.save_project_btn, self.load_project_btn, self.thumb_up_btn, self.thumb_down_btn]:
            buttons.addWidget(b)
        outer.addLayout(buttons)
        self.progress = QProgressBar(); self.progress.setRange(0, 100); outer.addWidget(self.progress)
        self.summary_box = QTextEdit(); self.summary_box.setReadOnly(True); self.summary_box.setMinimumHeight(170); outer.addWidget(self.summary_box)
        self._add_tab(self._scroll_tab(tab), "tab_generate")

    def _build_tracks_tab(self) -> None:
        tab = QWidget(); layout = QVBoxLayout(tab)
        self.tracks_info = QLabel(); self.tracks_info.setWordWrap(True); layout.addWidget(self.tracks_info)
        self.track_table = QTableWidget(0, 12)
        self.track_table.setHorizontalHeaderLabels(["Enabled", "Name", "Role", "Instrument", "Volume", "Pan", "Octave", "Density", "Complexity", "Activity", "Pattern", "Channel"])
        self.track_table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        self.track_table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        layout.addWidget(self.track_table)
        row = QHBoxLayout()
        self.add_track_btn = QPushButton(); self.add_track_btn.clicked.connect(self.add_track)
        self.remove_track_btn = QPushButton(); self.remove_track_btn.clicked.connect(self.remove_track)
        self.normalize_channels_btn = QPushButton(); self.normalize_channels_btn.clicked.connect(self.normalize_channels)
        row.addWidget(self.add_track_btn); row.addWidget(self.remove_track_btn); row.addWidget(self.normalize_channels_btn); row.addStretch(1)
        layout.addLayout(row)
        self._add_tab(tab, "tab_tracks")

    def _build_options_tab(self) -> None:
        tab = QWidget(); layout = QVBoxLayout(tab)
        audio = self._group("group_audio"); aform = QFormLayout(audio)
        self.normalize_check = QCheckBox(); self._tip(self.normalize_check, "tooltip_normalize")
        self.normalize_target_spin = QSpinBox(); self.normalize_target_spin.setRange(35, 120)
        self.normalize_strength_spin = QSpinBox(); self.normalize_strength_spin.setRange(0, 100)
        self.range_guard_check = QCheckBox(); self._tip(self.range_guard_check, "tooltip_range_guard")
        self.max_melody_pitch_spin = QSpinBox(); self.max_melody_pitch_spin.setRange(60, 96); self._tip(self.max_melody_pitch_spin, "tooltip_max_melody_pitch")
        self.render_wav_check = QCheckBox(); self._tip(self.render_wav_check, "tooltip_render_wav")
        self.render_mp3_check = QCheckBox(); self._tip(self.render_mp3_check, "tooltip_render_mp3")
        self.sample_rate_spin = QSpinBox(); self.sample_rate_spin.setRange(8000, 192000); self.sample_rate_spin.setSingleStep(1000)
        self.ffmpeg_label = QLabel("ffmpeg: " + ("available" if ffmpeg_available() else "not found"))
        for key, widget in [("normalize_loudness", self.normalize_check), ("normalize_target", self.normalize_target_spin), ("normalize_strength", self.normalize_strength_spin), ("range_guard", self.range_guard_check), ("max_melody_pitch", self.max_melody_pitch_spin), ("render_wav", self.render_wav_check), ("render_mp3", self.render_mp3_check), ("sample_rate", self.sample_rate_spin), ("ffmpeg_status", self.ffmpeg_label)]:
            self._row(aform, key, widget)
        layout.addWidget(audio)

        ui = self._group("group_ui"); uform = QFormLayout(ui)
        self.theme_combo = QComboBox(); self.theme_combo.addItems(list(THEMES.keys())); self.theme_combo.currentTextChanged.connect(self.apply_theme); self._tip(self.theme_combo, "tooltip_theme")
        self.language_combo = QComboBox(); self.language_combo.addItem("English", "en"); self.language_combo.addItem("Deutsch", "de"); self.language_combo.currentIndexChanged.connect(self._language_combo_changed); self._tip(self.language_combo, "tooltip_language")
        self._row(uform, "theme", self.theme_combo); self._row(uform, "language", self.language_combo)
        layout.addWidget(ui)
        notes = self._group("group_presets"); nlayout = QVBoxLayout(notes)
        self.preset_notes = QTextEdit(); self.preset_notes.setReadOnly(True); self.preset_notes.setMinimumHeight(220)
        nlayout.addWidget(self.preset_notes)
        layout.addWidget(notes)
        layout.addStretch(1)
        self._add_tab(self._scroll_tab(tab), "tab_options")

    def _build_history_tab(self) -> None:
        tab = QWidget(); layout = QVBoxLayout(tab)
        self.history_table = QTableWidget(0, 7)
        self.history_table.setHorizontalHeaderLabels(["Rating", "Created", "Title", "Seed", "Notes", "Preset", "MIDI path"])
        self.history_table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        self.history_table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        layout.addWidget(self.history_table)
        row = QHBoxLayout()
        self.hist_play_btn = QPushButton(); self.hist_play_btn.clicked.connect(self.play_selected_history)
        self.hist_load_btn = QPushButton(); self.hist_load_btn.clicked.connect(self.load_selected_history_settings)
        self.hist_up_btn = QPushButton("👍 selected"); self.hist_up_btn.clicked.connect(lambda: self.rate_selected_history(1))
        self.hist_down_btn = QPushButton("👎 selected"); self.hist_down_btn.clicked.connect(lambda: self.rate_selected_history(-1))
        self.reset_ratings_btn = QPushButton(); self.reset_ratings_btn.clicked.connect(self.reset_ratings)
        for b in [self.hist_play_btn, self.hist_load_btn, self.hist_up_btn, self.hist_down_btn, self.reset_ratings_btn]: row.addWidget(b)
        row.addStretch(1); layout.addLayout(row)
        self.profile_box = QTextEdit(); self.profile_box.setReadOnly(True); self.profile_box.setMaximumHeight(130); layout.addWidget(self.profile_box)
        self._add_tab(tab, "tab_history")

    def _build_xml_tab(self) -> None:
        tab = QWidget(); layout = QHBoxLayout(tab)
        left = QVBoxLayout(); self.xml_label = QLabel(); self.xml_combo = QComboBox(); self.xml_combo.currentTextChanged.connect(self.xml_selected)
        left.addWidget(self.xml_label); left.addWidget(self.xml_combo)
        self.xml_note = QLabel(); self.xml_note.setWordWrap(True); left.addWidget(self.xml_note); left.addStretch(1)
        layout.addLayout(left, 1)
        self.xml_preview = QTextEdit(); self.xml_preview.setReadOnly(True); layout.addWidget(self.xml_preview, 3)
        self._add_tab(tab, "tab_xml")

    def _build_log_tab(self) -> None:
        tab = QWidget(); layout = QVBoxLayout(tab)
        self.log_box = QTextEdit(); self.log_box.setReadOnly(True); layout.addWidget(self.log_box)
        self._add_tab(tab, "tab_log")

    def apply_language(self, lang: str) -> None:
        self.lang = lang if lang in TRANSLATIONS else "en"
        for idx, key in enumerate(self.tab_keys):
            self.tabs.setTabText(idx, tr(self.lang, key))
        for box, key in self.group_titles:
            box.setTitle(tr(self.lang, key))
        for key, label in self.labels.items():
            label.setText(tr(self.lang, key))
        for widget, key in self.tooltip_widgets:
            widget.setToolTip(tr(self.lang, key))
        self.file_menu.setTitle(tr(self.lang, "menu_file")); self.help_menu.setTitle(tr(self.lang, "menu_help"))
        self.save_project_action.setText(tr(self.lang, "save_project_menu")); self.load_project_action.setText(tr(self.lang, "load_project_menu")); self.open_output_action.setText(tr(self.lang, "open_output_menu")); self.about_action.setText(tr(self.lang, "about_menu"))
        for key, check in [("lfo", self.lfo_check), ("call_response", self.call_response_check), ("bass_roots", self.bass_roots_check), ("markers", self.markers_check), ("export_json", self.export_json_check), ("export_chords", self.export_chords_check), ("rating_memory", self.rating_memory_check), ("normalize_loudness", self.normalize_check), ("range_guard", self.range_guard_check), ("render_wav", self.render_wav_check), ("render_mp3", self.render_mp3_check)]:
            check.setText(tr(self.lang, key))
        for key, btn in [("generate", self.generate_btn), ("play_midi", self.play_btn), ("play_audio", self.play_audio_btn), ("open_output", self.open_output_btn), ("save_project", self.save_project_btn), ("load_project", self.load_project_btn), ("rate_good", self.thumb_up_btn), ("rate_bad", self.thumb_down_btn), ("add_track", self.add_track_btn), ("remove_track", self.remove_track_btn), ("normalize_channels", self.normalize_channels_btn), ("history_play", self.hist_play_btn), ("history_load", self.hist_load_btn), ("history_up", self.hist_up_btn), ("history_down", self.hist_down_btn), ("reset_ratings", self.reset_ratings_btn)]:
            btn.setText(tr(self.lang, key))
        self.random_seed_check.setText(tr(self.lang, "random_seed"));
        self.tracks_info.setText(tr(self.lang, "tracks_info")); self.xml_note.setText(tr(self.lang, "xml_note")); self.xml_label.setText(tr(self.lang, "xml_label"))
        if self.summary_box.toPlainText() in ("Ready.", "Bereit."):
            self.summary_box.setText(tr(self.lang, "ready"))
        self._update_preset_notes()

    def _language_combo_changed(self) -> None:
        self.apply_language(self.language_combo.currentData() or "en")

    def apply_theme(self, theme_name: str) -> None:
        self.theme = theme_name if theme_name in THEMES else "Dark"
        if QApplication.instance():
            QApplication.instance().setStyleSheet(THEMES[self.theme])

    def _update_preset_notes(self) -> None:
        names = preset_names()
        self.preset_notes.setText("\n".join(f"- {name}" for name in names))

    def log(self, text: str) -> None:
        self.log_box.append(text)

    def load_preset_by_name(self, name: str) -> None:
        if not name:
            return
        self.current_settings = get_preset(name)
        self.apply_settings_to_ui(self.current_settings, keep_combo=True)

    def apply_settings_to_ui(self, s: GeneratorSettings, keep_combo: bool = False) -> None:
        if not keep_combo:
            idx = self.preset_combo.findText(s.preset_name)
            if idx >= 0:
                self.preset_combo.setCurrentIndex(idx)
        self.title_edit.setText(s.title)
        self.seed_spin.setValue(s.seed); self.random_seed_check.setChecked(s.randomize_seed)
        self.bpm_spin.setValue(s.bpm); self.bars_spin.setValue(s.bars); self.beats_spin.setValue(s.beats_per_bar); self.tpb_spin.setValue(s.ticks_per_beat)
        self.key_combo.setCurrentText(s.key); self.mode_combo.setCurrentText(s.mode); self.progression_combo.setCurrentText(s.progression); self.custom_progression.setText(s.custom_progression)
        self.harmonic_spin.setValue(s.harmonic_rhythm); self.section_spin.setValue(s.section_count); self.melody_template_combo.setCurrentText(s.melody_template)
        self.complexity_spin.setValue(s.complexity); self.variation_spin.setValue(s.variation); self.swing_spin.setValue(s.swing)
        self.motif_spin.setValue(s.motif_memory); self.accent_spin.setValue(s.accent_strength); self.human_ticks_spin.setValue(s.humanize_ticks); self.human_vel_spin.setValue(s.humanize_velocity)
        self.lfo_check.setChecked(s.lfo_expression); self.call_response_check.setChecked(s.call_response); self.bass_roots_check.setChecked(s.keep_bass_on_roots)
        self.markers_check.setChecked(s.add_markers); self.export_json_check.setChecked(s.export_json); self.export_chords_check.setChecked(s.export_chord_sheet); self.rating_memory_check.setChecked(s.use_rating_memory)
        self.normalize_check.setChecked(s.normalize_velocity); self.normalize_target_spin.setValue(s.normalize_target); self.normalize_strength_spin.setValue(s.normalize_strength)
        self.range_guard_check.setChecked(getattr(s, "auto_range_guard", True)); self.max_melody_pitch_spin.setValue(getattr(s, "max_melody_pitch", 79))
        self.render_wav_check.setChecked(s.render_wav); self.render_mp3_check.setChecked(s.render_mp3); self.sample_rate_spin.setValue(s.audio_sample_rate)
        if s.ui_theme in THEMES:
            self.theme_combo.setCurrentText(s.ui_theme); self.apply_theme(s.ui_theme)
        lang_idx = self.language_combo.findData(s.language)
        if lang_idx >= 0:
            self.language_combo.setCurrentIndex(lang_idx); self.apply_language(s.language)
        self.populate_track_table(s.tracks)
        self.summary_box.setText(s.description or tr(self.lang, "ready"))

    def settings_from_ui(self) -> GeneratorSettings:
        s = GeneratorSettings()
        s.preset_name = self.preset_combo.currentText() or "Custom"
        s.title = self.title_edit.text().strip()
        s.seed = self.seed_spin.value(); s.randomize_seed = self.random_seed_check.isChecked()
        s.bpm = self.bpm_spin.value(); s.bars = self.bars_spin.value(); s.beats_per_bar = self.beats_spin.value(); s.ticks_per_beat = self.tpb_spin.value()
        s.key = self.key_combo.currentText(); s.mode = self.mode_combo.currentText(); s.progression = self.progression_combo.currentText().strip() or "I,V,vi,IV"; s.custom_progression = self.custom_progression.text().strip()
        s.harmonic_rhythm = self.harmonic_spin.value(); s.section_count = self.section_spin.value(); s.melody_template = self.melody_template_combo.currentText()
        s.complexity = self.complexity_spin.value(); s.variation = self.variation_spin.value(); s.swing = self.swing_spin.value(); s.motif_memory = self.motif_spin.value(); s.accent_strength = self.accent_spin.value(); s.humanize_ticks = self.human_ticks_spin.value(); s.humanize_velocity = self.human_vel_spin.value()
        s.lfo_expression = self.lfo_check.isChecked(); s.call_response = self.call_response_check.isChecked(); s.keep_bass_on_roots = self.bass_roots_check.isChecked(); s.add_markers = self.markers_check.isChecked(); s.export_json = self.export_json_check.isChecked(); s.export_chord_sheet = self.export_chords_check.isChecked(); s.use_rating_memory = self.rating_memory_check.isChecked()
        s.normalize_velocity = self.normalize_check.isChecked(); s.normalize_target = self.normalize_target_spin.value(); s.normalize_strength = self.normalize_strength_spin.value(); s.auto_range_guard = self.range_guard_check.isChecked(); s.max_melody_pitch = self.max_melody_pitch_spin.value(); s.render_wav = self.render_wav_check.isChecked(); s.render_mp3 = self.render_mp3_check.isChecked(); s.audio_sample_rate = self.sample_rate_spin.value(); s.ui_theme = self.theme; s.language = self.lang
        s.tracks = self.tracks_from_table()
        return s

    def populate_track_table(self, tracks: List[TrackSettings]) -> None:
        self.track_table.setRowCount(0)
        for t in tracks:
            self._append_track_row(t)

    def _item(self, text: str, editable: bool = True) -> QTableWidgetItem:
        item = QTableWidgetItem(text)
        if not editable:
            item.setFlags(item.flags() & ~Qt.ItemFlag.ItemIsEditable)
        return item

    def _program_combo(self, program: int) -> QComboBox:
        combo = QComboBox()
        combo.addItem("Drum Kit / Percussion", 0)
        for name, num in sorted(GM_PROGRAMS.items(), key=lambda kv: kv[1]):
            combo.addItem(f"{num:03d} - {name}", num)
        idx = combo.findData(program)
        combo.setCurrentIndex(idx if idx >= 0 else 0)
        return combo

    def _simple_combo(self, values: List[str], current: str) -> QComboBox:
        combo = QComboBox(); combo.addItems(values)
        idx = combo.findText(current)
        if idx < 0 and current:
            combo.addItem(current)
            idx = combo.findText(current)
        combo.setCurrentIndex(idx if idx >= 0 else 0)
        return combo

    def _append_track_row(self, t: TrackSettings) -> None:
        row = self.track_table.rowCount(); self.track_table.insertRow(row)
        enabled = QTableWidgetItem("yes"); enabled.setCheckState(Qt.CheckState.Checked if t.enabled else Qt.CheckState.Unchecked); self.track_table.setItem(row, 0, enabled)
        self.track_table.setItem(row, 1, self._item(t.name))
        self.track_table.setCellWidget(row, 2, self._simple_combo(ROLE_OPTIONS, t.role))
        self.track_table.setCellWidget(row, 3, self._program_combo(t.program))
        for col, value in [(4, t.volume), (5, t.pan), (6, t.octave), (7, t.density), (8, t.complexity), (9, t.activity), (11, t.channel)]:
            self.track_table.setItem(row, col, self._item(str(value)))
        self.track_table.setCellWidget(row, 10, self._simple_combo(PATTERN_OPTIONS, t.pattern))

    def tracks_from_table(self) -> List[TrackSettings]:
        tracks: List[TrackSettings] = []
        for row in range(self.track_table.rowCount()):
            def text(col: int, default: str = "") -> str:
                item = self.track_table.item(row, col)
                return item.text().strip() if item else default
            def combo_text(col: int, default: str = "") -> str:
                w = self.track_table.cellWidget(row, col)
                return w.currentText() if isinstance(w, QComboBox) else default
            def combo_data(col: int, default: int = 0) -> int:
                w = self.track_table.cellWidget(row, col)
                return int(w.currentData()) if isinstance(w, QComboBox) and w.currentData() is not None else default
            def try_int(value: str, default: int, lo: int, hi: int) -> int:
                try:
                    return clamp(int(value), lo, hi)
                except Exception:
                    return default
            enabled_item = self.track_table.item(row, 0)
            enabled = enabled_item.checkState() == Qt.CheckState.Checked if enabled_item else True
            tracks.append(TrackSettings(
                name=text(1, "Track"), role=combo_text(2, "melody"), enabled=enabled,
                channel=try_int(text(11, "0"), 0, 0, 15), program=combo_data(3, 0),
                volume=try_int(text(4, "90"), 90, 1, 127), pan=try_int(text(5, "64"), 64, 0, 127), octave=try_int(text(6, "0"), 0, -4, 4), density=try_int(text(7, "70"), 70, 0, 100), complexity=try_int(text(8, "55"), 55, 0, 100), activity=try_int(text(9, "80"), 80, 0, 100), pattern=combo_text(10, "auto"),
            ))
        return tracks

    def add_track(self) -> None:
        channels = {t.channel for t in self.tracks_from_table()}
        ch = next((i for i in range(16) if i not in channels and i != 9), 7)
        self._append_track_row(TrackSettings(name="New Melody", role="melody", channel=ch, program=80, volume=88, pan=64, density=60, complexity=55, activity=70))

    def remove_track(self) -> None:
        rows = sorted({idx.row() for idx in self.track_table.selectedIndexes()}, reverse=True)
        for row in rows:
            self.track_table.removeRow(row)

    def normalize_channels(self) -> None:
        next_channel = 0
        for row in range(self.track_table.rowCount()):
            role = self.track_table.cellWidget(row, 2).currentText().lower() if isinstance(self.track_table.cellWidget(row, 2), QComboBox) else ""
            ch = 9 if role == "drum" else next_channel
            if role != "drum":
                next_channel += 1
                if next_channel == 9: next_channel += 1
                next_channel = min(next_channel, 15)
            self.track_table.setItem(row, 11, self._item(str(ch)))

    def generate_clicked(self) -> None:
        if self.worker and self.worker.isRunning():
            QMessageBox.information(self, "PythonSoundHelix", tr(self.lang, "already_running")); return
        settings = self.settings_from_ui()
        if not settings.tracks:
            QMessageBox.warning(self, "PythonSoundHelix", tr(self.lang, "no_tracks")); return
        self.progress.setValue(0); self.generate_btn.setEnabled(False); self.summary_box.setText(tr(self.lang, "generating"))
        self.worker = GenerateWorker(settings, OUTPUT_DIR, self.history.taste_profile())
        self.worker.progress.connect(self.on_progress); self.worker.done.connect(self.on_done); self.worker.failed.connect(self.on_failed); self.worker.start()

    def on_progress(self, value: int, text: str) -> None:
        self.progress.setValue(value); self.log(text)

    def on_done(self, result) -> None:
        self.generate_btn.setEnabled(True); self.current_result = result; self.seed_spin.setValue(result.seed); self.title_edit.setText(result.title)
        record = self.history.add_result(result.title, result.midi_path, result.settings.to_dict(), result.note_count, result.seed); self.current_record_id = record["id"]
        self.summary_box.setText(self._result_text(result)); self.refresh_history_table(); self.log(f"Generated: {result.midi_path}")
        if result.render_log:
            self.log(result.render_log)

    def on_failed(self, message: str) -> None:
        self.generate_btn.setEnabled(True); self.progress.setValue(0); self.summary_box.setText(message); QMessageBox.critical(self, "Generation failed", message)

    def _result_text(self, result) -> str:
        lines = [result.summary(), "", f"MIDI: {result.midi_path}"]
        if result.wav_path: lines.append(f"WAV: {result.wav_path}")
        if result.mp3_path: lines.append(f"MP3: {result.mp3_path}")
        if result.json_path: lines.append(f"JSON: {result.json_path}")
        if result.chord_sheet_path: lines.append(f"Chord sheet: {result.chord_sheet_path}")
        if result.render_log: lines += ["", f"Audio render: {result.render_log}"]
        lines.append(""); lines.append("Sections: " + ", ".join(f"{s.name} {s.bars} bars" for s in result.sections)); lines.append("First chords: " + ", ".join(f"{c.bar+1}:{c.symbol}" for c in result.chords[:16]))
        return "\n".join(lines)

    def play_last_midi(self) -> None:
        if self.current_result and self.current_result.midi_path: open_path(self.current_result.midi_path)
        else: QMessageBox.information(self, "PythonSoundHelix", tr(self.lang, "generate_first"))

    def _existing_audio_path(self) -> str:
        if not self.current_result:
            return ""
        for path in [self.current_result.mp3_path, self.current_result.wav_path]:
            if path and Path(path).exists():
                return path
        return ""

    def play_last_audio(self) -> None:
        path = self._existing_audio_path()
        if path:
            open_path(path); return
        if self.current_result and self.current_result.midi_path:
            self.render_audio_for_playback(); return
        QMessageBox.information(self, "PythonSoundHelix", tr(self.lang, "generate_first"))

    def render_audio_for_playback(self) -> None:
        if self.audio_worker and self.audio_worker.isRunning():
            QMessageBox.information(self, "PythonSoundHelix", tr(self.lang, "already_rendering")); return
        if not self.current_result:
            QMessageBox.information(self, "PythonSoundHelix", tr(self.lang, "generate_first")); return
        settings = GeneratorSettings.from_dict(self.current_result.settings.to_dict())
        settings.title = self.current_result.title
        settings.seed = self.current_result.seed
        settings.randomize_seed = False
        settings.render_wav = True
        settings.render_mp3 = self.render_mp3_check.isChecked()
        settings.audio_sample_rate = self.sample_rate_spin.value()
        self.summary_box.append("\n" + tr(self.lang, "rendering_audio"))
        self.progress.setValue(0)
        self.play_audio_btn.setEnabled(False)
        self.generate_btn.setEnabled(False)
        self.audio_worker = RenderAudioWorker(settings, OUTPUT_DIR, self.history.taste_profile())
        self.audio_worker.progress.connect(self.on_progress)
        self.audio_worker.done.connect(self.on_audio_done)
        self.audio_worker.failed.connect(self.on_audio_failed)
        self.audio_worker.start()

    def on_audio_done(self, result) -> None:
        self.play_audio_btn.setEnabled(True)
        self.generate_btn.setEnabled(True)
        self.current_result = result
        self.summary_box.setText(self._result_text(result))
        if result.render_log:
            self.log(result.render_log)
        path = self._existing_audio_path()
        if path:
            self.log(f"Audio ready: {path}")
            open_path(path)
        else:
            QMessageBox.warning(self, "PythonSoundHelix", result.render_log or "Audio rendering finished, but no WAV/MP3 file was created.")

    def on_audio_failed(self, message: str) -> None:
        self.play_audio_btn.setEnabled(True)
        self.generate_btn.setEnabled(True)
        self.progress.setValue(0)
        QMessageBox.critical(self, "Audio render failed", message)

    def rate_current(self, rating: int) -> None:
        if not self.current_record_id:
            QMessageBox.information(self, "PythonSoundHelix", "No generated song selected for rating."); return
        self.history.rate(self.current_record_id, rating); self.refresh_history_table()

    def refresh_history_table(self) -> None:
        rows = self.history.rows(); self.history_table.setRowCount(0)
        for r in rows:
            row = self.history_table.rowCount(); self.history_table.insertRow(row)
            rating = "👍" if r.get("rating") == 1 else "👎" if r.get("rating") == -1 else ""
            values = [rating, r.get("created_at", ""), r.get("title", ""), str(r.get("seed", "")), str(r.get("note_count", "")), r.get("settings", {}).get("preset_name", ""), r.get("midi_path", "")]
            for col, value in enumerate(values):
                item = self._item(str(value), editable=False); item.setData(Qt.ItemDataRole.UserRole, r.get("id", "")); self.history_table.setItem(row, col, item)
        self.profile_box.setText(json.dumps(self.history.taste_profile(), indent=2, ensure_ascii=False))

    def _selected_history_record(self) -> Optional[Dict[str, Any]]:
        rows = {idx.row() for idx in self.history_table.selectedIndexes()}
        if not rows: return None
        item = self.history_table.item(min(rows), 0); rid = item.data(Qt.ItemDataRole.UserRole) if item else ""
        for record in self.history.records:
            if record.get("id") == rid: return record
        return None

    def play_selected_history(self) -> None:
        r = self._selected_history_record()
        if r and r.get("midi_path"): open_path(r["midi_path"])

    def load_selected_history_settings(self) -> None:
        r = self._selected_history_record()
        if r and r.get("settings"): self.apply_settings_to_ui(GeneratorSettings.from_dict(r["settings"]))

    def rate_selected_history(self, rating: int) -> None:
        r = self._selected_history_record()
        if r: self.history.rate(r["id"], rating); self.refresh_history_table()

    def reset_ratings(self) -> None:
        self.history.reset_ratings(); self.refresh_history_table()

    def save_project(self) -> None:
        path, _ = QFileDialog.getSaveFileName(self, "Save PythonSoundHelix project", str(ROOT / "project.psh.json"), "PythonSoundHelix JSON (*.json)")
        if path: Path(path).write_text(json.dumps(self.settings_from_ui().to_dict(), indent=2, ensure_ascii=False), encoding="utf-8")

    def load_project(self) -> None:
        path, _ = QFileDialog.getOpenFileName(self, "Load PythonSoundHelix project", str(ROOT), "PythonSoundHelix JSON (*.json)")
        if path: self.apply_settings_to_ui(GeneratorSettings.from_dict(json.loads(Path(path).read_text(encoding="utf-8"))))

    def refresh_xml_list(self) -> None:
        self.xml_combo.clear(); files = xml_reference_files(ROOT)
        for path in files: self.xml_combo.addItem(path.name, str(path))
        if files: self.xml_selected(files[0].name)

    def xml_selected(self, _: str) -> None:
        path = self.xml_combo.currentData()
        if not path: return
        try: self.xml_preview.setText(format_summary(summarize_xml(path)))
        except Exception as exc: self.xml_preview.setText(str(exc))

    def show_about(self) -> None:
        QMessageBox.about(self, "About PythonSoundHelix", f"""PythonSoundHelix v{__version__}\n\nGPLv3 Python/PyQt6 reimplementation and expansion inspired by SoundHelix.\n\nOriginal project: https://www.soundhelix.com/\nOriginal source archive basis: soundhelix-code-r896-trunk / SoundHelix 0.10u.\nHistorical inspiration: Thomas Schürger's Amiga AlgoMusic 2.4, especially its Techno/House algorithmic-generator idea.\n\nThis Python version writes Standard MIDI Files without Java and adds GUI presets, random SoundHelix-style song titles, instrument dropdowns, musical range guard, loudness normalization, WAV/MP3 rendering, Amiga/MagicWB-inspired themes, language switching, rating memory, project JSON and chord sheets.""")


def run_gui() -> int:
    if QApplication is None:
        print("PyQt6 is not installed. Run install_windows.bat first, or pip install -r requirements.txt", file=sys.stderr)
        return 2
    app = QApplication(sys.argv)
    win = MainWindow(); win.show()
    return app.exec()


def run_cli(args: argparse.Namespace) -> int:
    settings = get_preset(args.preset) if args.preset else get_preset(preset_names()[0])
    if args.seed is not None: settings.seed = args.seed
    settings.randomize_seed = args.random_seed
    if args.title: settings.title = args.title
    if args.bpm: settings.bpm = args.bpm
    if args.bars: settings.bars = args.bars
    settings.normalize_velocity = args.normalize
    settings.auto_range_guard = not args.no_range_guard
    settings.max_melody_pitch = args.max_melody_pitch
    settings.render_wav = args.render_wav or args.render_mp3
    settings.render_mp3 = args.render_mp3
    result = generate_song(settings, args.output or OUTPUT_DIR)
    print(result.summary()); print(result.midi_path)
    if result.wav_path: print(result.wav_path)
    if result.mp3_path: print(result.mp3_path)
    if result.render_log: print(result.render_log)
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description="PythonSoundHelix PyQt6 GPLv3 algorithmic MIDI generator")
    parser.add_argument("--nogui", action="store_true", help="generate from the command line without opening PyQt6")
    parser.add_argument("--preset", choices=preset_names(), help="preset name for --nogui")
    parser.add_argument("--output", help="output directory for --nogui")
    parser.add_argument("--seed", type=int, help="fixed seed for --nogui")
    parser.add_argument("--random-seed", action="store_true", help="randomize seed for --nogui")
    parser.add_argument("--title", help="song title for --nogui; omitted means SoundHelix-style random title")
    parser.add_argument("--bpm", type=int, help="override BPM for --nogui")
    parser.add_argument("--bars", type=int, help="override bars for --nogui")
    parser.add_argument("--normalize", action="store_true", help="normalize per-instrument MIDI velocity")
    parser.add_argument("--no-range-guard", action="store_true", help="disable automatic octave/range guard")
    parser.add_argument("--max-melody-pitch", type=int, default=79, help="upper pitch for melodic voices when range guard is enabled")
    parser.add_argument("--render-wav", action="store_true", help="render a WAV through the built-in synth")
    parser.add_argument("--render-mp3", action="store_true", help="render MP3 through ffmpeg; implies WAV rendering")
    args = parser.parse_args()
    if args.nogui: return run_cli(args)
    return run_gui()


if __name__ == "__main__":
    raise SystemExit(main())
