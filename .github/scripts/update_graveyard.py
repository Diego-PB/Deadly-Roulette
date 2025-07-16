#!/usr/bin/env python3
from pathlib import Path
import json, subprocess, os

DEATHS_FILE = Path("deaths.json")
README_FILE = Path("README.md")
START_TAG   = "<!--GRAVEYARD_START-->"
END_TAG     = "<!--GRAVEYARD_END-->"

def load_deaths():
    data = json.loads(DEATHS_FILE.read_text(encoding="utf-8"))
    public = [d for d in data if d["public"]]
    anon   = sum(1 for d in data if not d["public"])
    return public, anon

def hall_of_fame(public, anon):
    header = "| # | Player | Shots | Date |\n|---|---|---|---|\n"
    rows = []
    for i, d in enumerate(public, 1):
        date  = d["timestamp"].split("T")[0]
        shots = d.get("shots", "?")
        rows.append(f"| {i} | @{d['login']} | {shots} | {date} |")
    return header + "\n".join(rows) + f"\n\n**{anon} anonymous deaths**\n"

def podium(public):
    top   = sorted(public, key=lambda d: d.get("shots", 0), reverse=True)[:3]
    if not top:
        return ""
    medals = ["🥇", "🥈", "🥉"]
    rows = [
        f"| {medals[i]} | @{d['login']} | {d.get('shots','?')} |"
        for i, d in enumerate(top)
    ]
    header = "| Rank | Player | Shots |\n|---|---|---|\n"
    return "### 🏆 Top trigger‑happy players\n\n" + header + "\n".join(rows) + "\n"

def update_readme(block_md):
    readme = README_FILE.read_text(encoding="utf-8")
    if START_TAG not in readme or END_TAG not in readme:
        readme += f"\n\n{START_TAG}\n{END_TAG}\n"   # ajoute les marqueurs si absents

    before, _mid, after  = readme.partition(START_TAG)
    _junk, _mid2, tail  = after.partition(END_TAG)

    new_readme = before + START_TAG + "\n\n" + block_md + END_TAG + tail
    if new_readme != readme:
        README_FILE.write_text(new_readme, encoding="utf-8")
        print("README updated")
        return True
    print("No change")
    return False

def main():
    public, anon = load_deaths()
    block_md = (
        "## 💀 Hall of Fame\n\n"
        + hall_of_fame(public, anon)
        + "\n"
        + podium(public)
    )
    if update_readme(block_md):
        subprocess.run(["git", "config", "user.name", "github-actions[bot]"])
        subprocess.run(["git", "config", "user.email", "github-actions[bot]@users.noreply.github.com"])
        subprocess.run(["git", "add", "README.md"])
        subprocess.run(["git", "commit", "-m", "chore: update graveyard"], check=True)
    else:
        print("README already up to date")

if __name__ == "__main__":
    main()
