"""Color palettes and small color-math helpers for the renderer."""

from __future__ import annotations

import re
from dataclasses import dataclass
from functools import lru_cache

_HEX_COLOR = re.compile(r"#(?:[0-9a-fA-F]{3}|[0-9a-fA-F]{6})\Z")
_THEME_KEY = re.compile(r"[a-z0-9][a-z0-9_-]{0,31}\Z")


def _rgb(color: str) -> tuple[int, int, int]:
    if not _HEX_COLOR.fullmatch(color):
        raise ValueError(f"invalid color: {color!r}")
    value = color.lstrip("#")
    if len(value) == 3:
        value = "".join(ch * 2 for ch in value)
    return int(value[0:2], 16), int(value[2:4], 16), int(value[4:6], 16)


@lru_cache(maxsize=4096)
def blend(first: str, second: str, amount: float) -> str:
    """Mix two hex colors. ``amount=0`` is first, ``amount=1`` is second.

    Pure function of its arguments, and the renderer calls it dozens of
    times per frame with repeating colors, so results are memoized.
    """

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
        """Resolve a semantic color role used by particles and popups.

        Role names double as palette attribute names ("snake" is the one
        exception), so this is a straight attribute lookup — called per
        particle per frame, avoid building the mapping each time.
        """

        return getattr(self, "snake_body" if role == "snake" else role, self.accent)

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

# Real terminal color schemes, mapped to game roles with their official hex
# values (draculatheme.com/spec, nordtheme.com, morhetz/gruvbox-contrib,
# catppuccin.com/palette, folke/tokyonight.nvim, ethanschoonover.com/solarized).
# Muted (dim) roles use readable upstream colors where the theme's comment color
# is too dark for HUD text (Nord nord9 #81a1c1, Tokyo fg_dark #a9b1d6); danger
# uses the bright red variant where the normal red is unreadable on the arena
# background (Gruvbox).

DRACULA = Palette(
    key="dracula",
    label="Dracula",
    bg_a="#282a36",
    bg_b="#21222c",
    frame="#8be9fd",
    frame_dim="#44475a",
    snake_head="#f8f8f2",
    snake_body="#50fa7b",
    snake_tail="#bd93f9",
    apple="#ff5555",
    golden="#f1fa8c",
    speed="#8be9fd",
    slow="#6272a4",
    frenzy="#ffb86c",
    ghost="#FF92DF",
    obstacle="#44475a",
    accent="#ff79c6",
    accent2="#8be9fd",
    text="#f8f8f2",
    dim="#6272a4",
    danger="#ff5555",
)

NORD = Palette(
    key="nord",
    label="Nord",
    bg_a="#2e3440",
    bg_b="#3b4252",
    frame="#88c0d0",
    frame_dim="#4c566a",
    snake_head="#eceff4",
    snake_body="#88c0d0",
    snake_tail="#5e81ac",
    apple="#bf616a",
    golden="#ebcb8b",
    speed="#8fbcbb",
    slow="#81a1c1",
    frenzy="#d08770",
    ghost="#b48ead",
    obstacle="#4c566a",
    accent="#b48ead",
    accent2="#88c0d0",
    text="#d8dee9",
    dim="#81a1c1",
    danger="#bf616a",
)

GRUVBOX = Palette(
    key="gruvbox",
    label="Gruvbox",
    bg_a="#282828",
    bg_b="#1d2021",
    frame="#8ec07c",
    frame_dim="#665c54",
    snake_head="#ebdbb2",
    snake_body="#8ec07c",
    snake_tail="#d3869b",
    apple="#fb4934",
    golden="#fabd2f",
    speed="#83a598",
    slow="#689d6a",
    frenzy="#fe8019",
    ghost="#b16286",
    obstacle="#665c54",
    accent="#d3869b",
    accent2="#8ec07c",
    text="#ebdbb2",
    dim="#a89984",
    danger="#fb4934",
)

MOCHA = Palette(
    key="mocha",
    label="Catppuccin Mocha",
    bg_a="#1e1e2e",
    bg_b="#181825",
    frame="#94e2d5",
    frame_dim="#585b70",
    snake_head="#cdd6f4",
    snake_body="#94e2d5",
    snake_tail="#cba6f7",
    apple="#f38ba8",
    golden="#f9e2af",
    speed="#89dceb",
    slow="#74c7ec",
    frenzy="#fab387",
    ghost="#b4befe",
    obstacle="#45475a",
    accent="#f5c2e7",
    accent2="#89b4fa",
    text="#cdd6f4",
    dim="#6c7086",
    danger="#f38ba8",
)

