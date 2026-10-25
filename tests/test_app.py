from __future__ import annotations

from pathlib import Path

from textual.geometry import Size

from snaktui.app import SnakTUI
from snaktui.game import Game
from snaktui.models import GameConfig
from snaktui.screens import (
    GameOverScreen,
    GameScreen,
    HelpScreen,
    HighScoresScreen,
    MenuScreen,
    SettingsScreen,
)
from snaktui.storage import Store


def make_app(tmp_path: Path) -> SnakTUI:
    return SnakTUI(store=Store(tmp_path / "state.json"))


async def test_starts_on_menu(tmp_path: Path) -> None:
    app = make_app(tmp_path)
    async with app.run_test(size=(100, 30)) as pilot:
        await pilot.pause(0.3)
        assert isinstance(app.screen, MenuScreen)


async def test_enter_starts_game_and_pause_toggles(tmp_path: Path) -> None:
    app = make_app(tmp_path)
    async with app.run_test(size=(100, 30)) as pilot:
        await pilot.pause(0.3)
        await pilot.press("enter")
        await pilot.pause(0.3)
        assert isinstance(app.screen, GameScreen)
        screen = app.screen
        assert screen.game.running is True

        await pilot.press("escape")
        await pilot.pause(0.1)
        assert screen.game.paused is True

        await pilot.press("escape")
        await pilot.pause(0.1)
        assert screen.game.running is True


async def test_q_returns_to_menu(tmp_path: Path) -> None:
    app = make_app(tmp_path)
    async with app.run_test(size=(100, 30)) as pilot:
        await pilot.pause(0.3)
        await pilot.press("enter")
        await pilot.pause(0.3)
        await pilot.press("q")
        await pilot.pause(0.3)
        assert isinstance(app.screen, MenuScreen)


async def test_settings_toggle_updates_store(tmp_path: Path) -> None:
    app = make_app(tmp_path)
    async with app.run_test(size=(100, 30)) as pilot:
        await pilot.pause(0.3)
        await pilot.press("s")
        await pilot.pause(0.3)
        assert isinstance(app.screen, SettingsScreen)

        await pilot.press("down", "down", "enter")
        await pilot.pause(0.2)
        assert app.store.settings.wrap is True

        await pilot.press("escape")
        await pilot.pause(0.2)
        assert isinstance(app.screen, MenuScreen)


async def test_help_and_scores_modals_open(tmp_path: Path) -> None:
    app = make_app(tmp_path)
    async with app.run_test(size=(100, 30)) as pilot:
        await pilot.pause(0.3)
        await pilot.press("h")
        await pilot.pause(0.2)
        assert isinstance(app.screen, HelpScreen)

        await pilot.press("escape")
        await pilot.pause(0.2)
        await pilot.press("l")
        await pilot.pause(0.2)
        assert isinstance(app.screen, HighScoresScreen)


async def test_death_opens_game_over_screen(tmp_path: Path) -> None:
    app = make_app(tmp_path)
    async with app.run_test(size=(100, 30)) as pilot:
        await pilot.pause(0.3)
        await pilot.press("enter")
        await pilot.pause(0.3)
        screen = app.screen
        assert isinstance(screen, GameScreen)

        screen.game.ready_timer = 0
        screen.game._die("boom")
        await pilot.pause(1.5)
        assert isinstance(app.screen, GameOverScreen)


async def test_narrow_terminal_hides_sidebar(tmp_path: Path) -> None:
    app = make_app(tmp_path)
    async with app.run_test(size=(70, 24)) as pilot:
        await pilot.pause(0.3)
        await pilot.press("enter")
        await pilot.pause(0.3)
        assert isinstance(app.screen, GameScreen)
        assert len(app.screen.query("#sidebar")) == 0


def test_build_config_adapts_to_size(tmp_path: Path) -> None:
    app = make_app(tmp_path)
    app._size = Size(100, 30)  # type: ignore[attr-defined]
    config = app.build_config()
    assert config.width == 44
    assert config.height == 22

    app._size = Size(80, 24)  # type: ignore[attr-defined]
    config = app.build_config()
    assert config.width == 44
    assert config.height == 19


def test_complete_run_skips_zero_score(tmp_path: Path) -> None:
    app = make_app(tmp_path)
    game = Game(GameConfig())

    game.score = 0
    app.complete_run(game)
    assert app.store.scores == []

    game.score = 123
    stats = app.complete_run(game)
    assert len(app.store.scores) == 1
    assert stats.new_high_score is True
    assert app.store.high_score == 123
