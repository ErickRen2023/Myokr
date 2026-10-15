from datetime import datetime, timezone
from typing import Optional

from sqlalchemy import BigInteger, Boolean, DateTime, Numeric
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.dialects.mysql import JSON

from app.models.base import Base


class ProgressRecord(Base):
    __tablename__ = "progress_record"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    key_result_id: Mapped[int] = mapped_column(BigInteger, nullable=False)
    value: Mapped[float] = mapped_column(Numeric(10, 2), nullable=False)
    is_achieved: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    target_snapshot: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)
    recorded_at: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, default=lambda: datetime.now(timezone.utc)
    )

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "value": float(self.value),
            "is_achieved": self.is_achieved,
            "target_snapshot": self.target_snapshot,
            "recorded_at": self.recorded_at.isoformat() if self.recorded_at else None,
        }
