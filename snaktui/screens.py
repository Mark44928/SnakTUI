"""All Textual screens for SnakTUI."""

from __future__ import annotations

import contextlib
import math
import time
from dataclasses import replace
from typing import TYPE_CHECKING

from rich.text import Text
from textual import events
from textual.app import ComposeResult
from textual.containers import Container, Horizontal, ScrollableContainer, Vertical
from textual.screen import ModalScreen, Screen
from textual.widgets import Static

from .board import SnakeBoard
from .game import LEVEL_EVERY, Game
from .models import (
    DIFFICULTIES,
    DIFFICULTY_ORDER,
    Direction,
    EventKind,
    FoodKind,
    GameConfig,
    GameStatus,
    RunStats,
)
from .storage import Store
from .theme import THEME_ORDER, Palette, blend, darken

if TYPE_CHECKING:
    from .app import SnakTUI

MENU_WIDTH = 42
LOGO = (
    " █▀▀ █▄ █ ▄▀█ █▄▀ ▀█▀ █ █ █",
    " ▄██ █ ▀█ █▀█ █ █  █  █▀█ █",
)
EFFECT_ORDER = (FoodKind.SPEED, FoodKind.SLOW, FoodKind.GHOST, FoodKind.FRENZY)
EFFECT_GLYPHS = {
    FoodKind.SPEED: "▲",
    FoodKind.SLOW: "◈",
    FoodKind.GHOST: "○",
    FoodKind.FRENZY: "✦",
}
FOOD_GLYPHS_UI = {
    FoodKind.APPLE: "●",
    FoodKind.GOLDEN: "◆",
    FoodKind.SPEED: "▲",
    FoodKind.SLOW: "◈",
    FoodKind.GHOST: "○",
    FoodKind.FRENZY: "✦",
}
FOOD_ROWS = (
    (FoodKind.APPLE, "Apple", "+10", "every run"),
    (FoodKind.GOLDEN, "Golden", "+50", "timed / rare"),
    (FoodKind.SPEED, "Speed", "+15", "boost 6s"),
    (FoodKind.SLOW, "Slow", "+15", "slow-mo 6s"),
    (FoodKind.GHOST, "Ghost", "+20", "phase 5s"),
    (FoodKind.FRENZY, "Frenzy", "+25", "2x pts 6s"),
)


def format_time(seconds: float) -> str:
    minutes = int(seconds) // 60
    secs = int(seconds) % 60
    return f"{minutes:02d}:{secs:02d}"


def app_of(screen: Screen) -> SnakTUI:
    return screen.app  # type: ignore[return-value]


def gradient_text(
    value: str,
    start: str,
    end: str,
    *,
    bold: bool = False,
    offset: float = 0.0,
) -> Text:
    result = Text()
    span = max(1, len(value) - 1)
    for index, char in enumerate(value):
        color = blend(start, end, (index / span + offset) % 1.0)
        result.append(char, style=f"bold {color}" if bold else color)
    return result


def label_value(
    label: str,
    value: str,
    palette: Palette,
    *,
    label_width: int = 7,
) -> Text:
    line = Text()
    line.append(f"{label:<{label_width}}", style=palette.dim)
    line.append(value, style=f"bold {palette.text}")
    return line


