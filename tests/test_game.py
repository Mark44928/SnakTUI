from __future__ import annotations

import random

import pytest

from snaktui.game import LEVEL_EVERY, Game
from snaktui.models import (
    DIFFICULTIES,
    Direction,
    EventKind,
    Food,
    FoodKind,
    GameConfig,
    GameStatus,
    Point,
)


def make_game(**overrides: object) -> Game:
    values: dict[str, object] = {
        "width": 20,
        "height": 12,
        "wrap": False,
        "obstacles": False,
        "grid": False,
        "difficulty": DIFFICULTIES["classic"],
    }
    values.update(overrides)
    game = Game(GameConfig(**values), rng=random.Random(7))
    game.ready_timer = 0
    return game


def place_snake(game: Game, head: Point, direction: Direction = Direction.RIGHT) -> None:
    game.snake = [head, Point(head.x - 1, head.y), Point(head.x - 2, head.y)]
    game.direction = direction


def test_initial_state() -> None:
    game = make_game()
    assert game.length == 4
    assert game.score == 0
    assert game.level == 1
    assert game.status is GameStatus.RUNNING
    assert game.food is not None
    assert game.head == Point(10, 6)


def test_moves_after_ready_countdown() -> None:
    game = make_game()
    game.ready_timer = 0.5
    game.update(0.2)
    assert game.head == Point(10, 6)

    game.ready_timer = 0
    game.update(0.2)
    assert game.head == Point(11, 6)


def test_direct_reverse_is_rejected() -> None:
    game = make_game()
    assert game.turn(Direction.LEFT) is False
    assert game.turn(Direction.UP) is True
    assert game.turn(Direction.DOWN) is False


def test_turn_queue_is_limited_and_ordered() -> None:
    game = make_game()
    assert game.turn(Direction.UP) is True
    assert game.turn(Direction.LEFT) is True
    assert game.turn(Direction.DOWN) is True
    assert game.turn(Direction.RIGHT) is False


def test_wall_collision_ends_run() -> None:
    game = make_game()
    place_snake(game, Point(19, 6))
    game.food = Food(FoodKind.APPLE, Point(2, 2))
    game.update(0.2)
    assert game.game_over is True
    assert game.death_reason == "You slammed into the wall"


def test_wrap_moves_through_the_edge() -> None:
    game = make_game(wrap=True)
    place_snake(game, Point(19, 6))
    game.food = Food(FoodKind.APPLE, Point(2, 2))
    game.update(0.2)
    assert game.head == Point(0, 6)
    assert game.running is True


def test_ghost_effect_phases_through_the_wall() -> None:
    game = make_game()
    place_snake(game, Point(19, 6))
    game.food = Food(FoodKind.APPLE, Point(2, 2))
    game.effects[FoodKind.GHOST] = 3.0
    game.update(0.2)
    assert game.head == Point(0, 6)
    assert game.running is True


def test_obstacle_collision_ends_run() -> None:
    game = make_game()
    place_snake(game, Point(5, 5))
    game.food = Food(FoodKind.APPLE, Point(2, 2))
    game.obstacles = {Point(6, 5)}
    game.update(0.2)
    assert game.game_over is True
    assert game.death_reason == "You crashed into a hazard"


def test_self_collision_ends_run() -> None:
    game = make_game()
    game.snake = [
        Point(5, 5),
        Point(4, 5),
        Point(4, 6),
        Point(5, 6),
        Point(6, 6),
        Point(6, 5),
    ]
    game.direction = Direction.DOWN
    game.food = Food(FoodKind.APPLE, Point(2, 2))
    game.update(0.2)
    assert game.game_over is True
    assert game.death_reason == "You ate your own tail"


def test_eating_an_apple_grows_and_scores() -> None:
    game = make_game()
    place_snake(game, Point(5, 5))
    game.food = Food(FoodKind.APPLE, Point(6, 5))
    game.update(0.2)

    assert game.head == Point(6, 5)
    assert game.length == 4
    assert game.score == 10
    assert game.apples_eaten == 1
    assert game.food_eaten == 1
    assert game.combo == 1
    assert game.food is not None
    assert game.food.pos not in set(game.snake)


def test_combo_multiplier_stacks() -> None:
    game = make_game()
    place_snake(game, Point(5, 5))
    game.food = Food(FoodKind.APPLE, Point(6, 5))
    game.update(0.2)

    game.food = Food(FoodKind.APPLE, Point(7, 5))
    game.update(0.07)

    assert game.score == 30
    assert game.multiplier == 2
    assert game.max_combo == 2


def test_combo_resets_when_window_expires() -> None:
    game = make_game()
    game.combo = 4
    game.combo_timer = 0.05
    game.update(0.1)
    assert game.combo == 0


