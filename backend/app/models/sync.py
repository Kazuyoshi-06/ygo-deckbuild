from datetime import datetime

from sqlalchemy import Enum as SAEnum, Text
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.sql import func
from sqlalchemy.types import JSON

from app.models.base import Base
from app.models.enums import SyncStatus, SyncType


class SyncRun(Base):
    __tablename__ = "sync_runs"

    id: Mapped[int] = mapped_column(primary_key=True)
    sync_type: Mapped[SyncType] = mapped_column(SAEnum(SyncType, name="synctype"))
    status: Mapped[SyncStatus] = mapped_column(SAEnum(SyncStatus, name="syncstatus"), default=SyncStatus.running)
    started_at: Mapped[datetime] = mapped_column(server_default=func.now())
    finished_at: Mapped[datetime | None] = mapped_column()
    summary_json: Mapped[dict | None] = mapped_column(JSON)
    error_log: Mapped[str | None] = mapped_column(Text)
