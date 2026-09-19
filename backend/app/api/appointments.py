from datetime import datetime, timedelta, timezone
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy import select, text
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.db import get_db
from app.models import Appointment, AppointmentStatus, Customer, Service
from app.schemas_appointments import AppointmentCreate, AppointmentResponse
from app.services.auth import verify_customer_token

router = APIRouter(prefix="/api/v1/appointments", tags=["appointments"])


async def current_customer(request: Request, db: AsyncSession) -> Customer:
    authorization = request.headers.get("Authorization", "")
    if not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Oturum gerekli.")
    try:
        customer_id = UUID(verify_customer_token(authorization[7:]))
    except ValueError as error:
        raise HTTPException(status_code=401, detail=str(error)) from error
    customer = await db.get(Customer, customer_id)
    if not customer:
        raise HTTPException(status_code=401, detail="Oturum sahibi bulunamadı.")
    return customer


@router.post("", response_model=AppointmentResponse, status_code=status.HTTP_201_CREATED)
async def create_appointment(payload: AppointmentCreate, request: Request, db: AsyncSession = Depends(get_db)) -> Appointment:
    customer = await current_customer(request, db)
    service = await db.get(Service, payload.service_id)
    if not service or not service.active:
        raise HTTPException(status_code=404, detail="Hizmet bulunamadı.")
    if payload.start_at.tzinfo is None:
        raise HTTPException(status_code=422, detail="Randevu zamanı timezone içermeli.")
    start_at = payload.start_at.astimezone(timezone.utc)
    if start_at <= datetime.now(timezone.utc):
        raise HTTPException(status_code=422, detail="Geçmiş bir saate randevu alınamaz.")
    end_at = start_at + timedelta(minutes=service.duration_minutes)
    await db.execute(text("SELECT pg_advisory_xact_lock(hashtextextended(:key, 0))"), {"key": start_at.isoformat()[:16]})
    overlap = await db.scalar(select(Appointment.id).where(
        Appointment.status != AppointmentStatus.CANCELLED,
        Appointment.start_at < end_at,
        Appointment.end_at > start_at,
    ).with_for_update())
    if overlap:
        raise HTTPException(status_code=409, detail="Bu saat artık müsait değil.")
    appointment = Appointment(customer_id=customer.id, service_id=service.id, start_at=start_at, end_at=end_at)
    db.add(appointment)
    try:
        await db.commit()
    except IntegrityError:
        await db.rollback()
        raise HTTPException(status_code=409, detail="Bu saat artık müsait değil.") from None
    await db.refresh(appointment)
    return appointment


@router.get("", response_model=list[AppointmentResponse])
async def list_my_appointments(request: Request, db: AsyncSession = Depends(get_db)) -> list[Appointment]:
    customer = await current_customer(request, db)
    result = await db.scalars(select(Appointment).where(Appointment.customer_id == customer.id).order_by(Appointment.start_at))
    return list(result)


@router.delete("/{appointment_id}", response_model=AppointmentResponse)
async def cancel_appointment(appointment_id: UUID, request: Request, db: AsyncSession = Depends(get_db)) -> Appointment:
    customer = await current_customer(request, db)
    appointment = await db.scalar(select(Appointment).where(Appointment.id == appointment_id, Appointment.customer_id == customer.id).with_for_update())
    if not appointment:
        raise HTTPException(status_code=404, detail="Randevu bulunamadı.")
    if appointment.status == AppointmentStatus.CANCELLED:
        return appointment
    if appointment.start_at <= datetime.now(timezone.utc):
        raise HTTPException(status_code=422, detail="Geçmiş randevu iptal edilemez.")
    appointment.status = AppointmentStatus.CANCELLED
    await db.commit()
    await db.refresh(appointment)
    return appointment


@router.patch("/{appointment_id}", response_model=AppointmentResponse)
async def reschedule_appointment(appointment_id: UUID, payload: AppointmentCreate, request: Request, db: AsyncSession = Depends(get_db)) -> Appointment:
    customer = await current_customer(request, db)
    appointment = await db.scalar(select(Appointment).where(Appointment.id == appointment_id, Appointment.customer_id == customer.id).with_for_update())
    if not appointment or appointment.status == AppointmentStatus.CANCELLED:
        raise HTTPException(status_code=404, detail="Randevu bulunamadı.")
    service = await db.get(Service, payload.service_id)
    if not service or not service.active or payload.start_at.tzinfo is None:
        raise HTTPException(status_code=422, detail="Geçerli hizmet ve timezone içeren saat gerekli.")
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
    try:
        await db.commit()
    except IntegrityError:
        await db.rollback()
        raise HTTPException(status_code=409, detail="Bu saat artık müsait değil.") from None
    await db.refresh(appointment)
    return appointment