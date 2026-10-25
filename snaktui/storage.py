"""Persistence for settings and high scores.

Data lives under ``$HOME/.local/share/snaktui`` (or ``$XDG_DATA_HOME``),
never in a system path. Set ``SNAKTUI_DATA_DIR`` to override the location.
"""

from __future__ import annotations

import json
import os
from dataclasses import asdict, dataclass, fields, replace
from datetime import datetime
from pathlib import Path

from .models import DIFFICULTIES
from .theme import THEMES

MAX_SCORES = 10


def default_data_dir() -> Path:
    override = os.environ.get("SNAKTUI_DATA_DIR")
    if override:
        return Path(override).expanduser()
    xdg = os.environ.get("XDG_DATA_HOME")
    base = Path(xdg).expanduser() if xdg else Path.home() / ".local" / "share"
    return base / "snaktui"


@dataclass
class Settings:
    """User preferences that survive between runs."""

    theme: str = "neon"
    difficulty: str = "classic"
    wrap: bool = False
    obstacles: bool = True
    grid: bool = True
    sound: bool = True

    def sanitized(self) -> Settings:
        theme = self.theme if self.theme in THEMES else "neon"
        difficulty = self.difficulty if self.difficulty in DIFFICULTIES else "classic"
        return replace(
            self,
            theme=theme,
            difficulty=difficulty,
            wrap=bool(self.wrap),
            obstacles=bool(self.obstacles),
            grid=bool(self.grid),
            sound=bool(self.sound),
        )


@dataclass
class ScoreEntry:
    score: int
    level: int
    length: int
    difficulty: str
    theme: str
    date: str


class Store:
    """Loads and saves a small JSON document."""

    def __init__(self, path: Path | None = None) -> None:
        self.path = path or default_data_dir() / "state.json"
        self.settings = Settings()
        self.scores: list[ScoreEntry] = []
        self.load()

    # -- persistence -------------------------------------------------
    def load(self) -> None:
        try:
            raw = json.loads(self.path.read_text(encoding="utf-8"))
        except (OSError, ValueError):
            return
        if not isinstance(raw, dict):
            return

        raw_settings = raw.get("settings")
        if isinstance(raw_settings, dict):
            allowed = {field.name for field in fields(Settings)}
            values = {k: v for k, v in raw_settings.items() if k in allowed}
            try:
                self.settings = Settings(**values).sanitized()
            except TypeError:
                self.settings = Settings()

        raw_scores = raw.get("scores")
        if isinstance(raw_scores, list):
            entries: list[ScoreEntry] = []
            for item in raw_scores:
                if not isinstance(item, dict):
                    continue
                try:
                    entries.append(
                        ScoreEntry(
                            score=int(item["score"]),
                            level=int(item.get("level", 1)),
                            length=int(item.get("length", 4)),
                            difficulty=str(item.get("difficulty", "classic")),
                            theme=str(item.get("theme", "neon")),
                            date=str(item.get("date", "")),
                        )
                    )
                except (KeyError, TypeError, ValueError):
                    continue
            self.scores = sorted(entries, key=lambda entry: entry.score, reverse=True)[
                :MAX_SCORES
            ]

    def save(self) -> None:
        payload = {
            "version": 1,
            "settings": asdict(self.settings),
            "scores": [asdict(entry) for entry in self.scores],
        }
        try:
            self.path.parent.mkdir(parents=True, exist_ok=True)
            tmp = self.path.with_name(self.path.name + ".tmp")
            tmp.write_text(json.dumps(payload, indent=2), encoding="utf-8")
            tmp.replace(self.path)
        except OSError:
            # A read-only home should never crash a game.
            pass

    # -- scores ------------------------------------------------------
    @property
    def high_score(self) -> int:
        return self.scores[0].score if self.scores else 0

    def add_score(self, entry: ScoreEntry) -> bool:
        """Insert a score, returning True when it is a new personal best."""

        new_best = entry.score > self.high_score
        self.scores.append(entry)
        self.scores.sort(key=lambda item: item.score, reverse=True)
        del self.scores[MAX_SCORES:]
        self.save()
        return new_best

    def reset_scores(self) -> None:
        self.scores = []
        self.save()

    # -- settings ----------------------------------------------------
    def update_settings(self, **changes: object) -> Settings:
        self.settings = replace(self.settings, **changes).sanitized()
        self.save()
        return self.settings


def make_entry(
    score: int,
    level: int,
    length: int,
    difficulty: str,
    theme: str,
) -> ScoreEntry:
    return ScoreEntry(
        score=score,
        level=level,
        length=length,
        difficulty=difficulty,
        theme=theme,
        date=datetime.now().strftime("%Y-%m-%d %H:%M"),
    )