TOKYO = Palette(
    key="tokyo",
    label="Tokyo Night",
    bg_a="#1a1b26",
    bg_b="#16161e",
    frame="#7aa2f7",
    frame_dim="#292e42",
    snake_head="#c0caf5",
    snake_body="#7dcfff",
    snake_tail="#73daca",
    apple="#f7768e",
    golden="#e0af68",
    speed="#2ac3de",
    slow="#7aa2f7",
    frenzy="#ff9e64",
    ghost="#bb9af7",
    obstacle="#414868",
    accent="#bb9af7",
    accent2="#7dcfff",
    text="#c0caf5",
    dim="#a9b1d6",
    danger="#f7768e",
)

SOLARIZED = Palette(
    key="solarized",
    label="Solarized Dark",
    bg_a="#002b36",
    bg_b="#073642",
    frame="#2aa198",
    frame_dim="#586e75",
    snake_head="#eee8d5",
    snake_body="#2aa198",
    snake_tail="#268bd2",
    apple="#dc322f",
    golden="#b58900",
    speed="#268bd2",
    slow="#6c71c4",
    frenzy="#cb4b16",
    ghost="#d33682",
    obstacle="#586e75",
    accent="#d33682",
    accent2="#2aa198",
    text="#839496",
    dim="#657b83",
    danger="#dc322f",
)

YELLEN = Palette(
    key="yellen",
    label="Yellen",
    bg_a="#171408",
    bg_b="#24200C",
    frame="#F2D14E",
    frame_dim="#6E5B25",
    snake_head="#FBF1C7",
    snake_body="#F2D14E",
    snake_tail="#D8A93B",
    apple="#C76A52",
    golden="#F7DE72",
    speed="#F2D14E",
    slow="#D6A843",
    frenzy="#C98B6B",
    ghost="#C6986A",
    obstacle="#745F2B",
    accent="#F2D14E",
    accent2="#E6C15A",
    text="#F3E8B8",
    dim="#A79765",
    danger="#C76A52",
)

THEMES: dict[str, Palette] = {
    palette.key: palette
    for palette in (NEON, AMBER, MATRIX, ICE, CANDY, DRACULA, NORD, GRUVBOX, MOCHA, TOKYO, SOLARIZED, YELLEN)
}
BUILTIN_THEME_KEYS = tuple(THEMES)
THEME_ORDER = list(BUILTIN_THEME_KEYS)

# Curated swatches for the in-app palette editor.
SWATCHES = (
    "#05010f", "#0a0320", "#10151f", "#1e1e2e", "#282828", "#2e3440", "#002b36",
    "#ffffff", "#e6f1ff", "#c4fffd", "#ffd166", "#ff3b6b", "#ff2bd6", "#22d3ee",
    "#c084fc", "#7c3aed", "#50fa7b", "#ffb000", "#2de2e6", "#f7768e",
)


def get_palette(key: str) -> Palette:
    return THEMES.get(key, NEON)


def register_theme(palette: Palette) -> None:
    """Add a custom palette to the live theme list."""
    THEMES[palette.key] = palette
    if palette.key not in THEME_ORDER:
        THEME_ORDER.append(palette.key)


def palette_from_mapping(raw: dict[str, object]) -> Palette | None:
    """Validate a persisted custom palette; return None when malformed."""
    if not isinstance(raw, dict):
        return None
    key = raw.get("key")
    label = raw.get("label")
    if not isinstance(key, str) or not _THEME_KEY.fullmatch(key):
        return None
    if key.startswith("__") or key in BUILTIN_THEME_KEYS:
        return None
    if not isinstance(label, str):
        return None
    label = "".join(ch for ch in label if ch.isprintable()).strip()
    if not label:
        return None
    values: dict[str, str] = {}
    for field_name in Palette.__dataclass_fields__:
        if field_name in ("key", "label"):
            continue
        value = raw.get(field_name)
        if not isinstance(value, str):
            return None
        try:
            _rgb(value)
        except ValueError:
            return None
        values[field_name] = value
    return Palette(key=key, label=label[:24], **values)
