"""
Main GUI shell for the PTFS tracker, styled after vPilot's layout.
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
from PyQt6.QtGui import QFont, QIcon

from updater import check_for_update, CURRENT_VERSION, apply_pending_update_and_maybe_restart
from backend_worker import TrackerWorker

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
        self.worker = None

        # Try to show the configured callsign right away if backend config exists.
        try:
            from backend_worker import config as backend_config
            self.callsign_label.setText(f"Callsign: {backend_config.CALLSIGN}")
        except Exception:
            pass

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

        freq_label = QLabel("POSITION:")
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

            self.worker = TrackerWorker()
            self.worker.log.connect(self._log)
            self.worker.position.connect(self._on_position_update)
            self.worker.error.connect(self._on_worker_error)
            self.worker.start()
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

        if self.worker is not None:
            self.worker.stop()
            self.worker.wait(3000)  # wait up to 3s for the thread to exit cleanly
            self.worker = None

        self._log("Disconnected.")

    def _on_position_update(self, gx: float, gy: float):
        self.freq_value.setText(f"{gx:.0f}, {gy:.0f}")
        self._log(f"Position: ({gx:.1f}, {gy:.1f})")

    def _on_worker_error(self, message: str):
        self._log(f"ERROR: {message}")
        # Roll the UI back to disconnected state since the worker bailed out.
        self.connect_btn.setChecked(False)