class MenuScreen(Screen):
    """Animated main menu."""

    def __init__(self) -> None:
        super().__init__()
        self.index = 0
        self._time = 0.0
        self._timer = None
        self.items: list[tuple[str, str]] = []

    def compose(self) -> ComposeResult:
        with Container(id="menu-root"):
            with Vertical(id="menu-box"):
                yield Static(id="menu-status")
                yield Static(id="menu-logo")
                yield Static(id="menu-tagline")
                yield Static(id="menu-rule")
                yield Static(id="menu-list")
                yield Static(id="menu-footer")

    def on_mount(self) -> None:
        self._refresh_values()
        self._refresh_logo()
        self._refresh_rule()
        self._refresh_list()
        self._timer = self.set_interval(0.09, self._animate)

    def on_unmount(self) -> None:
        if self._timer is not None:
            self._timer.stop()

    # -- rendering ---------------------------------------------------
    def _refresh_values(self) -> None:
        app = app_of(self)
        palette = app.palette
        difficulty = DIFFICULTIES[app.settings.difficulty]
        high = app.store.high_score
        self.items = [
            ("PLAY", ""),
            ("DIFFICULTY", difficulty.label),
            ("THEME", palette.label),
            ("SETTINGS", f"wrap {'on' if app.settings.wrap else 'off'}"),
            ("HIGH SCORES", f"best {high:,}"),
            ("HOW TO PLAY", ""),
            ("QUIT", ""),
        ]

        status = Text()
        status.append("BEST ", style=palette.dim)
        status.append(f"{high:,}", style=f"bold {palette.golden}")
        status.append("   ·   ", style=palette.frame_dim)
        status.append(f"RUNS {len(app.store.scores)}", style=palette.text)
        status.append("   ·   ", style=palette.frame_dim)
        status.append(difficulty.label.upper(), style=f"bold {palette.accent2}")
        status.append("   ·   ", style=palette.frame_dim)
        status.append(palette.label.upper(), style=f"bold {palette.accent}")
        self.query_one("#menu-status", Static).update(status)

        tagline = Text()
        tagline.append("N E O N   S E R P E N T", style=f"bold {palette.accent}")
        tagline.append("   ·   TEXTUAL ARCADE", style=palette.dim)
        self.query_one("#menu-tagline", Static).update(tagline)

        footer = Text()
        footer.append("↑↓  ", style=f"bold {palette.accent2}")
        footer.append("move    ", style=palette.dim)
        footer.append("ENTER  ", style=f"bold {palette.accent2}")
        footer.append("select\n", style=palette.dim)
        footer.append("D  ", style=f"bold {palette.accent2}")
        footer.append("difficulty    ", style=palette.dim)
        footer.append("T  ", style=f"bold {palette.accent2}")
        footer.append("theme    ", style=palette.dim)
        footer.append("Q  ", style=f"bold {palette.accent2}")
        footer.append("quit", style=palette.dim)
        self.query_one("#menu-footer", Static).update(footer)

    def _refresh_logo(self) -> None:
        palette = app_of(self).palette
        logo = Text()
        shimmer = 0.5 + 0.5 * math.sin(self._time * 2.4)
        for row_index, row in enumerate(LOGO):
            if row_index:
                logo.append("\n")
            span = max(1, len(row) - 1)
            for index, char in enumerate(row):
                color = blend(palette.snake_body, palette.accent, index / span)
                color = blend(color, "#ffffff", 0.1 + shimmer * 0.18)
                logo.append(char, style=f"bold {color}")
        self.query_one("#menu-logo", Static).update(logo)

    def _refresh_rule(self) -> None:
        palette = app_of(self).palette
        rule = Text()
        rule.append("◆", style=palette.frame_dim)
        span = MENU_WIDTH - 2
        position = int((span - 3) * abs(math.sin(self._time * 0.9)))
        for index in range(span):
            if position <= index < position + 3:
                color = palette.snake_head if index == position + 2 else palette.snake_body
                if index == position:
                    color = palette.snake_tail
                rule.append("█", style=f"bold {color}")
            else:
                rule.append("─", style=darken(palette.frame, 0.6))
        rule.append("◆", style=palette.frame_dim)
        self.query_one("#menu-rule", Static).update(rule)

    def _refresh_list(self) -> None:
        palette = app_of(self).palette
        lines: list[Text] = []
        label_width = 27
        value_width = 12
        for position, (label, value) in enumerate(self.items):
            selected = position == self.index
            background = blend(palette.bg_a, palette.accent, 0.24 if selected else 0.0)
            if selected:
                marker_style = f"bold {palette.accent} on {background}"
                label_style = f"bold {palette.text} on {background}"
                value_style = f"bold {palette.accent2} on {background}"
            else:
                marker_style = f"{palette.dim} on {background}"
                label_style = f"{palette.dim} on {background}"
                value_style = f"{palette.frame_dim} on {background}"

            line = Text()
            line.append(" ▶ " if selected else "   ", style=marker_style)
            line.append(f"{label:<{label_width}}", style=label_style)
            line.append(f"{value:>{value_width}}", style=value_style)
            lines.append(line)
        body = Text()
        for index, line in enumerate(lines):
            body.append_text(line)
            if index < len(lines) - 1:
                body.append("\n")
        self.query_one("#menu-list", Static).update(body)

    def _animate(self) -> None:
        self._time += 0.09
        self._refresh_logo()
        self._refresh_rule()

    # -- actions -----------------------------------------------------
    def _cycle_difficulty(self, step: int = 1) -> None:
        app = app_of(self)
        order = DIFFICULTY_ORDER
        position = order.index(app.settings.difficulty)
        app.apply_settings(difficulty=order[(position + step) % len(order)])
        self._refresh_values()
        self._refresh_list()

    def _cycle_theme(self, step: int = 1) -> None:
        app = app_of(self)
        order = THEME_ORDER
        position = order.index(app.settings.theme)
        app.apply_settings(theme=order[(position + step) % len(order)])
        self._refresh_values()
        self._refresh_list()
        self._refresh_logo()

    def activate(self) -> None:
        item = self.items[self.index][0]
        if item == "PLAY":
            app_of(self).new_game()
        elif item == "DIFFICULTY":
            self._cycle_difficulty()
        elif item == "THEME":
            self._cycle_theme()
        elif item == "SETTINGS":
            self.app.push_screen(SettingsScreen(app_of(self).store))
        elif item == "HIGH SCORES":
            self.app.push_screen(HighScoresScreen(app_of(self).store))
        elif item == "HOW TO PLAY":
            self.app.push_screen(HelpScreen())
        elif item == "QUIT":
            self.app.exit()

    def on_key(self, event: events.Key) -> None:
        key = event.key
        if key in ("up", "k"):
            self.index = (self.index - 1) % len(self.items)
            self._refresh_list()
        elif key in ("down", "j"):
            self.index = (self.index + 1) % len(self.items)
            self._refresh_list()
        elif key in ("enter", "space"):
            self.activate()
        elif key == "d":
            self._cycle_difficulty()
        elif key == "t":
            self._cycle_theme()
        elif key == "s":
            self.app.push_screen(SettingsScreen(app_of(self).store))
        elif key == "h":
            self.app.push_screen(HelpScreen())
        elif key in ("g", "l"):
            self.app.push_screen(HighScoresScreen(app_of(self).store))
        elif key == "q":
            self.app.exit()
        else:
            return
        event.stop()


