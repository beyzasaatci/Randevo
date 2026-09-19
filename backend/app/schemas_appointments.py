from datetime import datetime
from uuid import UUID

from pydantic import BaseModel


class AppointmentCreate(BaseModel):
    service_id: UUID
    start_at: datetime


class AppointmentResponse(BaseModel):
    id: UUID
    service_id: UUID
    start_at: datetime
    end_at: datetime
    status: str

    model_config = {"from_attributes": True}