from datetime import datetime
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