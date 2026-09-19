from datetime import date, datetime, time
from decimal import Decimal
from uuid import UUID

from pydantic import BaseModel, Field


class AdminLogin(BaseModel):
    username: str
    password: str


class AdminLoginResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"


class ServiceWrite(BaseModel):
    name: str = Field(min_length=2, max_length=120)
    duration_minutes: int = Field(gt=0, le=480)
    price: Decimal = Field(ge=0, decimal_places=2)
    active: bool = True


class AdminAppointmentResponse(BaseModel):
    id: UUID
    customer_name: str | None
    customer_phone: str
    service_name: str
    start_at: datetime
    end_at: datetime
    status: str


class WorkingHourWrite(BaseModel):
    day_of_week: int = Field(ge=0, le=6)
    start_time: time
    end_time: time
    active: bool = True


class BlockedTimeWrite(BaseModel):
    date: date
    start_time: time
    end_time: time
    reason: str | None = Field(default=None, max_length=255)


class ManualAppointmentCreate(BaseModel):
    phone_number: str = Field(min_length=8, max_length=20)
    customer_name: str = Field(min_length=2, max_length=120)
    service_id: UUID
    start_at: datetime