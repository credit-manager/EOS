from datetime import datetime
from uuid import UUID, uuid4

from sqlalchemy import JSON, Boolean, DateTime, ForeignKey, Integer, String, Text, UniqueConstraint, Uuid, func
from sqlalchemy.orm import Mapped, mapped_column

from ..db import Base


class AnalyticsReport(Base):
    __tablename__ = "analytics_reports"
    __table_args__ = (UniqueConstraint("tenant_id", "code", name="uq_analytics_report_tenant_code"),)

    id: Mapped[UUID] = mapped_column(Uuid, primary_key=True, default=uuid4)
    tenant_id: Mapped[UUID] = mapped_column(
        Uuid, ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False, index=True
    )
    code: Mapped[str] = mapped_column(String(100), nullable=False)
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    entity_code: Mapped[str] = mapped_column(String(100), nullable=False)
    metric: Mapped[str] = mapped_column(String(20), nullable=False)
    field: Mapped[str | None] = mapped_column(String(100), nullable=True)
    conditions_json: Mapped[str | None] = mapped_column(Text, nullable=True)
    group_by: Mapped[str | None] = mapped_column(String(100), nullable=True)
    created_by: Mapped[UUID | None] = mapped_column(
        Uuid, ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())


class ReportRun(Base):
    __tablename__ = "report_runs"

    id: Mapped[UUID] = mapped_column(Uuid, primary_key=True, default=uuid4)
    tenant_id: Mapped[UUID] = mapped_column(
        Uuid, ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False, index=True
    )
    report_id: Mapped[UUID] = mapped_column(
        Uuid, ForeignKey("analytics_reports.id", ondelete="CASCADE"), nullable=False, index=True
    )
    result_json: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict)
    created_by: Mapped[UUID] = mapped_column(Uuid, ForeignKey("users.id", ondelete="RESTRICT"), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class ScheduledReport(Base):
    """Scheduled report execution configuration."""
    __tablename__ = "scheduled_reports"

    id: Mapped[UUID] = mapped_column(Uuid, primary_key=True, default=uuid4)
    tenant_id: Mapped[UUID] = mapped_column(
        Uuid, ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False, index=True
    )
    report_id: Mapped[UUID] = mapped_column(
        Uuid, ForeignKey("analytics_reports.id", ondelete="CASCADE"), nullable=False, index=True
    )
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    frequency: Mapped[str] = mapped_column(String(20), nullable=False)  # daily, weekly, monthly
    day_of_week: Mapped[int | None] = mapped_column(Integer, nullable=True)  # 0=Mon, 6=Sun
    day_of_month: Mapped[int | None] = mapped_column(Integer, nullable=True)  # 1-31
    hour: Mapped[int] = mapped_column(Integer, nullable=False, default=8)
    minute: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    export_format: Mapped[str] = mapped_column(String(10), nullable=False, default="csv")  # csv, pdf
    recipients_json: Mapped[str | None] = mapped_column(Text, nullable=True)  # JSON array of email addresses
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    last_run_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    next_run_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_by: Mapped[UUID | None] = mapped_column(
        Uuid, ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