class GameScreen(Screen):
    """The playable arena."""

    BINDINGS = [
        ("space", "toggle_pause", "Pause"),
        ("p", "toggle_pause", "Pause"),
        ("escape", "toggle_pause", "Pause"),
        ("q", "quit_to_menu", "Menu"),
        ("r", "restart_run", "Restart"),
        ("m", "toggle_sound", "Sound"),
    ]

    def __init__(self, config: GameConfig, store: Store) -> None:
        super().__init__()
        self.config = config
        self.store = store
        self.game = Game(config)
        self.palette: Palette | None = None
        self._timer = None
        self._last_tick = 0.0
        self._hud_acc = 0.0
        self._finish_at: float | None = None
        self._finished = False
        self._board: SnakeBoard | None = None

    def compose(self) -> ComposeResult:
        app = app_of(self)
        palette = app.palette
        self.palette = palette
        show_sidebar = (self.app.size.width or 80) >= 76
        yield Static(id="hud")
        with Horizontal(id="game-body"):
            board = SnakeBoard(self.game, palette)
            self._board = board
            yield board
            if show_sidebar:
                sidebar = Static(id="sidebar")
                sidebar.styles.height = self.game.height + 2
                yield sidebar
        yield Static(id="hint")

    def on_mount(self) -> None:
        self._last_tick = time.monotonic()
        self._update_hud(force=True)
        self._timer = self.set_interval(1 / 20, self._tick)
        if self.app.size.width < 34 or self.app.size.height < 14:
            self.app.notify("Terminal is small — resize for the full arena", timeout=3)

    def on_unmount(self) -> None:
        if self._timer is not None:
            self._timer.stop()

    # -- main loop ---------------------------------------------------
    def _tick(self) -> None:
        now = time.monotonic()
        dt = min(0.1, max(0.0, now - self._last_tick))
        self._last_tick = now
        game = self.game
        if game.paused:
            return

        game.update(dt)
        events = game.drain_events()
        for event in events:
            self._handle_event(event)
        if self._board is not None:
            self._board.refresh()

        self._hud_acc += dt
        if self._hud_acc >= 0.12:
            self._hud_acc = 0.0
            self._update_hud()

        if game.game_over and self._finish_at is None:
            self._finish_at = now + 1.05
        if self._finish_at is not None and now >= self._finish_at:
            self._finish_run()

    def _handle_event(self, event: object) -> None:
        if not self.config.sound or not isinstance(event, EventKind):
            return
        if event in (EventKind.GOLDEN, EventKind.POWER, EventKind.LEVEL, EventKind.DEATH):
            with contextlib.suppress(Exception):
                self.app.bell()

    def _finish_run(self) -> None:
        if self._finished:
            return
        self._finished = True
        if self._timer is not None:
            self._timer.stop()
        stats = app_of(self).complete_run(self.game)
        self.app.switch_screen(GameOverScreen(stats))

    # -- rendering ---------------------------------------------------
    def _update_hud(self, force: bool = False) -> None:
        if not self.is_mounted:
            return
        palette = self.palette or app_of(self).palette
        width = self.app.size.width or 80
        game = self.game
        hud = self.query_one("#hud", Static)
        sidebar = self.query_optional_one("#sidebar")
        hint = self.query_one("#hint", Static)

        line_one = Text()
        if width >= 64:
            line_one.append("◆ ", style=f"bold {palette.accent}")
            line_one.append("SNAKTUI", style=f"bold {palette.accent2}")
            line_one.append("   ", style="")
        stats = [
            ("SCORE", f"{game.score:,}"),
            ("BEST", f"{max(self.store.high_score, game.score):,}"),
            ("LVL", f"{game.level:02d}"),
            ("LEN", f"{game.length:02d}"),
        ]
        if width >= 72:
            stats.append(("TIME", format_time(game.elapsed)))
        for label, value in stats:
            line_one.append(f"{label} ", style=palette.dim)
            line_one.append(value, style=f"bold {palette.text}")
            if label == "BEST" and game.score > self.store.high_score and game.score > 0:
                line_one.append(" ★", style=f"bold {palette.golden}")
            line_one.append("  ", style="")

        line_two = Text()
        if game.combo >= 2:
            line_two.append(f"COMBO x{game.multiplier} ", style=f"bold {palette.accent}")
            line_two.append_text(self._combo_bar(palette, width=10))
            line_two.append("  ", style="")
        for kind in EFFECT_ORDER:
            remaining = game.effect_remaining(kind)
            if remaining > 0:
                line_two.append(EFFECT_GLYPHS[kind] + " ", style=f"bold {palette.role(kind.value)}")
                line_two.append(f"{remaining:3.1f}s  ", style=palette.role(kind.value))
        flags = []
        flags.append("WRAP" if self.config.wrap else "WALLS")
        if self.config.obstacles:
            flags.append("HAZ")
        if not self.app.settings.sound:
            flags.append("MUTE")
        if game.is_ready:
            flags.append("READY")
        if game.paused:
            flags.append("PAUSED")
        line_two.append(" · ".join(flags) + "   ", style=palette.frame_dim)
        if game.combo < 2 and not game.paused and not game.game_over:
            line_two.append("eat fast for combos", style=palette.dim)

        hud.update(Text.assemble(line_one, "\n", line_two))

        if sidebar is not None:
            sidebar.update(self._sidebar_text(palette))

        hint_text = Text()
        if width < 60:
            hints = [
                ("WASD", "move"),
                ("SPACE", "pause"),
                ("Q", "menu"),
            ]
        elif width < 90:
            hints = [
                ("↑↓←→", "move"),
                ("SPACE", "pause"),
                ("Q", "menu"),
                ("M", "sound"),
            ]
        else:
            hints = [
                ("↑↓←→/WASD", "move"),
                ("SPACE", "pause"),
                ("R", "restart"),
                ("Q", "menu"),
                ("M", "sound"),
            ]
        for index, (key, action) in enumerate(hints):
            hint_text.append(key + "  ", style=f"bold {palette.accent2}")
            hint_text.append(action, style=palette.dim)
            if index < len(hints) - 1:
                hint_text.append("   ·   ", style=palette.frame_dim)
        hint.update(Text.assemble(hint_text))

    def _combo_bar(self, palette: Palette, width: int) -> Text:
        game = self.game
        window = max(0.001, game.difficulty.combo_window)
        ratio = max(0.0, min(1.0, game.combo_timer / window))
        filled = round(ratio * width)
        bar = Text()
        bar.append("█" * filled, style=f"bold {palette.accent}")
        bar.append("░" * (width - filled), style=palette.frame_dim)
        return bar

    def _sidebar_text(self, palette: Palette) -> Text:
        game = self.game
        best = max(self.store.high_score, game.score)
        text = Text()
        text.append("◆ RUN STATE\n", style=f"bold {palette.accent}")
        for label, value in (
            ("SCORE", f"{game.score:,}"),
            ("BEST", f"{best:,}"),
            ("LEVEL", f"{game.level}  next {game.apples_to_next_level}/{LEVEL_EVERY}"),
            ("BODY", f"{game.length}"),
            ("TIME", format_time(game.elapsed)),
        ):
            text.append_text(label_value(label, value, palette))
            if label == "BEST" and game.score > self.store.high_score and game.score > 0:
                text.append(" ★", style=f"bold {palette.golden}")
            text.append("\n")

        text.append("\n")
        text.append("COMBO  ", style=f"bold {palette.accent}")
        if game.combo >= 2:
            text.append(f"x{game.multiplier}", style=f"bold {palette.accent}")
        else:
            text.append("—", style=palette.dim)
        text.append("\n")
        text.append_text(self._combo_bar(palette, width=16))
        text.append("\n\n")

        text.append("BOOSTS\n", style=f"bold {palette.accent}")
        active = False
        for kind in EFFECT_ORDER:
            remaining = game.effect_remaining(kind)
            if remaining > 0:
                active = True
                text.append(EFFECT_GLYPHS[kind] + " ", style=f"bold {palette.role(kind.value)}")
                text.append(f"{kind.value:<6}", style=palette.text)
                text.append(f"{remaining:4.1f}s\n", style=palette.role(kind.value))
        if not active:
            text.append("— none —\n", style=palette.dim)

        text.append("\n")
        text.append("MODE  ", style=f"bold {palette.accent}")
        mode = "wrap" if self.config.wrap else "walls"
        mode += "·haz" if self.config.obstacles else "·safe"
        mode += "·grid" if self.config.grid else ""
        text.append(mode + "\n", style=palette.text)
        text.append("SOUND ", style=f"bold {palette.accent}")
        text.append(
            "on\n" if self.app.settings.sound else "muted\n",
            style=palette.text,
        )
        text.append("FOOD  ", style=f"bold {palette.accent}")
        for kind in (
            FoodKind.APPLE,
            FoodKind.GOLDEN,
            FoodKind.SPEED,
            FoodKind.SLOW,
            FoodKind.GHOST,
            FoodKind.FRENZY,
        ):
            text.append(FOOD_GLYPHS_UI[kind], style=f"bold {palette.role(kind.value)}")
        text.append("▓", style=f"bold {palette.obstacle}")

        if game.height >= 20:
            tip = "chain apples"
            if game.effect_remaining(FoodKind.GHOST) > 0:
                tip = "phase walls"
            elif game.effect_remaining(FoodKind.FRENZY) > 0:
                tip = "double points"
            elif game.effect_remaining(FoodKind.SPEED) > 0:
                tip = "fast tempo"
            elif game.effect_remaining(FoodKind.SLOW) > 0:
                tip = "easy turns"
            text.append("\n\n")
            text.append("TIP  ", style=f"bold {palette.accent}")
            text.append(tip, style=palette.dim)
        return text

    def query_optional_one(self, selector: str) -> Static | None:
        try:
            return self.query_one(selector, Static)
        except Exception:
            return None

    # -- input & actions --------------------------------------------
    def on_key(self, event: events.Key) -> None:
        mapping = {
            "up": Direction.UP,
            "w": Direction.UP,
            "down": Direction.DOWN,
            "s": Direction.DOWN,
            "left": Direction.LEFT,
            "a": Direction.LEFT,
            "right": Direction.RIGHT,
            "d": Direction.RIGHT,
        }
        direction = mapping.get(event.key)
        if direction is not None:
            self.game.turn(direction)
            event.stop()

    def action_toggle_pause(self) -> None:
        status = self.game.toggle_pause()
        self._update_hud(force=True)
        if self._board is not None:
            self._board.refresh()
        if status is GameStatus.PAUSED:
            self._last_tick = time.monotonic()

    def action_quit_to_menu(self) -> None:
        app_of(self).show_menu()

    def action_restart_run(self) -> None:
        app_of(self).new_game()

    def action_toggle_sound(self) -> None:
        app = app_of(self)
        app.apply_settings(sound=not app.settings.sound)
        self.config = replace(self.config, sound=app.settings.sound)
        self._update_hud(force=True)


