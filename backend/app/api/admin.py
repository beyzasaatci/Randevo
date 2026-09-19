import base64
import hashlib
import hmac
import json
import time
from datetime import datetime, timezone
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Request, status
from datetime import timedelta

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.db import get_db
from app.models import Appointment, AppointmentSource, AppointmentStatus, BlockedTime, Customer, Service, WorkingHour
from app.schemas_admin import (AdminAppointmentResponse, AdminAppointmentUpdate, AdminLogin, AdminLoginResponse,
                               BlockedTimeWrite, ManualAppointmentCreate, ServiceWrite, WorkingHourWrite)
from app.services.auth import normalize_phone

router = APIRouter(prefix="/api/v1/admin", tags=["admin"])


def admin_token() -> str:
    settings = get_settings()
    encoded = base64.urlsafe_b64encode(json.dumps({"sub": "admin", "exp": int(time.time()) + 28800}).encode()).decode().rstrip("=")
    signature = hmac.new(settings.secret_key.encode(), encoded.encode(), hashlib.sha256).hexdigest()
    return f"{encoded}.{signature}"


def require_admin(request: Request) -> None:
    authorization = request.headers.get("Authorization", "")
    if not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Admin oturumu gerekli.")
    try:
        encoded, signature = authorization[7:].split(".", 1)
        expected = hmac.new(get_settings().secret_key.encode(), encoded.encode(), hashlib.sha256).hexdigest()
        payload = json.loads(base64.urlsafe_b64decode(encoded + "=" * (-len(encoded) % 4)))
        if not hmac.compare_digest(signature, expected) or payload["sub"] != "admin" or payload["exp"] < time.time():
            raise ValueError
    except (ValueError, KeyError, TypeError, json.JSONDecodeError):
        raise HTTPException(status_code=401, detail="Admin oturumu geçersiz.") from None


@router.post("/auth/login", response_model=AdminLoginResponse)
async def login(payload: AdminLogin) -> AdminLoginResponse:
    settings = get_settings()
    if not hmac.compare_digest(payload.username, settings.admin_username) or not hmac.compare_digest(payload.password, settings.admin_password):
        raise HTTPException(status_code=401, detail="Kullanıcı adı veya şifre hatalı.")
    return AdminLoginResponse(access_token=admin_token())


@router.get("/dashboard", response_model=list[AdminAppointmentResponse])
async def dashboard(request: Request, db: AsyncSession = Depends(get_db)) -> list[AdminAppointmentResponse]:
    require_admin(request)
    today = datetime.now(timezone.utc).date()
    result = await db.execute(select(Appointment, Customer, Service).join(Customer).join(Service).where(Appointment.start_at >= datetime.combine(today, datetime.min.time(), timezone.utc), Appointment.start_at < datetime.combine(today, datetime.max.time(), timezone.utc)).order_by(Appointment.start_at))
    return [AdminAppointmentResponse(id=appointment.id, customer_name=customer.name, customer_phone=customer.phone_number, service_name=service.name, start_at=appointment.start_at, end_at=appointment.end_at, status=appointment.status.value) for appointment, customer, service in result]


@router.post("/services", status_code=status.HTTP_201_CREATED)
async def create_service(payload: ServiceWrite, request: Request, db: AsyncSession = Depends(get_db)) -> Service:
    require_admin(request)
    service = Service(**payload.model_dump())
    db.add(service)
    await db.commit()
    await db.refresh(service)
    return service


@router.patch("/services/{service_id}")
async def update_service(service_id: UUID, payload: ServiceWrite, request: Request, db: AsyncSession = Depends(get_db)) -> Service:
    require_admin(request)
    service = await db.get(Service, service_id)
    if not service:
        raise HTTPException(status_code=404, detail="Hizmet bulunamadı.")
    for key, value in payload.model_dump().items():
        setattr(service, key, value)
    await db.commit()
    await db.refresh(service)
    return service


