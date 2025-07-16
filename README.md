# 🎲 Deadly Roulette

One chamber, one bullet, zero second chances.

Deadly Roulette is a tiny Python + PySide 6 Russian‑roulette game.If the bullet fires, your GitHub username is written forever in the Graveyard and you can never play again—unless you create a new account!

---

## 🚀 Features

- Minimal GUI with “click” and “bang” sound effects.

- GitHub authentication to enforce global, permanent death.

- Opt‑in public graveyard (or stay anonymous—only the hash is stored).

- Shot counter; automatic Top 3 trigger‑happy players podium.

- README auto‑updated by GitHub Actions.

---

## 🛠️ Quick install (players)

1. Download the latest release : [Deadly Roulette.exe](https://github.com/Diego-PB/Deadly-Roulette/releases/latest)

2. Install [GitHub CLI](https://cli.github.com/) and log in:

```bash
gh auth login
gh auth refresh -h github.com -s public_repo
```

3. Run the executable. Pull the trigger. Good luck!

---

## 🔐 Privacy

- The game always stores a SHA‑256 hash of your GitHub login.

- If you tick “Display my GitHub username…”, your login is stored in clear indeaths.json and shown in the Hall of Fame.

- Otherwise, the entry remains anonymous and only the “anonymous deaths” counter increases.

You may request removal (right to be forgotten) via a pull request or issue.

<!--GRAVEYARD_START-->

## 💀 Hall of Fame

| # | Player | Shots | Date |
|---|---|---|---|
| 1 | @Diego-PB | 11 | 2025-07-16 |

**0 anonymous deaths**

### 🏆 Top trigger‑happy players

| Rank | Player | Shots |
|---|---|---|
| 🥇 | @Diego-PB | 11 |
<!--GRAVEYARD_END-->
