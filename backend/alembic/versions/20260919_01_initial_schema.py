"""initial schema

Revision ID: 20260919_01
Revises:
Create Date: 2026-09-19
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "20260919_01"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("CREATE EXTENSION IF NOT EXISTS btree_gist")
    appointment_status = postgresql.ENUM("CONFIRMED", "CANCELLED", "COMPLETED", name="appointmentstatus", create_type=False)
    appointment_source = postgresql.ENUM("ONLINE", "ADMIN", name="appointmentsource", create_type=False)
    appointment_status.create(op.get_bind(), checkfirst=True)
    appointment_source.create(op.get_bind(), checkfirst=True)

    op.create_table(
        "customers",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("phone_number", sa.String(20), nullable=False),
        sa.Column("name", sa.String(120), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.UniqueConstraint("phone_number"),
    )
    op.create_index("ix_customers_phone_number", "customers", ["phone_number"], unique=False)
    op.create_table(
        "services",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("name", sa.String(120), nullable=False),
        sa.Column("duration_minutes", sa.Integer(), nullable=False),
        sa.Column("price", sa.Numeric(10, 2), nullable=False),
        sa.Column("active", sa.Boolean(), nullable=False, server_default=sa.true()),
    )
    op.create_index("ix_services_active", "services", ["active"], unique=False)
    op.create_table(
        "working_hours",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("day_of_week", sa.Integer(), nullable=False),
        sa.Column("start_time", sa.Time(), nullable=False),
        sa.Column("end_time", sa.Time(), nullable=False),
        sa.Column("active", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.UniqueConstraint("day_of_week"),
    )
    op.create_table(
        "blocked_times",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("date", sa.Date(), nullable=False),
        sa.Column("start_time", sa.Time(), nullable=False),
        sa.Column("end_time", sa.Time(), nullable=False),
        sa.Column("reason", sa.String(255), nullable=True),
    )
    op.create_index("ix_blocked_times_date", "blocked_times", ["date"], unique=False)
    op.create_table(
        "appointments",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("customer_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("customers.id"), nullable=False),
        sa.Column("service_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("services.id"), nullable=False),
        sa.Column("start_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("end_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("status", appointment_status, nullable=False, server_default="CONFIRMED"),
        sa.Column("source", appointment_source, nullable=False, server_default="ONLINE"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.UniqueConstraint("customer_id", "start_at", name="uq_customer_start"),
    )
    op.create_index("ix_appointments_customer_id", "appointments", ["customer_id"], unique=False)
    op.create_index("ix_appointments_service_id", "appointments", ["service_id"], unique=False)
    op.create_index("ix_appointments_start_at", "appointments", ["start_at"], unique=False)
    op.execute(
        "ALTER TABLE appointments ADD CONSTRAINT no_active_appointment_overlap "
        "EXCLUDE USING gist (tstzrange(start_at, end_at, '[)') WITH &&) "
        "WHERE (status <> 'CANCELLED')"
    )
    op.create_table(
        "otp_codes",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("phone_number", sa.String(20), nullable=False),
        sa.Column("request_ip_hash", sa.String(128), nullable=False),
        sa.Column("code_digest", sa.String(128), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("attempts", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("consumed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_index("ix_otp_codes_phone_number", "otp_codes", ["phone_number"], unique=False)
    op.create_index("ix_otp_codes_request_ip_hash", "otp_codes", ["request_ip_hash"], unique=False)
    op.create_index("ix_otp_codes_expires_at", "otp_codes", ["expires_at"], unique=False)


def downgrade() -> None:
    op.drop_table("otp_codes")
    op.drop_table("appointments")
    op.drop_table("blocked_times")
    op.drop_table("working_hours")
    op.drop_table("services")
    op.drop_table("customers")
    sa.Enum(name="appointmentsource").drop(op.get_bind(), checkfirst=True)
    sa.Enum(name="appointmentstatus").drop(op.get_bind(), checkfirst=True)