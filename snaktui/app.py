"""SnakTUI application shell and screen wiring."""

from __future__ import annotations

from textual.app import App
from textual.binding import Binding
from textual.theme import Theme

from .game import Game
from .models import DIFFICULTIES, GameConfig, RunStats
from .screens import GameScreen, MenuScreen
from .storage import Store, make_entry
from .theme import THEMES, Palette, blend, get_palette


def build_theme(palette: Palette) -> Theme:
    """Expose a game palette as a Textual theme.

    Registering each palette lets ``styles.tcss`` chrome (screen background,
    borders, panels) follow the selected theme through CSS variables instead of
    staying frozen on the Neon colors.
    """

    panel = blend(palette.bg_a, palette.frame, 0.12)
    return Theme(
        name=palette.key,
        primary=palette.frame,
        secondary=palette.accent2,
        accent=palette.accent,
        foreground=palette.text,
        background=palette.bg_a,
        surface=palette.bg_b,
        panel=panel,
        dark=True,
        variables={
            "snake-bg-a": palette.bg_a,
            "snake-bg-b": palette.bg_b,
            "snake-frame": palette.frame,
            "snake-frame-dim": palette.frame_dim,
            "snake-accent": palette.accent,
            "snake-accent2": palette.accent2,
            "snake-text": palette.text,
            "snake-dim": palette.dim,
            "snake-danger": palette.danger,
            "snake-golden": palette.golden,
            "snake-panel": panel,
        },
    )


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
        for palette in THEMES.values():
            self.register_theme(build_theme(palette))
        self.theme = self.palette.key
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
        theme_key = changes.get("theme")
        if isinstance(theme_key, str) and theme_key in THEMES:
            self.theme = theme_key  # re-skins CSS chrome, not just Rich text

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
