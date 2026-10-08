from datetime import datetime, timezone

from sqlalchemy import (
    BigInteger,
    DateTime,
    Float,
    Integer,
    JSON,
    String,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column

from database import Base


class Telemetry(Base):
    __tablename__ = "telemetry"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)

    event_id: Mapped[str] = mapped_column(String(64), unique=True, index=True)

    device_id: Mapped[str] = mapped_column(String(100), index=True)

    event_time: Mapped[datetime] = mapped_column(DateTime(timezone=True), index=True)

    received_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)
    )

    timestamp_ms: Mapped[int] = mapped_column(BigInteger)

    lax: Mapped[float | None] = mapped_column(Float, nullable=True)

    lay: Mapped[float | None] = mapped_column(Float, nullable=True)

    laz: Mapped[float | None] = mapped_column(Float, nullable=True)

    roll: Mapped[float | None] = mapped_column(Float, nullable=True)

    pitch: Mapped[float | None] = mapped_column(Float, nullable=True)

    yaw: Mapped[float | None] = mapped_column(Float, nullable=True)

    moving: Mapped[int | None] = mapped_column(Integer, nullable=True)

    session_id: Mapped[str | None] = mapped_column(
        String(100), index=True, nullable=True
    )

    label: Mapped[str | None] = mapped_column(String(100), index=True, nullable=True)

    group: Mapped[str | None] = mapped_column(String(100), nullable=True)

    raw_json: Mapped[dict | None] = mapped_column(JSON, nullable=True)