class GameOverScreen(Screen):
    """Results after a run ends."""

    def __init__(self, stats: RunStats) -> None:
        super().__init__()
        self.stats = stats
        self.index = 0

    def compose(self) -> ComposeResult:
        palette = app_of(self).palette
        with Container(classes="modal-root"):
            with Vertical(classes="modal-box gameover-box"):
                yield Static(id="gameover-title")
                yield Static(id="gameover-reason")
                yield Static(id="gameover-stats")
                yield Static(id="gameover-actions")
                yield Static(id="gameover-hint")
        self._palette = palette

    def on_mount(self) -> None:
        self._refresh()

    def _refresh(self) -> None:
        palette = app_of(self).palette
        stats = self.stats
        if stats.new_high_score:
            title = gradient_text("★  NEW HIGH SCORE  ★", palette.golden, palette.apple, bold=True)
        else:
            title = gradient_text("G A M E   O V E R", palette.danger, palette.accent, bold=True)
        self.query_one("#gameover-title", Static).update(title)

        reason = Text(stats.reason, style=palette.dim)
        self.query_one("#gameover-reason", Static).update(reason)

        body = Text()
        rows = (
            ("SCORE", f"{stats.score:,}"),
            ("PERSONAL BEST", f"{stats.best:,}"),
            ("LEVEL", str(stats.level)),
            ("LENGTH", str(stats.length)),
            ("FOOD EATEN", str(stats.food_eaten)),
            ("MAX COMBO", f"x{stats.max_combo}"),
            ("TIME", format_time(stats.elapsed)),
            ("DIFFICULTY", stats.difficulty),
        )
        width = 22
        for label, value in rows:
            body.append(f"{label:<14}", style=palette.dim)
            body.append(f"{value:>{width - 14}}", style=f"bold {palette.text}")
            body.append("\n")
        self.query_one("#gameover-stats", Static).update(body)

        actions = ["PLAY AGAIN", "HIGH SCORES", "MAIN MENU"]
        listing = Text()
        for position, label in enumerate(actions):
            selected = position == self.index
            if selected:
                background = blend(palette.bg_a, palette.accent, 0.24)
                line_style = f"bold {palette.text} on {background}"
                marker_style = f"bold {palette.accent} on {background}"
                prefix = " ▶ "
            else:
                line_style = palette.dim
                marker_style = palette.frame_dim
                background = palette.bg_a
                prefix = "   "
            listing.append(prefix, style=marker_style)
            listing.append(f"{label:<24}", style=line_style)
            listing.append(
                " ",
                style=f"on {background}" if selected else "",
            )
            listing.append("\n", style=line_style)
        self.query_one("#gameover-actions", Static).update(listing)

        hint = Text()
        hint.append("↑↓  ", style=f"bold {palette.accent2}")
        hint.append("choose   ", style=palette.dim)
        hint.append("ENTER  ", style=f"bold {palette.accent2}")
        hint.append("select   ", style=palette.dim)
        hint.append("R  ", style=f"bold {palette.accent2}")
        hint.append("replay   ", style=palette.dim)
        hint.append("M  ", style=f"bold {palette.accent2}")
        hint.append("menu", style=palette.dim)
        self.query_one("#gameover-hint", Static).update(hint)

    def activate(self) -> None:
        app = app_of(self)
        if self.index == 0:
            app.new_game()
        elif self.index == 1:
            self.app.push_screen(HighScoresScreen(app.store))
        else:
            app.show_menu()

    def on_key(self, event: events.Key) -> None:
        key = event.key
        if key in ("up", "k"):
            self.index = (self.index - 1) % 3
            self._refresh()
        elif key in ("down", "j"):
            self.index = (self.index + 1) % 3
            self._refresh()
        elif key in ("enter", "space"):
            self.activate()
        elif key == "r":
            app_of(self).new_game()
        elif key in ("m", "q", "escape"):
            app_of(self).show_menu()
        elif key == "l":
            self.app.push_screen(HighScoresScreen(app_of(self).store))
        else:
            return
        event.stop()


