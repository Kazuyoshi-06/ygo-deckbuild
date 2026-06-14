from datetime import datetime

from pydantic import BaseModel, ConfigDict

from app.models.enums import SyncStatus, SyncType


class SyncRunOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    sync_type: SyncType
    status: SyncStatus
    started_at: datetime
    finished_at: datetime | None = None
    summary_json: dict | None = None
    error_log: str | None = None
