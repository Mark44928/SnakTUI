"""Persistence for settings and high scores.

Data lives under ``$HOME/.local/share/snaktui`` (or ``$XDG_DATA_HOME``),
never in a system path. Set ``SNAKTUI_DATA_DIR`` to override the location.
"""

from __future__ import annotations

import base64
import contextlib
import fcntl
import json
import math
import os
from dataclasses import asdict, dataclass, fields, replace
from datetime import datetime
from pathlib import Path

from .models import DIFFICULTIES
from .theme import THEMES, Palette, palette_from_mapping, register_theme

MAX_SCORES = 10
MAX_CUSTOM_THEMES = 64
MAX_GHOST_TRACK = 5000
ARENA_SIZES = ("auto", "small", "medium", "large")
ARENA_LABELS = {
    "auto": "Auto",
    "small": "Small",
    "medium": "Medium",
    "large": "Large",
}


def default_data_dir() -> Path:
    override = os.environ.get("SNAKTUI_DATA_DIR")
    if override:
        return Path(override).expanduser()
    xdg = os.environ.get("XDG_DATA_HOME")
    base = Path(xdg).expanduser() if xdg else Path.home() / ".local" / "share"
    return base / "snaktui"


def _strict_bool(value: object, default: bool) -> bool:
    # JSON "false"/"true" strings must not become truthy/falsy by accident;
    # only real booleans and integral 0/1 are accepted.
    if isinstance(value, bool):
        return value
    if isinstance(value, int | float) and value in (0, 1):
        return bool(value)
    return default


@dataclass
class Settings:
    """User preferences that survive between runs."""

    theme: str = "neon"
    difficulty: str = "classic"
    wrap: bool = False
    obstacles: bool = True
    grid: bool = True
    sound: bool = True
    low_gfx: bool = False
    arena: str = "auto"
    a11y: bool = False

    def sanitized(self) -> Settings:
        theme = self.theme if self.theme in THEMES else "neon"
        difficulty = self.difficulty if self.difficulty in DIFFICULTIES else "classic"
        arena = self.arena if self.arena in ARENA_SIZES else "auto"
        return replace(
            self,
            theme=theme,
            difficulty=difficulty,
            wrap=_strict_bool(self.wrap, False),
            obstacles=_strict_bool(self.obstacles, True),
            grid=_strict_bool(self.grid, True),
            sound=_strict_bool(self.sound, True),
            low_gfx=_strict_bool(self.low_gfx, False),
            arena=arena,
            a11y=_strict_bool(self.a11y, False),
        )


@dataclass
class ScoreEntry:
    score: int
    level: int
    length: int
    difficulty: str
    theme: str
    date: str
    daily: bool = False


@dataclass
class GhostRun:
    score: int
    seed: int | None
    width: int
    height: int
    difficulty: str
    daily: bool
    track: list[tuple[float, int, int]]


