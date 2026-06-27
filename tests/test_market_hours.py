from datetime import datetime
from zoneinfo import ZoneInfo

from trading_core.safety.market_hours import is_market_open_at

ET = ZoneInfo("America/New_York")


def test_open_on_regular_weekday_during_hours():
    # Monday, 10:00 ET — ordinary trading day.
    assert is_market_open_at(datetime(2026, 6, 22, 10, 0, tzinfo=ET)) is True


def test_closed_before_open():
    assert is_market_open_at(datetime(2026, 6, 22, 9, 0, tzinfo=ET)) is False


def test_closed_after_close():
    assert is_market_open_at(datetime(2026, 6, 22, 16, 0, tzinfo=ET)) is False


def test_closed_on_weekend():
    # Saturday.
    assert is_market_open_at(datetime(2026, 6, 20, 12, 0, tzinfo=ET)) is False


def test_closed_on_nyse_holiday():
    # Thursday, but it's New Year's Day (NYSE holiday) — closed even during trading hours.
    assert is_market_open_at(datetime(2026, 1, 1, 12, 0, tzinfo=ET)) is False
