"""Color palettes and small color-math helpers for the renderer."""

from __future__ import annotations

from dataclasses import dataclass


def _rgb(color: str) -> tuple[int, int, int]:
    value = color.lstrip("#")
    if len(value) == 3:
        value = "".join(ch * 2 for ch in value)
    if len(value) != 6:
        raise ValueError(f"invalid color: {color!r}")
    return int(value[0:2], 16), int(value[2:4], 16), int(value[4:6], 16)


def blend(first: str, second: str, amount: float) -> str:
    """Mix two hex colors. ``amount=0`` is first, ``amount=1`` is second."""

    amount = max(0.0, min(1.0, amount))
    r1, g1, b1 = _rgb(first)
    r2, g2, b2 = _rgb(second)
    r = round(r1 + (r2 - r1) * amount)
    g = round(g1 + (g2 - g1) * amount)
    b = round(b1 + (b2 - b1) * amount)
    return f"#{r:02x}{g:02x}{b:02x}"


def darken(color: str, amount: float) -> str:
    return blend(color, "#000000", amount)


def lighten(color: str, amount: float) -> str:
    return blend(color, "#ffffff", amount)


@dataclass(frozen=True, slots=True)
class Palette:
    """All colors used by the arena and HUD in a given theme."""

    key: str
    label: str
    bg_a: str
    bg_b: str
    frame: str
    frame_dim: str
    snake_head: str
    snake_body: str
    snake_tail: str
    apple: str
    golden: str
    speed: str
    slow: str
    ghost: str
    frenzy: str
    obstacle: str
    accent: str
    accent2: str
    text: str
    dim: str
    danger: str

    def role(self, role: str) -> str:
        """Resolve a semantic color role used by particles and popups."""

        return {
            "apple": self.apple,
            "golden": self.golden,
            "speed": self.speed,
            "slow": self.slow,
            "ghost": self.ghost,
            "frenzy": self.frenzy,
            "danger": self.danger,
            "accent": self.accent,
            "snake": self.snake_body,
            "text": self.text,
        }.get(role, self.accent)

    def snake_gradient(self, index: int, length: int) -> str:
        if index == 0:
            return self.snake_head
        if length <= 2:
            return self.snake_body
        position = (index - 1) / max(1, length - 2)
        return blend(self.snake_body, self.snake_tail, position)


NEON = Palette(
    key="neon",
    label="Neon",
    bg_a="#05010f",
    bg_b="#0a0320",
    frame="#2de2e6",
    frame_dim="#155e6b",
    snake_head="#c4fffd",
    snake_body="#22d3ee",
    snake_tail="#7c3aed",
    apple="#ff3b6b",
    golden="#ffd166",
    speed="#2de2e6",
    slow="#60a5fa",
    frenzy="#ff8a3d",
    ghost="#c084fc",
    obstacle="#475569",
    accent="#ff2bd6",
    accent2="#2de2e6",
    text="#e6f1ff",
    dim="#7183b0",
    danger="#ff3b30",
)

AMBER = Palette(
    key="amber",
    label="Amber CRT",
    bg_a="#0d0700",
    bg_b="#150c02",
    frame="#ffb000",
    frame_dim="#7a5200",
    snake_head="#fff3c4",
    snake_body="#ffb000",
    snake_tail="#b45309",
    apple="#ff6b6b",
    golden="#ffe08a",
    speed="#ffc857",
    slow="#9ecbff",
    frenzy="#ff7a45",
    ghost="#e0aaff",
    obstacle="#5b4636",
    accent="#ff9f1c",
    accent2="#ffe08a",
    text="#fff3d6",
    dim="#a8845c",
    danger="#ff4d4d",
)

MATRIX = Palette(
    key="matrix",
    label="Matrix",
    bg_a="#000a02",
    bg_b="#001205",
    frame="#22c55e",
    frame_dim="#0f5f2d",
    snake_head="#d9f99d",
    snake_body="#22c55e",
    snake_tail="#065f46",
    apple="#ef4444",
    golden="#facc15",
    speed="#4ade80",
    slow="#38bdf8",
    frenzy="#f97316",
    ghost="#a78bfa",
    obstacle="#14532d",
    accent="#86efac",
    accent2="#22c55e",
    text="#dcfce7",
    dim="#4d7c5f",
    danger="#ff5252",
)

ICE = Palette(
    key="ice",
    label="Ice",
    bg_a="#020617",
    bg_b="#071429",
    frame="#38bdf8",
    frame_dim="#0c4a6e",
    snake_head="#e0f2fe",
    snake_body="#38bdf8",
    snake_tail="#6366f1",
    apple="#fb7185",
    golden="#fde047",
    speed="#67e8f9",
    slow="#a5b4fc",
    frenzy="#f472b6",
    ghost="#d8b4fe",
    obstacle="#334155",
    accent="#a5f3fc",
    accent2="#38bdf8",
    text="#e0f2fe",
    dim="#64748b",
    danger="#fb7185",
)

CANDY = Palette(
    key="candy",
    label="Candy",
    bg_a="#120016",
    bg_b="#1d0124",
    frame="#f472b6",
    frame_dim="#831843",
    snake_head="#ffe4f2",
    snake_body="#f472b6",
    snake_tail="#a855f7",
    apple="#fb7185",
    golden="#fde047",
    speed="#67e8f9",
    slow="#93c5fd",
    frenzy="#ff9de2",
    ghost="#c084fc",
    obstacle="#6b2145",
    accent="#f9a8d4",
    accent2="#f472b6",
    text="#ffe9f6",
    dim="#9d6b8c",
    danger="#ff4d6d",
)

THEMES: dict[str, Palette] = {
    palette.key: palette for palette in (NEON, AMBER, MATRIX, ICE, CANDY)
}
THEME_ORDER = ("neon", "amber", "matrix", "ice", "candy")


def get_palette(key: str) -> Palette:
    return THEMES.get(key, NEON)
