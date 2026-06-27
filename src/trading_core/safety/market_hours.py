"""US regular trading hours.

Fractional orders only execute during RTH, and in general we don't want to fire MKT
orders while the market is closed. Considers the day of the week, the time window in the
market's timezone, and the **NYSE holidays** (via the ``holidays`` library).

Known limitation: **early-close** sessions (half-days ~13:00 ET, e.g. Christmas Eve) are
not handled — the calendar only marks full closures. On those days IBKR still rejects
orders after the real close.
"""

from __future__ import annotations

from datetime import datetime, time
from zoneinfo import ZoneInfo

import holidays

# NYSE calendar. Generates years on demand; reusing a single instance is the efficient
# pattern recommended by the library itself.
_NYSE_HOLIDAYS = holidays.NYSE()


def is_market_open_at(
    moment: datetime,
    open_time: str = "09:30",
    close_time: str = "16:00",
) -> bool:
    """RTH for an instant already in the market's timezone (pure, testable without a clock)."""
    if moment.weekday() > 4:  # 5=Saturday, 6=Sunday
        return False
    if moment.date() in _NYSE_HOLIDAYS:
        return False
    return time.fromisoformat(open_time) <= moment.time() < time.fromisoformat(close_time)


def is_market_open_now(
    tz_name: str = "America/New_York",
    open_time: str = "09:30",
    close_time: str = "16:00",
) -> bool:
    return is_market_open_at(datetime.now(ZoneInfo(tz_name)), open_time, close_time)
