from datetime import datetime

from shared.dates import inclusive_end_of_day


def test_midnight_value_extends_to_end_of_day():
    value = datetime(2026, 9, 9, 0, 0, 0)
    result = inclusive_end_of_day(value)
    assert result.date() == value.date()
    assert result.hour == 23
    assert result.minute == 59
    assert result.second == 59


def test_non_midnight_value_is_returned_unchanged():
    value = datetime(2026, 9, 9, 14, 30, 0)
    assert inclusive_end_of_day(value) == value
