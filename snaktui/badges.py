"""Dynamic achievement badges for SnakTUI.

Badges are derived from persisted scores every time the leaderboard renders,
so importing a valid run or resetting state cannot strand stale unlocks.
"""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass

from .models import DIFFICULTIES
from .storage import ScoreEntry


@dataclass(frozen=True, slots=True)
class Badge:
    key: str
    title: str
    detail: str


def badges_for(entries: Sequence[ScoreEntry]) -> list[Badge]:
    if not entries:
        return []

    best = max(entry.score for entry in entries)
    longest = max(entry.length for entry in entries)
    runs = len(entries)
    daily_days = {entry.date for entry in entries if entry.daily and entry.date}
    insane_wins = sum(1 for entry in entries if entry.difficulty == DIFFICULTIES["insane"].label)

    badges = [Badge("first-bite", "FIRST BITE", "completed a run")]
    if best >= 100:
        badges.append(Badge("centum", "CENTUM CLUB", "scored 100+ in a run"))
    if best >= 250:
        badges.append(Badge("serpent", "SERPENT ASCENDANT", "scored 250+ in a run"))
    if best >= 500:
        badges.append(Badge("apex", "APEX SERPENT", "scored 500+ in a run"))
    if best >= 1000:
        badges.append(Badge("mythic", "MYTHIC SNAKE", "scored 1000+ in a run"))
    if longest >= 18:
        badges.append(Badge("full-plate", "FULL PLATE", "reached length 18 in a run"))
    if runs >= 10:
        badges.append(Badge("regular", "ARENA REGULAR", "completed 10 runs"))
    if runs >= 25:
        badges.append(Badge("keeper", "KEEPER OF THE TRAIL", "completed 25 runs"))
    if len(daily_days) >= 7:
        badges.append(Badge("daily-devotion", "DAILY DEVOTION", "played Daily Challenge on 7 days"))
    if insane_wins >= 3:
        badges.append(Badge("danger-zone", "DANGER ZONE", "banked 3 Insane runs"))
    return badges
