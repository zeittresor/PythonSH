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
from .generator import generate_song
from .history import HistoryStore
from .models import GeneratorSettings, TrackSettings
from .music_theory import GM_PROGRAMS, clamp
from .presets import PRESETS, get_preset, preset_names, xml_reference_files
from .xml_tools import format_summary, summarize_xml

ROOT = Path(__file__).resolve().parents[1]
OUTPUT_DIR = ROOT / "output"
APP_DATA = ROOT / "app_data"
HISTORY_PATH = APP_DATA / "generation_history.json"

DARK_QSS = """
QMainWindow, QWidget { background: #17191f; color: #e7eaf0; font-size: 10pt; }
QGroupBox { border: 1px solid #343846; border-radius: 9px; margin-top: 12px; padding: 10px; font-weight: bold; }
QGroupBox::title { subcontrol-origin: margin; left: 12px; padding: 0 6px; }
QPushButton { background: #2f6fed; color: white; border: 0; border-radius: 7px; padding: 8px 12px; }
QPushButton:hover { background: #3d7cff; }
QPushButton:disabled { background: #3a3d46; color: #8d93a1; }
QLineEdit, QTextEdit, QComboBox, QSpinBox, QTableWidget { background: #222631; color: #f3f5f8; border: 1px solid #3b4050; border-radius: 6px; padding: 4px; }
QHeaderView::section { background: #2a2e39; color: #f2f3f5; padding: 5px; border: 0; }
QTabWidget::pane { border: 1px solid #343846; }
QTabBar::tab { background: #242833; color: #d8dce5; padding: 9px 14px; border-top-left-radius: 7px; border-top-right-radius: 7px; }
QTabBar::tab:selected { background: #2f6fed; color: white; }
QProgressBar { border: 1px solid #3b4050; border-radius: 6px; text-align: center; background: #222631; }
QProgressBar::chunk { background: #2f6fed; border-radius: 5px; }
"""


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
        QApplication,
        QAbstractItemView,
        QCheckBox,
        QComboBox,
        QFileDialog,
        QFormLayout,
        QGridLayout,
        QGroupBox,
        QHBoxLayout,
        QHeaderView,
        QLabel,
        QLineEdit,
        QMainWindow,
        QMessageBox,
        QProgressBar,
        QPushButton,
        QSpinBox,
        QTabWidget,
        QTableWidget,
        QTableWidgetItem,
        QTextEdit,
        QVBoxLayout,
        QWidget,
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


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle(f"PythonSoundHelix v{__version__} - PyQt6 GPLv3")
        self.resize(1280, 820)
        self.history = HistoryStore(HISTORY_PATH)
        self.current_settings = get_preset(preset_names()[0])
        self.current_result = None
        self.current_record_id = ""
        self.worker: Optional[GenerateWorker] = None
        self._build_ui()
        self.apply_settings_to_ui(self.current_settings)
        self.refresh_history_table()
        self.refresh_xml_list()

    def _build_ui(self) -> None:
        central = QWidget()
        root = QVBoxLayout(central)
        self.tabs = QTabWidget()
        root.addWidget(self.tabs)
        self.setCentralWidget(central)

        self._build_generate_tab()
        self._build_tracks_tab()
        self._build_history_tab()
        self._build_xml_tab()
        self._build_log_tab()
        self._build_menu()

    def _build_menu(self) -> None:
        file_menu = self.menuBar().addMenu("File")
        save_project = QAction("Save project JSON...", self)
        save_project.triggered.connect(self.save_project)
        load_project = QAction("Load project JSON...", self)
        load_project.triggered.connect(self.load_project)
        open_output = QAction("Open output folder", self)
        open_output.triggered.connect(lambda: open_path(OUTPUT_DIR))
        file_menu.addAction(save_project)
        file_menu.addAction(load_project)
        file_menu.addSeparator()
        file_menu.addAction(open_output)

        help_menu = self.menuBar().addMenu("Help")
        about = QAction("About / License", self)
        about.triggered.connect(self.show_about)
        help_menu.addAction(about)

    def _build_generate_tab(self) -> None:
        tab = QWidget()
        outer = QVBoxLayout(tab)
        top = QHBoxLayout()
        outer.addLayout(top)

        general = QGroupBox("Generator")
        form = QFormLayout(general)
        self.preset_combo = QComboBox()
        self.preset_combo.addItems(preset_names())
        self.preset_combo.currentTextChanged.connect(self.load_preset_by_name)
        self.title_edit = QLineEdit()
        self.seed_spin = QSpinBox(); self.seed_spin.setRange(0, 2_147_483_647)
        self.random_seed_check = QCheckBox("randomize on generate")
        seed_row = QHBoxLayout(); seed_row.addWidget(self.seed_spin); seed_row.addWidget(self.random_seed_check)
        seed_widget = QWidget(); seed_widget.setLayout(seed_row)
        self.bpm_spin = QSpinBox(); self.bpm_spin.setRange(40, 240)
        self.bars_spin = QSpinBox(); self.bars_spin.setRange(8, 512); self.bars_spin.setSingleStep(8)
        self.beats_spin = QSpinBox(); self.beats_spin.setRange(2, 12)
        self.tpb_spin = QSpinBox(); self.tpb_spin.setRange(24, 1920); self.tpb_spin.setSingleStep(24)
        form.addRow("Preset", self.preset_combo)
        form.addRow("Song title", self.title_edit)
        form.addRow("Seed", seed_widget)
        form.addRow("BPM", self.bpm_spin)
        form.addRow("Bars", self.bars_spin)
        form.addRow("Beats per bar", self.beats_spin)
        form.addRow("Ticks per beat", self.tpb_spin)
        top.addWidget(general, 1)

        harmony = QGroupBox("Harmony / structure")
        hform = QFormLayout(harmony)
        self.key_combo = QComboBox(); self.key_combo.addItems(["C", "C#", "D", "Eb", "E", "F", "F#", "G", "Ab", "A", "Bb", "B"])
        self.mode_combo = QComboBox(); self.mode_combo.addItems(["major", "minor", "dorian", "mixolydian", "phrygian", "lydian", "pentatonic major", "pentatonic minor", "blues"])
        self.progression_combo = QComboBox(); self.progression_combo.setEditable(True)
        self.progression_combo.addItems(["I,V,vi,IV", "I,vi,IV,V", "i,VII,VI,V", "I,V,vi,iii,IV,I,IV,V", "Am/10,G/2,F/2,Am/12,G/2,F/2,Am/2,+C/8,Em/2,D/2,C/12,Em/2,D/2,C/4"])
        self.custom_progression = QLineEdit(); self.custom_progression.setPlaceholderText("Optional override, e.g. I,V,vi,IV or Am,G,F,Em")
        self.harmonic_spin = QSpinBox(); self.harmonic_spin.setRange(1, 8)
        self.section_spin = QSpinBox(); self.section_spin.setRange(3, 7)
        self.melody_template_combo = QComboBox(); self.melody_template_combo.addItems(["auto", "Popcorn-style original pulse", "Ode-to-Joy public-domain hint", "Fuer-Elise public-domain hint", "Canon public-domain hint", "Toccata public-domain hint", "Original arcade anthem"])
        hform.addRow("Key", self.key_combo)
        hform.addRow("Mode", self.mode_combo)
        hform.addRow("Progression", self.progression_combo)
        hform.addRow("Custom progression", self.custom_progression)
        hform.addRow("Harmonic rhythm", self.harmonic_spin)
        hform.addRow("Sections", self.section_spin)
        hform.addRow("Melody template", self.melody_template_combo)
        top.addWidget(harmony, 1)

        performance = QGroupBox("Performance / advanced")
        grid = QGridLayout(performance)
        self.complexity_spin = QSpinBox(); self.complexity_spin.setRange(1, 100)
        self.variation_spin = QSpinBox(); self.variation_spin.setRange(1, 100)
        self.swing_spin = QSpinBox(); self.swing_spin.setRange(0, 60)
        self.motif_spin = QSpinBox(); self.motif_spin.setRange(0, 100)
        self.accent_spin = QSpinBox(); self.accent_spin.setRange(0, 100)
        self.human_ticks_spin = QSpinBox(); self.human_ticks_spin.setRange(0, 80)
        self.human_vel_spin = QSpinBox(); self.human_vel_spin.setRange(0, 40)
        self.lfo_check = QCheckBox("LFO expression CC")
        self.call_response_check = QCheckBox("call/response melody")
        self.bass_roots_check = QCheckBox("bass favors chord roots")
        self.markers_check = QCheckBox("section markers")
        self.export_json_check = QCheckBox("export JSON project result")
        self.export_chords_check = QCheckBox("export chord sheet")
        self.rating_memory_check = QCheckBox("use thumbs-up rating memory")
        labels = ["Complexity", "Variation", "Swing", "Motif memory", "Accent", "Humanize ticks", "Humanize velocity"]
        widgets = [self.complexity_spin, self.variation_spin, self.swing_spin, self.motif_spin, self.accent_spin, self.human_ticks_spin, self.human_vel_spin]
        for i, (label, widget) in enumerate(zip(labels, widgets)):
            grid.addWidget(QLabel(label), i, 0); grid.addWidget(widget, i, 1)
        checks = [self.lfo_check, self.call_response_check, self.bass_roots_check, self.markers_check, self.export_json_check, self.export_chords_check, self.rating_memory_check]
        for i, check in enumerate(checks):
            grid.addWidget(check, i, 2)
        outer.addWidget(performance)

        buttons = QHBoxLayout()
        self.generate_btn = QPushButton("Generate MIDI")
        self.generate_btn.clicked.connect(self.generate_clicked)
        self.play_btn = QPushButton("Play last MIDI")
        self.play_btn.clicked.connect(self.play_last)
        self.open_output_btn = QPushButton("Open output folder")
        self.open_output_btn.clicked.connect(lambda: open_path(OUTPUT_DIR))
        self.save_project_btn = QPushButton("Save project")
        self.save_project_btn.clicked.connect(self.save_project)
        self.load_project_btn = QPushButton("Load project")
        self.load_project_btn.clicked.connect(self.load_project)
        self.thumb_up_btn = QPushButton("👍 Rate good")
        self.thumb_up_btn.clicked.connect(lambda: self.rate_current(1))
        self.thumb_down_btn = QPushButton("👎 Rate bad")
        self.thumb_down_btn.clicked.connect(lambda: self.rate_current(-1))
        for b in [self.generate_btn, self.play_btn, self.open_output_btn, self.save_project_btn, self.load_project_btn, self.thumb_up_btn, self.thumb_down_btn]:
            buttons.addWidget(b)
        outer.addLayout(buttons)
        self.progress = QProgressBar(); self.progress.setRange(0, 100)
        outer.addWidget(self.progress)
        self.summary_box = QTextEdit(); self.summary_box.setReadOnly(True); self.summary_box.setMinimumHeight(150)
        outer.addWidget(self.summary_box)
        self.tabs.addTab(tab, "Generate")

    def _build_tracks_tab(self) -> None:
        tab = QWidget()
        layout = QVBoxLayout(tab)
        info = QLabel("Tracks are editable. Roles: drum, bass, chord, arpeggio, melody, pad, counter, texture. Channel 10 is MIDI drum channel; internally shown as 9 because MIDI channels are 0-based.")
        info.setWordWrap(True)
        layout.addWidget(info)
        self.track_table = QTableWidget(0, 11)
        self.track_table.setHorizontalHeaderLabels(["Enabled", "Name", "Role", "Channel", "Program", "Volume", "Pan", "Octave", "Density", "Complexity", "Activity/Pattern"])
        self.track_table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        self.track_table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        layout.addWidget(self.track_table)
        row = QHBoxLayout()
        add_btn = QPushButton("Add melody track")
        add_btn.clicked.connect(self.add_track)
        remove_btn = QPushButton("Remove selected")
        remove_btn.clicked.connect(self.remove_track)
        normalize_btn = QPushButton("Normalize channels")
        normalize_btn.clicked.connect(self.normalize_channels)
        row.addWidget(add_btn); row.addWidget(remove_btn); row.addWidget(normalize_btn); row.addStretch(1)
        layout.addLayout(row)
        self.tabs.addTab(tab, "Tracks")

    def _build_history_tab(self) -> None:
        tab = QWidget()
        layout = QVBoxLayout(tab)
        self.history_table = QTableWidget(0, 7)
        self.history_table.setHorizontalHeaderLabels(["Rating", "Created", "Title", "Seed", "Notes", "Preset", "MIDI path"])
        self.history_table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        self.history_table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        layout.addWidget(self.history_table)
        row = QHBoxLayout()
        play = QPushButton("Play selected")
        play.clicked.connect(self.play_selected_history)
        load = QPushButton("Load selected settings")
        load.clicked.connect(self.load_selected_history_settings)
        up = QPushButton("👍 selected")
        up.clicked.connect(lambda: self.rate_selected_history(1))
        down = QPushButton("👎 selected")
        down.clicked.connect(lambda: self.rate_selected_history(-1))
        reset = QPushButton("Reset all ratings")
        reset.clicked.connect(self.reset_ratings)
        for b in [play, load, up, down, reset]: row.addWidget(b)
        row.addStretch(1)
        layout.addLayout(row)
        self.profile_box = QTextEdit(); self.profile_box.setReadOnly(True); self.profile_box.setMaximumHeight(130)
        layout.addWidget(self.profile_box)
        self.tabs.addTab(tab, "History / Ratings")

    def _build_xml_tab(self) -> None:
        tab = QWidget()
        layout = QHBoxLayout(tab)
        left = QVBoxLayout()
        self.xml_combo = QComboBox()
        self.xml_combo.currentTextChanged.connect(self.xml_selected)
        left.addWidget(QLabel("Bundled original SoundHelix XML references"))
        left.addWidget(self.xml_combo)
        xml_note = QLabel("These XML files are bundled as GPLv3 reference/preset material. The Python generator does not require Java.")
        xml_note.setWordWrap(True)
        left.addWidget(xml_note)
        left.addStretch(1)
        layout.addLayout(left, 1)
        self.xml_preview = QTextEdit(); self.xml_preview.setReadOnly(True)
        layout.addWidget(self.xml_preview, 3)
        self.tabs.addTab(tab, "Original XML Inspector")

    def _build_log_tab(self) -> None:
        tab = QWidget(); layout = QVBoxLayout(tab)
        self.log_box = QTextEdit(); self.log_box.setReadOnly(True)
        layout.addWidget(self.log_box)
        self.tabs.addTab(tab, "Log")

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
        self.seed_spin.setValue(s.seed)
        self.random_seed_check.setChecked(s.randomize_seed)
        self.bpm_spin.setValue(s.bpm)
        self.bars_spin.setValue(s.bars)
        self.beats_spin.setValue(s.beats_per_bar)
        self.tpb_spin.setValue(s.ticks_per_beat)
        self.key_combo.setCurrentText(s.key)
        self.mode_combo.setCurrentText(s.mode)
        self.progression_combo.setCurrentText(s.progression)
        self.custom_progression.setText(s.custom_progression)
        self.harmonic_spin.setValue(s.harmonic_rhythm)
        self.section_spin.setValue(s.section_count)
        self.melody_template_combo.setCurrentText(s.melody_template)
        self.complexity_spin.setValue(s.complexity)
        self.variation_spin.setValue(s.variation)
        self.swing_spin.setValue(s.swing)
        self.motif_spin.setValue(s.motif_memory)
        self.accent_spin.setValue(s.accent_strength)
        self.human_ticks_spin.setValue(s.humanize_ticks)
        self.human_vel_spin.setValue(s.humanize_velocity)
        self.lfo_check.setChecked(s.lfo_expression)
        self.call_response_check.setChecked(s.call_response)
        self.bass_roots_check.setChecked(s.keep_bass_on_roots)
        self.markers_check.setChecked(s.add_markers)
        self.export_json_check.setChecked(s.export_json)
        self.export_chords_check.setChecked(s.export_chord_sheet)
        self.rating_memory_check.setChecked(s.use_rating_memory)
        self.populate_track_table(s.tracks)
        self.summary_box.setText(s.description or "Ready.")

    def settings_from_ui(self) -> GeneratorSettings:
        s = GeneratorSettings()
        s.preset_name = self.preset_combo.currentText() or "Custom"
        s.title = self.title_edit.text().strip()
        s.seed = self.seed_spin.value(); s.randomize_seed = self.random_seed_check.isChecked()
        s.bpm = self.bpm_spin.value(); s.bars = self.bars_spin.value(); s.beats_per_bar = self.beats_spin.value(); s.ticks_per_beat = self.tpb_spin.value()
        s.key = self.key_combo.currentText(); s.mode = self.mode_combo.currentText()
        s.progression = self.progression_combo.currentText().strip() or "I,V,vi,IV"
        s.custom_progression = self.custom_progression.text().strip()
        s.harmonic_rhythm = self.harmonic_spin.value(); s.section_count = self.section_spin.value()
        s.melody_template = self.melody_template_combo.currentText()
        s.complexity = self.complexity_spin.value(); s.variation = self.variation_spin.value(); s.swing = self.swing_spin.value()
        s.motif_memory = self.motif_spin.value(); s.accent_strength = self.accent_spin.value()
        s.humanize_ticks = self.human_ticks_spin.value(); s.humanize_velocity = self.human_vel_spin.value()
        s.lfo_expression = self.lfo_check.isChecked(); s.call_response = self.call_response_check.isChecked(); s.keep_bass_on_roots = self.bass_roots_check.isChecked()
        s.add_markers = self.markers_check.isChecked(); s.export_json = self.export_json_check.isChecked(); s.export_chord_sheet = self.export_chords_check.isChecked(); s.use_rating_memory = self.rating_memory_check.isChecked()
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

    def _append_track_row(self, t: TrackSettings) -> None:
        row = self.track_table.rowCount(); self.track_table.insertRow(row)
        enabled = QTableWidgetItem("yes")
        enabled.setCheckState(Qt.CheckState.Checked if t.enabled else Qt.CheckState.Unchecked)
        self.track_table.setItem(row, 0, enabled)
        values = [t.name, t.role, str(t.channel), str(t.program), str(t.volume), str(t.pan), str(t.octave), str(t.density), str(t.complexity), f"{t.activity}|{t.pattern}"]
        for col, value in enumerate(values, start=1):
            self.track_table.setItem(row, col, self._item(value))

    def tracks_from_table(self) -> List[TrackSettings]:
        tracks: List[TrackSettings] = []
        for row in range(self.track_table.rowCount()):
            def text(col: int, default: str = "") -> str:
                item = self.track_table.item(row, col)
                return item.text().strip() if item else default
            enabled = self.track_table.item(row, 0).checkState() == Qt.CheckState.Checked if self.track_table.item(row, 0) else True
            activity_pattern = text(10, "80|auto")
            if "|" in activity_pattern:
                activity_text, pattern = activity_pattern.split("|", 1)
            else:
                activity_text, pattern = activity_pattern, "auto"
            try_int = lambda value, default, lo, hi: clamp(int(value), lo, hi) if str(value).strip().lstrip("-").isdigit() else default
            tracks.append(TrackSettings(
                name=text(1, "Track"), role=text(2, "melody"), enabled=enabled,
                channel=try_int(text(3, "0"), 0, 0, 15), program=try_int(text(4, "0"), 0, 0, 127),
                volume=try_int(text(5, "90"), 90, 1, 127), pan=try_int(text(6, "64"), 64, 0, 127),
                octave=try_int(text(7, "0"), 0, -4, 4), density=try_int(text(8, "70"), 70, 0, 100),
                complexity=try_int(text(9, "55"), 55, 0, 100), activity=try_int(activity_text, 80, 0, 100),
                pattern=pattern.strip() or "auto",
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
            role = (self.track_table.item(row, 2).text() if self.track_table.item(row, 2) else "").lower()
            ch = 9 if role == "drum" else next_channel
            if role != "drum":
                next_channel += 1
                if next_channel == 9: next_channel += 1
                next_channel = min(next_channel, 15)
            self.track_table.setItem(row, 3, self._item(str(ch)))

    def generate_clicked(self) -> None:
        if self.worker and self.worker.isRunning():
            QMessageBox.information(self, "PythonSoundHelix", "Generation is already running.")
            return
        settings = self.settings_from_ui()
        if not settings.tracks:
            QMessageBox.warning(self, "PythonSoundHelix", "No tracks configured.")
            return
        self.progress.setValue(0); self.generate_btn.setEnabled(False); self.summary_box.setText("Generating...")
        self.worker = GenerateWorker(settings, OUTPUT_DIR, self.history.taste_profile())
        self.worker.progress.connect(self.on_progress)
        self.worker.done.connect(self.on_done)
        self.worker.failed.connect(self.on_failed)
        self.worker.start()

    def on_progress(self, value: int, text: str) -> None:
        self.progress.setValue(value); self.log(text)

    def on_done(self, result) -> None:
        self.generate_btn.setEnabled(True)
        self.current_result = result
        self.seed_spin.setValue(result.seed)
        record = self.history.add_result(result.title, result.midi_path, result.settings.to_dict(), result.note_count, result.seed)
        self.current_record_id = record["id"]
        self.summary_box.setText(self._result_text(result))
        self.refresh_history_table()
        self.log(f"Generated: {result.midi_path}")

    def on_failed(self, message: str) -> None:
        self.generate_btn.setEnabled(True)
        self.progress.setValue(0)
        self.summary_box.setText(message)
        QMessageBox.critical(self, "Generation failed", message)

    def _result_text(self, result) -> str:
        lines = [result.summary(), "", f"MIDI: {result.midi_path}"]
        if result.json_path: lines.append(f"JSON: {result.json_path}")
        if result.chord_sheet_path: lines.append(f"Chord sheet: {result.chord_sheet_path}")
        lines.append("")
        lines.append("Sections: " + ", ".join(f"{s.name} {s.bars} bars" for s in result.sections))
        lines.append("First chords: " + ", ".join(f"{c.bar+1}:{c.symbol}" for c in result.chords[:16]))
        return "\n".join(lines)

    def play_last(self) -> None:
        if self.current_result and self.current_result.midi_path:
            open_path(self.current_result.midi_path)
        else:
            QMessageBox.information(self, "PythonSoundHelix", "Generate a MIDI first.")

    def rate_current(self, rating: int) -> None:
        if not self.current_record_id:
            QMessageBox.information(self, "PythonSoundHelix", "No generated song selected for rating.")
            return
        self.history.rate(self.current_record_id, rating)
        self.refresh_history_table()

    def refresh_history_table(self) -> None:
        rows = self.history.rows()
        self.history_table.setRowCount(0)
        for r in rows:
            row = self.history_table.rowCount(); self.history_table.insertRow(row)
            rating = "👍" if r.get("rating") == 1 else "👎" if r.get("rating") == -1 else ""
            values = [rating, r.get("created_at", ""), r.get("title", ""), str(r.get("seed", "")), str(r.get("note_count", "")), r.get("settings", {}).get("preset_name", ""), r.get("midi_path", "")]
            for col, value in enumerate(values):
                item = self._item(str(value), editable=False)
                item.setData(Qt.ItemDataRole.UserRole, r.get("id", ""))
                self.history_table.setItem(row, col, item)
        profile = self.history.taste_profile()
        self.profile_box.setText(json.dumps(profile, indent=2, ensure_ascii=False))

    def _selected_history_record(self) -> Optional[Dict[str, Any]]:
        rows = {idx.row() for idx in self.history_table.selectedIndexes()}
        if not rows:
            return None
        row = min(rows)
        item = self.history_table.item(row, 0)
        rid = item.data(Qt.ItemDataRole.UserRole) if item else ""
        for record in self.history.records:
            if record.get("id") == rid:
                return record
        return None

    def play_selected_history(self) -> None:
        r = self._selected_history_record()
        if r and r.get("midi_path"):
            open_path(r["midi_path"])

    def load_selected_history_settings(self) -> None:
        r = self._selected_history_record()
        if r and r.get("settings"):
            s = GeneratorSettings.from_dict(r["settings"])
            self.apply_settings_to_ui(s)

    def rate_selected_history(self, rating: int) -> None:
        r = self._selected_history_record()
        if r:
            self.history.rate(r["id"], rating)
            self.refresh_history_table()

    def reset_ratings(self) -> None:
        self.history.reset_ratings()
        self.refresh_history_table()

    def save_project(self) -> None:
        path, _ = QFileDialog.getSaveFileName(self, "Save PythonSoundHelix project", str(ROOT / "project.psh.json"), "PythonSoundHelix JSON (*.json)")
        if not path:
            return
        Path(path).write_text(json.dumps(self.settings_from_ui().to_dict(), indent=2, ensure_ascii=False), encoding="utf-8")

    def load_project(self) -> None:
        path, _ = QFileDialog.getOpenFileName(self, "Load PythonSoundHelix project", str(ROOT), "PythonSoundHelix JSON (*.json)")
        if not path:
            return
        data = json.loads(Path(path).read_text(encoding="utf-8"))
        s = GeneratorSettings.from_dict(data)
        self.apply_settings_to_ui(s)

    def refresh_xml_list(self) -> None:
        self.xml_combo.clear()
        files = xml_reference_files(ROOT)
        for path in files:
            self.xml_combo.addItem(path.name, str(path))
        if files:
            self.xml_selected(files[0].name)

    def xml_selected(self, _: str) -> None:
        path = self.xml_combo.currentData()
        if not path:
            return
        try:
            self.xml_preview.setText(format_summary(summarize_xml(path)))
        except Exception as exc:
            self.xml_preview.setText(str(exc))

    def show_about(self) -> None:
        QMessageBox.about(self, "About PythonSoundHelix", f"""PythonSoundHelix v{__version__}\n\nGPLv3 Python/PyQt6 reimplementation and expansion inspired by SoundHelix.\n\nOriginal project: https://www.soundhelix.com/\nOriginal source archive basis: soundhelix-code-r896-trunk / SoundHelix 0.10u.\n\nThis Python version writes Standard MIDI Files without Java and adds GUI presets, rating memory, project JSON, chord sheets and extended arrangement controls.""")


def run_gui() -> int:
    if QApplication is None:
        print("PyQt6 is not installed. Run install_windows.bat first, or pip install -r requirements.txt", file=sys.stderr)
        return 2
    app = QApplication(sys.argv)
    app.setStyleSheet(DARK_QSS)
    win = MainWindow()
    win.show()
    return app.exec()


def run_cli(args: argparse.Namespace) -> int:
    settings = get_preset(args.preset) if args.preset else get_preset(preset_names()[0])
    if args.seed is not None:
        settings.seed = args.seed
    settings.randomize_seed = args.random_seed
    if args.title:
        settings.title = args.title
    if args.bpm:
        settings.bpm = args.bpm
    if args.bars:
        settings.bars = args.bars
    result = generate_song(settings, args.output or OUTPUT_DIR)
    print(result.summary())
    print(result.midi_path)
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description="PythonSoundHelix PyQt6 GPLv3 algorithmic MIDI generator")
    parser.add_argument("--nogui", action="store_true", help="generate from the command line without opening PyQt6")
    parser.add_argument("--preset", choices=preset_names(), help="preset name for --nogui")
    parser.add_argument("--output", help="output directory for --nogui")
    parser.add_argument("--seed", type=int, help="fixed seed for --nogui")
    parser.add_argument("--random-seed", action="store_true", help="randomize seed for --nogui")
    parser.add_argument("--title", help="song title for --nogui")
    parser.add_argument("--bpm", type=int, help="override BPM for --nogui")
    parser.add_argument("--bars", type=int, help="override bars for --nogui")
    args = parser.parse_args()
    if args.nogui:
        return run_cli(args)
    return run_gui()


if __name__ == "__main__":
    raise SystemExit(main())
