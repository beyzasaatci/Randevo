from datetime import date, datetime, time, timedelta
from uuid import UUID
from zoneinfo import ZoneInfo

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.db import get_db
from app.models import Appointment, AppointmentStatus, BlockedTime, Service, WorkingHour
from app.schemas_catalog import AvailabilityResponse, AvailabilitySlot, ServiceResponse

router = APIRouter(prefix="/api/v1", tags=["catalog"])


@router.get("/services", response_model=list[ServiceResponse])
async def list_services(db: AsyncSession = Depends(get_db)) -> list[Service]:
    result = await db.scalars(select(Service).where(Service.active.is_(True)).order_by(Service.name))
    return list(result)


@router.get("/availability", response_model=AvailabilityResponse)
async def get_availability(
    appointment_date: date = Query(alias="date"),
    service_id: UUID = Query(),
    db: AsyncSession = Depends(get_db),
) -> AvailabilityResponse:
    service = await db.get(Service, service_id)
    if not service or not service.active:
        raise HTTPException(status_code=404, detail="Hizmet bulunamadı.")
    local_zone = ZoneInfo(get_settings().business_timezone)
    weekday = appointment_date.weekday()
    hours = await db.scalar(select(WorkingHour).where(WorkingHour.day_of_week == weekday, WorkingHour.active.is_(True)))
    if not hours:
        return AvailabilityResponse(date=appointment_date, service_id=service.id, slots=[])

    local_start = datetime.combine(appointment_date, hours.start_time, tzinfo=local_zone)
    local_close = datetime.combine(appointment_date, hours.end_time, tzinfo=local_zone)
    day_start_utc = local_start.astimezone(ZoneInfo("UTC"))
    day_end_utc = local_close.astimezone(ZoneInfo("UTC"))
    appointments = await db.scalars(select(Appointment).where(
        Appointment.status != AppointmentStatus.CANCELLED,
        Appointment.start_at < day_end_utc,
        Appointment.end_at > day_start_utc,
    ))
    blocked = await db.scalars(select(BlockedTime).where(BlockedTime.date == appointment_date))
    occupied = [(item.start_at, item.end_at) for item in appointments]
    blocked_ranges = [
        (datetime.combine(appointment_date, item.start_time, tzinfo=local_zone), datetime.combine(appointment_date, item.end_time, tzinfo=local_zone))
        for item in blocked
    ]
    slots: list[AvailabilitySlot] = []
    cursor = local_start
    duration = timedelta(minutes=service.duration_minutes)
    interval = timedelta(minutes=get_settings().slot_interval_minutes)
    while cursor + duration <= local_close:
        end = cursor + duration
        start_utc, end_utc = cursor.astimezone(ZoneInfo("UTC")), end.astimezone(ZoneInfo("UTC"))
        overlaps_appointment = any(start_utc < existing_end and end_utc > existing_start for existing_start, existing_end in occupied)
        overlaps_block = any(cursor < blocked_end and end > blocked_start for blocked_start, blocked_end in blocked_ranges)
        if not overlaps_appointment and not overlaps_block:
            slots.append(AvailabilitySlot(start_at=cursor, end_at=end))
        cursor += interval
    return AvailabilityResponse(date=appointment_date, service_id=service.id, slots=slots)