class SettingsScreen(ModalScreen):
    """Live settings editor."""

    def __init__(self, store: Store) -> None:
        super().__init__()
        self.store = store
        self.index = 0
        self.message = ""

    def compose(self) -> ComposeResult:
        with Container(classes="modal-root"):
            with Vertical(classes="modal-box settings-box"):
                yield Static(id="settings-title")
                yield Static(id="settings-list")
                yield Static(id="settings-message")
                yield Static(id="settings-hint")

    def on_mount(self) -> None:
        self._refresh()

    def _options(self) -> list[tuple[str, str]]:
        settings = app_of(self).settings
        palette = app_of(self).palette
        difficulty = DIFFICULTIES[settings.difficulty]
        return [
            ("Theme", palette.label),
            ("Difficulty", difficulty.label),
            ("Wrap walls", "on" if settings.wrap else "off"),
            ("Hazards", "on" if settings.obstacles else "off"),
            ("Grid", "on" if settings.grid else "off"),
            ("Sound", "on" if settings.sound else "off"),
            ("Reset high scores", ""),
            ("Back", ""),
        ]

    def _refresh(self) -> None:
        palette = app_of(self).palette
        title = Text()
        title.append("◆ ", style=f"bold {palette.accent}")
        title.append("SETTINGS", style=f"bold {palette.text}")
        self.query_one("#settings-title", Static).update(title)

        listing = Text()
        for position, (label, value) in enumerate(self._options()):
            selected = position == self.index
            if selected:
                background = blend(palette.bg_a, palette.accent, 0.24)
                label_style = f"bold {palette.text} on {background}"
                value_style = f"bold {palette.accent2} on {background}"
                marker_style = f"bold {palette.accent} on {background}"
                marker = " ▶ "
            else:
                label_style = palette.danger if label.startswith("Reset") else palette.dim
                value_style = palette.frame_dim
                marker_style = palette.frame_dim
                marker = "   "
            listing.append(marker, style=marker_style)
            listing.append(f"{label:<22}", style=label_style)
            listing.append(f"{value:<10}", style=value_style)
            listing.append(
                " " * 3,
                style=f"on {background}" if selected else "",
            )
            listing.append("\n", style=value_style)
        self.query_one("#settings-list", Static).update(listing)

        message = Text(self.message, style=palette.golden)
        self.query_one("#settings-message", Static).update(message)

        hint = Text()
        for key, action in (
            ("↑↓  ", "move"),
            ("←→  ", "change"),
            ("ENTER  ", "toggle"),
            ("ESC  ", "back"),
        ):
            hint.append(key, style=f"bold {palette.accent2}")
            hint.append(f"{action}   ", style=palette.dim)
        self.query_one("#settings-hint", Static).update(hint)

    def _change(self, step: int) -> None:
        app = app_of(self)
        label = self._options()[self.index][0]
        self.message = ""
        if label == "Theme":
            order = THEME_ORDER
            position = order.index(app.settings.theme)
            app.apply_settings(theme=order[(position + step) % len(order)])
        elif label == "Difficulty":
            order = DIFFICULTY_ORDER
            position = order.index(app.settings.difficulty)
            app.apply_settings(difficulty=order[(position + step) % len(order)])
        elif label == "Wrap walls":
            app.apply_settings(wrap=not app.settings.wrap)
        elif label == "Hazards":
            app.apply_settings(obstacles=not app.settings.obstacles)
        elif label == "Grid":
            app.apply_settings(grid=not app.settings.grid)
        elif label == "Sound":
            app.apply_settings(sound=not app.settings.sound)
        elif label == "Reset high scores":
            app.store.reset_scores()
            self.message = "High scores cleared."
        self._refresh()

    def activate(self) -> None:
        label = self._options()[self.index][0]
        if label == "Back":
            self.dismiss()
        elif label in ("Reset high scores", "Wrap walls", "Hazards", "Grid", "Sound"):
            self._change(1)
        else:
            self._change(1)

    def on_key(self, event: events.Key) -> None:
        key = event.key
        if key in ("up", "k"):
            self.index = (self.index - 1) % len(self._options())
            self.message = ""
            self._refresh()
        elif key in ("down", "j"):
            self.index = (self.index + 1) % len(self._options())
            self.message = ""
            self._refresh()
        elif key in ("left", "h"):
            self._change(-1)
        elif key in ("right", "l"):
            self._change(1)
        elif key in ("enter", "space"):
            self.activate()
        elif key in ("escape", "backspace", "q"):
            self.dismiss()
        else:
            return
        event.stop()


