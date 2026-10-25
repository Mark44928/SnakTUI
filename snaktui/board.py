"""The arena widget: draws the grid, snake, food, particles and overlays."""

from __future__ import annotations

import math

from rich.text import Text
from textual.widget import Widget

from .game import Game
from .models import FoodKind, Point
from .theme import Palette, blend, darken

EMPTY = (" ", "")
SNAKE_CHAR = "█"
HAZARD_CHAR = "▓"
HALO_CHAR = "·"

FOOD_GLYPHS: dict[FoodKind, str] = {
    FoodKind.APPLE: "●",
    FoodKind.GOLDEN: "◆",
    FoodKind.SPEED: "▲",
    FoodKind.SLOW: "◈",
    FoodKind.GHOST: "○",
}


class SnakeBoard(Widget):
    """Renders the whole arena as a single Rich renderable."""

    can_focus = False

    def __init__(self, game: Game, palette: Palette, **kwargs: object) -> None:
        super().__init__(**kwargs)
        self.game = game
        self.palette = palette
        self.styles.width = game.width + 2
        self.styles.height = game.height + 2
        self.styles.border = ("round", palette.frame)
        self.border_title = "◆ SNAKTUI ARENA ◆"
        self.border_subtitle = f"{game.difficulty.label} · {palette.label}"

    def render(self) -> Text:
        game = self.game
        palette = self.palette
        width, height = game.width, game.height

        flash = min(1.0, game.flash / 0.75)
        grid: list[list[tuple[str, str]]] = []

        for y in range(height):
            row: list[tuple[str, str]] = []
            for x in range(width):
                background = (
                    palette.bg_b if game.config.grid and (x + y) % 2 else palette.bg_a
                )
                if flash > 0:
                    background = blend(background, palette.danger, flash * 0.28)
                row.append((" ", f"on {background}"))
            grid.append(row)

        for obstacle in game.obstacles:
            if 0 <= obstacle.x < width and 0 <= obstacle.y < height:
                grid[obstacle.y][obstacle.x] = (
                    HAZARD_CHAR,
                    f"{palette.obstacle} on {darken(palette.obstacle, 0.65)}",
                )

        snake = game.snake
        length = len(snake)
        for index in range(length - 1, -1, -1):
            point = snake[index]
            if not (0 <= point.x < width and 0 <= point.y < height):
                continue
            color = palette.snake_gradient(index, length)
            if index == 0:
                grid[point.y][point.x] = (SNAKE_CHAR, f"bold {color}")
            else:
                grid[point.y][point.x] = (SNAKE_CHAR, color)

        if snake:
            head = snake[0]
            for dx, dy in ((0, -1), (1, 0), (0, 1), (-1, 0)):
                x, y = head.x + dx, head.y + dy
                if 0 <= x < width and 0 <= y < height and grid[y][x][0] == " ":
                    grid[y][x] = (HALO_CHAR, darken(palette.snake_head, 0.45))

        if game.food is not None:
            self._draw_food(grid, game.food.kind, game.food.pos, game.animation_time, 0.0)
        if game.special is not None:
            self._draw_food(
                grid,
                game.special.kind,
                game.special.pos,
                game.animation_time,
                game.special.remaining,
            )

        for particle in game.particles:
            x, y = round(particle.x), round(particle.y)
            if not (0 <= x < width and 0 <= y < height):
                continue
            ratio = max(0.0, particle.life / particle.max_life)
            color = blend(palette.bg_a, palette.role(particle.role), 0.35 + ratio * 0.65)
            grid[y][x] = (particle.char, f"bold {color}")

        for popup in game.popups:
            y = round(popup.y)
            if not (0 <= y < height):
                continue
            color = blend(palette.role(popup.role), "#ffffff", 0.25)
            for offset, char in enumerate(popup.text):
                x = round(popup.x) + offset
                if 0 <= x < width:
                    grid[y][x] = (char, f"bold {color}")

        if game.paused:
            self._draw_overlay(grid, width, height, "P A U S E D", "SPACE resume · Q quit")
        elif game.is_ready:
            self._draw_overlay(
                grid,
                width,
                height,
                "G E T   R E A D Y",
                "steer with arrows / WASD",
            )

        result = Text()
        for row_index, row in enumerate(grid):
            for char, style in row:
                result.append(char, style=style)
            if row_index < height - 1:
                result.append("\n")
        return result

    # ------------------------------------------------------------------
    # Draw helpers
    # ------------------------------------------------------------------
    def _draw_food(
        self,
        grid: list[list[tuple[str, str]]],
        kind: FoodKind,
        point: Point,
        time: float,
        remaining: float,
    ) -> None:
        palette = self.palette
        if not (0 <= point.x < self.game.width and 0 <= point.y < self.game.height):
            return
        color = palette.role(kind.value)
        glyph = FOOD_GLYPHS[kind]
        pulse = 0.5 + 0.5 * math.sin(time * 6.0)

        if kind is FoodKind.GOLDEN:
            color = blend(palette.golden, "#ffffff", 0.15 + pulse * 0.45)
        if remaining and remaining < 2.5 and int(time * 10) % 2 == 0:
            color = blend(color, palette.bg_a, 0.55)

        background = blend(palette.bg_a, palette.role(kind.value), 0.18 + pulse * 0.08)
        grid[point.y][point.x] = (glyph, f"bold {color} on {background}")

    def _draw_overlay(
        self,
        grid: list[list[tuple[str, str]]],
        width: int,
        height: int,
        title_text: str,
        hint_text: str,
    ) -> None:
        palette = self.palette
        panel_width = max(18, min(width - 2, 36))
        panel_height = 5
        left = (width - panel_width) // 2
        top = (height - panel_height) // 2
        background = darken(palette.bg_a, 0.15)

        for y in range(top, top + panel_height):
            for x in range(left, left + panel_width):
                if 0 <= x < width and 0 <= y < height:
                    grid[y][x] = (" ", f"on {background}")

        border_style = f"bold {palette.golden} on {background}"
        top_edge = "╭" + "─" * (panel_width - 2) + "╮"
        bottom_edge = "╰" + "─" * (panel_width - 2) + "╯"
        self._put_text(grid, left, top, top_edge, border_style)
        self._put_text(grid, left, top + panel_height - 1, bottom_edge, border_style)
        for y in range(top + 1, top + panel_height - 1):
            if 0 <= left < width:
                grid[y][left] = ("│", border_style)
            if 0 <= left + panel_width - 1 < width:
                grid[y][left + panel_width - 1] = ("│", border_style)

        text_x = left + max(1, (panel_width - len(title_text)) // 2)
        hint_x = left + max(1, (panel_width - len(hint_text)) // 2)
        self._put_text(
            grid, text_x, top + 1, title_text, f"bold {palette.golden} on {background}"
        )
        self._put_text(
            grid, hint_x, top + 3, hint_text, f"{palette.dim} on {background}"
        )

    @staticmethod
    def _put_text(
        grid: list[list[tuple[str, str]]],
        x: int,
        y: int,
        text: str,
        style: str,
    ) -> None:
        for offset, char in enumerate(text):
            column = x + offset
            if 0 <= column < len(grid[0]) and 0 <= y < len(grid):
                grid[y][column] = (char, style)
