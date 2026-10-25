from __future__ import annotations

import json
import re
from pathlib import Path

from snaktui.storage import (
    MAX_SCORES,
    ScoreEntry,
    Settings,
    Store,
    default_data_dir,
    make_entry,
)


def test_default_data_dir_honors_override(monkeypatch, tmp_path: Path) -> None:
    monkeypatch.setenv("SNAKTUI_DATA_DIR", str(tmp_path / "custom"))
    assert default_data_dir() == tmp_path / "custom"


def test_default_data_dir_honors_xdg(monkeypatch, tmp_path: Path) -> None:
    monkeypatch.delenv("SNAKTUI_DATA_DIR", raising=False)
    monkeypatch.setenv("XDG_DATA_HOME", str(tmp_path / "xdg"))
    assert default_data_dir() == tmp_path / "xdg" / "snaktui"


def test_default_data_dir_falls_back_to_home(monkeypatch, tmp_path: Path) -> None:
    monkeypatch.delenv("SNAKTUI_DATA_DIR", raising=False)
    monkeypatch.delenv("XDG_DATA_HOME", raising=False)
    monkeypatch.setenv("HOME", str(tmp_path))
    assert default_data_dir() == tmp_path / ".local" / "share" / "snaktui"


def test_settings_are_sanitized() -> None:
    settings = Settings(theme="nope", difficulty="nope", wrap=1, obstacles=0).sanitized()
    assert settings.theme == "neon"
    assert settings.difficulty == "classic"
    assert settings.wrap is True
    assert settings.obstacles is False


def test_round_trip_persists_settings_and_scores(tmp_path: Path) -> None:
    path = tmp_path / "state.json"
    store = Store(path)
    store.update_settings(theme="amber", difficulty="insane", wrap=True, sound=False)
    store.add_score(make_entry(120, 2, 8, "Insane", "amber"))
    store.add_score(make_entry(340, 4, 14, "Insane", "amber"))

    loaded = Store(path)
    assert loaded.settings.theme == "amber"
    assert loaded.settings.difficulty == "insane"
    assert loaded.settings.wrap is True
    assert loaded.settings.sound is False
    assert loaded.high_score == 340
    assert len(loaded.scores) == 2
    assert loaded.scores[0].score == 340


def test_scores_are_sorted_and_capped(tmp_path: Path) -> None:
    store = Store(tmp_path / "state.json")
    for value in range(1, MAX_SCORES + 6):
        store.add_score(make_entry(value * 10, 1, 4, "Classic", "neon"))

    assert len(store.scores) == MAX_SCORES
    scores = [entry.score for entry in store.scores]
    assert scores == sorted(scores, reverse=True)
    assert store.high_score == (MAX_SCORES + 5) * 10


def test_add_score_reports_new_best(tmp_path: Path) -> None:
    store = Store(tmp_path / "state.json")
    assert store.add_score(make_entry(100, 1, 4, "Classic", "neon")) is True
    assert store.add_score(make_entry(50, 1, 4, "Classic", "neon")) is False
    assert store.add_score(make_entry(200, 2, 9, "Classic", "neon")) is True


def test_reset_scores_clears_and_persists(tmp_path: Path) -> None:
    path = tmp_path / "state.json"
    store = Store(path)
    store.add_score(make_entry(500, 3, 12, "Classic", "neon"))
    store.reset_scores()

    assert store.scores == []
    assert store.high_score == 0
    assert Store(path).scores == []


def test_update_settings_sanitizes_bad_values(tmp_path: Path) -> None:
    store = Store(tmp_path / "state.json")
    store.update_settings(theme="bogus", difficulty="bogus")
    assert store.settings.theme == "neon"
    assert store.settings.difficulty == "classic"


def test_corrupt_json_is_ignored(tmp_path: Path) -> None:
    path = tmp_path / "state.json"
    path.write_text("{not json", encoding="utf-8")
    store = Store(path)
    assert store.settings == Settings()
    assert store.scores == []


def test_non_dict_payload_is_ignored(tmp_path: Path) -> None:
    path = tmp_path / "state.json"
    path.write_text("[]", encoding="utf-8")
    assert Store(path).scores == []


def test_bad_entries_are_skipped(tmp_path: Path) -> None:
    path = tmp_path / "state.json"
    path.write_text(
        json.dumps(
            {
                "settings": {"theme": "ice", "difficulty": "chill", "unknown": 1},
                "scores": [
                    {"score": "not-a-number"},
                    {"score": 90, "level": 2, "length": 6, "difficulty": "Chill"},
                    "junk",
                ],
            }
        ),
        encoding="utf-8",
    )
    store = Store(path)
    assert store.settings.theme == "ice"
    assert store.settings.difficulty == "chill"
    assert len(store.scores) == 1
    assert store.scores[0].score == 90
    assert store.scores[0].theme == "neon"


def test_make_entry_formats_date() -> None:
    entry = make_entry(10, 1, 4, "Classic", "neon")
    assert isinstance(entry, ScoreEntry)
    assert re.fullmatch(r"\d{4}-\d{2}-\d{2} \d{2}:\d{2}", entry.date)
