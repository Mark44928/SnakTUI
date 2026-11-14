# AGENTS.md — SnakTUI

Repository-specific guidance for coding agents. The global Termux directive still applies: no FHS paths, no root tooling, Termux shebangs, `TMPDIR` set, and never run recursive commands on `/sdcard` or `~/storage`.

## What This Project Is

SnakTUI is a terminal Snake game built with Python and Textual. The game core is pure Python; Textual only renders and routes input. Keep that separation. CI at `.github/workflows/ci.yml`.

## Architecture

| Path | Responsibility |
| --- | --- |
| `snaktui/game.py` | Pure simulation. **No Textual imports.** Movement, collisions, food, combos, levels, effects, particles, stats. |
| `snaktui/models.py` | Dataclasses, enums, difficulty presets, food metadata. **No Textual imports.** |
| `snaktui/theme.py` | Palettes and color blending. No Textual imports. |
| `snaktui/storage.py` | Atomic JSON persistence for settings and top-10 scores. No Textual imports. |
| `snaktui/board.py` | Arena widget. Builds one `rich.text.Text` per frame from game state. |
| `snaktui/screens.py` | All screens, HUD, sidebar, modals, key handling, and rendering. |
| `snaktui/app.py` | App shell, adaptive board sizing, screen navigation, score saving. |
| `snaktui/styles.tcss` | Layout and color CSS. |
| `tests/` | Pytest suite (72 tests, headless — no TTY needed), including headless Textual smoke tests. |

## Invariants

- `game.py`, `models.py`, `theme.py`, and `storage.py` must stay importable without Textual.
- All timing through `Game.update(dt)`. No wall-clock calls in simulation.
- Spawning never overlaps snake, existing food, or hazards. Use `_free_cells()`.
- Scores capped at `MAX_SCORES`, sorted descending. Zero-score runs not persisted.
- Persistence atomic (`tmp.replace`), never raises on I/O errors.
- Settings sanitized through `Settings.sanitized()`.
- UI usable at **80×24**; sidebar hidden below 76 cols, hint shortens below 90 cols.
- v1.1.0: `FoodKind.MAGNET` drags the apple one cell toward the head every
  other step (`Game._pull_food`) — a pull, never a teleport, and it may never
  place food on the snake, a hazard or the special. `EFFECT_ORDER`,
  `EFFECT_GLYPHS`, `board.FOOD_GLYPHS` and the help-screen `FOOD_ROWS` all
  cover the new kind; the HUD's `NEXT` level bar (`GameScreen._level_bar`) only
  renders at width ≥ 80.
- v1.2.0: eleven themes in `theme.py` — five hand-tuned + six real terminal
  schemes (Dracula, Nord, Gruvbox, Catppuccin Mocha, Tokyo Night, Solarized
  Dark) with official hex values from their upstream palettes. `THEMES` and
  `THEME_ORDER` must stay key-for-key in sync (tests assert it). Version is
  declared in `pyproject.toml` and `snaktui/__init__.py` — keep both equal.

## Commands (Termux)

```bash
export TMPDIR=/data/data/com.termux/files/usr/tmp
. .venv/bin/activate

python -m snaktui          # run the game
pytest -q                  # tests (headless, no TTY needed)
ruff check .               # lint
```

`pip install -e ".[dev]"`. If `ruff` fails to build on Termux, install prebuilt: `pkg install ruff`.

## Code Style

- Python 3.10+, `from __future__ import annotations`, typed public functions.
- Line length 100. Ruff: `E`, `F`, `I`, `UP`, `B`, `SIM`.
- Small helpers and dataclasses. Comments only when explaining *why*.
- Terminal output Unicode-block based; avoid emoji in the UI.
- No new runtime dependencies without strong reason.

## Tests

- Unit-test simulation and storage without Textual.
- Use `App.run_test(size=(...))` and `pilot.press(...)` for UI flows.
- Set `game.ready_timer = 0` in simulation tests.
- Do not assert exact colors or full screenshot output; assert state and screen types.

## Git

- Run `ruff check .` and `pytest -q` before committing.
- Conventional imperative commit subjects (e.g. `Add ghost power-up`).
- Do not commit `.venv/`, `__pycache__/`, local `state.json`, or generated screenshots outside `docs/`.