class Store:
    """Loads and saves a small JSON document."""

    def __init__(self, path: Path | None = None) -> None:
        self.path = path or default_data_dir() / "state.json"
        self.settings = Settings()
        self.scores: list[ScoreEntry] = []
        self.total_runs = 0
        self.custom_themes: list[dict[str, object]] = []
        self.ghost: GhostRun | None = None
        self.load()

    # -- persistence -------------------------------------------------
    def load(self) -> None:
        try:
            raw = json.loads(self.path.read_text(encoding="utf-8"))
        except (OSError, ValueError):
            return
        if not isinstance(raw, dict):
            return

        raw_themes = raw.get("custom_themes")
        if isinstance(raw_themes, list):
            seen: set[str] = set()
            for item in raw_themes[:MAX_CUSTOM_THEMES]:
                palette = palette_from_mapping(item) if isinstance(item, dict) else None
                if palette is None or palette.key in seen:
                    continue
                seen.add(palette.key)
                register_theme(palette)
                self.custom_themes.append(asdict(palette))

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
                    entry_score = int(item["score"])
                    if entry_score <= 0:
                        # Zero/negative runs are never persisted; drop them on load too.
                        continue
                    entries.append(
                        ScoreEntry(
                            score=entry_score,
                            level=int(item.get("level", 1)),
                            length=int(item.get("length", 4)),
                            difficulty=str(item.get("difficulty", "classic")),
                            theme=str(item.get("theme", "neon")),
                            date=str(item.get("date", "")),
                            daily=item.get("daily") is True,
                        )
                    )
                except (KeyError, TypeError, ValueError, OverflowError):
                    continue
            self.scores = sorted(entries, key=lambda entry: entry.score, reverse=True)[
                :MAX_SCORES
            ]

        raw_ghost = raw.get("ghost")
        if isinstance(raw_ghost, dict):
            try:
                score = int(raw_ghost["score"])
                seed = raw_ghost.get("seed")
                seed = int(seed) if seed is not None else None
                width, height = int(raw_ghost["width"]), int(raw_ghost["height"])
                difficulty = str(raw_ghost["difficulty"]).lower()
                daily = raw_ghost.get("daily") is True
                track = []
                for frame in raw_ghost.get("track", []):
                    if not isinstance(frame, (list, tuple)) or len(frame) != 3:
                        continue
                    t, x, y = float(frame[0]), int(frame[1]), int(frame[2])
                    if math.isfinite(t) and t >= 0 and 0 <= x < width and 0 <= y < height:
                        track.append((t, x, y))
                    if len(track) >= MAX_GHOST_TRACK:
                        break
                if score > 0 and width > 0 and height > 0 and difficulty in DIFFICULTIES and track:
                    self.ghost = GhostRun(score, seed, width, height, difficulty, daily, track)
            except (KeyError, TypeError, ValueError, OverflowError):
                self.ghost = None

        raw_total = raw.get("total_runs")
        if isinstance(raw_total, int) and not isinstance(raw_total, bool) and 0 <= raw_total <= 1_000_000_000:
            self.total_runs = max(raw_total, len(self.scores))
        else:
            self.total_runs = len(self.scores)

    @contextlib.contextmanager
    def _locked(self):
        self.path.parent.mkdir(parents=True, exist_ok=True)
        lock_path = self.path.with_name(self.path.name + ".lock")
        with open(lock_path, "a", encoding="utf-8") as lock:
            fcntl.flock(lock.fileno(), fcntl.LOCK_EX)
            try:
                yield
            finally:
                fcntl.flock(lock.fileno(), fcntl.LOCK_UN)

    def _fresh(self) -> Store:
        return Store(self.path)

    def _absorb(self, other: Store) -> None:
        self.settings = other.settings
        self.scores = other.scores
        self.total_runs = other.total_runs
        self.custom_themes = other.custom_themes
        self.ghost = other.ghost

    def save(self) -> None:
        payload = {
            "version": 1,
            "settings": asdict(self.settings),
            "scores": [asdict(entry) for entry in self.scores],
            "total_runs": self.total_runs,
            "custom_themes": self.custom_themes,
            "ghost": asdict(self.ghost) if self.ghost else None,
        }
        try:
            self.path.parent.mkdir(parents=True, exist_ok=True)
            tmp = self.path.with_name(f"{self.path.name}.{os.getpid()}.tmp")
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
        """Insert a score, returning True when it is a new personal best.

        Zero scores are ignored here too (not just in the app layer): the
        invariant "zero-score runs not persisted" must hold for every caller,
        otherwise one careless call site silently writes junk to the board.
        """

        if entry.score <= 0:
            return False
        with self._locked():
            fresh = self._fresh()
            new_best = entry.score > fresh.high_score
            fresh.scores.append(entry)
            fresh.scores.sort(key=lambda item: item.score, reverse=True)
            del fresh.scores[MAX_SCORES:]
            fresh.total_runs += 1
            fresh.save()
            self._absorb(fresh)
        return new_best

    def matching_ghost(self, config) -> GhostRun | None:
        ghost = self.ghost
        if ghost is None or ghost.score <= 0:
            return None
        if (
            ghost.width != config.width
            or ghost.height != config.height
            or ghost.difficulty != config.difficulty.key
            or ghost.daily != config.daily
        ):
            return None
        if config.daily and ghost.seed != config.seed:
            return None
        return ghost

    def save_ghost(self, ghost: GhostRun) -> None:
        if ghost.score <= 0 or not ghost.track:
            return
        with self._locked():
            fresh = self._fresh()
            fresh.ghost = ghost
            fresh.save()
            self._absorb(fresh)

    def reset_scores(self) -> None:
        with self._locked():
            fresh = self._fresh()
            fresh.scores = []
            fresh.save()
            self._absorb(fresh)

    # -- settings ----------------------------------------------------
    def update_settings(self, **changes: object) -> Settings:
        with self._locked():
            fresh = self._fresh()
            fresh.settings = replace(fresh.settings, **changes).sanitized()
            fresh.save()
            self._absorb(fresh)
        return self.settings

    def save_custom_theme(self, palette: Palette) -> None:
        register_theme(palette)
        entry = asdict(palette)
        with self._locked():
            fresh = self._fresh()
            fresh.custom_themes = [t for t in fresh.custom_themes if t.get("key") != palette.key]
            fresh.custom_themes.append(entry)
            del fresh.custom_themes[:-MAX_CUSTOM_THEMES]
            fresh.save()
            self._absorb(fresh)


