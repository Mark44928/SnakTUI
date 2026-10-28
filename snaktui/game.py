"""Pure Snake game simulation.

The game is deliberately free of any Textual imports so that it can be
unit-tested and reused. The UI calls :meth:`Game.update` with a delta time and
reads the public state back out.
"""

from __future__ import annotations

import math
import random
from collections import deque

from .models import (
    DIFFICULTIES,
    Direction,
    EventKind,
    Food,
    FoodKind,
    GameConfig,
    GameStatus,
    Particle,
    Point,
    Popup,
    RunStats,
)

LEVEL_EVERY = 4
MAX_PARTICLES = 140
SPECIAL_MIN_GAP = 8.0
SPECIAL_MAX_GAP = 14.0
LEVEL_MIN_GAP = 4.0
LEVEL_MAX_GAP = 9.0


class Game:
    """A single run of Snake."""

    def __init__(self, config: GameConfig, rng: random.Random | None = None) -> None:
        self.config = config
        self.width = max(14, config.width)
        self.height = max(9, config.height)
        self.rng = rng or random.Random()
        self.difficulty = config.difficulty

        center_x, center_y = self.width // 2, self.height // 2
        self.snake: list[Point] = [
            Point(center_x - offset, center_y) for offset in range(4)
        ]
        self.direction = Direction.RIGHT
        self._pending: deque[Direction] = deque()
        self.obstacles: set[Point] = set()
        self.food: Food | None = None
        self.special: Food | None = None

        self.score = 0
        self.apples_eaten = 0
        self.food_eaten = 0
        self.level = 1
        self.combo = 0
        self.combo_timer = 0.0
        self.max_combo = 1
        self.effects: dict[FoodKind, float] = {}
        self.status = GameStatus.RUNNING
        self.elapsed = 0.0
        self.death_reason = ""
        self.events: list[EventKind] = []
        self.ready_timer = 1.2

        self.particles: list[Particle] = []
        self.popups: list[Popup] = []
        self.flash = 0.0
        self._move_acc = 0.0
        self._special_timer = self.rng.uniform(5.0, 8.0)
        self._animation_time = 0.0

        if self.config.obstacles and self.difficulty.start_obstacles:
            self._spawn_obstacles(self.difficulty.start_obstacles)
        self.food = self._spawn_food(FoodKind.APPLE)

    # ------------------------------------------------------------------
    # Read-only properties used by the UI
    # ------------------------------------------------------------------
    @property
    def head(self) -> Point:
        return self.snake[0]

    @property
    def length(self) -> int:
        return len(self.snake)

    @property
    def running(self) -> bool:
        return self.status is GameStatus.RUNNING

    @property
    def paused(self) -> bool:
        return self.status is GameStatus.PAUSED

    @property
    def game_over(self) -> bool:
        return self.status is GameStatus.GAME_OVER

    @property
    def base_speed(self) -> float:
        speed = self.difficulty.base_speed + (self.level - 1) * self.difficulty.speed_step
        return min(self.difficulty.max_speed, speed)

    @property
    def current_speed(self) -> float:
        speed = self.base_speed
        if FoodKind.SPEED in self.effects:
            speed *= 1.45
        if FoodKind.SLOW in self.effects:
            speed *= 0.62
        return max(2.5, min(self.difficulty.max_speed * 1.6, speed))

    @property
    def move_interval(self) -> float:
        return 1.0 / self.current_speed

    @property
    def multiplier(self) -> int:
        return min(5, max(1, self.combo))

    @property
    def apples_to_next_level(self) -> int:
        return LEVEL_EVERY - (self.apples_eaten % LEVEL_EVERY)

    @property
    def animation_time(self) -> float:
        return self._animation_time

    @property
    def is_ready(self) -> bool:
        return self.ready_timer > 0 and self.status is GameStatus.RUNNING

    def effect_remaining(self, kind: FoodKind) -> float:
        return max(0.0, self.effects.get(kind, 0.0))

    # ------------------------------------------------------------------
    # Input
    # ------------------------------------------------------------------
    def turn(self, direction: Direction) -> bool:
        """Queue a turn. Reversing directly into yourself is ignored."""

        if not self.running:
            return False
        last = self._pending[-1] if self._pending else self.direction
        if direction is last or direction is last.opposite:
            return False
        if len(self._pending) >= 3:
            return False
        self._pending.append(direction)
        return True

    def toggle_pause(self) -> GameStatus:
        if self.status is GameStatus.RUNNING:
            self.status = GameStatus.PAUSED
        elif self.status is GameStatus.PAUSED:
            self.status = GameStatus.RUNNING
            self._move_acc = 0.0
        return self.status

    def pause(self) -> None:
        if self.status is GameStatus.RUNNING:
            self.status = GameStatus.PAUSED

    def resume(self) -> None:
        if self.status is GameStatus.PAUSED:
            self.status = GameStatus.RUNNING
            self._move_acc = 0.0

    # ------------------------------------------------------------------
    # Simulation
    # ------------------------------------------------------------------
    def update(self, dt: float) -> None:
        """Advance the simulation by ``dt`` seconds."""

        if dt <= 0:
            return
        dt = min(dt, 0.25)
        self._animate(dt)
        if not self.running:
            return

        if self.ready_timer > 0:
            self.ready_timer = max(0.0, self.ready_timer - dt)
            if self.ready_timer > 0:
                return

        self.elapsed += dt
        self._move_acc += dt
        steps = 0
        while self._move_acc >= self.move_interval and self.running and steps < 4:
            self._move_acc -= self.move_interval
            self._step()
            steps += 1
        if not self.running:
            self._move_acc = 0.0

    def _animate(self, dt: float) -> None:
        self._animation_time += dt
        self.flash = max(0.0, self.flash - dt)

        for particle in self.particles:
            particle.life -= dt
            particle.x += particle.vx * dt
            particle.y += particle.vy * dt
            particle.vy += 4.0 * dt
        self.particles = [p for p in self.particles if p.life > 0]

        for popup in self.popups:
            popup.life -= dt
            popup.y -= 1.1 * dt
        self.popups = [p for p in self.popups if p.life > 0]

        for kind in list(self.effects):
            self.effects[kind] -= dt
            if self.effects[kind] <= 0:
                del self.effects[kind]
                self.events.append(EventKind.EXPIRE)

        if self.combo_timer > 0:
            self.combo_timer = max(0.0, self.combo_timer - dt)
            if self.combo_timer == 0:
                self.combo = 0

        if self.food is not None and self.food.ttl > 0:
            self.food.age += dt
            if self.food.expired:
                self.food = None

        if self.special is not None:
            self.special.age += dt
            if self.special.expired:
                self.special = None
                self.events.append(EventKind.EXPIRE)
                self._special_timer = self.rng.uniform(SPECIAL_MIN_GAP, SPECIAL_MAX_GAP)

        self._special_timer -= dt
        if self.special is None and self._special_timer <= 0 and self.running:
            self._spawn_special()
            self._special_timer = self.rng.uniform(SPECIAL_MIN_GAP, SPECIAL_MAX_GAP)

    def _step(self) -> None:
        if self._pending:
            self.direction = self._pending.popleft()

        ghost = FoodKind.GHOST in self.effects
        new_head = self.head.moved(self.direction)
        wrapped = not (0 <= new_head.x < self.width and 0 <= new_head.y < self.height)

        if self.config.wrap or ghost:
            new_head = new_head.wrapped(self.width, self.height)
        elif wrapped:
            self._die("You slammed into the wall")
            return

        apple = self.food if self.food is not None and self.food.pos == new_head else None
        special = (
            self.special
            if self.special is not None and self.special.pos == new_head
            else None
        )
        growing = apple is not None or special is not None

        if not ghost:
            body = self.snake if growing else self.snake[:-1]
            if new_head in body:
                self._die("You ate your own tail")
                return
            if new_head in self.obstacles:
                self._die("You crashed into a hazard")
                return

        self.snake.insert(0, new_head)
        if not growing:
            self.snake.pop()

        if apple is not None:
            self._consume(apple, new_head)
        if special is not None:
            self._consume(special, new_head)

    def _consume(self, food: Food, head: Point) -> None:
        kind = food.kind
        if kind is FoodKind.APPLE:
            self.apples_eaten += 1
            self.food = None
        else:
            self.special = None
            self._special_timer = self.rng.uniform(SPECIAL_MIN_GAP, SPECIAL_MAX_GAP)

        if self.combo_timer > 0:
            self.combo = min(9, self.combo + 1)
        else:
            self.combo = 1
        self.combo_timer = self.difficulty.combo_window
        self.max_combo = max(self.max_combo, self.multiplier)

        gained = kind.score * self.multiplier
        if FoodKind.FRENZY in self.effects:
            gained *= 2
        self.score += gained
        self.food_eaten += 1

        if kind.is_powerup:
            self.effects[kind] = kind.effect_seconds
            self.events.append(EventKind.POWER)
        elif kind is FoodKind.GOLDEN:
            self.events.append(EventKind.GOLDEN)
        else:
            self.events.append(EventKind.EAT)

        self._burst(head, kind.value, count=12 if kind is FoodKind.GOLDEN else 8)
        label = f"+{gained}" if self.multiplier == 1 else f"+{gained} x{self.multiplier}"
        self._popup(head, label, kind.value, life=0.95)

        new_level = 1 + self.apples_eaten // LEVEL_EVERY
        if new_level > self.level:
            self.level = new_level
            self.events.append(EventKind.LEVEL)
            self._popup(Point(head.x, max(0, head.y - 1)), f"LEVEL {self.level}", "accent", 1.2)
            self._burst(head, "accent", count=16, spread=5.0)
            if self.config.obstacles:
                self._spawn_obstacles(1 + self.level // 2)

        if self.food is None:
            self.food = self._spawn_food(FoodKind.APPLE)
            if self.food is None:
                self._die("You conquered the arena", cleared=True)

    def _die(self, reason: str, cleared: bool = False) -> None:
        if self.status is GameStatus.GAME_OVER:
            return
        self.status = GameStatus.GAME_OVER
        self.death_reason = reason
        self.flash = 0.75
        for segment in self.snake:
            self._burst(segment, "danger", count=2, spread=4.0, life=1.0)
        self._burst(self.head, "danger", count=24, spread=9.0, life=1.3)
        self.events.append(EventKind.CLEAR if cleared else EventKind.DEATH)

    # ------------------------------------------------------------------
    # Spawning helpers
    # ------------------------------------------------------------------
    def _occupied(self, include_special: bool = True) -> set[Point]:
        occupied = set(self.snake)
        occupied |= self.obstacles
        if self.food is not None:
            occupied.add(self.food.pos)
        if include_special and self.special is not None:
            occupied.add(self.special.pos)
        return occupied

    def _free_cells(self, min_head_distance: int = 0) -> list[Point]:
        occupied = self._occupied()
        head = self.head
        cells: list[Point] = []
        for y in range(self.height):
            for x in range(self.width):
                point = Point(x, y)
                if point in occupied:
                    continue
                if min_head_distance and point.manhattan(head) < min_head_distance:
                    continue
                cells.append(point)
        return cells

    def _spawn_food(self, kind: FoodKind) -> Food | None:
        cells = self._free_cells(min_head_distance=2)
        if not cells:
            cells = self._free_cells()
        if not cells:
            return None
        pos = self.rng.choice(cells)
        return Food(kind=kind, pos=pos, ttl=kind.duration)

    def _spawn_special(self) -> None:
        if self.special is not None:
            return
        kinds = [
            FoodKind.GOLDEN,
            FoodKind.GOLDEN,
            FoodKind.GOLDEN,
            FoodKind.SPEED,
            FoodKind.SPEED,
            FoodKind.SLOW,
            FoodKind.GHOST,
            FoodKind.GHOST,
            FoodKind.FRENZY,
        ]
        kind = self.rng.choice(kinds)
        cells = [
            cell
            for cell in self._free_cells(min_head_distance=4)
            if self.food is None or cell.manhattan(self.food.pos) >= 3
        ]
        if not cells:
            return
        self.special = Food(
            kind=kind,
            pos=self.rng.choice(cells),
            ttl=kind.duration,
        )

    def _spawn_obstacles(self, count: int) -> None:
        area = self.width * self.height
        cap = min(30, max(6, area // 32))
        count = min(count, cap - len(self.obstacles))
        if count <= 0:
            return
        cells = [
            point
            for point in self._free_cells(min_head_distance=6)
            if 1 <= point.x < self.width - 1 and 1 <= point.y < self.height - 1
        ]
        if not cells:
            return
        for point in self.rng.sample(cells, min(count, len(cells))):
            self.obstacles.add(point)

    # ------------------------------------------------------------------
    # Effects
    # ------------------------------------------------------------------
    def _burst(
        self,
        at: Point,
        role: str,
        *,
        count: int,
        spread: float = 3.6,
        life: float = 0.7,
    ) -> None:
        palette_chars = ("*", "+", "·", "•", "∙")
        for _ in range(count):
            if len(self.particles) >= MAX_PARTICLES:
                break
            lifetime = self.rng.uniform(life * 0.55, life)
            angle = self.rng.uniform(0.0, 6.283185)
            speed = self.rng.uniform(0.4, spread)
            self.particles.append(
                Particle(
                    x=float(at.x),
                    y=float(at.y),
                    vx=math.cos(angle) * speed,
                    vy=math.sin(angle) * speed,
                    life=lifetime,
                    max_life=lifetime,
                    char=self.rng.choice(palette_chars),
                    role=role,
                )
            )

    def _popup(self, at: Point, text: str, role: str, life: float = 0.9) -> None:
        self.popups.append(
            Popup(
                x=float(at.x),
                y=float(at.y),
                text=text,
                life=life,
                max_life=life,
                role=role,
            )
        )

    # ------------------------------------------------------------------
    # Results
    # ------------------------------------------------------------------
    def drain_events(self) -> list[EventKind]:
        events = self.events
        self.events = []
        return events

    def stats(self, best: int, new_high_score: bool = False) -> RunStats:
        return RunStats(
            score=self.score,
            best=best,
            level=self.level,
            length=self.length,
            food_eaten=self.food_eaten,
            max_combo=self.max_combo,
            elapsed=self.elapsed,
            reason=self.death_reason or "Run complete",
            difficulty=self.difficulty.label,
            theme=self.config.theme,
            new_high_score=new_high_score,
        )


__all__ = ["Game", "LEVEL_EVERY", "DIFFICULTIES"]
