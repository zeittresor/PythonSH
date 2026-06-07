from __future__ import annotations

import os
import sys
import json
import subprocess
from pathlib import Path

from PyQt6.QtCore import Qt
from PyQt6.QtGui import QAction, QDesktopServices
from PyQt6.QtCore import QUrl
from PyQt6.QtWidgets import (
    QApplication, QCheckBox, QComboBox, QFileDialog, QFormLayout, QGridLayout, QGroupBox,
    QHBoxLayout, QLabel, QLineEdit, QMainWindow, QMessageBox, QPushButton, QScrollArea,
    QSlider, QSpinBox, QTabWidget, QTextEdit, QVBoxLayout, QWidget
)

from .generator import APP_VERSION, GeneratorSettings, PRESET_NAMES, PROGRESSION_NAMES, MELODY_TEMPLATES, TrackSettings, generate_song, preset_defaults, sanitize_mode_progression

ROOT = Path(__file__).resolve().parent.parent
OUTPUT_DIR = ROOT / "output"

GM_PROGRAMS = [
    "Acoustic Grand Piano", "Bright Acoustic Piano", "Electric Grand Piano", "Honky-tonk Piano", "Electric Piano 1", "Electric Piano 2", "Harpsichord", "Clavinet",
    "Celesta", "Glockenspiel", "Music Box", "Vibraphone", "Marimba", "Xylophone", "Tubular Bells", "Dulcimer",
    "Drawbar Organ", "Percussive Organ", "Rock Organ", "Church Organ", "Reed Organ", "Accordion", "Harmonica", "Tango Accordion",
    "Acoustic Guitar nylon", "Acoustic Guitar steel", "Electric Guitar jazz", "Electric Guitar clean", "Electric Guitar muted", "Overdriven Guitar", "Distortion Guitar", "Guitar Harmonics",
    "Acoustic Bass", "Electric Bass finger", "Electric Bass pick", "Fretless Bass", "Slap Bass 1", "Slap Bass 2", "Synth Bass 1", "Synth Bass 2",
    "Violin", "Viola", "Cello", "Contrabass", "Tremolo Strings", "Pizzicato Strings", "Orchestral Harp", "Timpani",
    "String Ensemble 1", "String Ensemble 2", "SynthStrings 1", "SynthStrings 2", "Choir Aahs", "Voice Oohs", "Synth Voice", "Orchestra Hit",
    "Trumpet", "Trombone", "Tuba", "Muted Trumpet", "French Horn", "Brass Section", "SynthBrass 1", "SynthBrass 2",
    "Soprano Sax", "Alto Sax", "Tenor Sax", "Baritone Sax", "Oboe", "English Horn", "Bassoon", "Clarinet",
    "Piccolo", "Flute", "Recorder", "Pan Flute", "Blown Bottle", "Shakuhachi", "Whistle", "Ocarina",
    "Lead 1 square", "Lead 2 sawtooth", "Lead 3 calliope", "Lead 4 chiff", "Lead 5 charang", "Lead 6 voice", "Lead 7 fifths", "Lead 8 bass+lead",
    "Pad 1 new age", "Pad 2 warm", "Pad 3 polysynth", "Pad 4 choir", "Pad 5 bowed", "Pad 6 metallic", "Pad 7 halo", "Pad 8 sweep",
    "FX 1 rain", "FX 2 soundtrack", "FX 3 crystal", "FX 4 atmosphere", "FX 5 brightness", "FX 6 goblins", "FX 7 echoes", "FX 8 sci-fi",
    "Sitar", "Banjo", "Shamisen", "Koto", "Kalimba", "Bag Pipe", "Fiddle", "Shanai",
    "Tinkle Bell", "Agogo", "Steel Drums", "Woodblock", "Taiko Drum", "Melodic Tom", "Synth Drum", "Reverse Cymbal",
    "Guitar Fret Noise", "Breath Noise", "Seashore", "Bird Tweet", "Telephone Ring", "Helicopter", "Applause", "Gunshot"
]

ROLE_NAMES = ["drum", "bass", "melody", "chord", "pad"]
LANGUAGE_NAMES = ["English", "Deutsch", "Français", "Русский"]
THEME_NAMES = ["Dark", "Light", "Matrix", "Ocean", "Purple", "Hellfire", "Sepia"]

