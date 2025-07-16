#!/usr/bin/env python3

import sys
import random
import hashlib
import json
import os
import subprocess
import base64
import time
from datetime import datetime, timezone

import requests
from PySide6.QtWidgets import (
    QApplication, QDialog, QWidget, QVBoxLayout, QLabel,
    QPushButton, QCheckBox, QMessageBox
)
from PySide6.QtCore import Qt
from PySide6.QtMultimedia import QSoundEffect

REPO_OWNER   = "Diego-PB"
REPO_NAME    = "Deadly-Roulette"
FILE_PATH    = "deaths.json"

RAW_URL      = f"https://raw.githubusercontent.com/{REPO_OWNER}/{REPO_NAME}/main/{FILE_PATH}"
API_CONTENTS = f"https://api.github.com/repos/{REPO_OWNER}/{REPO_NAME}/contents/{FILE_PATH}"

class GitHubError(RuntimeError):
    pass


def get_github_token() -> str:
    """
    Récupère le token via gh CLI ou la variable d'environnement GITHUB_TOKEN.
    Doit inclure le scope public_repo pour pouvoir pousser dans le repo.
    """
    token = os.getenv("GITHUB_TOKEN")
    if not token:
        try:
            token = subprocess.check_output(["gh", "auth", "token"], text=True).strip()
        except (subprocess.CalledProcessError, FileNotFoundError):
            pass
    if not token:
        raise GitHubError(
            "No GitHub credentials found.\n"
            "1) run `gh auth login`, puis\n"
            "2) `gh auth refresh -h github.com -s public_repo` "
            "to grant the public_repo scope."
        )
    return token


def sha256_hex(text: str) -> str:
    return hashlib.sha256(text.encode()).hexdigest()

def fetch_remote_deaths(token: str) -> tuple[list[dict], str]:
    """
    Retourne (deaths, sha_actuel) via l'API.
    On passe le token -> pas de cache CDN.
    """
    headers = {"Authorization": f"token {token}", "User-Agent": "deadly-roulette"}
    meta = requests.get(API_CONTENTS, headers=headers, timeout=10).json()
    sha_current = meta["sha"]
    deaths = json.loads(base64.b64decode(meta["content"]))
    return deaths, sha_current


def get_file_meta(token: str) -> dict:
    """GET /contents – renvoie JSON avec 'sha' et 'content' (base64)."""
    headers = {"Authorization": f"token {token}", "User-Agent": "deadly-roulette"}
    resp = requests.get(API_CONTENTS, headers=headers, timeout=10)
    resp.raise_for_status()
    return resp.json()


def push_new_deaths(token: str, deaths: list[dict], sha: str):
    """PUT /contents pour committer la nouvelle liste."""
    message = f"Add death {int(time.time())}"
    encoded = base64.b64encode(json.dumps(deaths, indent=2).encode()).decode()
    payload = {"message": message, "content": encoded, "sha": sha}
    headers = {"Authorization": f"token {token}", "User-Agent": "deadly-roulette"}
    resp = requests.put(API_CONTENTS, json=payload, headers=headers, timeout=10)
    if resp.status_code not in (200, 201):
        raise GitHubError(f"Commit failed: {resp.status_code} – {resp.text}")


def already_dead_remote(token: str, hash_login: str) -> bool:
    try:
        deaths, _ = fetch_remote_deaths(token)
        return any(d["hash"] == hash_login for d in deaths)
    except Exception:
        return False


def report_death_remote(token: str, login: str,
                        hash_login: str, public: bool, shots: int):
    for attempt in range(3):
        meta = get_file_meta(token)
        sha_current = meta["sha"]
        deaths = json.loads(base64.b64decode(meta["content"]))

        deaths.append({
            "hash": hash_login,
            "login": login if public else None,
            "public": public,
            "shots": shots,                 
            "timestamp": datetime.now(timezone.utc).isoformat(),
        })

        try:
            push_new_deaths(token, deaths, sha_current)
            return
        except GitHubError as err:
            if "409" in str(err) and attempt < 2:
                # Conflit: quelqu'un a commité juste avant → on retry
                time.sleep(1)
                continue
            raise

