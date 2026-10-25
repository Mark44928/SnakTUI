"""SnakTUI application shell and screen wiring."""

from __future__ import annotations

from textual.app import App
from textual.binding import Binding

from .game import Game
from .models import DIFFICULTIES, GameConfig, RunStats
from .screens import GameScreen, MenuScreen
from .storage import Store, make_entry
from .theme import Palette, get_palette


class SnakTUI(App):
    """A neon snake arcade in your terminal."""

    CSS_PATH = "styles.tcss"
    TITLE = "SnakTUI"
    SUB_TITLE = "Neon Serpent"
    ENABLE_COMMAND_PALETTE = False
    BINDINGS = [
        Binding("ctrl+c", "quit_app", "Quit", priority=True, show=False),
    ]

    def __init__(self, store: Store | None = None) -> None:
        super().__init__()
        self.store = store or Store()
        self.settings = self.store.settings

    @property
    def palette(self) -> Palette:
        return get_palette(self.settings.theme)

    def on_mount(self) -> None:
        self.push_screen(MenuScreen())

    # ------------------------------------------------------------------
    # Screen navigation
    # ------------------------------------------------------------------
    def new_game(self) -> None:
        self.switch_screen(GameScreen(self.build_config(), self.store))

    def show_menu(self) -> None:
        self.switch_screen(MenuScreen())

    def build_config(self) -> GameConfig:
        width, height = self.size.width, self.size.height
        if width <= 0 or height <= 0:
            width, height = 80, 24
        show_sidebar = width >= 76
        available_width = width - 4 - (25 if show_sidebar else 0)
        available_height = height - 5
        grid_width = max(18, min(44, available_width))
        grid_height = max(9, min(22, available_height))
        return GameConfig(
            width=grid_width,
            height=grid_height,
            wrap=self.settings.wrap,
            obstacles=self.settings.obstacles,
            grid=self.settings.grid,
            difficulty=DIFFICULTIES[self.settings.difficulty],
            theme=self.settings.theme,
            sound=self.settings.sound,
        )

    # ------------------------------------------------------------------
    # Settings & results
    # ------------------------------------------------------------------
    def apply_settings(self, **changes: object) -> None:
        self.store.update_settings(**changes)
        self.settings = self.store.settings

    def complete_run(self, game: Game) -> RunStats:
        entry = make_entry(
            score=game.score,
            level=game.level,
            length=game.length,
            difficulty=game.difficulty.label,
            theme=game.config.theme,
        )
        new_best = False
        if game.score > 0:
            new_best = self.store.add_score(entry)
        return game.stats(best=self.store.high_score, new_high_score=new_best)

    def action_quit_app(self) -> None:
        self.exit()


def main() -> None:
    SnakTUI().run()
