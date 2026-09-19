from datetime import date, datetime
from decimal import Decimal
from uuid import UUID

from pydantic import BaseModel


class ServiceResponse(BaseModel):
    id: UUID
    name: str
    duration_minutes: int
    price: Decimal
    active: bool

    model_config = {"from_attributes": True}


class AvailabilitySlot(BaseModel):
    start_at: datetime
    end_at: datetime


class AvailabilityResponse(BaseModel):
    date: date
    service_id: UUID
    slots: list[AvailabilitySlot]