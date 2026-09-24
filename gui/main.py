"""
Main GUI shell for the PTFS tracker, styled after vPilot's layout.

This is the frontend only for now — the "Connect" button currently just
toggles UI state and logs a placeholder message. Once the backend
(calibration + tracker loop) is wired in, connect_toggled() is where
that gets started/stopped.
"""

import sys
import os
from datetime import datetime

from PyQt6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QPushButton, QLabel, QListWidget, QListWidgetItem, QTabWidget,
    QTextEdit, QFrame, QSizePolicy,
)
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QFont

from updater import check_for_update, CURRENT_VERSION, apply_pending_update_and_maybe_restart

APP_TITLE = f"PTFS Tracker v{CURRENT_VERSION}"

# Static list of controller/positions shown in the left panel.
# Swap this later for a live "connected viewers" feed from the backend if
# you'd rather show who's watching than a fixed position list.
DEFAULT_POSITIONS = [
    "Center",
    "Approach/Departure",
    "Tower",
    "Ground",
    "Ramp",
    "Clearance Delivery",
    "ATIS",
    "Observers",
]


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle(APP_TITLE)
        self.resize(820, 420)
        self.connected = False

        self._build_ui()
        self._log(f"PTFS Tracker version {CURRENT_VERSION}")

        # Check for updates shortly after launch, non-blocking to the UI feel.
        self._check_updates_on_startup()

    # ---------- UI construction ----------

    def _build_ui(self):
        central = QWidget()
        self.setCentralWidget(central)
        root = QVBoxLayout(central)
        root.setContentsMargins(8, 8, 8, 8)
        root.setSpacing(8)

        root.addLayout(self._build_top_bar())
        root.addLayout(self._build_body(), stretch=1)

    def _build_top_bar(self):
        bar = QHBoxLayout()

        self.connect_btn = QPushButton("Connect")
        self.connect_btn.setObjectName("connectButton")
        self.connect_btn.setCheckable(True)
        self.connect_btn.clicked.connect(self.connect_toggled)
        bar.addWidget(self.connect_btn)

        self.disconnect_btn = QPushButton("X")
        self.disconnect_btn.setObjectName("disconnectButton")
        self.disconnect_btn.clicked.connect(self.force_disconnect)
        bar.addWidget(self.disconnect_btn)

        bar.addSpacing(16)

        self.status_label = QLabel("Not connected")
        self.status_label.setObjectName("statusLabel")
        self.status_label.setProperty("state", "idle")
        bar.addWidget(self.status_label)

        bar.addStretch(1)

        self.callsign_label = QLabel("Callsign: —")
        bar.addWidget(self.callsign_label)

        bar.addSpacing(16)

        freq_label = QLabel("STATUS:")
        bar.addWidget(freq_label)
        self.freq_value = QLabel("---.---")
        self.freq_value.setObjectName("freqLabel")
        bar.addWidget(self.freq_value)

        return bar

    def _build_body(self):
        body = QHBoxLayout()

        # Left panel: positions list
        left = QVBoxLayout()
        left_title = QLabel("Controllers In Range:")
        left.addWidget(left_title)

        self.positions_list = QListWidget()
        self.positions_list.setObjectName("positionsList")
        for name in DEFAULT_POSITIONS:
            item = QListWidgetItem(name)
            self.positions_list.addItem(item)
        left.addWidget(self.positions_list)

        left_container = QWidget()
        left_container.setLayout(left)
        left_container.setFixedWidth(220)
        body.addWidget(left_container)

        # Right panel: tabbed Messages / Notes
        self.tabs = QTabWidget()

        self.message_log = QTextEdit()
        self.message_log.setObjectName("messageLog")
        self.message_log.setReadOnly(True)
        self.tabs.addTab(self.message_log, "Messages")

        self.notes = QTextEdit()
        self.notes.setObjectName("messageLog")
        self.tabs.addTab(self.notes, "Notes")

        body.addWidget(self.tabs, stretch=1)

        return body

    # ---------- Behavior ----------

    def _log(self, text: str):
        timestamp = datetime.now().strftime("%H:%M:%S")
        self.message_log.append(f"[{timestamp}] {text}")

    def connect_toggled(self, checked: bool):
        self.connected = checked
        if checked:
            self.connect_btn.setText("Disconnect")
            self.connect_btn.setProperty("connected", "true")
            self.status_label.setText("Connected")
            self.status_label.setProperty("state", "connected")
            self._log("Connected. (Backend tracking not wired in yet.)")
            # TODO: start tracker.py's capture loop here once backend is ready
        else:
            self._do_disconnect()
        self._refresh_style()

    def force_disconnect(self):
        if self.connected:
            self.connect_btn.setChecked(False)
            self._do_disconnect()
            self._refresh_style()

    def _do_disconnect(self):
        self.connected = False
        self.connect_btn.setText("Connect")
        self.connect_btn.setProperty("connected", "false")
        self.status_label.setText("Not connected")
        self.status_label.setProperty("state", "idle")
        self._log("Disconnected.")
        # TODO: stop tracker.py's capture loop here once backend is ready

    def _refresh_style(self):
        # Force Qt to re-evaluate the [connected="true"] / [state=...] style rules
        for widget in (self.connect_btn, self.status_label):
            widget.style().unpolish(widget)
            widget.style().polish(widget)

    def _check_updates_on_startup(self):
        try:
            info = check_for_update()
        except Exception as e:
            self._log(f"Update check failed: {e}")
            return

        if info is None:
            self._log("You're on the latest version.")
            return

        self._log(f"Update available: v{info['version']} "
                   f"(you have v{CURRENT_VERSION}). Downloading...")
        try:
            from updater import apply_update
            apply_update(info)
            self._log("Update downloaded. Restart the app to apply it.")
        except Exception as e:
            self._log(f"Update download failed: {e}")


def main():
    # Must run before the GUI is built: if an update was downloaded on a
    # previous run, this swaps it in and relaunches, exiting this process.
    apply_pending_update_and_maybe_restart()

    app = QApplication(sys.argv)

    style_path = os.path.join(os.path.dirname(__file__), "style.qss")
    if os.path.exists(style_path):
        with open(style_path) as f:
            app.setStyleSheet(f.read())

    window = MainWindow()
    window.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
