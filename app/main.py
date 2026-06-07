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
from .style_reference_db import packaged_reference_count, reference_candidates, add_user_reference

ROOT = Path(__file__).resolve().parent.parent
OUTPUT_DIR = ROOT / "output"

def _load_direct_style_names():
    names = ["Auto / random style"]
    try:
        data = json.loads((ROOT / "app" / "prompt_style_words.json").read_text(encoding="utf-8"))
        style_names = sorted({str(s.get("name") or "").strip() for s in data.get("styles", []) if str(s.get("name") or "").strip()}, key=str.lower)
        names.extend(style_names)
    except Exception:
        names.extend(["Techno", "House", "Drum and Bass", "Goa Trance", "Psytrance", "Synthwave", "Ambient"] )
    return names

DIRECT_STYLE_NAMES = _load_direct_style_names()

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
        "prompt_box":"Prompt Composer", "prompt_label":"Describe the song you want", "prompt_generate":"Generate from prompt", "prompt_placeholder":"Example: dark but melodic drum and bass, fast, strong drums, evolving bass, airy pads, no dissonance", "prompt_note":"Prompt-first mode is active. Describe the music in natural language; the app interprets style, mood, tempo, instruments, density, key/mode and arrangement. You can switch back to direct parameter controls in Options.", "prompt_first":"Prompt-first Generate tab", "direct_params":"Show direct parameter controls", "prompt_mode_tip":"When enabled, the Generate tab uses natural-language prompts. When disabled, the original direct parameter controls are visible and the prompt is ignored.", "style_preset":"Style / drum preset", "style_preset_tip":"Direct-parameter mode only: choose one of the imported Synthwave MIDI Reimaginer style profiles as a style/drum/instrument hint. Auto keeps seed-based random style selection.",
        "generate_tab":"Generate", "finetuning_tab":"Finetuning", "options_tab":"Options", "reference_tab":"Reference DB", "log_tab":"Log",
        "help":"Help", "about":"About", "generate":"Generate Song", "play":"Play MIDI", "open":"Open output folder",
        "randomize":"randomize on generate", "lfo":"LFO expression CC", "call":"call/response melody", "bass":"bass favors chord roots", "markers":"section markers", "json":"export JSON result", "chords":"export chord sheet", "ratings":"use thumbs-up rating memory", "dissonance":"allow experimental dissonance/free counterpoint", "lock_instrument":"lock instrument",
        "tip_preset":"Auto Composer randomly chooses a style profile. Other presets are style hints; key/mode/progression/template stay automatic by default.",
        "tip_progression":"Auto mode-safe creates section-specific phrase plans. Manual progressions remain possible but are less varied.",
        "tip_language":"Changes main menus, tabs, buttons and tooltips immediately.",
        "options_note":"v0.7.8: presets act as style hints. Key, mode, progression and melody template stay Auto by default; the engine uses seed-specific role entry profiles so songs can begin with pad, melody, drums, chords or bass.",
    },
    "Deutsch": {
        "prompt_box":"Prompt-Komponist", "prompt_label":"Beschreibe den Song, den du willst", "prompt_generate":"Aus Prompt erzeugen", "prompt_placeholder":"Beispiel: düsterer aber melodischer Drum and Bass, schnell, starke Drums, bewegter Bass, luftige Pads, keine Dissonanzen", "prompt_note":"Prompt-Modus ist aktiv. Beschreibe die Musik als Fließtext; die App interpretiert Stil, Stimmung, Tempo, Instrumente, Dichte, Tonart/Modus und Arrangement. In den Optionen kannst du wieder zur direkten Parameterauswahl wechseln.", "prompt_first":"Prompt-first-Ansicht im Erzeugen-Tab", "direct_params":"Direkte Parameter anzeigen", "prompt_mode_tip":"Aktiv: Erzeugen per Fließtext-Prompt. Inaktiv: ursprüngliche direkte Parameteransicht; der Prompt wird ignoriert.", "style_preset":"Style-/Drum-Preset", "style_preset_tip":"Nur in der direkten Parameteransicht: wählt eines der importierten Synthwave-MIDI-Reimaginer-Stilprofile als Stil-/Drum-/Instrument-Hinweis. Auto behält die seed-basierte Zufallsauswahl.",
        "generate_tab":"Erzeugen", "finetuning_tab":"Feinabstimmung", "options_tab":"Optionen", "reference_tab":"Referenz-DB", "log_tab":"Log",
        "help":"Hilfe", "about":"Über", "generate":"Song erzeugen", "play":"MIDI abspielen", "open":"Ausgabeordner öffnen",
        "randomize":"Seed zufällig beim Erzeugen", "lfo":"LFO-Ausdruck CC", "call":"Call/Response-Melodie", "bass":"Bass bevorzugt Akkord-Grundtöne", "markers":"Abschnittsmarker", "json":"JSON exportieren", "chords":"Akkordblatt exportieren", "ratings":"Daumen-hoch-Bewertungen nutzen", "dissonance":"experimentelle Dissonanzen/freien Kontrapunkt erlauben", "lock_instrument":"Instrument sperren",
        "tip_preset":"Auto Composer wählt zufällig ein Stilprofil. Andere Presets sind Stil-Hinweise; Tonart/Modus/Progression/Melodie bleiben standardmäßig automatisch.",
        "tip_progression":"Auto mode-safe erzeugt abschnittsweise passende Phrasenpläne. Manuelle Progressionen bleiben möglich, sind aber weniger variabel.",
        "tip_language":"Ändert Hauptmenüs, Tabs, Buttons und Tooltips sofort.",
        "options_note":"v0.7.8: Presets sind Stil-Hinweise. Tonart, Modus, Progression und Melodie-Template bleiben standardmäßig Auto; die Engine nutzt seed-spezifische Einstiegsmuster, sodass Songs mit Pad, Melodie, Drums, Akkorden oder Bass beginnen können.",
    },
    "Français": {
        "prompt_box":"Compositeur par prompt", "prompt_label":"Décris le morceau souhaité", "prompt_generate":"Générer depuis le prompt", "prompt_placeholder":"Exemple : drum and bass sombre mais mélodique, rapide, batteries fortes, basse évolutive, pads aériens, sans dissonance", "prompt_note":"Le mode prompt-first est actif. Décris la musique en texte libre; l’application interprète style, humeur, tempo, instruments, densité, tonalité/mode et arrangement. Le mode paramètres directs peut être réactivé dans Options.", "prompt_first":"Onglet génération en mode prompt-first", "direct_params":"Afficher les paramètres directs", "prompt_mode_tip":"Activé : génération par texte libre. Désactivé : vue originale avec paramètres directs; le prompt est ignoré.", "style_preset":"Preset style / batterie", "style_preset_tip":"Mode paramètres directs seulement : choisit un profil de style importé comme indication de style, batterie et instrumentation. Auto conserve la sélection aléatoire par graine.",
        "generate_tab":"Générer", "finetuning_tab":"Réglage fin", "options_tab":"Options", "reference_tab":"Base références", "log_tab":"Journal",
        "help":"Aide", "about":"À propos", "generate":"Générer le morceau", "play":"Lire MIDI", "open":"Ouvrir le dossier de sortie",
        "randomize":"graine aléatoire à la génération", "lfo":"Expression LFO CC", "call":"mélodie appel/réponse", "bass":"basse sur fondamentales d’accords", "markers":"marqueurs de sections", "json":"exporter JSON", "chords":"exporter grille d’accords", "ratings":"utiliser les évaluations positives", "dissonance":"autoriser dissonances/contrepoint libre expérimentaux", "lock_instrument":"verrouiller l’instrument",
        "tip_preset":"Auto Composer choisit un profil de style aléatoire. Les autres presets restent des indications de style; tonalité/mode/progression/modèle mélodique restent automatiques par défaut.",
        "tip_progression":"Auto mode-safe crée des plans de phrases par section. Les progressions manuelles restent possibles, mais moins variées.",
        "tip_language":"Met à jour immédiatement menus, onglets, boutons et infobulles.",
        "options_note":"v0.7.8 : les presets sont des indications de style. Tonalité, mode, progression et modèle mélodique restent en Auto; le moteur utilise des entrées de rôles propres à la graine pour varier les débuts.",
    },
    "Русский": {
        "prompt_box":"Prompt-композитор", "prompt_label":"Опиши нужную композицию", "prompt_generate":"Создать по prompt", "prompt_placeholder":"Пример: тёмный, но мелодичный drum and bass, быстро, сильные ударные, развивающийся бас, воздушные пэды, без диссонанса", "prompt_note":"Активен режим prompt-first. Опиши музыку обычным текстом; приложение интерпретирует стиль, настроение, темп, инструменты, плотность, тональность/лад и аранжировку. В параметрах можно вернуть прямое управление.", "prompt_first":"Вкладка генерации в режиме prompt-first", "direct_params":"Показать прямые параметры", "prompt_mode_tip":"Включено: генерация по текстовому prompt. Выключено: исходная панель прямых параметров; prompt игнорируется.", "style_preset":"Стиль / ударные", "style_preset_tip":"Только в режиме прямых параметров: выбирает импортированный профиль стиля как подсказку для стиля, ударных и инструментов. Auto оставляет случайный выбор по seed.",
        "generate_tab":"Создать", "finetuning_tab":"Тонкая настройка", "options_tab":"Опции", "reference_tab":"База ссылок", "log_tab":"Журнал",
        "help":"Помощь", "about":"О программе", "generate":"Создать песню", "play":"Играть MIDI", "open":"Открыть папку вывода",
        "randomize":"случайный seed при создании", "lfo":"LFO expression CC", "call":"мелодия вопрос/ответ", "bass":"бас по основным тонам аккорда", "markers":"маркеры секций", "json":"экспорт JSON", "chords":"экспорт аккордов", "ratings":"использовать оценки лайков", "dissonance":"разрешить экспериментальные диссонансы/свободный контрапункт", "lock_instrument":"зафиксировать инструмент",
        "tip_preset":"Auto Composer случайно выбирает стилевой профиль. Остальные пресеты — подсказки стиля; тональность/лад/прогрессия/мелодия по умолчанию автоматические.",
        "tip_progression":"Auto mode-safe создает фразовые планы по секциям. Ручные прогрессии возможны, но менее вариативны.",
        "tip_language":"Сразу меняет меню, вкладки, кнопки и подсказки.",
        "options_note":"v0.7.8: пресеты являются стилевыми подсказками. Тональность, лад, прогрессия и шаблон мелодии остаются Auto; движок использует seed-зависимые входы партий, поэтому песня может начинаться с пада, мелодии, ударных, аккордов или баса.",
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
        self.tabs.addTab(self._scroll(self._reference_tab()), "Reference DB")
        self.tabs.addTab(self._scroll(self._log_tab()), "Log")
        menubar = self.menuBar()
        self.help_menu = menubar.addMenu("Help")
        self.about_action = QAction("About", self); self.about_action.triggered.connect(self.about)
        self.help_menu.addAction(self.about_action)

    def _generate_tab(self):
        page=QWidget(); outer=QVBoxLayout(page)
        self.prompt_box=QGroupBox("Prompt Composer"); prompt_box=self.prompt_box; prompt_layout=QVBoxLayout(prompt_box)
        self.prompt_label=QLabel("Describe the song you want")
        self.prompt=QTextEdit(); self.prompt.setMinimumHeight(170); self.prompt.setPlaceholderText("Example: dark but melodic drum and bass, fast, strong drums, evolving bass, airy pads, no dissonance")
        self.prompt_note=QLabel("Direct parameter controls are hidden in v0.7.8. Describe style, mood, tempo, instruments, density, key/mode and arrangement."); self.prompt_note.setWordWrap(True)
        prompt_layout.addWidget(self.prompt_label); prompt_layout.addWidget(self.prompt); prompt_layout.addWidget(self.prompt_note)
        outer.addWidget(prompt_box)
        top=QHBoxLayout(); outer.addLayout(top)
        gen=QGroupBox("Generator"); form=QFormLayout(gen); top.addWidget(gen,1)
        self.preset=QComboBox(); self.preset.addItems(PRESET_NAMES); self.preset.currentTextChanged.connect(self.on_preset)
        self.style_preset=QComboBox(); self.style_preset.addItems(DIRECT_STYLE_NAMES); self.style_preset.setToolTip(self._tr("style_preset_tip"))
        self.title=QLineEdit(); self.seed=QSpinBox(); self.seed.setRange(0,2_147_483_647); self.randomize=QCheckBox("randomize on generate")
        seedrow=QHBoxLayout(); seedwrap=QWidget(); seedrow.addWidget(self.seed); seedrow.addWidget(self.randomize); seedwrap.setLayout(seedrow)
        self.bpm=QSpinBox(); self.bpm.setRange(40,240)
        self.bars=QSpinBox(); self.bars.setRange(16,256)
        self.beats=QSpinBox(); self.beats.setRange(3,4)
        self.ticks=QSpinBox(); self.ticks.setRange(96,1920)
        for label,w in [("Preset",self.preset),(self._tr("style_preset"),self.style_preset),("Song title",self.title),("Seed",seedwrap),("BPM",self.bpm),("Bars",self.bars),("Beats per bar",self.beats),("Ticks per beat",self.ticks)]: form.addRow(label,w)
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
        self.direct_param_boxes=[gen,harm,adv]
        self.apply_generate_view_mode()
        buttons=QHBoxLayout(); outer.addLayout(buttons)
        self.btn_generate=QPushButton("Generate from prompt"); self.btn_generate.clicked.connect(self.generate)
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
            lock=QCheckBox(self._tr("lock_instrument") if hasattr(self, "tabs") else "lock instrument")
            vol=QSlider(Qt.Orientation.Horizontal); vol.setRange(0,127); vol_lbl=QLabel(str(t.volume))
            fine=QSlider(Qt.Orientation.Horizontal); fine.setRange(-100,100); fine_lbl=QLabel(f"{int(getattr(t,'fine_tune_cents',0)):+d} ct")
            octv=QSpinBox(); octv.setRange(-3,3)
            trans=QSpinBox(); trans.setRange(-12,12)
            en.setChecked(t.enabled); role.setCurrentText(t.role); lock.setChecked(bool(getattr(t,'lock_instrument',False))); vol.setValue(t.volume); fine.setValue(int(getattr(t,'fine_tune_cents',0))); octv.setValue(t.octave); trans.setValue(t.transpose)
            vol.valueChanged.connect(lambda v,l=vol_lbl: l.setText(str(v)))
            fine.valueChanged.connect(lambda v,l=fine_lbl: l.setText(f"{v:+d} ct"))
            for label,w in [
                ("Track name",name), ("Enabled",en), ("Function / role",role), ("Instrument",program), ("Lock instrument",lock),
                ("Volume",self._slider_with_label(vol,vol_lbl)), ("Finetune",self._slider_with_label(fine,fine_lbl)),
                ("Octave",octv), ("Transpose",trans)]:
                f.addRow(label,w)
            self.track_widgets.append((t,name,en,role,program,lock,vol,fine,octv,trans)); self.track_cards_layout.addWidget(box)
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
        self.settings.tracks.append(TrackSettings(name, role, True, ch, prog, vol, pan, octv, 0, 0, True))
        self.new_track_name.clear()
        self.rebuild_tracks_tab()

    def _options_tab(self):
        page=QWidget(); v=QVBoxLayout(page)
        ui=QGroupBox("Interface"); form=QFormLayout(ui); v.addWidget(ui)
        self.language_combo=QComboBox(); self.language_combo.addItems(LANGUAGE_NAMES); self.language_combo.currentTextChanged.connect(self.apply_language)
        self.theme_combo=QComboBox(); self.theme_combo.addItems(THEME_NAMES); self.theme_combo.setCurrentText("Dark"); self.theme_combo.currentTextChanged.connect(self.apply_theme)
        self.prompt_mode_checkbox=QCheckBox("Prompt-first Generate tab")
        self.prompt_mode_checkbox.setChecked(True)
        self.prompt_mode_checkbox.toggled.connect(self.apply_generate_view_mode)
        form.addRow("Language / Sprache / Langue / Язык", self.language_combo)
        form.addRow("Theme", self.theme_combo)
        form.addRow("Generate view", self.prompt_mode_checkbox)
        self.allow_dissonance = QCheckBox("allow experimental dissonance/free counterpoint")
        self.allow_dissonance.setChecked(False)
        form.addRow("Harmony safety", self.allow_dissonance)
        self.options_note=QTextEdit(); self.options_note.setMinimumHeight(320); self.options_note.setReadOnly(True)
        v.addWidget(self.options_note)
        v.addStretch(1)
        return page

    def _reference_tab(self):
        page = QWidget(); v = QVBoxLayout(page)
        info = QGroupBox("Style / artist / song reference database")
        il = QVBoxLayout(info)
        self.reference_stats = QLabel(f"Packaged references: {packaged_reference_count()} rows. References are used as high-level style traits only; original melodies/songs are not copied.")
        self.reference_stats.setWordWrap(True)
        il.addWidget(self.reference_stats)
        v.addWidget(info)

        search_box = QGroupBox("Test prompt/reference matching")
        sf = QFormLayout(search_box)
        self.reference_search = QLineEdit(); self.reference_search.setPlaceholderText("Example: genaside ii death of a kamikaze, vangelis, daft punk, metallica")
        self.reference_search_button = QPushButton("Search references")
        self.reference_search_button.clicked.connect(self.search_references)
        self.reference_results = QTextEdit(); self.reference_results.setReadOnly(True); self.reference_results.setMinimumHeight(160)
        sf.addRow("Prompt/reference", self.reference_search)
        sf.addRow("", self.reference_search_button)
        sf.addRow("Matches", self.reference_results)
        v.addWidget(search_box)

        add_box = QGroupBox("Add user reference")
        af = QFormLayout(add_box)
        self.user_ref_alias = QLineEdit(); self.user_ref_alias.setPlaceholderText("Name typed by user, e.g. local band / track reference")
        self.user_ref_canonical = QLineEdit(); self.user_ref_canonical.setPlaceholderText("Canonical display name")
        self.user_ref_family = QComboBox(); self.user_ref_family.addItems(["auto","psytrance","techno","house","trance","dnb","hardcore","ambient","piano","canon","band","latin","chiptune","hiphop","folk","bigbeat","breakbeat","cinematic_synth"])
        self.user_ref_traits = QTextEdit(); self.user_ref_traits.setMinimumHeight(90); self.user_ref_traits.setPlaceholderText("High-level traits only: e.g. dark oldschool breakbeat rave, heavy drums, sub bass, no cover/no melody copying.")
        self.user_ref_bpm_min = QSpinBox(); self.user_ref_bpm_min.setRange(0,240)
        self.user_ref_bpm_max = QSpinBox(); self.user_ref_bpm_max.setRange(0,240)
        self.user_ref_mode = QComboBox(); self.user_ref_mode.addItems(["auto","minor","major"])
        self.user_ref_add_button = QPushButton("Add to user reference list")
        self.user_ref_add_button.clicked.connect(self.add_user_reference_from_ui)
        af.addRow("Alias", self.user_ref_alias)
        af.addRow("Canonical name", self.user_ref_canonical)
        af.addRow("Style family", self.user_ref_family)
        af.addRow("BPM min", self.user_ref_bpm_min)
        af.addRow("BPM max", self.user_ref_bpm_max)
        af.addRow("Mode", self.user_ref_mode)
        af.addRow("Traits", self.user_ref_traits)
        af.addRow("", self.user_ref_add_button)
        v.addWidget(add_box)
        v.addStretch(1)
        return page

    def search_references(self):
        text = self.reference_search.text().strip()
        matches = reference_candidates(text, limit=8)
        if not matches:
            self.reference_results.setPlainText("No reference match.")
            return
        lines = []
        for m in matches:
            lines.append(f"{m.get('score',0)} | {m.get('reference_type')} | {m.get('alias')} -> {m.get('canonical_name')} | family={m.get('style_family')} | bpm={m.get('bpm_min')}-{m.get('bpm_max')} | no_cover={bool(m.get('no_copy',1))}")
            traits = (m.get('traits') or m.get('groove') or '').strip()
            if traits:
                lines.append(f"    {traits[:220]}")
        self.reference_results.setPlainText("\n".join(lines))

    def add_user_reference_from_ui(self):
        try:
            path = add_user_reference(
                self.user_ref_alias.text(),
                self.user_ref_canonical.text(),
                self.user_ref_family.currentText(),
                self.user_ref_traits.toPlainText(),
                self.user_ref_bpm_min.value(),
                self.user_ref_bpm_max.value(),
                self.user_ref_mode.currentText(),
            )
            QMessageBox.information(self, "Reference added", f"Saved to:\n{path}")
            self.user_ref_alias.clear(); self.user_ref_canonical.clear(); self.user_ref_traits.clear()
        except Exception as e:
            QMessageBox.warning(self, "Reference error", f"{type(e).__name__}: {e}")

    def _log_tab(self):
        self.log=QTextEdit(); self.log.setReadOnly(True); return self.log

    def _load_settings_to_ui(self):
        s=self.settings
        if hasattr(self, "prompt"):
            self.prompt.setPlainText(getattr(s, "prompt", ""))
        if hasattr(self, "prompt_mode_checkbox"):
            self.prompt_mode_checkbox.setChecked(bool(getattr(s, "prompt_mode", True)))
            self.apply_generate_view_mode()
        self.preset.blockSignals(True); self.preset.setCurrentText(s.preset_name); self.preset.blockSignals(False)
        if hasattr(self, "style_preset"):
            self.style_preset.setCurrentText(getattr(s, "direct_style_hint", "Auto / random style") or "Auto / random style")
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
        for t,name,en,role,program,lock,vol,fine,octv,trans in self.track_widgets:
            t.name=name.text().strip() or t.name; t.enabled=en.isChecked(); t.role=role.currentText(); t.program=program.currentIndex(); t.lock_instrument=lock.isChecked(); t.volume=vol.value(); t.fine_tune_cents=fine.value(); t.octave=octv.value(); t.transpose=trans.value()
        if hasattr(self, "prompt"):
            s.prompt=self.prompt.toPlainText().strip()
            s.prompt_language=self.language_combo.currentText() if hasattr(self, "language_combo") else "English"
            s.prompt_mode=self.prompt_mode_checkbox.isChecked() if hasattr(self, "prompt_mode_checkbox") else True
        if hasattr(self, "style_preset"):
            s.direct_style_hint=self.style_preset.currentText()
        sanitize_mode_progression(s)
        return s

    def on_preset(self, name):
        old_prompt_mode = self.prompt_mode_checkbox.isChecked() if hasattr(self, "prompt_mode_checkbox") else True
        old_style_hint = self.style_preset.currentText() if hasattr(self, "style_preset") else "Auto / random style"
        self.settings=preset_defaults(name)
        self.settings.prompt_mode = old_prompt_mode
        self.settings.direct_style_hint = old_style_hint
        self._load_settings_to_ui()

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

    def apply_generate_view_mode(self):
        prompt_mode = self.prompt_mode_checkbox.isChecked() if hasattr(self, "prompt_mode_checkbox") else True
        if hasattr(self, "prompt_box"):
            self.prompt_box.setVisible(prompt_mode)
        for box in getattr(self, "direct_param_boxes", []):
            box.setVisible(not prompt_mode)
        if hasattr(self, "btn_generate"):
            self.btn_generate.setText(self._tr("prompt_generate") if prompt_mode else self._tr("generate"))
        if hasattr(self, "prompt_mode_checkbox"):
            self.prompt_mode_checkbox.setText(self._tr("prompt_first"))
            self.prompt_mode_checkbox.setToolTip(self._tr("prompt_mode_tip"))

    def _tr(self, key: str) -> str:
        lang = getattr(self, "language_combo", None).currentText() if hasattr(self, "language_combo") else "English"
        return TRANSLATIONS.get(lang, TRANSLATIONS["English"]).get(key, TRANSLATIONS["English"].get(key, key))

    def apply_language(self, name=None):
        if not hasattr(self, "tabs"):
            return
        self.tabs.setTabText(0, self._tr("generate_tab")); self.tabs.setTabText(1, self._tr("finetuning_tab")); self.tabs.setTabText(2, self._tr("options_tab")); self.tabs.setTabText(3, self._tr("reference_tab")); self.tabs.setTabText(4, self._tr("log_tab"))
        if hasattr(self, "help_menu"):
            self.help_menu.setTitle(self._tr("help"))
        if hasattr(self, "about_action"):
            self.about_action.setText(self._tr("about"))
        if hasattr(self, "btn_generate"):
            self.btn_generate.setText(self._tr("prompt_generate") if (not hasattr(self, "prompt_mode_checkbox") or self.prompt_mode_checkbox.isChecked()) else self._tr("generate")); self.btn_play.setText(self._tr("play")); self.btn_open.setText(self._tr("open"))
            self.randomize.setText(self._tr("randomize")); self.lfo.setText(self._tr("lfo")); self.call.setText(self._tr("call")); self.bass_roots.setText(self._tr("bass")); self.markers.setText(self._tr("markers")); self.export_json.setText(self._tr("json")); self.export_chords.setText(self._tr("chords")); self.ratings.setText(self._tr("ratings"))
            if hasattr(self, "allow_dissonance"): self.allow_dissonance.setText(self._tr("dissonance"))
            if hasattr(self, "track_widgets"):
                for row in self.track_widgets:
                    if len(row) >= 10:
                        row[5].setText(self._tr("lock_instrument"))
            self.preset.setToolTip(self._tr("tip_preset")); self.progression.setToolTip(self._tr("tip_progression")); self.melody_template.setToolTip(self._tr("tip_preset")); self.coverage.setToolTip(self._tr("tip_progression"))
            if hasattr(self, "style_preset"):
                self.style_preset.setToolTip(self._tr("style_preset_tip"))
        if hasattr(self, "prompt_label"):
            self.prompt_label.setText(self._tr("prompt_label")); self.prompt.setPlaceholderText(self._tr("prompt_placeholder")); self.prompt_note.setText(self._tr("prompt_note"))
        if hasattr(self, "language_combo"):
            self.language_combo.setToolTip(self._tr("tip_language"))
        if hasattr(self, "prompt_mode_checkbox"):
            self.prompt_mode_checkbox.setText(self._tr("prompt_first")); self.prompt_mode_checkbox.setToolTip(self._tr("prompt_mode_tip"))
        if hasattr(self, "options_note"):
            self.options_note.setText(self._tr("options_note"))

    def about(self):
        QMessageBox.information(self,"About PythonSoundHelix", f"PythonSoundHelix v{APP_VERSION}\nGPLv3\n\nPythonSoundHelix is inspired by SoundHelix but is a separate Python/PyQt6 project by github.com/zeittresor.\n\nOriginal SoundHelix project: Thomas Schürger (soundhelix.com).\n\nThis build is prompt-first by default, but Options can switch the Generate tab back to the original direct parameter view, including a style/drum preset dropdown with the imported 170+ style profiles. The app maps style/mood/tempo/instrument words to safe musical settings using multilingual wordlists, imported Synthwave Midi Reimaginer style vocabulary and a local reference database for artist/song style traits. It never copies original songs or melodies.")

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
        preset="Auto Composer"; seed=None; output=str(OUTPUT_DIR); prompt=""; language="English"
        for i,a in enumerate(argv):
            if a=="--preset" and i+1<len(argv): preset=argv[i+1]
            if a=="--seed" and i+1<len(argv): seed=int(argv[i+1])
            if a=="--output" and i+1<len(argv): output=argv[i+1]
            if a=="--prompt" and i+1<len(argv): prompt=argv[i+1]
            if a=="--language" and i+1<len(argv): language=argv[i+1]
        s=preset_defaults(preset)
        s.prompt=prompt; s.prompt_language=language; s.prompt_mode=True
        if seed is not None: s.seed=seed; s.randomize_seed=False
        res=generate_song(s, output)
        print(f"{res.title} | seed={res.seed} | notes={res.note_count}")
        print(res.midi_path)
        return 0
    return run_gui()
