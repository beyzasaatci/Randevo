from contextlib import asynccontextmanager
from datetime import time

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import select, text

from app.core.config import get_settings
from app.models import Base
from app.api.auth import router as auth_router
from app.api.catalog import router as catalog_router
from app.api.appointments import router as appointments_router
from app.api.admin import router as admin_router
from app.db import SessionLocal, engine
from app.models import Service, WorkingHour


async def seed_development_data() -> None:
    async with SessionLocal() as session:
        has_services = await session.scalar(select(Service.id).limit(1))
        if not has_services:
            session.add_all([
                Service(name="Saç Kesimi", duration_minutes=30, price=500, active=True),
                Service(name="Sakal Tıraşı", duration_minutes=20, price=300, active=True),
                Service(name="Saç + Sakal", duration_minutes=50, price=750, active=True),
            ])
        has_hours = await session.scalar(select(WorkingHour.id).limit(1))
        if not has_hours:
            session.add_all([
                WorkingHour(day_of_week=day, start_time=time(9), end_time=time(20), active=True)
                for day in range(6)
            ])
        await session.commit()

settings = get_settings()


@asynccontextmanager
async def lifespan(_: FastAPI):
    if settings.environment == "development":
        async with engine.begin() as connection:
            await connection.execute(text("CREATE EXTENSION IF NOT EXISTS btree_gist"))
            await connection.run_sync(Base.metadata.create_all)
        await seed_development_data()
    yield


app = FastAPI(title=settings.app_name, version="0.1.0", lifespan=lifespan)
app.add_middleware(
    CORSMiddleware,
    allow_origins=[settings.frontend_origin],
    allow_credentials=True,
    allow_methods=["GET", "POST", "PATCH", "DELETE"],
    allow_headers=["Content-Type", "Authorization"],
)
app.include_router(auth_router)
app.include_router(catalog_router)
app.include_router(appointments_router)
app.include_router(admin_router)


@app.get("/health", tags=["system"])
async def health() -> dict[str, str]:
    return {"status": "ok", "environment": settings.environment}