def test_golden_food_is_worth_fifty() -> None:
    game = make_game()
    place_snake(game, Point(5, 5))
    game.food = Food(FoodKind.APPLE, Point(2, 2))
    game.special = Food(FoodKind.GOLDEN, Point(6, 5), ttl=9.0)
    game.update(0.2)

    assert game.score == 50
    assert game.special is None
    assert EventKind.GOLDEN in game.drain_events()


def test_speed_powerup_changes_speed() -> None:
    game = make_game()
    base = game.current_speed
    place_snake(game, Point(5, 5))
    game.food = Food(FoodKind.APPLE, Point(2, 2))
    game.special = Food(FoodKind.SPEED, Point(6, 5), ttl=9.0)
    game.update(0.2)

    assert game.effect_remaining(FoodKind.SPEED) == pytest.approx(6.0)
    assert game.current_speed > base
    assert EventKind.POWER in game.drain_events()


def test_ghost_powerup_is_applied() -> None:
    game = make_game()
    place_snake(game, Point(5, 5))
    game.food = Food(FoodKind.APPLE, Point(2, 2))
    game.special = Food(FoodKind.GHOST, Point(6, 5), ttl=9.0)
    game.update(0.2)
    assert game.effect_remaining(FoodKind.GHOST) == pytest.approx(5.0)


def test_special_food_expires() -> None:
    game = make_game()
    game.special = Food(FoodKind.GOLDEN, Point(2, 2), ttl=1.0, age=0.9)
    game.update(0.2)
    assert game.special is None
    assert EventKind.EXPIRE in game.drain_events()


def test_level_up_every_four_apples() -> None:
    game = make_game()
    place_snake(game, Point(5, 5))
    game.apples_eaten = LEVEL_EVERY - 1
    game.food = Food(FoodKind.APPLE, Point(6, 5))
    game.update(0.2)

    assert game.level == 2
    assert EventKind.LEVEL in game.drain_events()


def test_pause_freezes_the_snake() -> None:
    game = make_game()
    place_snake(game, Point(5, 5))
    game.food = Food(FoodKind.APPLE, Point(2, 2))
    head = game.head

    game.toggle_pause()
    game.update(1.0)
    assert game.status is GameStatus.PAUSED
    assert game.head == head

    game.toggle_pause()
    game.update(0.2)
    assert game.status is GameStatus.RUNNING
    assert game.head != head


def test_spawns_avoid_occupied_cells() -> None:
    game = make_game()
    game.obstacles = {Point(1, 1), Point(2, 2)}
    occupied = set(game.snake) | game.obstacles
    if game.food is not None:
        occupied.add(game.food.pos)
    free = set(game._free_cells())
    assert free
    assert free.isdisjoint(occupied)


def test_stats_snapshot() -> None:
    game = make_game()
    game.score = 123
    game.level = 3
    game.food_eaten = 9
    game.max_combo = 4
    game.elapsed = 42.0
    game.death_reason = "done"

    stats = game.stats(best=500, new_high_score=True)
    assert stats.score == 123
    assert stats.best == 500
    assert stats.level == 3
    assert stats.food_eaten == 9
    assert stats.max_combo == 4
    assert stats.elapsed == 42.0
    assert stats.reason == "done"
    assert stats.new_high_score is True


def test_frenzy_doubles_score_while_active() -> None:
    game = make_game()
    place_snake(game, Point(5, 5))
    game.food = Food(FoodKind.APPLE, Point(2, 2))
    game.special = Food(FoodKind.FRENZY, Point(6, 5), ttl=9.0)
    game.update(0.2)
    assert game.effect_remaining(FoodKind.FRENZY) == pytest.approx(6.0)
    assert EventKind.POWER in game.drain_events()
    assert game.score == 25  # frenzy itself is not doubled

    # a normal apple eaten during frenzy is worth double (combo 2 -> x2)
    game.snake = [Point(7, 5), Point(6, 5), Point(5, 5)]
    game.direction = Direction.RIGHT
    game.food = Food(FoodKind.APPLE, Point(8, 5))
    game.update(0.2)
    assert game.score == 25 + 40


def test_frenzy_expires_and_stops_doubling() -> None:
    game = make_game()
    place_snake(game, Point(5, 5))
    game.food = Food(FoodKind.APPLE, Point(2, 2))
    game.special = Food(FoodKind.FRENZY, Point(6, 5), ttl=9.0)
    game.update(0.2)
    assert game.score == 25

    # let frenzy lapse, then a plain apple scores without doubling
    game.effects[FoodKind.FRENZY] = 0.01
    game.snake = [Point(7, 5), Point(6, 5), Point(5, 5)]
    game.direction = Direction.RIGHT
    game.food = Food(FoodKind.APPLE, Point(8, 5))
    game.update(0.2)
    assert game.effect_remaining(FoodKind.FRENZY) == 0.0
    assert game.score == 25 + 20