class HighScoresScreen(ModalScreen):
    """Local leaderboard."""

    def __init__(self, store: Store) -> None:
        super().__init__()
        self.store = store

    def compose(self) -> ComposeResult:
        with Container(classes="modal-root"):
            with Vertical(classes="modal-box scores-box"):
                yield Static(id="scores-title")
                yield Static(id="scores-table")
                yield Static(id="scores-hint")

    def on_mount(self) -> None:
        palette = app_of(self).palette
        title = Text()
        title.append("★ ", style=f"bold {palette.golden}")
        title.append("HALL OF FAME", style=f"bold {palette.text}")
        self.query_one("#scores-title", Static).update(title)
        self._render_table()

    def _render_table(self) -> None:
        palette = app_of(self).palette
        scores = self.store.scores
        table = Text()
        if not scores:
            table.append("\n  No runs yet — the arena awaits.\n", style=palette.dim)
            table.append("  Play a run and claim the top spot.\n", style=palette.frame_dim)
        else:
            table.append(
                f"{'#':<3}{'SCORE':>8}  {'LVL':>3}  {'LEN':>3}  {'MODE':<8}  DATE\n",
                style=f"bold {palette.accent}",
            )
            for rank, entry in enumerate(scores, start=1):
                table.append(f"{rank:<3}", style=palette.dim)
                table.append(f"{entry.score:>8,}", style=f"bold {palette.text}")
                table.append(f"  {entry.level:>3}", style=palette.text)
                table.append(f"  {entry.length:>3}", style=palette.text)
                table.append(f"  {entry.difficulty[:8]:<8}", style=palette.accent2)
                table.append(f"  {entry.date}\n", style=palette.dim)
        self.query_one("#scores-table", Static).update(table)
        hint = Text("ESC / Q  back", style=palette.dim)
        self.query_one("#scores-hint", Static).update(hint)

    def on_key(self, event: events.Key) -> None:
        if event.key in ("escape", "q", "enter", "space", "backspace"):
            self.dismiss()
            event.stop()


