from snaktui.badges import badges_for
from snaktui.storage import ScoreEntry


def entry(score, *, length=4, daily=False, date="2026-11-18", difficulty="Classic"):
    return ScoreEntry(score, 1, length, difficulty, "neon", date, daily)


def keys(entries, total_runs=0):
    return {badge.key for badge in badges_for(entries, total_runs)}


def test_empty_has_no_badges():
    assert badges_for([]) == []


def test_first_badge_and_score_milestones():
    assert "first-bite" in keys([entry(10)])
    assert {"centum", "serpent", "apex"} <= keys([entry(500)])
    assert "mythic" in keys([entry(1000)])


def test_length_and_daily_badges():
    entries = [entry(50, length=18, daily=True, date=f"2026-11-{index:02d}") for index in range(1, 8)]
    assert {"full-plate", "daily-devotion"} <= keys(entries)


def test_run_count_and_insane_badge():
    entries = [entry(10, difficulty="insane") for _ in range(3)] + [entry(10) for _ in range(7)]
    assert {"regular", "danger-zone"} <= keys(entries)


def test_daily_badge_counts_calendar_days_not_timestamps():
    entries = [entry(50, daily=True, date=f"2026-11-18 10:0{index}") for index in range(7)]
    assert "daily-devotion" not in keys(entries)


def test_keeper_badge_uses_total_run_count():
    entries = [entry(10)]
    assert "keeper" not in keys(entries)
    assert "keeper" in keys(entries, total_runs=25)
