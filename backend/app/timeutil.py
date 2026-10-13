from datetime import UTC, date, datetime
from zoneinfo import ZoneInfo

BOGOTA = ZoneInfo("America/Bogota")


def today_bogota(now: datetime | None = None) -> date:
    return (now or datetime.now(UTC)).astimezone(BOGOTA).date()


def month_range(d: date) -> tuple[date, date]:
    """Primer día del mes de `d` y primer día del mes siguiente (límite exclusivo)."""
    start = d.replace(day=1)
    nxt = date(start.year + 1, 1, 1) if start.month == 12 else date(start.year, start.month + 1, 1)
    return start, nxt
