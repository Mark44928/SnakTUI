# Contributing to SnakTUI

Thanks for wanting to improve SnakTUI! A few ground rules before you code.

## Ground rules

1. **Python + Textual only.** Runtime deps go in `pyproject.toml` under
   `[project.dependencies]`; anything heavier (curses, pygame, images) is out
   of scope for a pure-TUI game.
2. **Everything renders in Unicode blocks.** No emoji sprites, no ASCII art
   files, no images. If a visual can't be drawn with `█▓▒░ ●` characters and
   rich styles, it doesn't belong.
3. **Match the existing architecture** — `app.py` (screens/input), `snake.py`
   (game model), `render.py` (drawing), `settings.py` (persistence). Don't
   create new top-level modules for small features.
4. **Style**: `ruff check .` must pass with the repo's config. Keep the
   existing naming and comment discipline (no comment noise).

## Getting started

1. Fork, clone, and set up an environment:
   ```bash
   python3 -m venv .venv && . .venv/bin/activate   # Termux: python3 -m venv venv
   pip install -e '.[dev]'
   ```
2. Play the game: `python -m snaktui` (or `snaktui`).
3. Run the test suite: `pytest` — all tests must pass.
4. Run `ruff check .` — must be clean.

## Pull requests

- One feature/fix per PR; keep the diff focused.
- Add tests for game-model changes (movement, collisions, scoring, food
  timers). Visual-only changes need at least a manual smoke test note.
- Screenshot or GIF (terminal capture) in the PR description for visuals.
- Commit style: one imperative line (`add combo multiplier decay`,
  `fix wall-pass collision`).

## Good first issues

- New food types (see `Food & scoring` table in the README).
- New themes (see `settings.py` theme data — must remain readable under all
  five existing themes too).
- Leaderboard export formats.

## Reporting issues

Open an issue including your terminal app (Termux / other), `python
--version`, `textual --version`-ish info, and steps to reproduce. Attach a
screenshot for rendering bugs.
