from datetime import datetime, time, timedelta


def inclusive_end_of_day(value: datetime) -> datetime:
    """Extend a date-range upper bound to cover the whole day when it looks
    like it came from a date-only picker (i.e. time component is midnight).

    Query params typed as `datetime` accept both a bare date ("2026-09-09",
    parsed as midnight) and a precise timestamp. Comparing with `<=` against
    a bare-date value excludes almost the entire day it names. An explicit
    non-midnight timestamp is treated as an exact cutoff and returned as-is.
    """
    if value.time() != time.min:
        return value
    return value + timedelta(days=1) - timedelta(microseconds=1)
