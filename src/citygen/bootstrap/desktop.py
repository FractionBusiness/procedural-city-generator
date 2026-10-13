"""PySide6 desktop shell — thin wrapper around CityPipeline with a live preview pane."""
from __future__ import annotations

import sys
from pathlib import Path

from loguru import logger
from PySide6.QtCore import QThread, Signal
from PySide6.QtWidgets import (
    QApplication, QMainWindow, QPushButton, QVBoxLayout, QWidget, QLabel, QFileDialog,
)

from citygen.core.pipeline import CityPipeline
from citygen.core.types import CitySpec
from citygen.services.config_loader import load_profile


class _GenWorker(QThread):
    finished_ok = Signal(str)
    failed = Signal(str)

    def __init__(self, spec: CitySpec) -> None:
        super().__init__()
        self._spec = spec

    def run(self) -> None:  # noqa: D401
        try:
            result = CityPipeline(self._spec).run()
            self.finished_ok.emit(str(result.output_dir))
        except Exception as exc:  # noqa: BLE001 — surface to UI
            logger.exception("generation failed")
            self.failed.emit(str(exc))


class MainWindow(QMainWindow):
    def __init__(self) -> None:
        super().__init__()
        self.setWindowTitle("procedural-city-generator 0.9.3")
        self.resize(960, 640)
        self._worker: _GenWorker | None = None

        root = QWidget()
        layout = QVBoxLayout(root)
        self.status = QLabel("ready — load a profile and hit generate")
        self.btn_load = QPushButton("load profile…")
        self.btn_go = QPushButton("generate")

        self.btn_load.clicked.connect(self._pick_profile)
        self.btn_go.clicked.connect(self._generate)

        for w in (self.status, self.btn_load, self.btn_go):
            layout.addWidget(w)
        self.setCentralWidget(root)
        self._profile_path = Path("config/default.yaml")

    def _pick_profile(self) -> None:
        path, _ = QFileDialog.getOpenFileName(self, "profile", "config", "YAML (*.yaml *.yml)")
        if path:
            self._profile_path = Path(path)
            self.status.setText(f"profile: {path}")

    def _generate(self) -> None:
        profile = load_profile(self._profile_path)
        spec = CitySpec.from_profile(profile)
        self.status.setText("generating…")
        self._worker = _GenWorker(spec)
        self._worker.finished_ok.connect(lambda d: self.status.setText(f"done → {d}"))
        self._worker.failed.connect(lambda e: self.status.setText(f"failed: {e}"))
        self._worker.start()


def run() -> int:
    app = QApplication(sys.argv)
    win = MainWindow()
    win.show()
    return app.exec()


if __name__ == "__main__":
    sys.exit(run())