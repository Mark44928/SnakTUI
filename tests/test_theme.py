from __future__ import annotations

import pytest

from snaktui.models import (
    DIFFICULTIES,
    DIFFICULTY_ORDER,
    Direction,
    FoodKind,
    Point,
)
from snaktui.theme import THEME_ORDER, THEMES, blend, darken, get_palette, lighten


def test_point_movement_and_wrapping() -> None:
    point = Point(3, 4)
    assert point.moved(Direction.UP) == Point(3, 3)
    assert point.moved(Direction.DOWN) == Point(3, 5)
    assert point.moved(Direction.LEFT) == Point(2, 4)
    assert point.moved(Direction.RIGHT) == Point(4, 4)
    assert Point(-1, 5).wrapped(10, 6) == Point(9, 5)
    assert Point(3, 4).manhattan(Point(0, 0)) == 7


def test_direction_opposites() -> None:
    for direction in Direction:
        assert direction.opposite.opposite is direction
        assert direction.opposite is not direction


def test_food_metadata() -> None:
    assert FoodKind.APPLE.score == 10
    assert FoodKind.GOLDEN.score == 50
    assert FoodKind.GHOST.effect_seconds == 5.0
    assert FoodKind.SPEED.is_powerup is True
    assert FoodKind.GOLDEN.is_powerup is False
    assert FoodKind.APPLE.is_powerup is False


def test_difficulty_order_matches_presets() -> None:
    assert set(DIFFICULTY_ORDER) == set(DIFFICULTIES)
    for key in DIFFICULTY_ORDER:
        preset = DIFFICULTIES[key]
        assert preset.key == key
        assert preset.base_speed < preset.max_speed


def test_blend_endpoints_and_midpoint() -> None:
    assert blend("#000000", "#ffffff", 0.0) == "#000000"
    assert blend("#000000", "#ffffff", 1.0) == "#ffffff"
    assert blend("#000000", "#ffffff", 0.5) == "#808080"
    assert darken("#ffffff", 1.0) == "#000000"
    assert lighten("#000000", 1.0) == "#ffffff"


def test_blend_clamps_and_accepts_short_hex() -> None:
    assert blend("#fff", "#000", 2.0) == "#000000"
    assert blend("#fff", "#000", -1.0) == "#ffffff"


def test_invalid_color_raises() -> None:
    with pytest.raises(ValueError):
        blend("red", "#000000", 0.5)


def test_every_theme_is_complete() -> None:
    assert set(THEME_ORDER) == set(THEMES)
    for key in THEME_ORDER:
        palette = get_palette(key)
        assert palette.key == key
        for kind in FoodKind:
            assert palette.role(kind.value).startswith("#")
        assert palette.role("unknown").startswith("#")


def test_get_palette_falls_back_to_neon() -> None:
    assert get_palette("does-not-exist").key == "neon"


def test_snake_gradient_endpoints() -> None:
    palette = get_palette("neon")
    assert palette.snake_gradient(0, 10) == palette.snake_head
    assert palette.snake_gradient(1, 2) == palette.snake_body
    assert palette.snake_gradient(1, 10).startswith("#")