TRANSLATIONS = {
    "English": {
        "generate_tab":"Generate", "finetuning_tab":"Finetuning", "options_tab":"Options", "log_tab":"Log",
        "help":"Help", "about":"About", "generate":"Generate Song", "play":"Play MIDI", "open":"Open output folder",
        "randomize":"randomize on generate", "lfo":"LFO expression CC", "call":"call/response melody", "bass":"bass favors chord roots", "markers":"section markers", "json":"export JSON result", "chords":"export chord sheet", "ratings":"use thumbs-up rating memory", "dissonance":"allow experimental dissonance/free counterpoint",
        "tip_preset":"Auto Composer randomly chooses a style profile. Other presets are style hints; key/mode/progression/template stay automatic by default.",
        "tip_progression":"Auto mode-safe creates section-specific phrase plans. Manual progressions remain possible but are less varied.",
        "tip_language":"Changes main menus, tabs, buttons and tooltips immediately.",
        "options_note":"v0.6.5: presets act as style hints. Key, mode, progression and melody template stay Auto by default; the engine uses seed-specific role entry profiles so songs can begin with pad, melody, drums, chords or bass.",
    },
    "Deutsch": {
        "generate_tab":"Erzeugen", "finetuning_tab":"Feinabstimmung", "options_tab":"Optionen", "log_tab":"Log",
        "help":"Hilfe", "about":"Über", "generate":"Song erzeugen", "play":"MIDI abspielen", "open":"Ausgabeordner öffnen",
        "randomize":"Seed zufällig beim Erzeugen", "lfo":"LFO-Ausdruck CC", "call":"Call/Response-Melodie", "bass":"Bass bevorzugt Akkord-Grundtöne", "markers":"Abschnittsmarker", "json":"JSON exportieren", "chords":"Akkordblatt exportieren", "ratings":"Daumen-hoch-Bewertungen nutzen", "dissonance":"experimentelle Dissonanzen/freien Kontrapunkt erlauben",
        "tip_preset":"Auto Composer wählt zufällig ein Stilprofil. Andere Presets sind Stil-Hinweise; Tonart/Modus/Progression/Melodie bleiben standardmäßig automatisch.",
        "tip_progression":"Auto mode-safe erzeugt abschnittsweise passende Phrasenpläne. Manuelle Progressionen bleiben möglich, sind aber weniger variabel.",
        "tip_language":"Ändert Hauptmenüs, Tabs, Buttons und Tooltips sofort.",
        "options_note":"v0.6.5: Presets sind Stil-Hinweise. Tonart, Modus, Progression und Melodie-Template bleiben standardmäßig Auto; die Engine nutzt seed-spezifische Einstiegsmuster, sodass Songs mit Pad, Melodie, Drums, Akkorden oder Bass beginnen können.",
    },
    "Français": {
        "generate_tab":"Générer", "finetuning_tab":"Réglage fin", "options_tab":"Options", "log_tab":"Journal",
        "help":"Aide", "about":"À propos", "generate":"Générer le morceau", "play":"Lire MIDI", "open":"Ouvrir le dossier de sortie",
        "randomize":"graine aléatoire à la génération", "lfo":"Expression LFO CC", "call":"mélodie appel/réponse", "bass":"basse sur fondamentales d’accords", "markers":"marqueurs de sections", "json":"exporter JSON", "chords":"exporter grille d’accords", "ratings":"utiliser les évaluations positives", "dissonance":"autoriser dissonances/contrepoint libre expérimentaux",
        "tip_preset":"Auto Composer choisit un profil de style aléatoire. Les autres presets restent des indications de style; tonalité/mode/progression/modèle mélodique restent automatiques par défaut.",
        "tip_progression":"Auto mode-safe crée des plans de phrases par section. Les progressions manuelles restent possibles, mais moins variées.",
        "tip_language":"Met à jour immédiatement menus, onglets, boutons et infobulles.",
        "options_note":"v0.6.5 : les presets sont des indications de style. Tonalité, mode, progression et modèle mélodique restent en Auto; le moteur utilise des entrées de rôles propres à la graine pour varier les débuts.",
    },
    "Русский": {
        "generate_tab":"Создать", "finetuning_tab":"Тонкая настройка", "options_tab":"Опции", "log_tab":"Журнал",
        "help":"Помощь", "about":"О программе", "generate":"Создать песню", "play":"Играть MIDI", "open":"Открыть папку вывода",
        "randomize":"случайный seed при создании", "lfo":"LFO expression CC", "call":"мелодия вопрос/ответ", "bass":"бас по основным тонам аккорда", "markers":"маркеры секций", "json":"экспорт JSON", "chords":"экспорт аккордов", "ratings":"использовать оценки лайков", "dissonance":"разрешить экспериментальные диссонансы/свободный контрапункт",
        "tip_preset":"Auto Composer случайно выбирает стилевой профиль. Остальные пресеты — подсказки стиля; тональность/лад/прогрессия/мелодия по умолчанию автоматические.",
        "tip_progression":"Auto mode-safe создает фразовые планы по секциям. Ручные прогрессии возможны, но менее вариативны.",
        "tip_language":"Сразу меняет меню, вкладки, кнопки и подсказки.",
        "options_note":"v0.6.5: пресеты являются стилевыми подсказками. Тональность, лад, прогрессия и шаблон мелодии остаются Auto; движок использует seed-зависимые входы партий, поэтому песня может начинаться с пада, мелодии, ударных, аккордов или баса.",
    },
}

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.settings = preset_defaults("Auto Composer")
        self.last_result = None
        self.setWindowTitle(f"PythonSoundHelix v{APP_VERSION} - PyQt6 GPLv3")
        self.resize(1340, 840)
        self._build_ui()
        self._load_settings_to_ui()
        self._apply_dark_theme()
        self.apply_language("English")

    def _scroll(self, widget: QWidget) -> QScrollArea:
        area = QScrollArea()
        area.setWidgetResizable(True)
        area.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOn)
        area.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        area.setWidget(widget)
        return area

    def _build_ui(self):
        self.tabs = QTabWidget(); self.setCentralWidget(self.tabs)
        self.tabs.addTab(self._scroll(self._generate_tab()), "Generate")
        self.tabs.addTab(self._scroll(self._tracks_tab()), "Finetuning")
        self.tabs.addTab(self._scroll(self._options_tab()), "Options")
        self.tabs.addTab(self._scroll(self._log_tab()), "Log")
        menubar = self.menuBar()
        self.help_menu = menubar.addMenu("Help")
        self.about_action = QAction("About", self); self.about_action.triggered.connect(self.about)
        self.help_menu.addAction(self.about_action)

    def _generate_tab(self):
        page=QWidget(); outer=QVBoxLayout(page)
        top=QHBoxLayout(); outer.addLayout(top)
        gen=QGroupBox("Generator"); form=QFormLayout(gen); top.addWidget(gen,1)
        self.preset=QComboBox(); self.preset.addItems(PRESET_NAMES); self.preset.currentTextChanged.connect(self.on_preset)
        self.title=QLineEdit(); self.seed=QSpinBox(); self.seed.setRange(0,2_147_483_647); self.randomize=QCheckBox("randomize on generate")
        seedrow=QHBoxLayout(); seedwrap=QWidget(); seedrow.addWidget(self.seed); seedrow.addWidget(self.randomize); seedwrap.setLayout(seedrow)
        self.bpm=QSpinBox(); self.bpm.setRange(40,240)
        self.bars=QSpinBox(); self.bars.setRange(16,256)
        self.beats=QSpinBox(); self.beats.setRange(3,4)
        self.ticks=QSpinBox(); self.ticks.setRange(96,1920)
        for label,w in [("Preset",self.preset),("Song title",self.title),("Seed",seedwrap),("BPM",self.bpm),("Bars",self.bars),("Beats per bar",self.beats),("Ticks per beat",self.ticks)]: form.addRow(label,w)
        harm=QGroupBox("Harmony / structure"); hform=QFormLayout(harm); top.addWidget(harm,1)
        self.key=QComboBox(); self.key.addItems(["Auto","C","C#","D","D#","E","F","F#","G","G#","A","A#","B"])
        self.mode=QComboBox(); self.mode.addItems(["auto","major","minor"]); self.mode.currentTextChanged.connect(self.on_mode_progression)
        self.progression=QComboBox(); self.progression.addItems(PROGRESSION_NAMES); self.progression.currentTextChanged.connect(self.on_mode_progression)
        self.custom=QLineEdit(); self.custom.setPlaceholderText("Optional override, e.g. i,V,i,iv or C#m,G#,F#m")
        self.hrhythm=QSpinBox(); self.hrhythm.setRange(1,8)
        self.sections=QSpinBox(); self.sections.setRange(5,5); self.sections.setEnabled(False)
        self.melody_template=QComboBox(); self.melody_template.addItems(MELODY_TEMPLATES)
        self.coverage=QSpinBox(); self.coverage.setRange(5,100); self.coverage.setSuffix(" %")
        for label,w in [("Key",self.key),("Mode",self.mode),("Progression",self.progression),("Custom progression",self.custom),("Harmonic rhythm",self.hrhythm),("Sections",self.sections),("Melody template",self.melody_template),("Melody coverage",self.coverage)]: hform.addRow(label,w)
        adv=QGroupBox("Performance / advanced"); grid=QGridLayout(adv); outer.addWidget(adv)
        self.complexity=QSpinBox(); self.complexity.setRange(0,100)
        self.variation=QSpinBox(); self.variation.setRange(0,100)
        self.seed_variation=QSpinBox(); self.seed_variation.setRange(0,100)
        self.swing=QSpinBox(); self.swing.setRange(0,40)
        self.motif=QSpinBox(); self.motif.setRange(0,100)
        self.accent=QSpinBox(); self.accent.setRange(0,100)
        self.hticks=QSpinBox(); self.hticks.setRange(0,32)
        self.hvel=QSpinBox(); self.hvel.setRange(0,32)
        spin_pairs=[("Complexity",self.complexity),("Variation",self.variation),("Seed variation",self.seed_variation),("Swing",self.swing),("Motif memory",self.motif),("Accent",self.accent),("Humanize ticks",self.hticks),("Humanize velocity",self.hvel)]
        for i,(label,w) in enumerate(spin_pairs): grid.addWidget(QLabel(label),i,0); grid.addWidget(w,i,1)
        self.lfo=QCheckBox("LFO expression CC"); self.call=QCheckBox("call/response melody"); self.bass_roots=QCheckBox("bass favors chord roots"); self.markers=QCheckBox("section markers"); self.export_json=QCheckBox("export JSON result"); self.export_chords=QCheckBox("export chord sheet"); self.ratings=QCheckBox("use thumbs-up rating memory")
        checks=[self.lfo,self.call,self.bass_roots,self.markers,self.export_json,self.export_chords,self.ratings]
        for i,c in enumerate(checks): grid.addWidget(c,i,2)
        buttons=QHBoxLayout(); outer.addLayout(buttons)
        self.btn_generate=QPushButton("Generate Song"); self.btn_generate.clicked.connect(self.generate)
        self.btn_play=QPushButton("Play MIDI"); self.btn_play.clicked.connect(self.play_midi)
        self.btn_open=QPushButton("Open output folder"); self.btn_open.clicked.connect(lambda: QDesktopServices.openUrl(QUrl.fromLocalFile(str(OUTPUT_DIR))))
        for b in [self.btn_generate,self.btn_play,self.btn_open]: buttons.addWidget(b)
        self.status=QTextEdit(); self.status.setMinimumHeight(110); self.status.setReadOnly(True); outer.addWidget(self.status)
        return page

    def _tracks_tab(self):
        self.track_page=QWidget(); self.track_layout=QVBoxLayout(self.track_page)
        self.track_widgets=[]
        add_box=QGroupBox("Add extra track / instrument"); add_form=QFormLayout(add_box)
        self.new_track_name=QLineEdit(); self.new_track_name.setPlaceholderText("Optional name, e.g. Second Pad")
        self.new_track_role=QComboBox(); self.new_track_role.addItems(ROLE_NAMES)
        self.new_track_program=QComboBox(); self.new_track_program.addItems([f"{i:03d} - {name}" for i,name in enumerate(GM_PROGRAMS)])
        self.btn_add_track=QPushButton("Add track to finetuning")
        self.btn_add_track.clicked.connect(self.add_track_from_finetuning)
        for label,w in [("Name", self.new_track_name), ("Function / role", self.new_track_role), ("Instrument", self.new_track_program), ("", self.btn_add_track)]:
            add_form.addRow(label,w)
        self.track_layout.addWidget(add_box)
        self.track_cards_container=QWidget(); self.track_cards_layout=QVBoxLayout(self.track_cards_container)
        self.track_layout.addWidget(self.track_cards_container)
        self.track_layout.addStretch(1)
        return self.track_page

    def _slider_with_label(self, slider: QSlider, label: QLabel):
        wrap=QWidget(); row=QHBoxLayout(wrap); row.setContentsMargins(0,0,0,0); row.addWidget(slider,1); row.addWidget(label)
        return wrap

    def _program_combo(self, program: int) -> QComboBox:
        combo=QComboBox(); combo.addItems([f"{i:03d} - {name}" for i,name in enumerate(GM_PROGRAMS)])
        combo.setCurrentIndex(max(0,min(127,int(program))))
        return combo

    def rebuild_tracks_tab(self):
        while self.track_cards_layout.count():
            item=self.track_cards_layout.takeAt(0)
            if item.widget(): item.widget().deleteLater()
        self.track_widgets=[]
        for idx,t in enumerate(self.settings.tracks):
            box=QGroupBox(f"{idx+1}. {t.name}"); f=QFormLayout(box)
            name=QLineEdit(t.name)
            en=QCheckBox("enabled")
            role=QComboBox(); role.addItems(ROLE_NAMES)
            program=self._program_combo(t.program)
            vol=QSlider(Qt.Orientation.Horizontal); vol.setRange(0,127); vol_lbl=QLabel(str(t.volume))
            fine=QSlider(Qt.Orientation.Horizontal); fine.setRange(-100,100); fine_lbl=QLabel(f"{int(getattr(t,'fine_tune_cents',0)):+d} ct")
            octv=QSpinBox(); octv.setRange(-3,3)
            trans=QSpinBox(); trans.setRange(-12,12)
            en.setChecked(t.enabled); role.setCurrentText(t.role); vol.setValue(t.volume); fine.setValue(int(getattr(t,'fine_tune_cents',0))); octv.setValue(t.octave); trans.setValue(t.transpose)
            vol.valueChanged.connect(lambda v,l=vol_lbl: l.setText(str(v)))
            fine.valueChanged.connect(lambda v,l=fine_lbl: l.setText(f"{v:+d} ct"))
            for label,w in [
                ("Track name",name), ("Enabled",en), ("Function / role",role), ("Instrument",program),
                ("Volume",self._slider_with_label(vol,vol_lbl)), ("Finetune",self._slider_with_label(fine,fine_lbl)),
                ("Octave",octv), ("Transpose",trans)]:
                f.addRow(label,w)
            self.track_widgets.append((t,name,en,role,program,vol,fine,octv,trans)); self.track_cards_layout.addWidget(box)
        self.track_cards_layout.addStretch(1)

    def _next_channel_for_role(self, role: str) -> int:
        if role == "drum":
            return 9
        used={t.channel for t in self.settings.tracks if t.enabled and t.role != "drum"}
        for ch in [5,6,7,8,10,11,12,13,14,15,0,1,2,3,4]:
            if ch != 9 and ch not in used:
                return ch
        return 5

    def add_track_from_finetuning(self):
        role=self.new_track_role.currentText()
        program=self.new_track_program.currentIndex()
        name=self.new_track_name.text().strip() or f"Extra {role.title()} {len(self.settings.tracks)+1}"
        defaults={"drum":(9,0,58,64,0),"bass":(self._next_channel_for_role(role),38,62,48,-1),"melody":(self._next_channel_for_role(role),program,58,64,0),"chord":(self._next_channel_for_role(role),program,46,36,0),"pad":(self._next_channel_for_role(role),program,38,82,0)}
        ch,prog,vol,pan,octv=defaults.get(role,(self._next_channel_for_role(role),program,50,64,0))
        if role not in ("drum","bass"):
            prog=program
        self.settings.tracks.append(TrackSettings(name, role, True, ch, prog, vol, pan, octv, 0, 0))
        self.new_track_name.clear()
        self.rebuild_tracks_tab()

    def _options_tab(self):
        page=QWidget(); v=QVBoxLayout(page)
        ui=QGroupBox("Interface"); form=QFormLayout(ui); v.addWidget(ui)
        self.language_combo=QComboBox(); self.language_combo.addItems(LANGUAGE_NAMES); self.language_combo.currentTextChanged.connect(self.apply_language)
        self.theme_combo=QComboBox(); self.theme_combo.addItems(THEME_NAMES); self.theme_combo.setCurrentText("Dark"); self.theme_combo.currentTextChanged.connect(self.apply_theme)
        form.addRow("Language / Sprache / Langue / Язык", self.language_combo)
        form.addRow("Theme", self.theme_combo)
        self.allow_dissonance = QCheckBox("allow experimental dissonance/free counterpoint")
        self.allow_dissonance.setChecked(False)
        form.addRow("Harmony safety", self.allow_dissonance)
        self.options_note=QTextEdit(); self.options_note.setMinimumHeight(320); self.options_note.setReadOnly(True)
        v.addWidget(self.options_note)
        v.addStretch(1)
        return page

    def _log_tab(self):
        self.log=QTextEdit(); self.log.setReadOnly(True); return self.log

    def _load_settings_to_ui(self):
        s=self.settings
        self.preset.blockSignals(True); self.preset.setCurrentText(s.preset_name); self.preset.blockSignals(False)
        self.title.setText(s.title); self.seed.setValue(s.seed); self.randomize.setChecked(s.randomize_seed)
        self.bpm.setValue(s.bpm); self.bars.setValue(s.bars); self.beats.setValue(s.beats_per_bar); self.ticks.setValue(s.ticks_per_beat)
        self.key.setCurrentText(s.key); self.mode.setCurrentText(s.mode); self.progression.setCurrentText(s.progression); self.custom.setText(s.custom_progression)
        self.hrhythm.setValue(s.harmonic_rhythm); self.sections.setValue(5); self.melody_template.setCurrentText(s.melody_template); self.coverage.setValue(s.melody_coverage)
        self.complexity.setValue(s.complexity); self.variation.setValue(s.variation); self.seed_variation.setValue(s.seed_variation_strength); self.swing.setValue(s.swing); self.motif.setValue(s.motif_memory); self.accent.setValue(s.accent_strength); self.hticks.setValue(s.humanize_ticks); self.hvel.setValue(s.humanize_velocity)
        self.lfo.setChecked(s.lfo_expression); self.call.setChecked(s.call_response); self.bass_roots.setChecked(s.keep_bass_on_roots); self.markers.setChecked(s.add_markers); self.export_json.setChecked(s.export_json); self.export_chords.setChecked(s.export_chord_sheet); self.ratings.setChecked(s.use_rating_memory)
        if hasattr(self, "allow_dissonance"): self.allow_dissonance.setChecked(getattr(s, "allow_dissonance", False))
        self.rebuild_tracks_tab()

    def _ui_to_settings(self):
        s=self.settings
        s.preset_name=self.preset.currentText(); s.title=self.title.text(); s.seed=self.seed.value(); s.randomize_seed=self.randomize.isChecked(); s.bpm=self.bpm.value(); s.bars=self.bars.value(); s.beats_per_bar=self.beats.value(); s.ticks_per_beat=self.ticks.value(); s.key=self.key.currentText(); s.mode=self.mode.currentText(); s.progression=self.progression.currentText(); s.custom_progression=self.custom.text(); s.harmonic_rhythm=self.hrhythm.value(); s.section_count=5; s.melody_template=self.melody_template.currentText(); s.melody_coverage=self.coverage.value(); s.complexity=self.complexity.value(); s.variation=self.variation.value(); s.seed_variation_strength=self.seed_variation.value(); s.swing=self.swing.value(); s.motif_memory=self.motif.value(); s.accent_strength=self.accent.value(); s.humanize_ticks=self.hticks.value(); s.humanize_velocity=self.hvel.value(); s.lfo_expression=self.lfo.isChecked(); s.call_response=self.call.isChecked(); s.keep_bass_on_roots=self.bass_roots.isChecked(); s.add_markers=self.markers.isChecked(); s.export_json=self.export_json.isChecked(); s.export_chord_sheet=self.export_chords.isChecked(); s.use_rating_memory=self.ratings.isChecked(); s.allow_dissonance=self.allow_dissonance.isChecked() if hasattr(self, "allow_dissonance") else False
        for t,name,en,role,program,vol,fine,octv,trans in self.track_widgets:
            t.name=name.text().strip() or t.name; t.enabled=en.isChecked(); t.role=role.currentText(); t.program=program.currentIndex(); t.volume=vol.value(); t.fine_tune_cents=fine.value(); t.octave=octv.value(); t.transpose=trans.value()
        sanitize_mode_progression(s)
        return s

    def on_preset(self, name):
        self.settings=preset_defaults(name); self._load_settings_to_ui()

    def on_mode_progression(self):
        prog=self.progression.currentText().lower()
        if prog.startswith("auto"):
            return
        if prog.startswith("minor") and self.mode.currentText() != "minor": self.mode.setCurrentText("minor")
        if prog.startswith("major") and self.mode.currentText() != "major": self.mode.setCurrentText("major")

    def generate(self):
        try:
            s=self._ui_to_settings(); OUTPUT_DIR.mkdir(exist_ok=True)
            if s.randomize_seed:
                s.title = ""
            res=generate_song(s, OUTPUT_DIR)
            self.last_result=res
            self.seed.setValue(res.seed); self.title.setText(res.title)
            msg=f"{res.title} | seed={res.seed} | notes={res.note_count}\nMIDI: {res.midi_path}\nChord sheet: {res.chord_sheet_path}\n{res.render_log}"
            self.status.setPlainText(msg); self.log.append(msg)
        except Exception as e:
            QMessageBox.critical(self,"Generate failed",f"{type(e).__name__}: {e}")
            raise

    def play_midi(self):
        if not self.last_result:
            QMessageBox.information(self,"PythonSoundHelix","Generate a song first."); return
        path=self.last_result.midi_path
        if sys.platform.startswith('win'):
            os.startfile(path)
        else:
            QDesktopServices.openUrl(QUrl.fromLocalFile(path))

    def _tr(self, key: str) -> str:
        lang = getattr(self, "language_combo", None).currentText() if hasattr(self, "language_combo") else "English"
        return TRANSLATIONS.get(lang, TRANSLATIONS["English"]).get(key, TRANSLATIONS["English"].get(key, key))

    def apply_language(self, name=None):
        if not hasattr(self, "tabs"):
            return
        self.tabs.setTabText(0, self._tr("generate_tab")); self.tabs.setTabText(1, self._tr("finetuning_tab")); self.tabs.setTabText(2, self._tr("options_tab")); self.tabs.setTabText(3, self._tr("log_tab"))
        if hasattr(self, "help_menu"):
            self.help_menu.setTitle(self._tr("help"))
        if hasattr(self, "about_action"):
            self.about_action.setText(self._tr("about"))
        if hasattr(self, "btn_generate"):
            self.btn_generate.setText(self._tr("generate")); self.btn_play.setText(self._tr("play")); self.btn_open.setText(self._tr("open"))
            self.randomize.setText(self._tr("randomize")); self.lfo.setText(self._tr("lfo")); self.call.setText(self._tr("call")); self.bass_roots.setText(self._tr("bass")); self.markers.setText(self._tr("markers")); self.export_json.setText(self._tr("json")); self.export_chords.setText(self._tr("chords")); self.ratings.setText(self._tr("ratings"))
            if hasattr(self, "allow_dissonance"): self.allow_dissonance.setText(self._tr("dissonance"))
            self.preset.setToolTip(self._tr("tip_preset")); self.progression.setToolTip(self._tr("tip_progression")); self.melody_template.setToolTip(self._tr("tip_preset")); self.coverage.setToolTip(self._tr("tip_progression"))
        if hasattr(self, "language_combo"):
            self.language_combo.setToolTip(self._tr("tip_language"))
        if hasattr(self, "options_note"):
            self.options_note.setText(self._tr("options_note"))

    def about(self):
        QMessageBox.information(self,"About PythonSoundHelix", f"PythonSoundHelix v{APP_VERSION}\nGPLv3\n\nOriginal SoundHelix project: Thomas Schürger.\nPythonSoundHelix is inspired by SoundHelix but is a separate Python/PyQt6 project intended for github.com/zeittresor.\n\nThis build is quality-first: presets are style hints, key/mode/progression/template default to Auto, songs use seed-specific arrangement entry profiles so different roles can start or stay subtle, and tabs/tooltips/themes/languages are updated live.")

    def apply_theme(self, name="Dark"):
        themes={
            "Dark": """
                QWidget { background:#1d212b; color:#f4f6ff; font-size:13px; }
                QGroupBox { border:1px solid #3c465c; border-radius:8px; margin-top:10px; padding:10px; font-weight:bold; }
                QGroupBox::title { subcontrol-origin: margin; left:12px; padding:0 5px; }
                QLineEdit,QSpinBox,QComboBox,QTextEdit { background:#252b38; color:#f4f6ff; border:1px solid #394257; padding:5px; border-radius:5px; }
                QPushButton { background:#3574ed; color:#ffffff; border:0; padding:10px; border-radius:7px; }
                QPushButton:hover { background:#4d88ff; }
                QTabBar::tab { background:#202638; padding:9px 16px; border-top-left-radius:6px; border-top-right-radius:6px; }
                QTabBar::tab:selected { background:#3574ed; }
            """,
            "Light": """
                QWidget { background:#f2f4f8; color:#172033; font-size:13px; }
                QGroupBox { border:1px solid #b6c0d0; border-radius:8px; margin-top:10px; padding:10px; font-weight:bold; }
                QLineEdit,QSpinBox,QComboBox,QTextEdit { background:#ffffff; color:#172033; border:1px solid #aab4c4; padding:5px; border-radius:5px; }
                QPushButton { background:#2d66cc; color:#ffffff; border:0; padding:10px; border-radius:7px; }
                QTabBar::tab:selected { background:#2d66cc; color:white; }
            """,
            "Matrix": """
                QWidget { background:#071107; color:#b6ffb6; font-size:13px; }
                QGroupBox { border:1px solid #1b7a30; border-radius:8px; margin-top:10px; padding:10px; font-weight:bold; }
                QLineEdit,QSpinBox,QComboBox,QTextEdit { background:#0b1d0b; color:#c8ffc8; border:1px solid #218c3a; padding:5px; border-radius:5px; }
                QPushButton { background:#176d2b; color:#ffffff; border:0; padding:10px; border-radius:7px; }
                QTabBar::tab:selected { background:#176d2b; }
            """,
            "Ocean": """
                QWidget { background:#071827; color:#d9f4ff; font-size:13px; }
                QGroupBox { border:1px solid #276b89; border-radius:8px; margin-top:10px; padding:10px; font-weight:bold; }
                QLineEdit,QSpinBox,QComboBox,QTextEdit { background:#0b2638; color:#e6f9ff; border:1px solid #2e7fa5; padding:5px; border-radius:5px; }
                QPushButton { background:#1681b8; color:#ffffff; border:0; padding:10px; border-radius:7px; }
                QTabBar::tab:selected { background:#1681b8; }
            """,
            "Purple": """
                QWidget { background:#1b1027; color:#f1e7ff; font-size:13px; }
                QGroupBox { border:1px solid #6b3ba1; border-radius:8px; margin-top:10px; padding:10px; font-weight:bold; }
                QLineEdit,QSpinBox,QComboBox,QTextEdit { background:#29173c; color:#f7edff; border:1px solid #7b4ab8; padding:5px; border-radius:5px; }
                QPushButton { background:#7c3fd0; color:#ffffff; border:0; padding:10px; border-radius:7px; }
                QTabBar::tab:selected { background:#7c3fd0; }
            """,
            "Hellfire": """
                QWidget { background:#1a0703; color:#ffe0c7; font-size:13px; }
                QGroupBox { border:1px solid #a83216; border-radius:8px; margin-top:10px; padding:10px; font-weight:bold; }
                QLineEdit,QSpinBox,QComboBox,QTextEdit { background:#2a0d06; color:#ffe7d1; border:1px solid #c94519; padding:5px; border-radius:5px; }
                QPushButton { background:#b63412; color:#ffffff; border:0; padding:10px; border-radius:7px; }
                QTabBar::tab:selected { background:#b63412; }
            """,
            "Sepia": """
                QWidget { background:#f0e2c5; color:#312314; font-size:13px; }
                QGroupBox { border:1px solid #a88954; border-radius:8px; margin-top:10px; padding:10px; font-weight:bold; }
                QLineEdit,QSpinBox,QComboBox,QTextEdit { background:#fff4dc; color:#312314; border:1px solid #b99760; padding:5px; border-radius:5px; }
                QPushButton { background:#9a6a2f; color:#ffffff; border:0; padding:10px; border-radius:7px; }
                QTabBar::tab:selected { background:#9a6a2f; color:white; }
            """,
        }
        tab_fix = {
            "Dark": """QTabBar::tab { background:#202638; color:#f4f6ff; padding:9px 16px; border-top-left-radius:6px; border-top-right-radius:6px; } QTabBar::tab:selected { background:#3574ed; color:white; } QTabBar::tab:hover { background:#2b3448; color:white; }""",
            "Light": """QTabBar::tab { background:#dfe5ef; color:#172033; padding:9px 16px; border-top-left-radius:6px; border-top-right-radius:6px; } QTabBar::tab:selected { background:#2d66cc; color:white; } QTabBar::tab:hover { background:#cfd8e8; color:#172033; }""",
            "Matrix": """QTabBar::tab { background:#0b1d0b; color:#c8ffc8; padding:9px 16px; border-top-left-radius:6px; border-top-right-radius:6px; } QTabBar::tab:selected { background:#176d2b; color:white; } QTabBar::tab:hover { background:#123b19; color:white; }""",
            "Ocean": """QTabBar::tab { background:#0b2638; color:#e6f9ff; padding:9px 16px; border-top-left-radius:6px; border-top-right-radius:6px; } QTabBar::tab:selected { background:#1681b8; color:white; } QTabBar::tab:hover { background:#12415c; color:white; }""",
            "Purple": """QTabBar::tab { background:#2a173d; color:#f4eaff; padding:9px 16px; border-top-left-radius:6px; border-top-right-radius:6px; } QTabBar::tab:selected { background:#7c3fd0; color:white; } QTabBar::tab:hover { background:#43205f; color:white; }""",
            "Hellfire": """QTabBar::tab { background:#2a0d06; color:#ffe7d1; padding:9px 16px; border-top-left-radius:6px; border-top-right-radius:6px; } QTabBar::tab:selected { background:#b63412; color:white; } QTabBar::tab:hover { background:#4a160b; color:white; }""",
            "Sepia": """QTabBar::tab { background:#e2cea7; color:#312314; padding:9px 16px; border-top-left-radius:6px; border-top-right-radius:6px; } QTabBar::tab:selected { background:#9a6a2f; color:white; } QTabBar::tab:hover { background:#d3bb8b; color:#312314; }""",
        }
        self.setStyleSheet(themes.get(name, themes["Dark"]) + "\n" + tab_fix.get(name, tab_fix["Dark"]))

    def _apply_dark_theme(self):
        self.apply_theme("Dark")


def run_gui():
    app=QApplication(sys.argv)
    win=MainWindow(); win.show()
    return app.exec()


def main(argv=None):
    argv=argv or sys.argv[1:]
    if "--nogui" in argv:
        preset="Auto Composer"; seed=None; output=str(OUTPUT_DIR)
        for i,a in enumerate(argv):
            if a=="--preset" and i+1<len(argv): preset=argv[i+1]
            if a=="--seed" and i+1<len(argv): seed=int(argv[i+1])
            if a=="--output" and i+1<len(argv): output=argv[i+1]
        s=preset_defaults(preset)
        if seed is not None: s.seed=seed; s.randomize_seed=False
        res=generate_song(s, output)
        print(f"{res.title} | seed={res.seed} | notes={res.note_count}")
        print(res.midi_path)
        return 0
    return run_gui()
