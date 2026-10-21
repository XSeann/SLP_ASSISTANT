import sys
import json
from collections import Counter
from pathlib import Path
from PySide6.QtCore import Qt, QUrl, QTimer
from PySide6.QtGui import QFont
from PySide6.QtMultimedia import QMediaPlayer, QAudioOutput
from PySide6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, QLabel,
    QPushButton, QLineEdit, QTextEdit, QListWidget, QListWidgetItem, QStackedWidget,
    QMessageBox, QDialog, QDialogButtonBox, QProgressBar, QFrame, QSplitter,
    QTabWidget, QFormLayout, QSizePolicy, QSlider
)
from modules.recorder import AudioRecorder
from html import escape

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
        outer.setContentsMargins(22, 12, 22, 16)
        outer.setSpacing(0)

        self.record_stage_stack = QStackedWidget()
        outer.addWidget(self.record_stage_stack)

        # =====================================================
        # SCREEN 1: RECORDING DETAILS
        # =====================================================
        self.details_stage = QWidget()
        details_layout = QVBoxLayout(self.details_stage)
        details_layout.setContentsMargins(8, 4, 8, 8)
        details_layout.setSpacing(12)

        # Header
        top = QHBoxLayout()
        back_home = QPushButton("← Back to Home")
        back_home.clicked.connect(self.go_home)

        details_title = QLabel("01  RECORDING DETAILS")
        details_title.setObjectName("heading")
        details_title.setAlignment(Qt.AlignCenter)

        top.addWidget(back_home)
        top.addStretch()
        top.addWidget(details_title)
        top.addStretch()
        details_layout.addLayout(top)

        intro = QLabel(
            "Prepare the assessment details before starting the recording."
        )
        intro.setObjectName("muted")
        intro.setAlignment(Qt.AlignCenter)
        intro.setWordWrap(True)
        details_layout.addWidget(intro)

        # Center the form and button in the available space
        details_layout.addStretch(1)

        form = QFrame()
        form.setObjectName("panel")
        form.setMaximumWidth(1050)

        form_layout = QVBoxLayout(form)
        form_layout.setContentsMargins(26, 22, 26, 22)
        form_layout.setSpacing(8)

        # Recording name label and input
        name_label = QLabel("Recording name")
        name_label.setStyleSheet("font-weight: 700;")
        name_label.setWordWrap(True)
        form_layout.addWidget(name_label)

        self.name_input = QLineEdit("session_1")
        self.name_input.setMinimumHeight(44)
        self.name_input.setPlaceholderText("e.g. session_1")
        form_layout.addWidget(self.name_input)

        # Expected sentence label and input
        sentence_label = QLabel("Expected sentence")
        sentence_label.setStyleSheet("font-weight: 700;")
        sentence_label.setWordWrap(True)
        form_layout.addWidget(sentence_label)

        self.words_input = QLineEdit()
        self.words_input.setMinimumHeight(44)
        self.words_input.setPlaceholderText(
            "Enter the sentence the client should say"
        )
        form_layout.addWidget(self.words_input)

        self.form_note = QLabel(
            "Both fields are required. Target phonemes will be generated "
            "before recording begins."
        )
        self.form_note.setObjectName("muted")
        self.form_note.setWordWrap(True)
        self.form_note.setSizePolicy(
            QSizePolicy.Policy.Expanding,
            QSizePolicy.Policy.Preferred
        )
        form_layout.addSpacing(4)
        form_layout.addWidget(self.form_note)

        # Keep the card from stretching too wide on large windows
        form_row = QHBoxLayout()
        form_row.addStretch(1)
        form_row.addWidget(form, 8)
        form_row.addStretch(1)
        details_layout.addLayout(form_row)

        continue_btn = QPushButton("Continue to Recording  →")
        continue_btn.setObjectName("primary")
        continue_btn.setMinimumHeight(52)
        continue_btn.setMaximumWidth(1050)
        continue_btn.clicked.connect(self.continue_to_recording)

        button_row = QHBoxLayout()
        button_row.addStretch(1)
        button_row.addWidget(continue_btn, 8)
        button_row.addStretch(1)
        details_layout.addLayout(button_row)

        details_layout.addStretch(1)
        self.record_stage_stack.addWidget(self.details_stage)

        # =====================================================
        # SCREEN 2: RECORDING WORKSTATION
        # =====================================================
        self.recording_stage = QWidget()
        recording_layout = QVBoxLayout(self.recording_stage)
        recording_layout.setContentsMargins(8, 2, 8, 8)
        recording_layout.setSpacing(8)

        # Header
        recording_top = QHBoxLayout()

        self.edit_details_btn = QPushButton("← Edit Details")
        self.edit_details_btn.clicked.connect(
            lambda: self.record_stage_stack.setCurrentWidget(
                self.details_stage
            )
        )

        recording_title = QLabel("Recording")
        recording_title.setObjectName("heading")
        recording_title.setAlignment(Qt.AlignCenter)

        recording_top.addWidget(self.edit_details_btn)
        recording_top.addStretch()
        recording_top.addWidget(recording_title)
        recording_top.addStretch()
        recording_layout.addLayout(recording_top)

        # Expected sentence
        sentence_panel = QFrame()
        sentence_panel.setObjectName("panel")
        sentence_layout = QVBoxLayout(sentence_panel)
        sentence_layout.setContentsMargins(18, 10, 18, 10)
        sentence_layout.setSpacing(5)

        sentence_hint = QLabel("SAY THE FOLLOWING SENTENCE")
        sentence_hint.setAlignment(Qt.AlignCenter)
        sentence_hint.setStyleSheet(
            "color: #38a4ff; font-size: 12px; font-weight: 700;"
        )

        self.expected_sentence_label = QLabel(
            "Your expected sentence will appear here."
        )
        self.expected_sentence_label.setWordWrap(True)
        self.expected_sentence_label.setAlignment(Qt.AlignCenter)
        self.expected_sentence_label.setStyleSheet(
            "font-size: 22px; font-weight: 700; color: #e8f0fb;"
        )

        sentence_layout.addWidget(sentence_hint)
        sentence_layout.addWidget(self.expected_sentence_label)
        recording_layout.addWidget(sentence_panel)

        # Audio monitor heading
        audio_heading = QLabel("02  AUDIO MONITOR")
        audio_heading.setStyleSheet(
            "font-size: 15px; font-weight: 700; color: #9bb0c8;"
        )
        recording_layout.addWidget(audio_heading)

        # Audio monitor gets the extra vertical space
        meter = QFrame()
        meter.setObjectName("panel")
        meter.setMinimumHeight(125)
        meter.setSizePolicy(
            QSizePolicy.Policy.Expanding,
            QSizePolicy.Policy.Expanding
        )

        meter_layout = QVBoxLayout(meter)
        meter_layout.setContentsMargins(14, 8, 14, 8)
        meter_layout.setSpacing(4)

        self.wave_label = QLabel("▁ ▂ ▃ ▅ ▇ ▅ ▃ ▂ ▁")
        self.wave_label.setAlignment(Qt.AlignCenter)
        self.wave_label.setMinimumHeight(48)
        self.wave_label.setStyleSheet(
            "font-size: 32px; color: #27b6d8; font-weight: 700;"
        )

        self.clock_label = QLabel("● 00:00")
        self.clock_label.setAlignment(Qt.AlignCenter)
        self.clock_label.setMinimumHeight(38)
        self.clock_label.setStyleSheet(
            "font-size: 23px; font-weight: 700;"
        )

        meter_layout.addStretch(1)
        meter_layout.addWidget(self.wave_label)
        meter_layout.addWidget(self.clock_label)
        meter_layout.addStretch(1)

        recording_layout.addWidget(meter, 1)

        # Recording controls
        controls_heading = QLabel("03  RECORDING CONTROLS")
        controls_heading.setStyleSheet(
            "font-size: 15px; font-weight: 700; color: #9bb0c8;"
        )
        recording_layout.addWidget(controls_heading)

        controls = QHBoxLayout()
        controls.setSpacing(12)

        self.start_btn = QPushButton("●  Start Recording")
        self.start_btn.setObjectName("primary")
        self.start_btn.setMinimumSize(170, 46)

        self.pause_btn = QPushButton("Ⅱ  Pause")
        self.pause_btn.setEnabled(False)
        self.pause_btn.setMinimumSize(115, 46)

        self.stop_btn = QPushButton("■  Stop")
        self.stop_btn.setObjectName("danger")
        self.stop_btn.setEnabled(False)
        self.stop_btn.setMinimumSize(100, 46)

        self.start_btn.clicked.connect(self.start_recording)
        self.pause_btn.clicked.connect(self.toggle_pause)
        self.stop_btn.clicked.connect(self.confirm_stop)

        controls.addStretch()
        controls.addWidget(self.start_btn)
        controls.addWidget(self.pause_btn)
        controls.addWidget(self.stop_btn)
        controls.addStretch()
        recording_layout.addLayout(controls)

        # Live status and recording feedback
        self.live_status = QLabel("●  READY TO RECORD")
        self.live_status.setAlignment(Qt.AlignCenter)
        self.live_status.setStyleSheet(
            "color: #9bb0c8; font-weight: 700;"
        )
        recording_layout.addWidget(self.live_status)

        self.record_status = QLabel(
            "Enter the recording details before you begin."
        )
        self.record_status.setObjectName("muted")
        self.record_status.setAlignment(Qt.AlignCenter)
        self.record_status.setWordWrap(True)
        recording_layout.addWidget(self.record_status)

        self.record_stage_stack.addWidget(self.recording_stage)
        self.record_stage_stack.setCurrentWidget(self.details_stage)

        return page

    def continue_to_recording(self):
        name = self.name_input.text().strip()
        words = self.words_input.text().strip()

        if not name or not words:
            QMessageBox.warning(
                self,
                "Missing information",
                "Please enter both the recording name and expected sentence "
                "before continuing."
            )
            return

        safe_name = "".join(
            c for c in name if c.isalnum() or c in "-_ "
        ).strip().replace(" ", "_")

        if not safe_name:
            QMessageBox.warning(
                self,
                "Invalid recording name",
                "Please use a name containing letters, numbers, hyphens, "
                "or underscores."
            )
            return

        self.name_input.setText(safe_name)
        self.expected_words = words

        self.expected_sentence_label.setText(words)
        self.record_status.setText(
            f"Ready to record: {safe_name}"
        )

        self.record_stage_stack.setCurrentWidget(self.recording_stage)

    def make_files_page(self):
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setContentsMargins(16, 12, 16, 16)
        layout.setSpacing(10)

        # ---------------- HEADER ----------------
        top = QHBoxLayout()

        back = QPushButton("← Home")
        back.clicked.connect(self.go_home)

        title_box = QVBoxLayout()
        title_box.setSpacing(2)

        title = QLabel("Saved Recordings")
        title.setObjectName("heading")

        subtitle = QLabel("Audio playback and speech analysis results")
        subtitle.setObjectName("muted")

        title_box.addWidget(title)
        title_box.addWidget(subtitle)

        refresh_btn = QPushButton("↻ Refresh")
        refresh_btn.clicked.connect(self.refresh_files)

        top.addWidget(back)
        top.addLayout(title_box, 1)
        top.addWidget(refresh_btn)
        layout.addLayout(top)

        # ---------------- MAIN SPLITTER ----------------
        splitter = QSplitter(Qt.Horizontal)
        splitter.setChildrenCollapsible(False)
        splitter.setHandleWidth(6)

        # LEFT: SESSION LIST
        left = QFrame()
        left.setObjectName("panel")
        left.setMinimumWidth(190)
        left.setMaximumWidth(380)

        left_layout = QVBoxLayout(left)
        left_layout.setContentsMargins(12, 12, 12, 12)
        left_layout.setSpacing(8)

        session_heading = QLabel("RECORDINGS")
        session_heading.setStyleSheet(
            "font-size: 15px; font-weight: 700; color: #9bb0c8;"
        )

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

        # RIGHT: DETAILS AND RESULTS
        right = QWidget()
        right_layout = QVBoxLayout(right)
        right_layout.setContentsMargins(0, 0, 0, 0)
        right_layout.setSpacing(8)

        detail_header = QHBoxLayout()

        title_column = QVBoxLayout()
        title_column.setSpacing(2)

        self.detail_title = QLabel("Select a recording")
        self.detail_title.setObjectName("heading")
        self.detail_title.setWordWrap(True)

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
        self.process_bar.setMaximumWidth(150)
        self.process_bar.setVisible(False)
        detail_header.addWidget(self.process_bar)

        right_layout.addLayout(detail_header)

        # ---------------- AUDIO PLAYER ----------------
        audio_panel = QFrame()
        audio_panel.setObjectName("panel")

        audio_layout = QVBoxLayout(audio_panel)
        audio_layout.setContentsMargins(12, 10, 12, 10)
        audio_layout.setSpacing(6)

        audio_heading = QLabel("AUDIO PLAYBACK")
        audio_heading.setStyleSheet(
            "font-weight: 700; color: #9bb0c8;"
        )
        audio_layout.addWidget(audio_heading)

        player_controls = QHBoxLayout()
        player_controls.setSpacing(8)

        self.audio_play_btn = QPushButton("▶ Play")
        self.audio_play_btn.setObjectName("primary")
        self.audio_play_btn.setMinimumWidth(90)
        self.audio_play_btn.clicked.connect(self.toggle_audio)

        self.audio_time_label = QLabel("00:00 / 00:00")
        self.audio_time_label.setMinimumWidth(100)
        self.audio_time_label.setAlignment(Qt.AlignCenter)

        self.audio_slider = QSlider(Qt.Horizontal)
        self.audio_slider.setRange(0, 0)
        self.audio_slider.setSingleStep(100)
        self.audio_slider.sliderMoved.connect(self.seek_audio)

        player_controls.addWidget(self.audio_play_btn)
        player_controls.addWidget(self.audio_slider, 1)
        player_controls.addWidget(self.audio_time_label)

        audio_layout.addLayout(player_controls)
        right_layout.addWidget(audio_panel)

        # Create the player once, not every time a session is selected.
        self.audio_output = QAudioOutput(self)
        self.audio_player = QMediaPlayer(self)
        self.audio_player.setAudioOutput(self.audio_output)

        self.audio_player.positionChanged.connect(
            self.update_audio_position
        )
        self.audio_player.durationChanged.connect(
            self.update_audio_duration
        )
        self.audio_player.playbackStateChanged.connect(
            self.update_audio_button
        )
        self.audio_player.errorOccurred.connect(
            self.handle_audio_error
        )

        # ---------------- RESULT TABS ----------------
        self.result_tabs = QTabWidget()

        self.result_text = QTextEdit()
        self.result_text.setReadOnly(True)
        self.result_text.setAcceptRichText(True)
        self.result_tabs.addTab(self.result_text, "Overview")

        self.analysis_text = QTextEdit()
        self.analysis_text.setReadOnly(True)
        self.analysis_text.setAcceptRichText(True)
        self.result_tabs.addTab(self.analysis_text, "Analysis Details")

        self.json_text = QTextEdit()
        self.json_text.setReadOnly(True)
        self.json_text.setAcceptRichText(False)
        self.json_text.setLineWrapMode(QTextEdit.NoWrap)
        self.result_tabs.addTab(self.json_text, "Raw JSON")

        right_layout.addWidget(self.result_tabs, 1)

        # ---------------- BOTTOM ACTIONS ----------------
        actions = QHBoxLayout()

        self.process_selected_btn = QPushButton(
            "▶ Process Recording"
        )
        self.process_selected_btn.setObjectName("primary")
        self.process_selected_btn.clicked.connect(
            self.process_selected
        )

        self.delete_btn = QPushButton("🗑 Delete")
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
        splitter.setSizes([250, 900])

        layout.addWidget(splitter, 1)

        # Initial player state
        self.audio_play_btn.setEnabled(False)
        self.audio_slider.setEnabled(False)

        return page

    def format_audio_time(self, milliseconds):
        seconds = max(0, int(milliseconds // 1000))
        return f"{seconds // 60:02d}:{seconds % 60:02d}"


    def toggle_audio(self):
        if self.audio_player.playbackState() == QMediaPlayer.PlayingState:
            self.audio_player.pause()
        else:
            self.audio_player.play()


    def seek_audio(self, position):
        self.audio_player.setPosition(position)


    def update_audio_position(self, position):
        if not self.audio_slider.isSliderDown():
            self.audio_slider.setValue(position)

        duration = self.audio_player.duration()
        self.audio_time_label.setText(
            f"{self.format_audio_time(position)} / "
            f"{self.format_audio_time(duration)}"
        )


    def update_audio_duration(self, duration):
        self.audio_slider.setRange(0, max(0, duration))
        self.audio_time_label.setText(
            f"{self.format_audio_time(self.audio_player.position())} / "
            f"{self.format_audio_time(duration)}"
        )


    def update_audio_button(self, state):
        if state == QMediaPlayer.PlayingState:
            self.audio_play_btn.setText("Ⅱ Pause")
        else:
            self.audio_play_btn.setText("▶ Play")


    def handle_audio_error(self, error, error_string):
        if error != QMediaPlayer.NoError:
            self.audio_time_label.setText("Audio unavailable")
            self.detail_status.setText(
                f"Could not play audio: {error_string}"
            )

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
        self.edit_details_btn.setEnabled(False)
        self.live_status.setText("●  RECORDING IN PROGRESS")
        self.live_status.setStyleSheet(
            "color: #35d07f; font-weight: 700;"
        )
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
        self.edit_details_btn.setEnabled(True)
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
        if not hasattr(self, "file_list"):
            return

        target_root = ROOT / "target_phonemes"
        target_root.mkdir(parents=True, exist_ok=True)

        current = self.file_list.currentItem()
        current_name = current.data(Qt.UserRole) if current else None

        sessions = sorted(
            [
                folder for folder in target_root.iterdir()
                if folder.is_dir()
                and (folder / f"{folder.name}.json").exists()
            ],
            key=lambda folder: folder.stat().st_mtime,
            reverse=True
        )

        self.file_list.blockSignals(True)
        self.file_list.clear()

        for folder in sessions:
            name = folder.name

            processed = all(
                (ROOT / result_folder / f"{name}.json").exists()
                for result_folder in (
                    "transcription",
                    "phoneme_word",
                    "phonetic_inventory",
                    "pcc_pvc",
                    "tttr_syllable_shape",
                    "soda",
                )
            )

            item = QListWidgetItem(
                f"{name}\n{'● Processed' if processed else '○ Incomplete'}"
            )
            item.setData(Qt.UserRole, name)
            item.setData(Qt.UserRole + 1, processed)
            self.file_list.addItem(item)

            if name == current_name:
                self.file_list.setCurrentItem(item)

        self.file_list.blockSignals(False)

        if self.file_list.currentItem():
            self.show_selected_record(self.file_list.currentItem())
            
        self.session_count.setText(f"Sessions: {len(sessions)}")

        if self.file_list.count() and self.file_list.currentRow() < 0:
            self.file_list.setCurrentRow(0)
        elif not self.file_list.count():
            self.audio_player.stop()
            self.audio_player.setSource(QUrl())
            self.detail_title.setText("No recordings yet")
            self.detail_status.setText(
                "Record a session to view its audio and analysis results."
            )
            self.result_text.clear()
            self.analysis_text.clear()
            self.json_text.clear()
            self.audio_play_btn.setEnabled(False)
            self.audio_slider.setEnabled(False)
            self.audio_time_label.setText("00:00 / 00:00")

    def show_selected_record(self, current, previous=None):
        if not current:
            return

        name = current.data(Qt.UserRole)
        processed = bool(current.data(Qt.UserRole + 1))

        self.detail_title.setText(name)
        self.detail_status.setText(
            "All analysis files found." if processed
            else "Some results are missing or this session has not been processed."
        )

        self.process_selected_btn.setEnabled(not processed)

        # Load the session's saved audio
        audio_path = ROOT / "target_phonemes" / name / f"{name}.wav"

        self.audio_player.stop()
        self.audio_player.setSource(QUrl())

        self.audio_slider.setRange(0, 0)
        self.audio_time_label.setText("00:00 / 00:00")

        if audio_path.exists():
            self.audio_player.setSource(QUrl.fromLocalFile(str(audio_path.resolve())))
            self.audio_play_btn.setEnabled(True)
            self.audio_slider.setEnabled(True)
        else:
            self.audio_play_btn.setEnabled(False)
            self.audio_slider.setEnabled(False)
            self.audio_time_label.setText("Audio not found")

        # Collect available JSON files
        folders = (
            "target_phonemes",
            "transcription",
            "phoneme_word",
            "phonetic_inventory",
            "pcc_pvc",
            "tttr_syllable_shape",
            "soda",
        )

        data = {}
        missing = []

        for folder in folders:
            if folder == "target_phonemes":
                path = ROOT / folder / name / f"{name}.json"
            else:
                path = ROOT / folder / f"{name}.json"

            if path.exists():
                try:
                    data[folder] = json.loads(
                        path.read_text(encoding="utf-8")
                    )
                except (OSError, json.JSONDecodeError) as exc:
                    data[folder] = {
                        "_read_error": str(exc)
                    }
            else:
                missing.append(folder)

        self.result_text.setHtml(self.format_session_overview(name, data))
        self.analysis_text.setHtml(self.format_analysis_details(data))
        self.json_text.setPlainText(
            json.dumps(data, indent=2, ensure_ascii=False)
        )

        if missing:
            self.detail_status.setText(
                f"{'Processed' if processed else 'Incomplete'} · "
                f"Missing results: {', '.join(missing)}"
            )

    def format_session_overview(self, name, data):
        target = data.get("target_phonemes", {})
        transcription = data.get("transcription", {})
        actual = data.get("phoneme_word", {})
        inventory = data.get("phonetic_inventory", {})
        scores = data.get("pcc_pvc", {})
        tttr = data.get("tttr_syllable_shape", {})
        soda = data.get("soda", {})

        target_input = target.get("target_input", {})
        sentence = target_input.get("sentence", "")
        transcript = transcription.get("transcript", "")
        # Get expected phonemes grouped by target word.
        target_words = target.get("words", [])

        expected_phonemes = " | ".join(
            f"{word.get('word', '')}: {' '.join(word.get('phonemes', []))}"
            for word in target_words
        ) or "Unavailable"
        summary = inventory.get("summary", {})
        ttr = tttr.get("TEMPLIN_TTR", {})

        def row(label, value):
            return (
                f"<tr><td><b>{escape(str(label))}</b></td>"
                f"<td>{escape(str(value))}</td></tr>"
            )

        html = [
            "<html><body style='font-family:Segoe UI; color:#e8f0fb;'>",
            f"<h2>{escape(name)}</h2>",
            "<h3>Recording Details</h3>",
            "<table width='100%' cellspacing='8'>",
            row("Expected sentence", sentence or "Unavailable"),
            row("Expected phonemes", expected_phonemes or "Unavailable"),
            row("Recognized transcript", transcript or "Unavailable"),
            row("Actual phoneme sequence",
                actual.get("phoneme_sequence", "Unavailable")),
            row("Grouped actual phonemes",
                actual.get("phoneme_words", "Unavailable")),
            "</table>",
            "<h3>Speech Analysis at a Glance</h3>",
            "<table width='100%' cellspacing='8'>",
            row("PCC", f"{scores.get('PCC', {}).get('percentage', '—')}%"),
            row("PVC", f"{scores.get('PVC', {}).get('percentage', '—')}%"),
            row("Target phoneme tokens",
                summary.get("target_phoneme_tokens", "—")),
            row("Actual phoneme tokens",
                summary.get("actual_phoneme_tokens", "—")),
            row("Unique words (TTR types)", ttr.get("types", "—")),
            row("Total words analyzed (TTR tokens)", ttr.get("tokens", "—")),
            row("TTR", f"{ttr.get('TTR', '—')}%"),
            row("SODA correct", soda.get("summary", {}).get("Correct", "—")),
            row("SODA omissions", soda.get("summary", {}).get("Omission", "—")),
            row("SODA substitutions",
                soda.get("summary", {}).get("Substitution", "—")),
            "</table>",
            "<p style='color:#9bb0c8;'>"
            "Automated phoneme recognition and scores may be inaccurate. "
            "Review the audio and detailed results before clinical interpretation."
            "</p>",
            "</body></html>",
        ]

        return "".join(html)

    def format_analysis_details(self, data):
        parts = [
            "<html><body style='font-family:Segoe UI; color:#e8f0fb;'>",
            "<h2>Speech Analysis Details</h2>",
        ]

        def heading(title):
            parts.append(
                f"<h3 style='color:#38a4ff; margin-top:20px;'>"
                f"{escape(title)}</h3>"
            )

        def table(headers, rows):
            parts.append(
                "<table width='100%' cellspacing='0' cellpadding='6' "
                "style='border-collapse:collapse;'>"
            )
            parts.append("<tr>")
            for header in headers:
                parts.append(
                    "<th align='left' style='background:#203b5b;'>"
                    f"{escape(str(header))}</th>"
                )
            parts.append("</tr>")

            for values in rows:
                parts.append("<tr>")
                for value in values:
                    if value is None or value == "":
                        value = "—"
                    parts.append(
                        "<td style='border-bottom:1px solid #29435f;'>"
                        f"{escape(str(value))}</td>"
                    )
                parts.append("</tr>")
            parts.append("</table>")

        # 1. PCC and PVC
        pcc_data = data.get("pcc_pvc", {})
        heading("1. PCC — Percentage of Consonants Correct")
        pcc = pcc_data.get("PCC", {})
        table(
            ["Correct", "Total", "Percentage"],
            [[pcc.get("correct", "—"), pcc.get("total", "—"),
            f"{pcc.get('percentage', '—')}%"]]
        )

        heading("2. PVC — Percentage of Vowels Correct")
        pvc = pcc_data.get("PVC", {})
        table(
            ["Correct", "Total", "Percentage"],
            [[pvc.get("correct", "—"), pvc.get("total", "—"),
            f"{pvc.get('percentage', '—')}%"]]
        )

        # 2. TTR and word frequency
        tttr_data = data.get("tttr_syllable_shape", {})
        ttr = tttr_data.get("TEMPLIN_TTR", {})

        heading("3. TEMPLIN Type-Token Ratio (TTR)")
        table(
            ["Types (unique words)", "Tokens (word occurrences)", "TTR"],
            [[ttr.get("types", "—"), ttr.get("tokens", "—"),
            f"{ttr.get('TTR', '—')}%"]]
        )

        # Count repeated words from the Whisper transcript segments.
        segments = data.get("transcription", {}).get("segments", [])
        word_counts = Counter(
            str(segment.get("word", "")).strip(".,!?;:\"'()[]{}").lower()
            for segment in segments
            if str(segment.get("word", "")).strip(".,!?;:\"'()[]{}")
        )

        heading("Word Frequency")
        if word_counts:
            table(
                ["Word", "Times said"],
                sorted(word_counts.items(), key=lambda item: (-item[1], item[0]))
            )
        else:
            parts.append("<p>No word-level transcript is available.</p>")

        # 3. Syllable shapes
        syllable_data = tttr_data.get("actual_syllable_analysis", [])
        heading("4. Syllable Shape Analysis")
        syllable_rows = []

        for item in syllable_data:
            shapes = item.get("syllable_shapes", [])
            phonemes = item.get("phonemes", [])
            syllable_rows.append([
                item.get("word", "—"),
                item.get("phoneme_group", "—"),
                " ".join(phonemes) or "—",
                item.get("syllable_count", "—"),
                ", ".join(shapes) or "—",
            ])

        table(
            ["Word", "Actual group", "Phonemes", "Syllables", "Shape"],
            syllable_rows
        )

        shape_summary = tttr_data.get("actual_syllable_shapes", {})
        shape_counts = shape_summary.get("shape_counts", {})
        shape_percentages = shape_summary.get("shape_percentages", {})

        if shape_counts:
            heading("Syllable Shape Totals")
            table(
                ["Shape", "Count", "Percentage"],
                [
                    [shape, count, f"{shape_percentages.get(shape, 0)}%"]
                    for shape, count in shape_counts.items()
                ]
            )

        # 4. SODA, target vs actual side by side
        soda_data = data.get("soda", {})
        heading("5. SODA Analysis — Target vs Actual")

        soda_rows = []
        for item in soda_data.get("word_results", []):
            counts = item.get("counts", {})
            soda_rows.append([
                item.get("word", "—"),
                " ".join(item.get("target_phonemes", [])) or "—",
                " ".join(item.get("actual_phonemes", [])) or "—",
                counts.get("Correct", 0),
                counts.get("Substitution", 0),
                counts.get("Omission", 0),
                counts.get("Distortion", 0),
                counts.get("Addition", 0),
            ])

        table(
            ["Word", "Target phonemes", "Actual phonemes",
            "Correct", "Sub.", "Omit.", "Dist.", "Add."],
            soda_rows
        )

        soda_summary = soda_data.get("summary", {})
        heading("SODA Totals")
        table(
            ["Correct", "Substitution", "Omission", "Distortion", "Addition"],
            [[
                soda_summary.get("Correct", "—"),
                soda_summary.get("Substitution", "—"),
                soda_summary.get("Omission", "—"),
                soda_summary.get("Distortion", "—"),
                soda_summary.get("Addition", "—"),
            ]]
        )

        # 5. Phonetic inventory
        inventory_data = data.get("phonetic_inventory", {})
        inventory_summary = inventory_data.get("summary", {})

        heading("6. Phonetic Inventory Summary")
        table(
            ["Measure", "Count / symbols"],
            [
                ["Target phoneme tokens",
                inventory_summary.get("target_phoneme_tokens", "—")],
                ["Actual phoneme tokens",
                inventory_summary.get("actual_phoneme_tokens", "—")],
                ["Target unique phonemes",
                inventory_summary.get("target_unique_phonemes", "—")],
                ["Actual unique phonemes",
                inventory_summary.get("actual_unique_phonemes", "—")],
                ["Shared phonemes",
                ", ".join(inventory_summary.get("shared_phonemes", [])) or "—"],
                ["Target not observed",
                ", ".join(inventory_summary.get("target_not_observed", [])) or "—"],
                ["Observed not in target",
                ", ".join(inventory_summary.get("observed_not_in_target", [])) or "—"],
            ]
        )

        # Full inventory table
        inventory_rows = []
        for item in inventory_data.get("inventory", []):
            inventory_rows.append([
                item.get("phoneme", "—"),
                item.get("sound_type", "—"),
                item.get("target_count", 0),
                item.get("actual_count", 0),
                item.get("status", "—"),
            ])

        if inventory_rows:
            heading("Phoneme-by-Phoneme Inventory")
            table(
                ["Phoneme", "Type", "Target count", "Actual count", "Status"],
                inventory_rows
            )

        parts.append(
            "<p style='color:#9bb0c8; margin-top:20px;'>"
            "These are automated comparisons of phoneme symbols. They do not "
            "independently verify pronunciation or establish a clinical diagnosis. "
            "Syllable shapes are estimates, and distortions require audio review "
            "and phonetic judgment.</p>"
        )

        parts.append("</body></html>")
        return "".join(parts)

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
            QMessageBox.warning(
                self, "No Recording Selected",
                "Please select a recording first."
            )
            return

        name = item.data(Qt.UserRole)
        results = self.get_session_data(name)

        # Check whether the main analysis results already exist.
        required_results = (
            "PCC / PVC",
            "SODA",
            "TTTR / Syllable Shape",
            "Phonetic Inventory",
        )

        if all(label in results for label in required_results):
            QMessageBox.information(
                self, "Already Processed",
                f"{name} already has its analysis results."
            )
            return

        # Get the expected sentence from the target JSON.
        target = results.get("Target Phonemes", {})
        expected_words = (
            target.get("target_input", {}).get("sentence", "")
        )

        if not expected_words:
            QMessageBox.warning(
                self, "Target Sentence Missing",
                "The expected sentence could not be found. "
                "Check the target phoneme JSON before processing."
            )
            return

        answer = QMessageBox.question(
            self,
            "Process this recording?",
            f"Run the analysis pipeline for {name}?",
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
