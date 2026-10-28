"""Core data types for SnakTUI, independent of the UI layer."""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum


class Direction(Enum):
    """The four cardinal directions the snake can travel."""

    UP = (0, -1)
    DOWN = (0, 1)
    LEFT = (-1, 0)
    RIGHT = (1, 0)

    @property
    def delta(self) -> tuple[int, int]:
        return self.value

    @property
    def opposite(self) -> Direction:
        return _OPPOSITES[self]


_OPPOSITES = {
    Direction.UP: Direction.DOWN,
    Direction.DOWN: Direction.UP,
    Direction.LEFT: Direction.RIGHT,
    Direction.RIGHT: Direction.LEFT,
}


@dataclass(frozen=True, slots=True)
class Point:
    """An immutable grid coordinate."""

    x: int
    y: int

    def moved(self, direction: Direction) -> Point:
        dx, dy = direction.delta
        return Point(self.x + dx, self.y + dy)

    def wrapped(self, width: int, height: int) -> Point:
        return Point(self.x % width, self.y % height)

    def manhattan(self, other: Point) -> int:
        return abs(self.x - other.x) + abs(self.y - other.y)


class FoodKind(Enum):
    """Every edible (and every power-up) that can appear on the arena."""

    APPLE = "apple"
    GOLDEN = "golden"
    SPEED = "speed"
    SLOW = "slow"
    GHOST = "ghost"
    FRENZY = "frenzy"

    @property
    def score(self) -> int:
        return _FOOD_SCORE[self]

    @property
    def duration(self) -> float:
        """How long the food stays on the board (seconds)."""

        return _FOOD_TTL[self]

    @property
    def effect_seconds(self) -> float:
        return _FOOD_EFFECT[self]

    @property
    def is_powerup(self) -> bool:
        return self not in (FoodKind.APPLE, FoodKind.GOLDEN)


_FOOD_SCORE = {
    FoodKind.APPLE: 10,
    FoodKind.GOLDEN: 50,
    FoodKind.SPEED: 15,
    FoodKind.SLOW: 15,
    FoodKind.GHOST: 20,
    FoodKind.FRENZY: 25,
}

_FOOD_TTL = {
    FoodKind.APPLE: 0.0,
    FoodKind.GOLDEN: 9.0,
    FoodKind.SPEED: 9.0,
    FoodKind.SLOW: 9.0,
    FoodKind.GHOST: 9.0,
    FoodKind.FRENZY: 9.0,
}

_FOOD_EFFECT = {
    FoodKind.APPLE: 0.0,
    FoodKind.GOLDEN: 0.0,
    FoodKind.SPEED: 6.0,
    FoodKind.SLOW: 6.0,
    FoodKind.GHOST: 5.0,
    FoodKind.FRENZY: 6.0,
}


@dataclass(slots=True)
class Food:
    """A piece of food currently on the board."""

    kind: FoodKind
    pos: Point
    age: float = 0.0
    ttl: float = 0.0

    @property
    def expired(self) -> bool:
        return self.ttl > 0 and self.age >= self.ttl

    @property
    def remaining(self) -> float:
        if self.ttl <= 0:
            return 0.0
        return max(0.0, self.ttl - self.age)


@dataclass(frozen=True, slots=True)
class Difficulty:
    """A difficulty preset. Speeds are measured in moves per second."""

    key: str
    label: str
    base_speed: float
    speed_step: float
    max_speed: float
    combo_window: float
    start_obstacles: int
    obstacle_every: int


DIFFICULTIES: dict[str, Difficulty] = {
    "chill": Difficulty(
        key="chill",
        label="Chill",
        base_speed=5.0,
        speed_step=0.35,
        max_speed=13.0,
        combo_window=3.6,
        start_obstacles=0,
        obstacle_every=4,
    ),
    "classic": Difficulty(
        key="classic",
        label="Classic",
        base_speed=7.5,
        speed_step=0.5,
        max_speed=17.0,
        combo_window=2.8,
        start_obstacles=0,
        obstacle_every=3,
    ),
    "insane": Difficulty(
        key="insane",
        label="Insane",
        base_speed=10.5,
        speed_step=0.8,
        max_speed=22.0,
        combo_window=2.2,
        start_obstacles=2,
        obstacle_every=2,
    ),
}

DIFFICULTY_ORDER = ("chill", "classic", "insane")


class GameStatus(Enum):
    RUNNING = "running"
    PAUSED = "paused"
    GAME_OVER = "game_over"


class EventKind(Enum):
    EAT = "eat"
    POWER = "power"
    GOLDEN = "golden"
    EXPIRE = "expire"
    LEVEL = "level"
    DEATH = "death"
    CLEAR = "clear"


@dataclass(frozen=True, slots=True)
class GameConfig:
    """Everything that configures a single run."""

    width: int = 40
    height: int = 18
    wrap: bool = False
    obstacles: bool = True
    grid: bool = True
    difficulty: Difficulty = DIFFICULTIES["classic"]
    theme: str = "neon"
    sound: bool = True


@dataclass(slots=True)
class Particle:
    """A short lived spark rendered on the arena."""

    x: float
    y: float
    vx: float
    vy: float
    life: float
    max_life: float
    char: str
    role: str


@dataclass(slots=True)
class Popup:
    """Floating score text that drifts upward."""

    x: float
    y: float
    text: str
    life: float
    max_life: float
    role: str


@dataclass(frozen=True, slots=True)
class RunStats:
    """Snapshot of a finished run, shown on the game over screen."""

    score: int
    best: int
    level: int
    length: int
    food_eaten: int
    max_combo: int
    elapsed: float
    reason: str
    difficulty: str
    theme: str
    new_high_score: bool = False
