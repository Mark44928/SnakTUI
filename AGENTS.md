# AGENTS.md — SnakTUI

Repository-specific guidance for coding agents. The global Termux directive
still applies: no FHS paths, no root tooling, Termux shebangs, `TMPDIR` set,
and never run recursive commands on `/sdcard` or `~/storage`.

## What this project is

SnakTUI is a terminal Snake game built with Python and Textual. The game core
is pure Python; Textual only renders and routes input. Keep that separation.

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
| `tests/` | Pytest suite, including headless Textual smoke tests. |

## Invariants

- `game.py`, `models.py`, `theme.py`, and `storage.py` must stay importable
  without Textual. Tests rely on this.
- All timing goes through `Game.update(dt)`. Do not add wall-clock calls inside
  the simulation.
- Food/obstacle spawning must never place anything on the snake, existing food,
  or hazards. Use `_free_cells()`.
- Scores are capped at `MAX_SCORES` and sorted descending. Zero-score runs are
  not persisted (`SnakTUI.complete_run`).
- Persistence must stay atomic (`tmp.replace`) and must never raise on I/O
  errors.
- Settings values are sanitized through `Settings.sanitized()`.
- Keep the UI usable at **80×24**; the sidebar is hidden below 76 columns and
  the hint line shortens below 90 columns.

## Commands (Termux)

```bash
export TMPDIR=/data/data/com.termux/files/usr/tmp
. .venv/bin/activate

python -m snaktui          # run the game
pytest -q                  # tests (headless, no TTY needed)
ruff check .               # lint
ruff format --check .      # formatting check (optional)
```

Install dev dependencies with `pip install -e ".[dev]"`. If `ruff` fails to
build on Termux, install the prebuilt binary: `pkg install ruff`.

Use the project venv. The global Textual install may be too old for this code.

## Visual verification

Textual can export an SVG screenshot without a TTY:

```python
app.export_screenshot()
```

Then rasterize for inspection:

```bash
rsvg-convert -w 1200 -b '#05010f' shot.svg -o shot.png
```

Render at `100x30` and `80x24` before claiming a layout change works. When
building `rich.text.Text` spans, put spaces at the **end** of the preceding
span; leading spaces inside a span can disappear in SVG export.

## Code style

- Python 3.10+, `from __future__ import annotations`, typed public functions.
- Line length 100. Ruff rules: `E`, `F`, `I`, `UP`, `B`, `SIM`.
- Prefer small helpers and dataclasses. No comments unless they explain *why*.
- Keep terminal output Unicode-block based; avoid emoji in the UI.
- Do not introduce new runtime dependencies without a strong reason.

## Tests

- Unit-test simulation and storage without Textual.
- Use `App.run_test(size=(...))` and `pilot.press(...)` for UI flows.
- Set `game.ready_timer = 0` in simulation tests so movement starts at once.
- Do not assert exact colors or full screenshot output; assert state and
  screen types.

## Git

- Run `ruff check .` and `pytest -q` before committing.
- Conventional, imperative commit subjects (e.g. `Add ghost power-up`).
- Do not commit `.venv/`, `__pycache__/`, local `state.json`, or generated
  screenshots outside `docs/`.
