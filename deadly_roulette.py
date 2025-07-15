#!/usr/bin/env python3
"""
Deadly Roulette – OFF‑LINE version
• Pas d’API, tout est stocké localement.
• Fichier JSON caché ~/.deadly_roulette/deaths.json (Linux/macOS)
  ou %APPDATA%\\DeadlyRoulette\\deaths.json (Windows).
"""

import sys
import random
import hashlib
import json
import os
import subprocess
from datetime import datetime, timezone
from pathlib import Path
import shutil
import stat

import requests  # uniquement pour l'appel GitHub (peut être retiré si tu passes à GITHUB_TOKEN)
from PySide6.QtWidgets import (
    QApplication, QDialog, QWidget, QVBoxLayout, QLabel,
    QPushButton, QCheckBox, QMessageBox
)
from PySide6.QtCore import Qt, QStandardPaths
from PySide6.QtMultimedia import QSoundEffect


# ---------- FICHIER DE PERSISTENCE ---------- #
def _storage_dir() -> Path:
    if os.name == "nt":  # Windows
        base = Path(os.getenv("APPDATA", Path.home() / "AppData" / "Roaming"))
        return base / "DeadlyRoulette"
    else:  # Linux, macOS
        return Path.home() / ".deadly_roulette"


def _deaths_file() -> Path:
    return _storage_dir() / "deaths.json"


def _ensure_storage():
    dir_ = _storage_dir()
    dir_.mkdir(parents=True, exist_ok=True)

    # Rendre caché sur Windows
    if os.name == "nt":
        try:
            subprocess.run(["attrib", "+h", str(dir_)], check=False, capture_output=True)
        except FileNotFoundError:
            pass

    # Permissions 700 sur Unix
    else:
        dir_.chmod(0o700)

    # Créer fichier vide si absent
    file = _deaths_file()
    if not file.exists():
        file.write_text("[]")
        if os.name != "nt":  # 600
            file.chmod(0o600)


def _load_deaths() -> list[dict]:
    _ensure_storage()
    with _deaths_file().open("r", encoding="utf-8") as f:
        return json.load(f)


def _save_deaths(data: list[dict]):
    with _deaths_file().open("w", encoding="utf-8") as f:
        json.dump(data, f, indent=2)


# ---------- utilitaires GitHub ---------- #
def get_github_login() -> str:
    """Essaye d'obtenir un login GitHub via gh CLI ou GITHUB_TOKEN."""
    token = os.getenv("GITHUB_TOKEN")
    if not token and shutil.which("gh"):
        try:
            token = subprocess.check_output(["gh", "auth", "token"], text=True).strip()
        except subprocess.CalledProcessError:
            pass

    if not token:
        raise RuntimeError(
            "No GitHub credentials found.\n"
            "Either run `gh auth login` or set the GITHUB_TOKEN env var."
        )

    resp = requests.get(
        "https://api.github.com/user",
        headers={"Authorization": f"token {token}", "User-Agent": "deadly-roulette"},
        timeout=10,
    )
    if resp.status_code != 200:
        raise RuntimeError("GitHub API call failed – invalid token?")
    return resp.json()["login"]


def sha256_hex(text: str) -> str:
    return hashlib.sha256(text.encode()).hexdigest()


# ---------- logique de mort locale ---------- #
def already_dead(hash_login: str) -> bool:
    deaths = _load_deaths()
    return any(d["hash"] == hash_login for d in deaths)


def report_death(login: str, hash_login: str, public: bool) -> None:
    deaths = _load_deaths()
    deaths.append(
        {
            "hash": hash_login,
            "login": login if public else None,
            "public": public,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }
    )
    _save_deaths(deaths)


# ---------- GUI ---------- #
class IntroDialog(QDialog):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Deadly Roulette – Rules")
        self.setWindowFlag(Qt.WindowType.WindowContextHelpButtonHint, False)

        rules = (
            "<h2>Welcome to Deadly Roulette</h2>"
            "<p>Spin the chamber. Six chances, one bullet.</p>"
            "<p>If the bullet fires, <b>you are dead.</b> Dead players can never play again.</p>"
            "<p>The game checks your GitHub login to enforce this rule.</p>"
            "<p>Do you agree to show your username publicly if you die?</p>"
        )
        lbl = QLabel(rules, wordWrap=True)

        self.opt_in = QCheckBox(
            "Yes, display my GitHub username in the public graveyard if I die."
        )
        self.play_btn = QPushButton("Play!")
        self.play_btn.clicked.connect(self.accept)

        lay = QVBoxLayout(self)
        lay.addWidget(lbl)
        lay.addWidget(self.opt_in)
        lay.addWidget(self.play_btn)

    @property
    def consent_public(self) -> bool:
        return self.opt_in.isChecked()


class GameWindow(QWidget):
    def __init__(self, login: str, hash_login: str, public: bool):
        super().__init__()
        self.login = login
        self.hash_login = hash_login
        self.public = public

        self.setWindowTitle("Deadly Roulette – Spin")
        self.setFixedSize(420, 240)

        self.status = QLabel("Press the trigger when ready…", alignment=Qt.AlignCenter)
        self.trigger = QPushButton("Pull the trigger")
        self.trigger.clicked.connect(self.pull_trigger)

        lay = QVBoxLayout(self)
        lay.addWidget(self.status)
        lay.addWidget(self.trigger)

        self.sfx_click = QSoundEffect()
        self.sfx_bang = QSoundEffect()
        # self.sfx_click.setSource(QUrl.fromLocalFile("assets/click.wav"))
        # self.sfx_bang.setSource(QUrl.fromLocalFile("assets/bang.wav"))

    def pull_trigger(self):
        if random.randint(1, 6) == 1:
            self.sfx_bang.play()
            self.status.setText("💥 BANG! You are dead.")
            report_death(self.login, self.hash_login, self.public)
            self.trigger.setEnabled(False)
        else:
            self.sfx_click.play()
            self.status.setText("Click… you survived! Care to try again?")


# ---------- main ---------- #
def main():
    app = QApplication(sys.argv)

    try:
        login = get_github_login()
    except RuntimeError as e:
        QMessageBox.critical(None, "GitHub Auth", str(e))
        sys.exit(1)

    h = sha256_hex(login)
    if already_dead(h):
        QMessageBox.critical(
            None, "R.I.P.", f"Sorry {login}, you already died earlier. No second chances."
        )
        sys.exit(0)

    intro = IntroDialog()
    if intro.exec() != QDialog.DialogCode.Accepted:
        sys.exit(0)

    win = GameWindow(login, h, intro.consent_public)
    win.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