class IntroDialog(QDialog):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Deadly Roulette – Rules")
        self.setWindowFlag(Qt.WindowType.WindowContextHelpButtonHint, False)

        rules_html = (
            "<h2>Welcome to Deadly Roulette</h2>"
            "<p>Spin the chamber. Six chances, one bullet.</p>"
            "<p>If the bullet fires, <b>you are dead.</b> Dead players can never play again.</p>"
            "<p>This game uploads your death to GitHub to enforce this rule.</p>"
            "<p>Do you agree to make your username public if you die?</p>"
        )
        lbl = QLabel(rules_html, wordWrap=True)

        self.opt_in = QCheckBox(
            "Yes, display my GitHub username in the public graveyard if I die."
        )
        self.play = QPushButton("Play!")
        self.play.clicked.connect(self.accept)

        lay = QVBoxLayout(self)
        lay.addWidget(lbl)
        lay.addWidget(self.opt_in)
        lay.addWidget(self.play)

    @property
    def consent_public(self) -> bool:
        return self.opt_in.isChecked()


class GameWindow(QWidget):
    def __init__(self, login: str, h: str, public: bool, token: str):
        super().__init__()
        self.login = login
        self.h = h
        self.public = public
        self.token = token

        self.setWindowTitle("Deadly Roulette – Spin")
        self.setFixedSize(420, 240)

        self.status = QLabel("Press the trigger when ready…", alignment=Qt.AlignCenter)
        self.trigger = QPushButton("Pull the trigger")
        self.trigger.clicked.connect(self.pull_trigger)

        self.shots = 0  #
        self.status = QLabel("Press the trigger (shots: 0)…", alignment=Qt.AlignCenter)

        self.committed = False

        lay = QVBoxLayout(self)
        lay.addWidget(self.status)
        lay.addWidget(self.trigger)

        self.sfx_click = QSoundEffect()
        self.sfx_bang = QSoundEffect()
        # self.sfx_click.setSource(QUrl.fromLocalFile("assets/click.wav"))
        # self.sfx_bang.setSource(QUrl.fromLocalFile("assets/bang.wav"))

    def pull_trigger(self):
        self.shots += 1
        if random.randint(1, 6) == 1:
            self.sfx_bang.play()
            self.status.setText(f"💥 BANG! You are dead after {self.shots} shots.")
            try:
                report_death_remote(
                    self.token, self.login, self.h, self.public, self.shots
                )
                self.committed = True
                QMessageBox.information(
                    self,
                    "Recorded",
                    "Your death has been recorded on GitHub.\nYou may now close the game.",
                )
            except GitHubError as err:
                QMessageBox.warning(
                    self,
                    "GitHub error",
                    f"Could not record your death automatically:\n{err}\n"
                    "The game will try again next launch.",
                )
            self.trigger.setEnabled(False)
        else:
            self.sfx_click.play()
            self.status.setText(f"Click… shots so far: {self.shots}")

def main():
    app = QApplication(sys.argv)

    # 1. Auth GitHub
    try:
        token = get_github_token()
    except GitHubError as e:
        QMessageBox.critical(None, "GitHub Auth Error", str(e))
        sys.exit(1)

    # 2. Récupérer le login
    headers = {"Authorization": f"token {token}", "User-Agent": "deadly-roulette"}
    login = requests.get("https://api.github.com/user", headers=headers, timeout=10).json()["login"]

    h = sha256_hex(login)
    if already_dead_remote(token, h):
        QMessageBox.critical(
            None, "R.I.P.", f"Sorry {login}, you already died earlier. No second chances."
        )
        sys.exit(0)

    # 3. Intro + consentement
    intro = IntroDialog()
    if intro.exec() != QDialog.DialogCode.Accepted:
        sys.exit(0)

    # 4. Lancer le jeu
    win = GameWindow(login, h, intro.consent_public, token)
    win.show()
    sys.exit(app.exec())

if __name__ == "__main__":
    main()