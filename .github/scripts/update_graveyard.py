#!/usr/bin/env python3
"""
Met à jour le README :
• Affiche un tableau des joueurs morts qui ont `public == true`
• Affiche le nombre de morts anonymes
Le script doit être lancé depuis la racine du repo.
"""

from pathlib import Path
import json
from datetime import datetime

DEATHS_FILE = Path("deaths.json")
README_FILE = Path("README.md")
START_TAG   = "<!--GRAVEYARD_START-->"
END_TAG     = "<!--GRAVEYARD_END-->"

def load_deaths():
    data = json.loads(DEATHS_FILE.read_text(encoding="utf-8"))
    public = [d for d in data if d["public"]]
    anon   = sum(1 for d in data if not d["public"])
    return public, anon

def build_table(public, anon):
    header = "| # | Player | Shots | Date |\n|---|---|---|---|\n"
    rows = []
    for i, d in enumerate(public, 1):
        date  = d["timestamp"].split("T")[0]
        shots = d.get("shots", "?")          # les anciennes entrées n’en ont pas
        rows.append(f"| {i} | @{d['login']} | {shots} | {date} |")
    table = header + "\n".join(rows) + f"\n\n**{anon} anonymous deaths**\n"
    return table

def update_readme(table_md):
    readme = README_FILE.read_text(encoding="utf-8")
    if START_TAG not in readme or END_TAG not in readme:
        # Ajoute les marqueurs à la fin si absents
        readme += f"\n\n{START_TAG}\n{END_TAG}\n"

    before, _mid, after = readme.partition(START_TAG)
    _junk, _mid2, tail  = after.partition(END_TAG)

    new_block = f"{START_TAG}\n\n## 💀 Hall of Fame\n\n{table_md}{END_TAG}"
    new_readme = before + new_block + tail

    if new_readme != readme:
        README_FILE.write_text(new_readme, encoding="utf-8")
        print("README updated")
        return True
    print("No change")
    return False

def main():
    public, anon = load_deaths()
    table_md = build_table(public, anon)
    changed = update_readme(table_md)
    if changed:
        # GitHub Actions : on demande à git d'enregistrer la modif
        import subprocess, os
        subprocess.run(["git", "config", "user.name", "github-actions[bot]"])
        subprocess.run(["git", "config", "user.email", "github-actions[bot]@users.noreply.github.com"])
        subprocess.run(["git", "add", "README.md"])
        subprocess.run(["git", "commit", "-m", "chore: update graveyard"], check=True)
    else:
        print("README already up to date")

if __name__ == "__main__":
    main()
