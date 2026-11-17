from __future__ import annotations

import json
import re
from pathlib import Path

from snaktui.models import DIFFICULTIES, GameConfig
from snaktui.storage import (
    MAX_SCORES,
    GhostRun,
    ScoreEntry,
    Settings,
    Store,
    default_data_dir,
    entry_from_share_code,
    make_entry,
    make_share_code,
    parse_share_code,
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
    assert settings.low_gfx is False
    assert Settings(low_gfx="yes").sanitized().low_gfx is False


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


def test_zero_score_ignored_at_storage_layer(tmp_path: Path) -> None:
    # The invariant lives in storage too, not only in the app guard.
    store = Store(tmp_path / "state.json")
    assert store.add_score(make_entry(0, 1, 3, "Classic", "neon")) is False
    assert store.scores == []


def test_string_bools_do_not_leak_into_settings(tmp_path: Path) -> None:
    path = tmp_path / "state.json"
    path.write_text(
        json.dumps(
            {
                "settings": {"wrap": "false", "sound": "false", "grid": "yes", "obstacles": 1},
            }
        ),
        encoding="utf-8",
    )
    store = Store(path)
    assert store.settings.wrap is False
    assert store.settings.sound is True  # field default, not truthy-string
    assert store.settings.grid is True  # field default
    assert store.settings.obstacles is True


def test_non_positive_scores_are_dropped_on_load(tmp_path: Path) -> None:
    path = tmp_path / "state.json"
    path.write_text(
        json.dumps(
            {
                "scores": [
                    {"score": -50, "level": 1, "length": 4, "difficulty": "Classic"},
                    {"score": 0, "level": 1, "length": 4, "difficulty": "Classic"},
                    {"score": 120, "level": 2, "length": 6, "difficulty": "Classic"},
                ],
            }
        ),
        encoding="utf-8",
    )
    store = Store(path)
    assert [entry.score for entry in store.scores] == [120]
    assert store.high_score == 120


def test_arena_setting_round_trips_and_sanitizes(tmp_path: Path) -> None:
    path = tmp_path / "state.json"
    store = Store(path)
    store.update_settings(arena="large")
    assert Store(path).settings.arena == "large"
    assert Settings(arena="nope").sanitized().arena == "auto"


def test_custom_theme_round_trips(tmp_path: Path) -> None:
    from dataclasses import replace

    from snaktui.theme import THEMES

    path = tmp_path / "state.json"
    store = Store(path)
    palette = replace(THEMES["neon"], key="custom-test", label="Custom Test", accent="#123456")
    store.save_custom_theme(palette)
    store.update_settings(theme="custom-test")

    loaded = Store(path)
    assert loaded.settings.theme == "custom-test"
    assert any(item["key"] == "custom-test" for item in loaded.custom_themes)
    assert THEMES["custom-test"].accent == "#123456"


def test_accessibility_setting_sanitizes() -> None:
    assert Settings(a11y=1).sanitized().a11y is True
    assert Settings(a11y="yes").sanitized().a11y is False


def test_daily_score_marker_round_trips(tmp_path: Path) -> None:
    path = tmp_path / "state.json"
    store = Store(path)
    store.add_score(make_entry(250, 3, 9, "Classic", "neon", daily=True))

    loaded = Store(path)
    assert loaded.scores[0].daily is True
    assert loaded.scores[0].score == 250


def test_share_code_round_trips() -> None:
    code = make_share_code(420, 5, 18, "Classic", "neon", daily=True, seed=20261116)
    assert code.startswith("SNAK1-")
    payload = parse_share_code(code)
    assert payload is not None
    assert payload["score"] == 420
    assert payload["daily"] is True
    assert payload["seed"] == 20261116
    assert parse_share_code("not-a-code") is None


def test_share_code_imports_as_score(tmp_path: Path) -> None:
    code = make_share_code(420, 5, 18, "classic", "neon", daily=True, seed=20261116)
    entry = entry_from_share_code(code)
    assert entry.score == 420
    assert entry.difficulty == "classic"
    assert entry.daily is True
    store = Store(tmp_path / "state.json")
    store.add_score(entry)
    assert store.scores[0].score == 420


def test_ghost_round_trips_for_matching_seed(tmp_path: Path) -> None:
    path = tmp_path / "state.json"
    store = Store(path)
    store.save_ghost(
        GhostRun(120, 20261117, 32, 16, "classic", True, [(0.1, 1, 1), (0.2, 2, 1)])
    )
    loaded = Store(path)
    assert loaded.ghost is not None
    assert loaded.ghost.track == [(0.1, 1, 1), (0.2, 2, 1)]
    config = GameConfig(
        width=32,
        height=16,
        difficulty=DIFFICULTIES["classic"],
        seed=20261117,
        daily=True,
    )
    assert loaded.matching_ghost(config) is not None
    other_day = GameConfig(
        width=32,
        height=16,
        difficulty=DIFFICULTIES["classic"],
        seed=20261118,
        daily=True,
    )
    assert loaded.matching_ghost(other_day) is None


def test_non_finite_state_numbers_do_not_crash(tmp_path: Path) -> None:
    path = tmp_path / "state.json"
    path.write_text(
        json.dumps(
            {
                "scores": [{"score": float("inf")}],
                "ghost": {
                    "score": float("inf"),
                    "width": 10,
                    "height": 10,
                    "difficulty": "classic",
                    "track": [[0, 1, 1]],
                },
            }
        ),
        encoding="utf-8",
    )
    store = Store(path)
    assert store.scores == []
    assert store.ghost is None
