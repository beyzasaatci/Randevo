from datetime import datetime, timedelta, timezone
from zoneinfo import ZoneInfo

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.models import BlockedTime, WorkingHour


async def is_valid_booking_window(
    db: AsyncSession,
    start_at: datetime,
    end_at: datetime,
) -> bool:
    settings = get_settings()
    local_zone = ZoneInfo(settings.business_timezone)
    local_start = start_at.astimezone(local_zone)
    local_end = end_at.astimezone(local_zone)
    if local_start.date() != local_end.date():
        return False

    working_hour = await db.scalar(
        select(WorkingHour).where(
            WorkingHour.day_of_week == local_start.weekday(),
            WorkingHour.active.is_(True),
        )
    )
    if not working_hour:
        return False

    opening = datetime.combine(local_start.date(), working_hour.start_time, tzinfo=local_zone)
    closing = datetime.combine(local_start.date(), working_hour.end_time, tzinfo=local_zone)
    if local_start < opening or local_end > closing:
        return False

    interval = timedelta(minutes=settings.slot_interval_minutes)
    if (local_start - opening) % interval != timedelta(0):
        return False

    blocked_times = await db.scalars(
        select(BlockedTime).where(BlockedTime.date == local_start.date())
    )
    return not any(
        local_start < datetime.combine(local_start.date(), blocked.end_time, tzinfo=local_zone)
        and local_end > datetime.combine(local_start.date(), blocked.start_time, tzinfo=local_zone)
        for blocked in blocked_times
    )
