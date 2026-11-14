from __future__ import annotations

import sys
from pathlib import Path

import pytest

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
    ThemeScreen,
)
from snaktui.storage import Store


def make_app(tmp_path: Path, **settings: object) -> SnakTUI:
    store = Store(tmp_path / "state.json")
    if settings:
        store.update_settings(**settings)
    return SnakTUI(store=store)


async def test_starts_on_menu(tmp_path: Path) -> None:
    app = make_app(tmp_path)
    async with app.run_test(size=(100, 30)) as pilot:
        await pilot.pause(0.3)
        assert isinstance(app.screen, MenuScreen)


async def test_enter_starts_game_and_pause_toggles(tmp_path: Path) -> None:
    # Wrap walls off: pilot.pause() can consume seconds of wall time, and a plain
    # rightward snake would legitimately reach the wall before the second press.
    app = make_app(tmp_path, wrap=True)
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


async def test_theme_change_retints_css_chrome(tmp_path: Path) -> None:
    # Switching the game palette must also switch the registered Textual
    # theme, otherwise styles.tcss chrome stays Neon forever.
    app = make_app(tmp_path, theme="candy")
    async with app.run_test(size=(100, 30)) as pilot:
        await pilot.pause(0.3)
        assert app.theme == "candy"
        app.apply_settings(theme="matrix")
        assert app.theme == "matrix"
        assert app.settings.theme == "matrix"


async def test_resize_restores_sidebar(tmp_path: Path) -> None:
    # The sidebar is decided in compose(); growing the terminal mid-run must
    # mount it back instead of leaving the arena cramped.
    app = make_app(tmp_path)
    async with app.run_test(size=(70, 24)) as pilot:
        await pilot.pause(0.3)
        await pilot.press("enter")
        await pilot.pause(0.3)
        assert len(app.screen.query("#sidebar")) == 0
        await pilot.resize_terminal(100, 30)
        await pilot.pause(0.3)
        assert len(app.screen.query("#sidebar")) == 1
        await pilot.resize_terminal(70, 24)
        await pilot.pause(0.3)
        assert len(app.screen.query("#sidebar")) == 0


async def test_build_config_adapts_to_size(tmp_path: Path) -> None:
    app = make_app(tmp_path)
    async with app.run_test(size=(100, 30)):
        config = app.build_config()
        assert config.width == 44
        assert config.height == 22
    app2 = make_app(tmp_path)
    async with app2.run_test(size=(80, 24)):
        config = app2.build_config()
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


def test_cli_version_flag(capsys: pytest.CaptureFixture[str], monkeypatch: pytest.MonkeyPatch) -> None:
    from snaktui import __version__
    from snaktui.app import main

    monkeypatch.setattr(sys, "argv", ["snaktui", "--version"])
    main()
    assert capsys.readouterr().out.strip() == f"snaktui {__version__}"


def test_cli_help_flag(capsys: pytest.CaptureFixture[str], monkeypatch: pytest.MonkeyPatch) -> None:
    from snaktui.app import main

    monkeypatch.setattr(sys, "argv", ["snaktui", "--help"])
    main()
    out = capsys.readouterr().out
    assert "usage" in out


async def test_theme_picker_previews_and_cancel_restores(tmp_path: Path) -> None:
    app = make_app(tmp_path)
    async with app.run_test(size=(100, 30)) as pilot:
        await pilot.pause(0.3)
        start = app.settings.theme

        await pilot.press("p")
        await pilot.pause(0.2)
        assert isinstance(app.screen, ThemeScreen)

        await pilot.press("down")
        await pilot.pause(0.2)
        assert app.settings.theme != start

        await pilot.press("escape")
        await pilot.pause(0.2)
        assert app.settings.theme == start
        assert isinstance(app.screen, MenuScreen)


async def test_theme_picker_enter_applies(tmp_path: Path) -> None:
    app = make_app(tmp_path)
    async with app.run_test(size=(100, 30)) as pilot:
        await pilot.pause(0.3)
        start = app.settings.theme

        await pilot.press("p")
        await pilot.pause(0.2)
        await pilot.press("down", "enter")
        await pilot.pause(0.2)

        assert isinstance(app.screen, MenuScreen)
        assert app.settings.theme != start
        assert app.store.settings.theme == app.settings.theme


async def test_sidebar_lists_magnet_food_glyph(tmp_path: Path) -> None:
    # v1.1.0 added the Magnet power-up; every other surface (help rows,
    # board glyphs, boost bar) lists it, so the FOOD legend must too.
    app = make_app(tmp_path)
    async with app.run_test(size=(100, 30)) as pilot:
        await pilot.pause(0.3)
        await pilot.press("enter")
        await pilot.pause(0.3)
        sidebar = app.screen.query_one("#sidebar")
        assert "\u271a" in str(sidebar.content)