class HelpScreen(ModalScreen):
    """Controls, food and scoring reference."""

    def compose(self) -> ComposeResult:
        with Container(classes="modal-root"):
            with Vertical(classes="modal-box tall"):
                yield Static(id="help-title")
                with ScrollableContainer(id="help-scroll"):
                    yield Static(id="help-body")
                yield Static(id="help-hint")

    def on_mount(self) -> None:
        palette = app_of(self).palette
        title = Text()
        title.append("? ", style=f"bold {palette.accent}")
        title.append("HOW TO PLAY", style=f"bold {palette.text}")
        self.query_one("#help-title", Static).update(title)

        body = Text()
        body.append("CONTROLS\n", style=f"bold {palette.accent}")
        controls = (
            ("↑ ↓ ← → / WASD", "steer the snake"),
            ("SPACE / P / ESC", "pause & resume"),
            ("R", "restart the run"),
            ("M", "toggle sound"),
            ("Q", "quit to the menu"),
        )
        for keys, description in controls:
            body.append(f"  {keys:<18}", style=f"bold {palette.text}")
            body.append(f"{description}\n", style=palette.dim)

        body.append("\nFOOD & POWER-UPS\n", style=f"bold {palette.accent}")
        for kind, name, score, note in FOOD_ROWS:
            body.append(f"  {FOOD_GLYPHS_UI[kind]} ", style=f"bold {palette.role(kind.value)}")
            body.append(f"{name:<10}", style=f"bold {palette.text}")
            body.append(f"{score:>4}  ", style=palette.accent2)
            body.append(f"{note}\n", style=palette.dim)
        body.append("  ▓ ", style=f"bold {palette.obstacle}")
        body.append(f"{'Hazard':<10}", style=f"bold {palette.text}")
        body.append("       appears as levels climb\n", style=palette.dim)

        body.append("\nSCORING\n", style=f"bold {palette.accent}")
        for line in (
            "Eat fast to build combos — the multiplier caps at x5.",
            "Level up every 4 apples. Golden food is rare and worth +50.",
            "Speed / Slow / Ghost last a few seconds; Ghost phases walls.",
        ):
            body.append(f"  · {line}\n", style=palette.dim)
        self.query_one("#help-body", Static).update(body)

        hint = Text("↑↓ / PgUp PgDn  scroll    ESC / Q  back", style=palette.dim)
        self.query_one("#help-hint", Static).update(hint)

    def on_key(self, event: events.Key) -> None:
        if event.key in ("escape", "q", "enter", "space", "backspace"):
            self.dismiss()
            event.stop()

