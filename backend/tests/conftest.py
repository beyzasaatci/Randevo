import os

os.environ.setdefault("DATABASE_URL", "postgresql+psycopg://barber:barber@localhost:5432/barber_appointment")
os.environ.setdefault("SECRET_KEY", "test-secret-key")