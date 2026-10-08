import os
from datetime import datetime, timezone

from dotenv import load_dotenv
from fastapi import Depends, FastAPI, Header, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.orm import Session

from database import Base, engine, get_db
from models import Telemetry

load_dotenv()


app = FastAPI(title="PawGuard Tracking API", version="0.1.0")


# Local development only.
# Later we will restrict this to your real frontend domain.
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)


Base.metadata.create_all(bind=engine)


class TelemetrySample(BaseModel):
    event_id: str = Field(min_length=1, max_length=64)

    timestamp_ms: int

    timestamp_iso: str | None = None

    lax: float | None = None
    lay: float | None = None
    laz: float | None = None

    roll: float | None = None
    pitch: float | None = None
    yaw: float | None = None

    moving: int | None = None

    session_id: str | None = None
    label: str | None = None
    group: str | None = None


class TelemetryBatch(BaseModel):
    device_id: str = Field(min_length=1, max_length=100)
    samples: list[TelemetrySample] = Field(min_length=1, max_length=500)


def verify_api_token(authorization: str | None = Header(default=None)):
    expected_token = os.getenv("API_TOKEN")

    if not expected_token:
        return

    expected_header = f"Bearer {expected_token}"

    if authorization != expected_header:
        raise HTTPException(status_code=401, detail="Invalid or missing API token")


@app.get("/")
def root():
    return {"status": "PawGuard API is running"}


@app.get("/health")
def health():
    return {"status": "ok"}


@app.post("/api/v1/telemetry/batch", dependencies=[Depends(verify_api_token)])
def receive_telemetry(data: TelemetryBatch, db: Session = Depends(get_db)):
    event_ids = [sample.event_id for sample in data.samples]

    existing_ids = set(
        db.scalars(
            select(Telemetry.event_id).where(Telemetry.event_id.in_(event_ids))
        ).all()
    )

    new_rows = []
    duplicates = 0
    seen_ids = set(existing_ids)

    for sample in data.samples:

        if sample.event_id in seen_ids:
            duplicates += 1
            continue

        seen_ids.add(sample.event_id)

        event_time = datetime.fromtimestamp(sample.timestamp_ms / 1000, tz=timezone.utc)

        new_rows.append(
            Telemetry(
                event_id=sample.event_id,
                device_id=data.device_id,
                event_time=event_time,
                timestamp_ms=sample.timestamp_ms,
                lax=sample.lax,
                lay=sample.lay,
                laz=sample.laz,
                roll=sample.roll,
                pitch=sample.pitch,
                yaw=sample.yaw,
                moving=sample.moving,
                session_id=sample.session_id,
                label=sample.label,
                group=sample.group,
                raw_json=sample.model_dump(mode="json"),
            )
        )

    if new_rows:
        db.add_all(new_rows)
        db.commit()

    return {
        "status": "ok",
        "received": len(data.samples),
        "inserted": len(new_rows),
        "duplicates": duplicates,
    }


@app.get("/api/v1/telemetry", dependencies=[Depends(verify_api_token)])
def get_telemetry(
    device_id: str | None = None,
    limit: int = Query(default=100, ge=1, le=1000),
    db: Session = Depends(get_db),
):
    stmt = select(Telemetry).order_by(Telemetry.event_time.desc()).limit(limit)

    if device_id:
        stmt = stmt.where(Telemetry.device_id == device_id)

    rows = db.scalars(stmt).all()

    return [
        {
            "id": row.id,
            "event_id": row.event_id,
            "device_id": row.device_id,
            "event_time": row.event_time.isoformat(),
            "received_at": row.received_at.isoformat(),
            "timestamp_ms": row.timestamp_ms,
            "lax": row.lax,
            "lay": row.lay,
            "laz": row.laz,
            "roll": row.roll,
            "pitch": row.pitch,
            "yaw": row.yaw,
            "moving": row.moving,
            "session_id": row.session_id,
            "label": row.label,
            "group": row.group,
        }
        for row in rows
    ]
