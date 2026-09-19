import base64
import hashlib
import hmac
import json
import time
from datetime import datetime, timezone
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.db import get_db
from app.models import Appointment, Customer, Service
from app.schemas_admin import AdminAppointmentResponse, AdminLogin, AdminLoginResponse, ServiceWrite

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