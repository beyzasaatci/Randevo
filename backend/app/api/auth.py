import hashlib
from datetime import datetime, timedelta, timezone
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.db import get_db
from app.models import Customer, OtpCode
from app.schemas import CustomerProfileUpdate, OtpRequest, OtpRequestResponse, OtpVerify, OtpVerifyResponse
from app.services.auth import create_customer_token, digest_otp, generate_otp, normalize_phone, verify_customer_token
from app.services.sms import sms_service

router = APIRouter(prefix="/api/v1/auth", tags=["auth"])


def request_ip_hash(request: Request) -> str:
    ip = request.client.host if request.client else "unknown"
    return hashlib.sha256(ip.encode()).hexdigest()


@router.post("/request-otp", response_model=OtpRequestResponse)
async def request_otp(payload: OtpRequest, request: Request, db: AsyncSession = Depends(get_db)) -> OtpRequestResponse:
    try:
        phone_number = normalize_phone(payload.phone_number)
    except ValueError as error:
        raise HTTPException(status_code=422, detail=str(error)) from error
    now = datetime.now(timezone.utc)
    latest = await db.scalar(select(OtpCode).where(OtpCode.phone_number == phone_number).order_by(OtpCode.created_at.desc()))
    if latest and latest.created_at and (now - latest.created_at).total_seconds() < 60:
        raise HTTPException(status_code=429, detail="Yeni kod için biraz bekleyin.")
    code = generate_otp()
    otp = OtpCode(
        phone_number=phone_number,
        request_ip_hash=request_ip_hash(request),
        code_digest=digest_otp(phone_number, code),
        expires_at=now + timedelta(seconds=get_settings().otp_ttl_seconds),
    )
    db.add(otp)
    await db.commit()
    await sms_service.send_otp(phone_number, code)
    return OtpRequestResponse(message="Doğrulama kodu gönderildi.", retry_after_seconds=60)


@router.post("/verify-otp", response_model=OtpVerifyResponse)
async def verify_otp(payload: OtpVerify, db: AsyncSession = Depends(get_db)) -> OtpVerifyResponse:
    try:
        phone_number = normalize_phone(payload.phone_number)
    except ValueError as error:
        raise HTTPException(status_code=422, detail=str(error)) from error
    otp = await db.scalar(select(OtpCode).where(OtpCode.phone_number == phone_number).order_by(OtpCode.created_at.desc()))
    now = datetime.now(timezone.utc)
    settings = get_settings()
    if not otp or otp.consumed_at or otp.expires_at < now or otp.attempts >= settings.otp_max_attempts:
        raise HTTPException(status_code=400, detail="Kod geçersiz veya süresi dolmuş.")
    if not hmac_compare(digest_otp(phone_number, payload.code), otp.code_digest):
        otp.attempts += 1
        await db.commit()
        raise HTTPException(status_code=400, detail="Kod geçersiz veya süresi dolmuş.")
    otp.consumed_at = now
    customer = await db.scalar(select(Customer).where(Customer.phone_number == phone_number))
    if not customer:
        customer = Customer(phone_number=phone_number)
        db.add(customer)
        await db.flush()
    await db.commit()
    return OtpVerifyResponse(access_token=create_customer_token(str(customer.id)), customer_id=str(customer.id), requires_name=customer.name is None)


def hmac_compare(left: str, right: str) -> bool:
    import hmac
    return hmac.compare_digest(left, right)


@router.patch("/profile", status_code=status.HTTP_204_NO_CONTENT)
async def update_profile(payload: CustomerProfileUpdate, request: Request, db: AsyncSession = Depends(get_db)) -> None:
    authorization = request.headers.get("Authorization", "")
    if not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Oturum gerekli.")
    try:
        customer_id = UUID(verify_customer_token(authorization[7:]))
    except ValueError as error:
        raise HTTPException(status_code=401, detail=str(error)) from error
    customer = await db.get(Customer, customer_id)
    if not customer:
        raise HTTPException(status_code=404, detail="Müşteri bulunamadı.")
    customer.name = payload.name.strip()
    await db.commit()