def make_entry(
    score: int,
    level: int,
    length: int,
    difficulty: str,
    theme: str,
    daily: bool = False,
) -> ScoreEntry:
    return ScoreEntry(
        score=score,
        level=level,
        length=length,
        difficulty=difficulty,
        theme=theme,
        date=datetime.now().strftime("%Y-%m-%d %H:%M"),
        daily=daily,
    )


def make_share_code(score, level, length, difficulty, theme, daily=False, seed=None):
    payload = {
        "v": 1,
        "score": int(score),
        "level": int(level),
        "length": int(length),
        "difficulty": str(difficulty),
        "theme": str(theme),
        "daily": bool(daily),
        "seed": seed,
    }
    raw = json.dumps(payload, separators=(",", ":"), sort_keys=True).encode("utf-8")
    return "SNAK1-" + base64.urlsafe_b64encode(raw).decode("ascii").rstrip("=")


def parse_share_code(code):
    if not isinstance(code, str) or not code.startswith("SNAK1-"):
        return None
    body = code[6:]
    padding = "=" * (-len(body) % 4)
    try:
        payload = json.loads(base64.urlsafe_b64decode(body + padding).decode("utf-8"))
    except (ValueError, UnicodeDecodeError):
        return None
    if not isinstance(payload, dict) or payload.get("v") != 1:
        return None
    required = ("score", "level", "length", "difficulty", "theme", "daily", "seed")
    if any(key not in payload for key in required):
        return None
    return payload


def entry_from_share_code(code: str) -> ScoreEntry:
    payload = parse_share_code(code)
    if payload is None:
        raise ValueError("invalid run code")
    try:
        score = int(payload["score"])
        level = int(payload["level"])
        length = int(payload["length"])
    except (TypeError, ValueError, OverflowError):
        raise ValueError("run code contains an invalid score") from None
    difficulty = str(payload["difficulty"]).strip().lower()
    theme = str(payload["theme"]).strip().lower()
    if not 0 < score <= 10_000_000:
        raise ValueError("run code score is out of range")
    if not 1 <= level <= 999 or not 1 <= length <= 10_000:
        raise ValueError("run code result is out of range")
    if difficulty not in DIFFICULTIES:
        raise ValueError("run code names an unknown difficulty")
    if theme not in THEMES:
        theme = "neon"  # custom themes don't travel; fall back gracefully
    if not isinstance(payload["daily"], bool):
        raise ValueError("run code daily flag is invalid")
    return ScoreEntry(
        score=score,
        level=level,
        length=length,
        difficulty=difficulty,
        theme=theme,
        date=datetime.now().strftime("%Y-%m-%d %H:%M"),
        daily=payload["daily"],
    )
