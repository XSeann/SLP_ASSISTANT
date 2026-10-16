import sys
from pathlib import Path
from PySide6.QtCore import Qt, QTimer
from PySide6.QtGui import QFont
from PySide6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, QLabel,
    QPushButton, QLineEdit, QTextEdit, QListWidget, QListWidgetItem, QStackedWidget,
    QMessageBox, QDialog, QDialogButtonBox, QProgressBar, QFrame, QSplitter,
    QTabWidget, QFormLayout
)
from modules.recorder import AudioRecorder
from modules.pipeline import process_recording

from target_phonemizer import target_phonemizer_main

ROOT = Path(__file__).resolve().parent

RECORDINGS = ROOT / "target_phonemes"

RESULT_FOLDERS = {
    "Transcription": ROOT / "transcription",
    "Actual Phonemes": ROOT / "phoneme_word",
    "Phonetic Inventory": ROOT / "phonetic_inventory",
    "PCC / PVC": ROOT / "pcc_pvc",
    "TTR / Syllable Shape": ROOT / "tttr_syllable_shape",
    "SODA": ROOT / "soda",
}

RECORDINGS.mkdir(parents=True, exist_ok=True)

STYLE = """
QWidget {
    background: #0b1726;
    color: #e8f0fb;
    font-family: "Segoe UI", Arial;
    font-size: 14px;
}

QMainWindow {
    background: #0b1726;
}

QFrame#panel {
    background: #11243a;
    border: 1px solid #29435f;
    border-radius: 12px;
}

QLabel#muted {
    color: #9bb0c8;
}

QLabel#heading {
    font-size: 25px;
    font-weight: 700;
}

QLabel#sectionTitle {
    font-size: 15px;
    font-weight: 700;
    color: #c5d8ef;
}

QPushButton {
    background: #203b5b;
    border: 1px solid #355779;
    border-radius: 8px;
    padding: 9px 13px;
}

QPushButton:hover {
    background: #2b4e75;
}

QPushButton#primary {
    background: #1677f2;
    border: none;
    color: white;
    font-weight: 700;
}

QPushButton#primary:hover {
    background: #3289ff;
}

QPushButton#danger {
    background: #e34d62;
    border: none;
    color: white;
    font-weight: 700;
}

QPushButton:disabled,
QPushButton#primary:disabled {
    color: #8293a8;
    background: #1a2a3d;
    border: 1px solid #263b52;
}

QLineEdit, QTextEdit, QListWidget {
    background: #0e1d2e;
    border: 1px solid #29435f;
    border-radius: 7px;
    padding: 7px;
    selection-background-color: #1559a8;
}

QListWidget {
    padding: 6px;
    outline: none;
}

QListWidget::item {
    padding: 10px;
    margin: 3px 1px;
    border-radius: 7px;
}

QListWidget::item:hover {
    background: #172f49;
}

QListWidget::item:selected {
    background: #1559a8;
    color: white;
}

QTabWidget::pane {
    border: 1px solid #29435f;
    border-radius: 8px;
    top: -1px;
}

QTabBar::tab {
    background: #172b41;
    padding: 9px 15px;
    margin-right: 4px;
    border-radius: 6px;
}

QTabBar::tab:selected {
    background: #1677f2;
    color: white;
}

QProgressBar {
    border: 1px solid #29435f;
    border-radius: 6px;
    text-align: center;
    background: #0e1d2e;
}

QProgressBar::chunk {
    background: #1677f2;
    border-radius: 5px;
}

QSplitter::handle {
    background: #20354d;
}

QSplitter::handle:hover {
    background: #1677f2;
}


QFrame#meterPanel {
    background: #0e1d2e;
    border: 1px solid #29435f;
    border-radius: 14px;
}

QLabel#sectionLabel {
    color: #72baff;
    font-size: 13px;
    font-weight: 700;
    letter-spacing: 1px;
    background: transparent;
}

QLabel#waveDisplay {
    background: #10263b;
    border: 1px solid #203e59;
    border-radius: 10px;
    color: #28c3df;
    font-size: 32px;
    font-weight: 700;
}

QLabel#recordClock {
    background: transparent;
    color: #f1f6ff;
    font-size: 30px;
    font-weight: 700;
    padding: 2px;
}

QLabel#readyStatus {
    background: #183b38;
    color: #71e0b0;
    border-radius: 6px;
    padding: 6px 10px;
    font-size: 11px;
    font-weight: 700;
}

QLabel#statusMessage {
    background: #0e1d2e;
    border: 1px solid #29435f;
    border-radius: 8px;
    color: #b5c8df;
    padding: 10px;
}

QLineEdit:focus {
    border: 1px solid #3b9cff;
}

QPushButton#primary {
    background: #1677f2;
    border: none;
    border-radius: 9px;
    color: white;
    font-weight: 700;
}

QPushButton#primary:hover {
    background: #328cff;
}

QPushButton#danger {
    background: #e34d62;
    border: none;
    border-radius: 9px;
    color: white;
    font-weight: 700;
}

QPushButton#danger:hover {
    background: #f26074;
}

"""

