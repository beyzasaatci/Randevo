# Barber Appointment

Production-oriented online appointment system for a barber shop.

## Repository layout

```text
barber-appointment/
├── backend/     # FastAPI REST API
├── frontend/    # Next.js App Router client
└── docker-compose.yml
```

## Phase 1 status

The initial foundation is runnable: FastAPI configuration and database session management, PostgreSQL-ready SQLAlchemy models, a health endpoint, and a mobile-first Next.js landing screen are included. Business endpoints are intentionally added in later phases so authentication and booking invariants are implemented together.

## Run locally

Prerequisites: Docker, Python 3.12+, Node.js 20+, and npm.

1. Copy environment files:

   ```bash
   cp backend/.env.example backend/.env
   cp frontend/.env.example frontend/.env.local
   ```

2. Start PostgreSQL:

   ```bash
   docker compose up -d db
   ```

3. Start the API:

   ```bash
   cd backend
   python -m venv .venv
   source .venv/bin/activate
   pip install -e .
   uvicorn app.main:app --reload --port 8000
   ```

4. Start the frontend in another terminal:

   ```bash
   cd frontend
   npm install
   npm run dev
   ```

Open <http://localhost:3000>. API docs are available at <http://localhost:8000/docs>.

## Security decisions

- Customer identity is a verified phone number; no password is stored.
- OTP values will be stored only as digests, with expiry, attempt limits, and per-phone/IP throttling.
- Customer sessions will be short-lived and server-verifiable; every appointment mutation will check ownership server-side.
- Booking writes will use PostgreSQL transaction protection and an exclusion constraint over active appointment time ranges.
- Secrets belong in environment variables. Personal data is not written to application logs.

## Planned API surface

Public/customer: `POST /api/v1/auth/request-otp`, `POST /api/v1/auth/verify-otp`, `GET /api/v1/services`, `GET /api/v1/availability`, `POST /api/v1/appointments`, `GET/PATCH/DELETE /api/v1/me/appointments`.

Admin: `POST /api/v1/admin/auth/login`, `GET /api/v1/admin/dashboard`, CRUD for services, working hours, blocked times, and appointments.

## Database design

Core tables are `customers`, `services`, `appointments`, `working_hours`, `blocked_times`, and `otp_codes`. Appointments use UTC `start_at` and `end_at` timestamps rather than separate date/time columns, which avoids ambiguous timezone arithmetic and makes overlap constraints reliable. `source` distinguishes online and admin-created appointments.