@router.delete("/services/{service_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_service(service_id: UUID, request: Request, db: AsyncSession = Depends(get_db)) -> None:
    require_admin(request)
    service = await db.get(Service, service_id)
    if service:
        service.active = False
        await db.commit()


@router.put("/working-hours/{day_of_week}")
async def set_working_hours(day_of_week: int, payload: WorkingHourWrite, request: Request, db: AsyncSession = Depends(get_db)) -> WorkingHour:
    require_admin(request)
    if day_of_week != payload.day_of_week or payload.start_time >= payload.end_time:
        raise HTTPException(status_code=422, detail="Çalışma günü ve saat aralığı geçersiz.")
    working_hour = await db.scalar(select(WorkingHour).where(WorkingHour.day_of_week == day_of_week).with_for_update())
    if not working_hour:
        working_hour = WorkingHour(day_of_week=day_of_week)
        db.add(working_hour)
    working_hour.start_time = payload.start_time
    working_hour.end_time = payload.end_time
    working_hour.active = payload.active
    await db.commit()
    await db.refresh(working_hour)
    return working_hour


@router.get("/working-hours")
async def list_working_hours(request: Request, db: AsyncSession = Depends(get_db)) -> list[WorkingHour]:
    require_admin(request)
    result = await db.scalars(select(WorkingHour).order_by(WorkingHour.day_of_week))
    return list(result)


@router.post("/blocked-times", status_code=status.HTTP_201_CREATED)
async def create_blocked_time(payload: BlockedTimeWrite, request: Request, db: AsyncSession = Depends(get_db)) -> BlockedTime:
    require_admin(request)
    if payload.start_time >= payload.end_time:
        raise HTTPException(status_code=422, detail="Kapalı zaman aralığı geçersiz.")
    blocked_time = BlockedTime(**payload.model_dump())
    db.add(blocked_time)
    await db.commit()
    await db.refresh(blocked_time)
    return blocked_time


@router.delete("/blocked-times/{blocked_time_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_blocked_time(blocked_time_id: UUID, request: Request, db: AsyncSession = Depends(get_db)) -> None:
    require_admin(request)
    blocked_time = await db.get(BlockedTime, blocked_time_id)
    if blocked_time:
        await db.delete(blocked_time)
        await db.commit()


@router.post("/appointments", response_model=AdminAppointmentResponse, status_code=status.HTTP_201_CREATED)
async def create_manual_appointment(payload: ManualAppointmentCreate, request: Request, db: AsyncSession = Depends(get_db)) -> AdminAppointmentResponse:
    require_admin(request)
    try:
        phone_number = normalize_phone(payload.phone_number)
    except ValueError as error:
        raise HTTPException(status_code=422, detail=str(error)) from error
    service = await db.get(Service, payload.service_id)
    if not service or not service.active or payload.start_at.tzinfo is None:
        raise HTTPException(status_code=422, detail="Geçerli hizmet ve saat gerekli.")
    start_at = payload.start_at.astimezone(timezone.utc)
    end_at = start_at + timedelta(minutes=service.duration_minutes)
    overlap = await db.scalar(select(Appointment.id).where(
        Appointment.status != AppointmentStatus.CANCELLED,
        Appointment.start_at < end_at,
        Appointment.end_at > start_at,
    ).with_for_update())
    if overlap:
        raise HTTPException(status_code=409, detail="Bu saat artık müsait değil.")
    customer = await db.scalar(select(Customer).where(Customer.phone_number == phone_number).with_for_update())
    if not customer:
        customer = Customer(phone_number=phone_number, name=payload.customer_name.strip())
        db.add(customer)
        await db.flush()
    else:
        customer.name = payload.customer_name.strip()
    appointment = Appointment(customer_id=customer.id, service_id=service.id, start_at=start_at, end_at=end_at, source=AppointmentSource.ADMIN)
    db.add(appointment)
    await db.commit()
    await db.refresh(appointment)
    return AdminAppointmentResponse(id=appointment.id, customer_name=customer.name, customer_phone=customer.phone_number, service_name=service.name, start_at=appointment.start_at, end_at=appointment.end_at, status=appointment.status.value)


@router.patch("/appointments/{appointment_id}", response_model=AdminAppointmentResponse)
async def update_admin_appointment(appointment_id: UUID, payload: AdminAppointmentUpdate, request: Request, db: AsyncSession = Depends(get_db)) -> AdminAppointmentResponse:
    require_admin(request)
    appointment = await db.scalar(select(Appointment).where(Appointment.id == appointment_id).with_for_update())
    service = await db.get(Service, payload.service_id)
    if not appointment or appointment.status == AppointmentStatus.CANCELLED:
        raise HTTPException(status_code=404, detail="Randevu bulunamadı.")
    if not service or not service.active or payload.start_at.tzinfo is None:
        raise HTTPException(status_code=422, detail="Geçerli hizmet ve saat gerekli.")
    start_at = payload.start_at.astimezone(timezone.utc)
    end_at = start_at + timedelta(minutes=service.duration_minutes)
    overlap = await db.scalar(select(Appointment.id).where(
        Appointment.id != appointment.id,
        Appointment.status != AppointmentStatus.CANCELLED,
        Appointment.start_at < end_at,
        Appointment.end_at > start_at,
    ).with_for_update())
    if overlap:
        raise HTTPException(status_code=409, detail="Bu saat artık müsait değil.")
    appointment.service_id = service.id
    appointment.start_at = start_at
    appointment.end_at = end_at
    await db.commit()
    await db.refresh(appointment)
    customer = await db.get(Customer, appointment.customer_id)
    return AdminAppointmentResponse(id=appointment.id, customer_name=customer.name if customer else None, customer_phone=customer.phone_number if customer else "", service_name=service.name, start_at=appointment.start_at, end_at=appointment.end_at, status=appointment.status.value)


@router.delete("/appointments/{appointment_id}", response_model=AdminAppointmentResponse)
async def cancel_admin_appointment(appointment_id: UUID, request: Request, db: AsyncSession = Depends(get_db)) -> AdminAppointmentResponse:
    require_admin(request)
    appointment = await db.scalar(select(Appointment).where(Appointment.id == appointment_id).with_for_update())
    if not appointment:
        raise HTTPException(status_code=404, detail="Randevu bulunamadı.")
    appointment.status = AppointmentStatus.CANCELLED
    await db.commit()
    customer = await db.get(Customer, appointment.customer_id)
    service = await db.get(Service, appointment.service_id)
    return AdminAppointmentResponse(id=appointment.id, customer_name=customer.name if customer else None, customer_phone=customer.phone_number if customer else "", service_name=service.name if service else "", start_at=appointment.start_at, end_at=appointment.end_at, status=appointment.status.value)