def nice_name(path):
    return Path(path).stem

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("SLP AI Assistant")
        self.resize(1180, 760)
        self.recorder = AudioRecorder()
        self.record_path = None
        self.record_name = ""
        self.expected_words = ""
        self.elapsed = 0
        self.recording_active = False
        self.paused = False
        self.timer = QTimer(self)
        self.timer.setInterval(1000)
        self.timer.timeout.connect(self.tick)
        self.wave_timer = QTimer(self)
        self.wave_timer.setInterval(140)
        self.wave_timer.timeout.connect(self.animate_wave)

        self.stack = QStackedWidget()
        self.setCentralWidget(self.stack)
        self.home = self.make_home()
        self.record_page = self.make_record_page()
        self.files_page = self.make_files_page()
        self.stack.addWidget(self.home)
        self.stack.addWidget(self.record_page)
        self.stack.addWidget(self.files_page)
        self.refresh_files()

    def make_home(self):
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setAlignment(Qt.AlignCenter)
        layout.setSpacing(20)
        icon = QLabel("◖)))")
        icon.setAlignment(Qt.AlignCenter)
        icon.setStyleSheet("color:#38a4ff;font-size:52px;font-weight:800;")
        title = QLabel("SLP AI Assistant")
        title.setObjectName("heading")
        title.setAlignment(Qt.AlignCenter)
        subtitle = QLabel("Speech Analysis Workstation")
        subtitle.setAlignment(Qt.AlignCenter)
        subtitle.setObjectName("muted")
        desc = QLabel("Record speech, process phonemes, and review analysis results.")
        desc.setAlignment(Qt.AlignCenter)
        buttons = QHBoxLayout()
        record = QPushButton("🎙   Record\nOpen recording page")
        record.setObjectName("primary")
        record.setMinimumSize(220, 90)
        record.clicked.connect(lambda: self.stack.setCurrentWidget(self.record_page))
        files = QPushButton("📁   Files\nView saved recordings")
        files.setMinimumSize(220, 90)
        files.clicked.connect(self.open_files)
        buttons.addWidget(record)
        buttons.addWidget(files)
        layout.addWidget(icon)
        layout.addWidget(title)
        layout.addWidget(subtitle)
        layout.addWidget(desc)
        layout.addSpacing(12)
        layout.addLayout(buttons)
        footer = QLabel("LOCAL DESKTOP APP  •  Windows development / Raspberry Pi target")
        footer.setAlignment(Qt.AlignCenter)
        footer.setObjectName("muted")
        layout.addSpacing(40)
        layout.addWidget(footer)
        return page 
    
    def make_record_page(self):
        page = QWidget()
        outer = QVBoxLayout(page)
        outer.setContentsMargins(24, 18, 24, 22)
        outer.setSpacing(18)

        # ================= HEADER =================
        top = QHBoxLayout()

        back = QPushButton("←  Back to Home")
        back.setMinimumHeight(42)
        back.clicked.connect(self.go_home)

        heading_box = QVBoxLayout()
        self.record_title = QLabel("Recording Studio")
        self.record_title.setObjectName("heading")
        self.record_title.setAlignment(Qt.AlignCenter)

        subtitle = QLabel("Capture speech and analyze pronunciation")
        subtitle.setObjectName("muted")
        subtitle.setAlignment(Qt.AlignCenter)

        heading_box.addWidget(self.record_title)
        heading_box.addWidget(subtitle)

        top.addWidget(back)
        top.addStretch(1)
        top.addLayout(heading_box)
        top.addStretch(1)

        # Balance the header so the title stays centered.
        spacer = QWidget()
        spacer.setFixedWidth(back.sizeHint().width())
        top.addWidget(spacer)

        outer.addLayout(top)

        # ================= RECORD DETAILS =================
        form = QFrame()
        form.setObjectName("panel")
        form_layout = QFormLayout(form)
        form_layout.setContentsMargins(22, 18, 22, 18)
        form_layout.setHorizontalSpacing(20)
        form_layout.setVerticalSpacing(14)
        form_layout.setLabelAlignment(Qt.AlignLeft | Qt.AlignVCenter)

        section_label = QLabel("01  RECORDING DETAILS")
        section_label.setObjectName("sectionLabel")
        form_layout.addRow(section_label, QLabel(""))

        self.name_input = QLineEdit("session_1")
        self.name_input.setMinimumHeight(42)
        self.name_input.setPlaceholderText("e.g. session_1")

        self.words_input = QLineEdit()
        self.words_input.setMinimumHeight(42)
        self.words_input.setPlaceholderText(
            "Enter the sentence the speaker will say..."
        )

        name_label = QLabel("Record name")
        words_label = QLabel("Expected sentence")

        form_layout.addRow(name_label, self.name_input)
        form_layout.addRow(words_label, self.words_input)

        self.form_note = QLabel(
            "Target phonemes will be generated automatically before recording."
        )
        self.form_note.setObjectName("muted")
        self.form_note.setWordWrap(True)
        form_layout.addRow("", self.form_note)

        outer.addWidget(form)

        # ================= AUDIO MONITOR =================
        meter = QFrame()
        meter.setObjectName("meterPanel")
        meter_layout = QVBoxLayout(meter)
        meter_layout.setContentsMargins(20, 18, 20, 18)
        meter_layout.setSpacing(10)

        meter_header = QHBoxLayout()
        meter_title = QLabel("02  AUDIO MONITOR")
        meter_title.setObjectName("sectionLabel")

        self.live_status = QLabel("●  READY TO RECORD")
        self.live_status.setObjectName("readyStatus")
        self.live_status.setAlignment(Qt.AlignRight | Qt.AlignVCenter)

        meter_header.addWidget(meter_title)
        meter_header.addStretch()
        meter_header.addWidget(self.live_status)
        meter_layout.addLayout(meter_header)

        self.wave_label = QLabel("▁  ▂  ▃  ▄  ▅  ▆  ▇  ▆  ▅  ▄  ▃  ▂  ▁")
        self.wave_label.setObjectName("waveDisplay")
        self.wave_label.setAlignment(Qt.AlignCenter)
        self.wave_label.setMinimumHeight(100)
        meter_layout.addWidget(self.wave_label)

        self.clock_label = QLabel("●  00:00")
        self.clock_label.setObjectName("recordClock")
        self.clock_label.setAlignment(Qt.AlignCenter)
        meter_layout.addWidget(self.clock_label)

        outer.addWidget(meter)

        # ================= RECORDING CONTROLS =================
        controls_panel = QFrame()
        controls_panel.setObjectName("panel")
        controls_layout = QVBoxLayout(controls_panel)
        controls_layout.setContentsMargins(20, 18, 20, 18)
        controls_layout.setSpacing(14)

        controls_title = QLabel("03  RECORDING CONTROLS")
        controls_title.setObjectName("sectionLabel")
        controls_layout.addWidget(controls_title)

        buttons = QHBoxLayout()
        buttons.setSpacing(12)

        self.start_btn = QPushButton("●   Start Recording")
        self.start_btn.setObjectName("primary")
        self.start_btn.setMinimumHeight(50)
        self.start_btn.setMinimumWidth(200)

        self.pause_btn = QPushButton("Ⅱ   Pause")
        self.pause_btn.setMinimumHeight(50)
        self.pause_btn.setMinimumWidth(150)
        self.pause_btn.setEnabled(False)

        self.stop_btn = QPushButton("■   Stop Recording")
        self.stop_btn.setObjectName("danger")
        self.stop_btn.setMinimumHeight(50)
        self.stop_btn.setMinimumWidth(180)
        self.stop_btn.setEnabled(False)

        self.start_btn.clicked.connect(self.start_recording)
        self.pause_btn.clicked.connect(self.toggle_pause)
        self.stop_btn.clicked.connect(self.confirm_stop)

        buttons.addStretch()
        buttons.addWidget(self.start_btn)
        buttons.addWidget(self.pause_btn)
        buttons.addWidget(self.stop_btn)
        buttons.addStretch()

        controls_layout.addLayout(buttons)

        self.record_status = QLabel(
            "Ready. Enter a record name and expected sentence, then start."
        )
        self.record_status.setObjectName("statusMessage")
        self.record_status.setAlignment(Qt.AlignCenter)
        self.record_status.setWordWrap(True)
        controls_layout.addWidget(self.record_status)

        outer.addWidget(controls_panel)
        outer.addStretch(1)

        return page


    def make_files_page(self):
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setContentsMargins(18, 14, 18, 14)
        layout.setSpacing(12)

        # Compact page header
        top = QHBoxLayout()
        top.setSpacing(12)

        back = QPushButton("← Home")
        back.clicked.connect(self.go_home)

        title_box = QVBoxLayout()
        title_box.setSpacing(2)

        title = QLabel("Saved Recordings")
        title.setObjectName("heading")

        subtitle = QLabel("Review speech analysis and session results")
        subtitle.setObjectName("muted")

        title_box.addWidget(title)
        title_box.addWidget(subtitle)

        refresh_btn = QPushButton("↻ Refresh")
        refresh_btn.clicked.connect(self.refresh_files)

        top.addWidget(back, 0, Qt.AlignVCenter)
        top.addSpacing(8)
        top.addLayout(title_box)
        top.addStretch()
        top.addWidget(refresh_btn, 0, Qt.AlignVCenter)

        layout.addLayout(top)

        # Main content: left sessions, right results
        splitter = QSplitter(Qt.Horizontal)
        splitter.setChildrenCollapsible(False)
        splitter.setHandleWidth(5)

        # LEFT PANEL
        left = QFrame()
        left.setObjectName("panel")
        left.setMinimumWidth(210)

        left_layout = QVBoxLayout(left)
        left_layout.setContentsMargins(12, 12, 12, 12)
        left_layout.setSpacing(9)

        session_heading = QLabel("RECORDINGS")
        session_heading.setObjectName("sectionTitle")

        self.session_count = QLabel("Sessions: 0")
        self.session_count.setObjectName("muted")

        self.file_list = QListWidget()
        self.file_list.setSpacing(3)
        self.file_list.currentItemChanged.connect(
            self.show_selected_record
        )

        left_layout.addWidget(session_heading)
        left_layout.addWidget(self.session_count)
        left_layout.addWidget(self.file_list, 1)

        # RIGHT PANEL
        right = QWidget()
        right_layout = QVBoxLayout(right)
        right_layout.setContentsMargins(0, 0, 0, 0)
        right_layout.setSpacing(8)

        detail_header = QHBoxLayout()
        detail_header.setSpacing(10)

        title_column = QVBoxLayout()
        title_column.setSpacing(3)

        self.detail_title = QLabel("Select a recording")
        self.detail_title.setObjectName("heading")

        self.detail_status = QLabel(
            "Choose a session from the left panel."
        )
        self.detail_status.setObjectName("muted")
        self.detail_status.setWordWrap(True)

        title_column.addWidget(self.detail_title)
        title_column.addWidget(self.detail_status)

        detail_header.addLayout(title_column, 1)

        self.process_bar = QProgressBar()
        self.process_bar.setRange(0, 0)
        self.process_bar.setMaximumWidth(180)
        self.process_bar.setVisible(False)

        detail_header.addWidget(self.process_bar, 0, Qt.AlignVCenter)
        right_layout.addLayout(detail_header)

        self.result_tabs = QTabWidget()

        self.result_text = QTextEdit()
        self.result_text.setReadOnly(True)
        self.result_text.setAcceptRichText(False)
        self.result_tabs.addTab(
            self.result_text, "Overview / Results"
        )

        self.json_text = QTextEdit()
        self.json_text.setReadOnly(True)
        self.result_tabs.addTab(self.json_text, "Raw JSON")

        right_layout.addWidget(self.result_tabs, 1)

        # Bottom actions
        actions = QHBoxLayout()
        actions.setSpacing(8)

        self.process_selected_btn = QPushButton(
            "▶  Process Recording"
        )
        self.process_selected_btn.setObjectName("primary")
        self.process_selected_btn.clicked.connect(
            self.process_selected
        )

        self.delete_btn = QPushButton("🗑  Delete")
        self.delete_btn.setObjectName("danger")
        self.delete_btn.clicked.connect(self.delete_selected)

        actions.addWidget(self.process_selected_btn)
        actions.addStretch()
        actions.addWidget(self.delete_btn)

        right_layout.addLayout(actions)

        splitter.addWidget(left)
        splitter.addWidget(right)
        splitter.setStretchFactor(0, 0)
        splitter.setStretchFactor(1, 1)
        splitter.setSizes([270, 850])

        layout.addWidget(splitter, 1)

        return page

    def go_home(self):
        if self.recording_active:
            QMessageBox.information(self, "Recording in progress", "Stop the recording before returning to the home page.")
            return
        self.stack.setCurrentWidget(self.home)

    def open_files(self):
        self.refresh_files()
        self.stack.setCurrentWidget(self.files_page)

    def start_recording(self):
        name = self.name_input.text().strip()
        words = self.words_input.text().strip()
        if not name or not words:
            QMessageBox.warning(self, "Missing information", "Please enter both a record name and expected words.")
            return
        safe_name = "".join(c for c in name if c.isalnum() or c in "-_ ").strip().replace(" ", "_")
        if not safe_name:
            QMessageBox.warning(self, "Invalid name", "Please use a record name containing letters or numbers.")
            return

        target = target_phonemizer_main(safe_name, words)
        record_name = target["base"]
        recording_path = target["folder"] / f"{record_name}.wav"

        if recording_path.exists():
            answer = QMessageBox.question(self, "Name already exists", f"{safe_name} already exists. Replace it?",
                                          QMessageBox.Yes | QMessageBox.No, QMessageBox.No)
            if answer != QMessageBox.Yes:
                return
        # Generate target phonemes before recording by invoking the project's target script if configured.
        try:
            self.recorder.start(recording_path)
        except Exception as exc:
            QMessageBox.critical(self, "Could not start recording", str(exc))
            return
        self.record_name, self.expected_words, self.record_path = safe_name, words, recording_path
        self.elapsed = 0
        self.paused = False
        self.recording_active = True
        self.timer.start()
        self.wave_timer.start()
        self.start_btn.setEnabled(False)
        self.pause_btn.setEnabled(True)
        self.stop_btn.setEnabled(True)
        self.name_input.setEnabled(False)
        self.words_input.setEnabled(False)
        self.record_status.setText("Recording… Back to Home is disabled until recording stops.")
        self.live_status.setText("●  RECORDING")
        self.live_status.setStyleSheet(
            "background:#4a2632; color:#ff8b9b; "
            "border-radius:6px; padding:6px 10px; font-weight:700;"
        )


    def toggle_pause(self):
        if not self.recording_active:
            return
        if not self.paused:
            self.recorder.pause()
            self.timer.stop()
            self.wave_timer.stop()
            self.paused = True
            self.pause_btn.setText("▶ Resume")
            self.record_status.setText("Recording paused.")
            self.wave_label.setText("Ⅱ  PAUSED")
            self.live_status.setText("Ⅱ  PAUSED")
            self.live_status.setStyleSheet(
                "background:#40351f; color:#ffd27a; "
                "border-radius:6px; padding:6px 10px; font-weight:700;"
            )
        else:
            self.recorder.resume()
            self.timer.start()
            self.wave_timer.start()
            self.paused = False
            self.pause_btn.setText("Ⅱ Pause")
            self.record_status.setText("Recording…")
            self.live_status.setText("●  RECORDING")
            self.live_status.setStyleSheet(
                "background:#4a2632; color:#ff8b9b; "
                "border-radius:6px; padding:6px 10px; font-weight:700;"
            )

    def confirm_stop(self):
        if not self.recording_active:
            return
        answer = QMessageBox.question(self, "Stop Recording", "Are you sure you want to stop this recording?",
                                      QMessageBox.Yes | QMessageBox.No, QMessageBox.No)
        if answer != QMessageBox.Yes:
            if self.paused:
                self.recorder.resume()
                self.paused = False
                self.pause_btn.setText("Ⅱ Pause")
                self.timer.start()
                self.wave_timer.start()
            self.record_status.setText("Recording…")
            return
        try:
            self.recorder.stop()
        except Exception as exc:
            QMessageBox.critical(self, "Recording error", str(exc))
        self.timer.stop()
        self.wave_timer.stop()
        self.recording_active = False
        self.reset_record_controls()
        self.record_status.setText(f"Saved: {self.record_path.name if self.record_path else ''}")
        answer = QMessageBox.question(self, "Process Recording", "Do you want to process this record?",
                                      QMessageBox.Yes | QMessageBox.No, QMessageBox.Yes)
        if answer == QMessageBox.Yes:
            self.run_processing(self.record_name)
        self.refresh_files()

    def reset_record_controls(self):
        self.start_btn.setEnabled(True)
        self.pause_btn.setEnabled(False)
        self.stop_btn.setEnabled(False)
        self.pause_btn.setText("Ⅱ Pause")
        self.name_input.setEnabled(True)
        self.words_input.setEnabled(True)
        self.wave_label.setText("▁ ▂ ▃ ▅ ▇ ▅ ▃ ▂ ▁")
        self.live_status.setText("●  READY TO RECORD")
        self.live_status.setStyleSheet("")
        self.clock_label.setText("●  00:00")
        self.elapsed = 0

    def tick(self):
        self.elapsed += 1
        self.clock_label.setText(f"● {self.elapsed // 60:02d}:{self.elapsed % 60:02d}")

    def animate_wave(self):
        import random
        bars = ["▁", "▂", "▃", "▄", "▅", "▆", "▇"]
        self.wave_label.setText(" ".join(random.choice(bars) for _ in range(29)))

    def get_session_data(self, name):
        """Load all available JSON results for a session."""
        results = {}

        target_path = RECORDINGS / name / f"{name}.json"
        paths = {"Target Phonemes": target_path}

        for label, folder in RESULT_FOLDERS.items():
            paths[label] = folder / f"{name}.json"

        import json

        for label, path in paths.items():
            if path.is_file():
                try:
                    with path.open("r", encoding="utf-8") as file:
                        results[label] = json.load(file)
                except (OSError, json.JSONDecodeError) as exc:
                    results[label] = {"error": str(exc)}

        return results

    def refresh_files(self):
        """List session folders under target_phonemes."""
        if not hasattr(self, "file_list"):
            return

        current = self.file_list.currentItem()
        current_name = current.data(Qt.UserRole) if current else None

        self.file_list.blockSignals(True)
        self.file_list.clear()

        if RECORDINGS.exists():
            sessions = [
                folder for folder in RECORDINGS.iterdir()
                if folder.is_dir()
                and (folder / f"{folder.name}.json").is_file()
            ]

            sessions.sort(
                key=lambda p: (
                    0,
                    int(p.name.split("_")[-1])
                ) if p.name.startswith("session_")
                and p.name.split("_")[-1].isdigit()
                else (1, p.name.lower()),
                reverse=False
            )

            for folder in sessions:
                name = folder.name
                results = self.get_session_data(name)

                processed = any(
                    label in results
                    for label in (
                        "Transcription",
                        "Actual Phonemes",
                        "PCC / PVC",
                        "SODA",
                    )
                )

                status = "● Processed" if processed else "● Not processed"
                item = QListWidgetItem(f"{name}\n{status}")
                item.setData(Qt.UserRole, name)
                item.setData(Qt.UserRole + 1, processed)
                self.file_list.addItem(item)

                if name == current_name:
                    self.file_list.setCurrentItem(item)
                    
            self.session_count.setText(
                f"Sessions: {self.file_list.count()}"
            )

        self.file_list.blockSignals(False)

        if self.file_list.count() and self.file_list.currentRow() < 0:
            self.file_list.setCurrentRow(0)
        elif not self.file_list.count():
            self.detail_title.setText("No recordings yet")
            self.detail_status.setText(
                "Record a session to see its results here."
            )
            self.result_text.clear()
            self.json_text.clear()
            self.process_selected_btn.setEnabled(False)
            self.delete_btn.setEnabled(False)

    def show_selected_record(self, current, previous=None):
        if not current:
            return

        name = current.data(Qt.UserRole)
        results = self.get_session_data(name)

        self.detail_title.setText(name)

        target = results.get("Target Phonemes", {})
        sentence = target.get("target_input", {}).get("sentence", "")

        self.detail_status.setText(
            f"Expected sentence: {sentence}"
            if sentence else "Session results"
        )

        processed = any(
            label in results
            for label in (
                "Transcription",
                "Actual Phonemes",
                "PCC / PVC",
                "SODA",
            )
        )

        self.process_selected_btn.setEnabled(not processed)
        self.delete_btn.setEnabled(True)

        import json

        self.json_text.setPlainText(
            json.dumps(results, indent=2, ensure_ascii=False)
            if results else "No JSON results found."
        )

        self.result_text.setHtml(
            self.format_results(name, results)
        )

    def format_results(self, name, results):
        def esc(value):
            import html
            return html.escape(str(value))

        def section(title, content):
            return f"""
            <h2 style="color:#7db9ff; font-size:17px;
                       margin-top:20px;">{title}</h2>
            <div style="background:#11243a; border:1px solid #29435f;
                        border-radius:9px; padding:12px;">
                {content}
            </div>
            """

        def muted(text):
            return (
                f'<span style="color:#9bb0c8;">'
                f'{esc(text)}</span>'
            )

        lines = [
            '<div style="font-family:Segoe UI,Arial;'
            'font-size:14px;color:#e8f0fb;">',
            f'<h1 style="font-size:23px;margin-bottom:4px;">'
            f'{esc(name)}</h1>',
        ]

        target = results.get("Target Phonemes", {})
        target_input = target.get("target_input", {})
        sentence = target_input.get("sentence", "Not available")
        words = target.get("words", [])

        lines.append(
            f'<p style="color:#b7cbe3;">'
            f'{esc(sentence)}</p>'
        )

        # Score cards
        scores = results.get("PCC / PVC", {})
        pcc = scores.get("PCC", {})
        pvc = scores.get("PVC", {})

        def score_card(label, score):
            if not score:
                value = "—"
                detail = "Not available"
            else:
                value = f"{score.get('percentage', 0)}%"
                detail = (
                    f"{score.get('correct', 0)} correct / "
                    f"{score.get('total', 0)} scored"
                )

            return f"""
            <td width="50%" style="padding:5px;">
                <div style="background:#142b43;
                            border:1px solid #315373;
                            border-radius:10px;padding:14px;">
                    <div style="color:#9bb0c8;font-size:13px;">
                        {label}
                    </div>
                    <div style="font-size:29px;font-weight:bold;
                                color:#72b7ff;margin:5px 0;">
                        {esc(value)}
                    </div>
                    <div style="color:#b5c8dd;font-size:12px;">
                        {esc(detail)}
                    </div>
                </div>
            </td>
            """

        lines.append(
            '<table width="100%" cellspacing="0"><tr>'
            + score_card("PCC · Consonants", pcc)
            + score_card("PVC · Vowels", pvc)
            + '</tr></table>'
        )

        # Target phonemes by word
        rows = ""
        for word in words:
            phones = " ".join(word.get("phonemes", []))
            rows += (
                f"<tr><td>{esc(word.get('word', '?'))}</td>"
                f"<td style='color:#91c8ff;'>"
                f"{esc(phones)}</td></tr>"
            )

        target_html = (
            "<table width='100%' cellspacing='0' cellpadding='6'>"
            "<tr><th align='left'>Word</th>"
            "<th align='left'>Target phonemes</th></tr>"
            f"{rows}</table>"
            if rows else muted("Target data unavailable.")
        )
        lines.append(section("Target words & phonemes", target_html))

        # Recognized speech and word timestamps
        transcription = results.get("Transcription", {})
        transcript = transcription.get("transcript", "Not processed")
        segments = transcription.get("segments", [])

        timestamp_rows = ""
        for seg in segments:
            timestamp_rows += (
                f"<tr><td>{esc(seg.get('word', '?'))}</td>"
                f"<td>{seg.get('start', 0):.2f}s</td>"
                f"<td>{seg.get('end', 0):.2f}s</td></tr>"
            )

        transcript_html = (
            f"<p style='font-size:16px;'>"
            f"{esc(transcript)}</p>"
        )

        if timestamp_rows:
            transcript_html += (
                "<table width='100%' cellspacing='0' cellpadding='5'>"
                "<tr><th align='left'>Word</th>"
                "<th align='left'>Start</th>"
                "<th align='left'>End</th></tr>"
                f"{timestamp_rows}</table>"
            )

        lines.append(section("Recognized speech", transcript_html))

        # Actual phonemes
        actual = results.get("Actual Phonemes", {})
        actual_sequence = actual.get(
            "phoneme_sequence", "Not available"
        )
        actual_groups = actual.get(
            "phoneme_words", "Not available"
        )

        actual_html = (
            f"<p><b>Sequence</b><br>"
            f"<span style='color:#91c8ff;font-size:16px;'>"
            f"{esc(actual_sequence)}</span></p>"
            f"<p><b>Grouped by word</b><br>"
            f"{esc(actual_groups)}</p>"
        )
        lines.append(section("Recognized phonemes", actual_html))

        # SODA
        soda = results.get("SODA", {})
        soda_summary = soda.get("summary", {})

        if soda_summary:
            categories = [
                "Correct", "Substitution", "Omission",
                "Distortion", "Addition"
            ]
            soda_cells = "".join(
                f"<td style='padding:7px;text-align:center;'>"
                f"<div style='color:#9bb0c8;font-size:12px;'>"
                f"{category}</div>"
                f"<b style='font-size:21px;'>"
                f"{soda_summary.get(category, 0)}</b></td>"
                for category in categories
            )

            soda_html = (
                f"<table width='100%'><tr>{soda_cells}</tr></table>"
                "<p style='color:#9bb0c8;font-size:12px;'>"
                "Distortions cannot be reliably identified from "
                "phoneme strings alone.</p>"
            )

            word_rows = ""
            for item in soda.get("word_results", []):
                word_rows += (
                    f"<tr><td>{esc(item.get('word', '?'))}</td>"
                    f"<td>{esc(item.get('actual_phoneme_group', ''))}"
                    f"</td></tr>"
                )

            if word_rows:
                soda_html += (
                    "<table width='100%' cellpadding='5'>"
                    "<tr><th align='left'>Word</th>"
                    "<th align='left'>Actual group</th></tr>"
                    f"{word_rows}</table>"
                )
        else:
            soda_html = muted("SODA results unavailable.")

        lines.append(section("SODA analysis", soda_html))

        # Phonetic inventory
        inventory = results.get("Phonetic Inventory", {})
        summary = inventory.get("summary", {})

        if summary:
            inventory_html = ""
            for label, key in [
                ("Shared phonemes", "shared_phonemes"),
                ("Target not observed", "target_not_observed"),
                ("Observed outside target", "observed_not_in_target"),
            ]:
                phones = ", ".join(summary.get(key, [])) or "None"
                inventory_html += (
                    f"<p><b>{label}</b><br>{esc(phones)}</p>"
                )
        else:
            inventory_html = muted("Inventory unavailable.")

        lines.append(section("Phonetic inventory", inventory_html))

        # TTR and syllable shapes
        ttr_report = results.get("TTR / Syllable Shape", {})
        ttr = ttr_report.get("TEMPLIN_TTR", {})
        shapes = ttr_report.get("actual_syllable_shapes", {})

        if ttr:
            ttr_html = (
                f"<p><b>TTR:</b> "
                f"<span style='color:#91c8ff;font-size:20px;'>"
                f"{ttr.get('TTR', 0)}%</span></p>"
                f"<p>{ttr.get('types', 0)} unique word types / "
                f"{ttr.get('tokens', 0)} total tokens</p>"
            )
        else:
            ttr_html = muted("TTR unavailable.")

        if shapes:
            ttr_html += (
                f"<p><b>Total syllables:</b> "
                f"{shapes.get('total_syllables', 0)}</p>"
            )

            for shape, count in shapes.get("shape_counts", {}).items():
                percentage = shapes.get(
                    "shape_percentages", {}
                ).get(shape, 0)

                ttr_html += (
                    f"<p>{esc(shape)}: {count} "
                    f"({percentage}%)</p>"
                )

        lines.append(section("TTR & syllable shapes", ttr_html))

        lines.append(
            "<p style='color:#9bb0c8;font-size:12px;margin-top:18px;'>"
            "Automated phoneme recognition and alignment can be "
            "inaccurate. These results are not independently verified "
            "clinical measurements.</p></div>"
        )

        return "".join(lines)

    def process_selected(self):
        item = self.file_list.currentItem()
        if not item:
            return

        name = item.data(Qt.UserRole)
        results = self.get_session_data(name)

        if any(
            label in results
            for label in (
                "Transcription",
                "Actual Phonemes",
                "PCC / PVC",
                "SODA",
            )
        ):
            return

        target = results.get("Target Phonemes", {})
        expected_words = (
            target.get("target_input", {}).get("sentence")
        )

        answer = QMessageBox.question(
            self,
            "Process this file?",
            f"Process {name} using the analysis pipeline?",
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No,
        )

        if answer == QMessageBox.Yes:
            self.run_processing(name, expected_words)

    def run_processing(self, name, expected_words=None):
        self.process_bar.setVisible(True)
        self.process_bar.setRange(0, 0)
        self.detail_status.setText("Processing modules in sequence…")
        QApplication.setOverrideCursor(Qt.WaitCursor)

        try:
            process_recording(name, expected_words)
            QMessageBox.information(
                self, "Processing complete",
                f"Processing finished for {name}."
            )
        except Exception as exc:
            QMessageBox.critical(
                self, "Processing failed", str(exc)
            )
            self.detail_status.setText("Processing failed.")

        finally:
            QApplication.restoreOverrideCursor()
            self.process_bar.setVisible(False)
            self.refresh_files()

            for i in range(self.file_list.count()):
                item = self.file_list.item(i)
                if item.data(Qt.UserRole) == name:
                    self.file_list.setCurrentItem(item)
                    self.show_selected_record(item)
                    break

    def delete_selected(self):
        item = self.file_list.currentItem()
        if not item:
            return

        name = item.data(Qt.UserRole)

        answer = QMessageBox.question(
            self,
            "Delete session",
            f"Delete {name} and all its generated result files?",
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No,
        )

        if answer != QMessageBox.Yes:
            return

        try:
            import shutil

            # Delete the session folder containing its WAV, TXT, and target JSON.
            target_folder = RECORDINGS / name
            if target_folder.exists():
                shutil.rmtree(target_folder)

            # Delete matching result JSON files from every output directory.
            for folder in RESULT_FOLDERS.values():
                result_file = folder / f"{name}.json"
                if result_file.is_file():
                    result_file.unlink()

            self.refresh_files()

            QMessageBox.information(
                self, "Deleted",
                f"{name} and its generated result files were deleted."
            )

        except Exception as exc:
            QMessageBox.critical(
                self, "Delete failed", str(exc)
            )

if __name__ == "__main__":
    app = QApplication(sys.argv)
    app.setStyle("Fusion")
    app.setFont(QFont("Segoe UI", 10))
    app.setStyleSheet(STYLE)
    window = MainWindow()
    window.show()
    sys.exit(app.exec())
